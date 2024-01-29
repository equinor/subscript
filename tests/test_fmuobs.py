"""Test that ERT observations represented as dataframes can be exported to
other formats, and test the ERT hook"""

import io
import os
import subprocess
from pathlib import Path

import pandas as pd
import pytest
import yaml
from subscript.fmuobs.fmuobs import autoparse_file, main
from subscript.fmuobs.parsers import ertobs2df, obsdict2df, resinsight_df2df
from subscript.fmuobs.writers import df2ertobs, df2obsdict, df2resinsight_df

TESTDATA_DIR = Path(__file__).absolute().parent / "testdata_fmuobs"

# pylint: disable=unused-argument  # false positive from fixtures


@pytest.fixture(name="readonly_testdata_dir")
def fixture_readonly_testdata_dir():
    """When used as a fixture, the test function will run in the testdata
    directory. Do not write new or temporary files in here"""
    cwd = os.getcwd()
    try:
        os.chdir(TESTDATA_DIR)
        yield
    finally:
        os.chdir(cwd)


@pytest.mark.parametrize(
    "filename, expected_format",
    [
        ("ert-doc.obs", "ert"),
        ("ri-obs.csv", "resinsight"),
        ("ert-doc.yml", "yaml"),
        ("ert-doc.csv", "csv"),
        ("fmu-ensemble-obs.yml", "yaml"),
        ("drogon_wbhp_rft_wct_gor_tracer_4d.obs", "ert"),
    ],
)
def test_autoparse_file(filename, expected_format, readonly_testdata_dir):
    """Test that the included observation file formats in the test suite
    are correctly recognized"""
    assert autoparse_file(filename)[0] == expected_format


@pytest.mark.parametrize(
    "string, expected_format",
    [
        ("", None),
        ("barf", None),
        (";", None),
        # -------------------------------
        ("SMRY_OBSERVATION FOO {VALUE=1;};", None),  # Wrong  CLASSNAME
        ("SUMMARY_OBSERVATION FOO {VALUE=1;};", "ert"),
        ("SUMMARY_OBSERVATION FOO\t{VALUE=1;};", "ert"),
        ("BLOCK_OBSERVATION FOO {VALUE=1;};", "ert"),
        ("GENERAL_OBSERVATION FOO {VALUE=1;};", "ert"),
        ("HISTORY_OBSERVATION FOO {VALUE=1;};", "ert"),  # (invalid though)
        ("HISTORY_OBSERVATION FOPR;", "ert"),
        ("include foo.obs;", "ert"),
        # -------------------------------
        ("CLASS,LABEL", None),  # Empty..
        ("CLASS,LABEL\nA,B", "csv"),  # Must be non-empty
        ("LABEL,CLASS\nA,B", "csv"),
        ("CLASS,label\nA,B", None),
        ("CLASS,LABBEL\nA,B", None),
        # -------------------------------
        ("DATE;VECTOR;VALUE;ERROR", None),  # empty.
        ("DATE,VECTOR,VALUE,ERROR\n1,1,1,1", None),  # Must be semi-column
        ("DATE;VECTOR;VALUE;ERROR\n1;1;1;1", "resinsight"),
        ("DATE;VECTOR;VALUE;ERROR;COMMENT\n1;1;1;1;1", "resinsight"),
        ("DATE;VECTOR;VALUE;ERROR,COMMENT\n1;1;1", None),  # missing data
        ("DATE;VECTOR;VALEU;ERROR\n1;1;1;1", None),  # typo in column header
        # -------------------------------
        ("smry", None),
        ("smry:", None),
        ("rft:", None),
        ("smry: foo", "yaml"),
        ("rft: foo", "yaml"),
    ],
)
def test_autoparse_string(string, expected_format, tmp_path):
    """Test that difficult-to-parse-strings are recognized correctly
    (or not recognized at all). The filetype detector code has very mild
    requirements on dataframe validitiy."""
    os.chdir(tmp_path)
    Path("inputfile.txt").write_text(string, encoding="utf8")
    assert autoparse_file("inputfile.txt")[0] == expected_format


@pytest.mark.parametrize(
    "filename",
    [
        ("ert-doc.obs"),
        ("ri-obs.csv"),
        ("ert-doc.yml"),
        ("ert-doc.csv"),
        ("fmu-ensemble-obs.yml"),
        ("drogon_wbhp_rft_wct_gor_tracer_4d.obs"),
    ],
)
def test_roundtrip_ertobs(filename, readonly_testdata_dir):
    """Test converting all included test data sets into ERT observations
    (as strings) and then parsing it, ensuring that we end up in the
    same place"""
    dframe = autoparse_file(filename)[1]

    # Convert to ERT obs format and back again:
    ertobs_str = df2ertobs(dframe)
    ert_roundtrip_dframe = ertobs2df(ertobs_str)
    ert_roundtrip_dframe.set_index("CLASS", inplace=True)
    dframe.set_index("CLASS", inplace=True)

    # This big loop is only here to aid in debugging when
    # the dataframes do not match, asserting equivalence of
    # subframes
    for _class in dframe.index.unique():
        roundtrip_subframe = (
            ert_roundtrip_dframe.loc[[_class]]
            .dropna(axis=1, how="all")
            .sort_index(axis=1)
        )
        subframe = dframe.loc[[_class]].dropna(axis=1, how="all").sort_index(axis=1)
        roundtrip_subframe.set_index(
            list(
                {"CLASS", "LABEL", "OBS", "SEGMENT"}.intersection(
                    set(roundtrip_subframe.columns)
                )
            ),
            inplace=True,
        )
        roundtrip_subframe.sort_index(inplace=True)
        subframe.set_index(
            list(
                {"CLASS", "LABEL", "OBS", "SEGMENT"}.intersection(set(subframe.columns))
            ),
            inplace=True,
        )
        subframe.sort_index(inplace=True)
        # Comments are not preservable through ertobs roundtrips:
        subframe.drop(
            ["COMMENT", "SUBCOMMENT"], axis="columns", errors="ignore", inplace=True
        )
        if _class == "BLOCK_OBSERVATION" and "WELL" in subframe:
            # WELL as used in yaml is not preservable in roundtrips
            del subframe["WELL"]
        # print(roundtrip_subframe)
        # print(subframe)

        pd.testing.assert_frame_equal(
            roundtrip_subframe.sort_index(),
            subframe.sort_index(),
            check_dtype=False,
        )
        # check_dtype is turned off to avoid integer vs. floating dtype
        # differences, which we really cannot preserve properly.


@pytest.mark.parametrize(
    "filename",
    [
        ("ert-doc.obs"),
        ("ri-obs.csv"),
        ("ert-doc.yml"),
        ("ert-doc.csv"),
        ("fmu-ensemble-obs.yml"),
        ("drogon_wbhp_rft_wct_gor_tracer_4d.obs"),
    ],
)
def test_roundtrip_yaml(filename, readonly_testdata_dir):
    """Test converting all test data sets in testdir into yaml and back again.

    Due to yaml supporting a subset of features in the internal dataframe format
    some exceptions must be hardcoded in this test function.

    Also pay attention to the way the yaml parser creates LABEL data.
    """
    dframe = autoparse_file(filename)[1]

    # Reduce to the subset supported by yaml:
    dframe = dframe[
        (dframe["CLASS"] == "SUMMARY_OBSERVATION")
        | (dframe["CLASS"] == "BLOCK_OBSERVATION")
    ].dropna(axis="columns", how="all")
    # Convert to YAML (really dict) format and back again:
    obsdict = df2obsdict(dframe)
    yaml_roundtrip_dframe = obsdict2df(obsdict)
    yaml_roundtrip_dframe.set_index("CLASS", inplace=True)
    dframe.set_index("CLASS", inplace=True)
    if "WELL" in yaml_roundtrip_dframe:
        # WELL as used in yaml is not preservable in roundtrips
        del yaml_roundtrip_dframe["WELL"]
    if "WELL" in dframe:
        del dframe["WELL"]
    # print(yaml_roundtrip_dframe)
    # print(dframe)
    pd.testing.assert_frame_equal(
        yaml_roundtrip_dframe.sort_index(axis="columns").sort_values("LABEL"),
        dframe.sort_index(axis="columns").sort_values("LABEL"),
        check_like=True,
    )


@pytest.mark.parametrize(
    "filename",
    [
        ("ert-doc.obs"),
        ("ri-obs.csv"),
        ("ert-doc.yml"),
        ("ert-doc.csv"),
        ("fmu-ensemble-obs.yml"),
        ("drogon_wbhp_rft_wct_gor_tracer_4d.obs"),
    ],
)
def test_roundtrip_resinsight(filename, readonly_testdata_dir):
    """Test converting all test data sets in testdir into resinsight and back again.

    ResInsight only supports SUMMARY_OBSERVATION.
    """
    dframe = autoparse_file(filename)[1]

    # Reduce to the subset supported by yaml:
    dframe = dframe[dframe["CLASS"] == "SUMMARY_OBSERVATION"].dropna(
        axis="columns", how="all"
    )
    # Drop observations with no date:
    dframe = dframe[~dframe["DATE"].isna()].dropna(axis=1, how="all")

    # Convert to ResInsight dataframe format and back again:
    ri_dframe = df2resinsight_df(dframe)
    ri_roundtrip_dframe = resinsight_df2df(ri_dframe)

    # LABEL is not part of the ResInsight format, and a made-up label
    # is obtained through the roundtrip (when importing back). Skip it
    # when comparing.

    pd.testing.assert_frame_equal(
        ri_roundtrip_dframe.sort_index(axis="columns").drop(
            ["LABEL", "COMMENT", "SUBCOMMENT"], axis="columns", errors="ignore"
        ),
        dframe.sort_index(axis="columns").drop(
            ["LABEL", "COMMENT", "SUBCOMMENT"], axis="columns", errors="ignore"
        ),
        check_like=True,
    )


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["fmuobs", "-h"])


@pytest.mark.integration
@pytest.mark.parametrize("verbose", ["", "--verbose", "--debug"])
def test_commandline(tmp_path, verbose, mocker, caplog):
    """Test the executable versus on the ERT doc observation data
    and compare to precomputed CSV and YML.

    When code changes, updates to the CSV and YML might
    be necessary.
    """
    os.chdir(tmp_path)
    mocker.patch(
        "sys.argv",
        list(
            filter(
                None,
                [
                    # [
                    "fmuobs",
                    "--includedir",
                    str(TESTDATA_DIR),
                    verbose,
                    "--csv",
                    "output.csv",
                    "--yml",
                    "output.yml",
                    "--resinsight",
                    "ri_output.csv",
                    str(TESTDATA_DIR / "ert-doc.obs"),
                ],
            )
        ),
    )
    main()
    assert Path("output.csv").exists()
    assert Path("output.yml").exists()
    assert Path("ri_output.csv").exists()

    if verbose == "--verbose":
        # This is from the logger "subscript.fmuobs":
        assert "Observation dataframe validated" in caplog.text
        assert "Injecting include file" in caplog.text
    elif verbose == "--debug":
        # This is from the logger "subscript.fmuobs.parsers":
        assert "Parsing observation" in caplog.text
    else:
        assert "Observation dataframe validated" not in caplog.text
        assert "Injecting include file" not in caplog.text
        assert "Parsing observation" not in caplog.text

    dframe_from_csv_on_disk = pd.read_csv("output.csv")
    reference_dframe_from_disk = pd.read_csv(TESTDATA_DIR / "ert-doc.csv")
    pd.testing.assert_frame_equal(
        dframe_from_csv_on_disk.sort_index(axis=1),
        reference_dframe_from_disk.sort_index(axis=1),
    )

    dict_from_yml_on_disk = yaml.safe_load(
        Path("output.yml").read_text(encoding="utf8")
    )
    reference_dict_from_yml = yaml.safe_load(
        (TESTDATA_DIR / "ert-doc.yml").read_text(encoding="utf8")
    )
    assert dict_from_yml_on_disk == reference_dict_from_yml

    ri_from_csv_on_disk = pd.read_csv("ri_output.csv")
    reference_ri_from_disk = pd.read_csv(TESTDATA_DIR / "ri-obs.csv")
    pd.testing.assert_frame_equal(
        # Enforce correct column order
        ri_from_csv_on_disk,
        reference_ri_from_disk,
    )

    # Test CSV to stdout:
    arguments = [
        "fmuobs",
        "--includedir",
        str(TESTDATA_DIR),
        "--csv",
        "-",  # fmuobs.__MAGIC_STDOUT__
        str(TESTDATA_DIR / "ert-doc.obs"),
    ]
    run_result = subprocess.run(arguments, check=True, stdout=subprocess.PIPE)
    dframe_from_stdout = pd.read_csv(io.StringIO(run_result.stdout.decode("utf-8")))
    # pylint: disable=no-member  # false positive on Pandas object
    pd.testing.assert_frame_equal(
        dframe_from_stdout.sort_index(axis=1),
        reference_dframe_from_disk.sort_index(axis=1),
    )


@pytest.mark.integration
@pytest.mark.parametrize("verbose", ["", '"--verbose"', '"--debug"'])
def test_ert_workflow_hook(verbose, tmp_path):
    """Mock an ERT config with FMUOBS as a workflow and run it"""
    # pylint: disable=redefined-outer-name
    # pylint: disable=unused-argument
    obs_file = TESTDATA_DIR / "ert-doc.obs"
    os.chdir(tmp_path)

    Path("FOO.DATA").write_text("--Empty", encoding="utf8")

    Path("wf_fmuobs").write_text(
        "FMUOBS "
        + verbose
        + " "
        + str(obs_file)
        + ' "--yaml" ert-obs.yml "--resinsight" ri-obs.csv "--includedir" '
        + str(TESTDATA_DIR)
        + "\n",
        encoding="utf8",
    )

    ert_config = [
        "ECLBASE FOO.DATA",
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH <CONFIG_PATH>",
        "LOAD_WORKFLOW wf_fmuobs",
        "HOOK_WORKFLOW wf_fmuobs PRE_SIMULATION",
    ]

    ert_config_fname = "test.ert"
    Path(ert_config_fname).write_text("\n".join(ert_config), encoding="utf8")

    subprocess.run(["ert", "test_run", ert_config_fname], check=True)

    assert Path("ert-obs.yml").exists()
    assert Path("ri-obs.csv").exists()

    # Verify that we can control whether INFO messages from fmuobs through ERT
    # is emitted.
    log_file = next(Path("logs").glob("ert-log*txt"))
    ert_output = log_file.read_text(encoding="utf-8")

    # This is slightly tricky, as ERT has its own logging handler which is able
    # to pick up the log messages, but whose level cannot be controlled by
    # the fmuobs.py file. Thus, we test on the exact subscript logger format:
    if verbose == "--verbose":
        assert "INFO:subscript.fmuobs.parsers:Injecting include file" in ert_output
    elif verbose == "--debug":
        assert (
            "DEBUG:subscript.fmuobs.parsers:"
            "Parsing observation SUMMARY_OBSERVATION SEP_TEST_2005" in ert_output
        )
    else:
        assert "INFO:subscript.fmuobs.parsers:Injecting include file" not in ert_output
