"""Test that ERT observations represented as dataframes can be exported to
other formats, and test the ERT hook"""

import os
import io
import sys
import subprocess

import pandas as pd
import yaml

import pytest


from subscript.ertobs.ertobs import (
    autoparse_file,
    main,
)

from subscript.ertobs.parsers import ertobs2df, obsdict2df
from subscript.ertobs.writers import df2ertobs, df2obsdict


try:
    # pylint: disable=unused-import
    import ert_shared  # noqa

    HAVE_ERT = True
except ImportError:
    HAVE_ERT = False


@pytest.mark.parametrize(
    "filename, expected_format",
    [
        ("ert-doc.obs", "ert"),
        ("ri-obs.csv", "resinsight"),
        ("ert-doc.yml", "yaml"),
        ("ert-doc.csv", "csv"),
    ],
)
def test_autoparse_file(filename, expected_format):
    """Test that the included observation file formats in the test suite
    are correctly recognized"""
    testdata_dir = os.path.join(os.path.dirname(__file__), "testdata_ertobs")
    os.chdir(testdata_dir)
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
def test_autoparse_string(string, expected_format, tmpdir):
    """Test that difficult-to-parse-strings are recognized correctly
    (or not recognized at all). The filetype detector code has very mild
    requirements on dataframe validitiy."""
    tmpdir.chdir()
    with open("inputfile.txt", "w") as f_handle:
        f_handle.write(string)
    assert autoparse_file("inputfile.txt")[0] == expected_format


@pytest.mark.parametrize(
    "filename, orig_format",
    [
        ("ert-doc.obs", "ert"),
        ("ri-obs.csv", "resinsight"),
        ("ert-doc.yml", "yaml"),
        ("ert-doc.csv", "csv"),
    ],
)
def test_roundtrip_ertobs(filename, orig_format):
    testdata_dir = os.path.join(os.path.dirname(__file__), "testdata_ertobs")
    os.chdir(testdata_dir)
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
        if _class == "BLOCK_OBSERVATION":
            if "WELL" in subframe:
                # WELL as used in yaml is not preservable in roundtrips
                del subframe["WELL"]
        pd.testing.assert_frame_equal(roundtrip_subframe, subframe, check_dtype=False)
        # check_dtype is turned off to avoid integer vs. floating dtype
        # differences, which we really cannot preserve properly.


@pytest.mark.parametrize(
    "filename, orig_format",
    [
        ("ert-doc.obs", "ert"),
        ("ri-obs.csv", "resinsight"),
        ("ert-doc.yml", "yaml"),
        ("ert-doc.csv", "csv"),
    ],
)
def test_roundtrip_yaml(filename, orig_format):
    testdata_dir = os.path.join(os.path.dirname(__file__), "testdata_ertobs")
    os.chdir(testdata_dir)
    dframe = autoparse_file(filename)[1]

    # Reduce to the subset supported by yaml:
    dframe = dframe[
        (dframe["CLASS"] == "SUMMARY_OBSERVATION")
        | (dframe["CLASS"] == "BLOCK_OBSERVATION")
    ].dropna(axis="columns", how="all")
    # Convert to ERT obs format and back again:
    obsdict = df2obsdict(dframe)
    yaml_roundtrip_dframe = obsdict2df(obsdict)
    yaml_roundtrip_dframe.set_index("CLASS", inplace=True)
    dframe.set_index("CLASS", inplace=True)
    if "WELL" in yaml_roundtrip_dframe:
        # WELL as used in yaml is not preservable in roundtrips
        del yaml_roundtrip_dframe["WELL"]
    if "WELL" in dframe:
        del dframe["WELL"]
    pd.testing.assert_frame_equal(yaml_roundtrip_dframe, dframe, check_like=True)


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["ertobs", "-h"])


@pytest.mark.integration
def test_commandline(tmpdir, monkeypatch):
    """Test the executable versus on the ERT doc observation data
    and compare to precomputed CSV and YML.

    When code changes, updates to the CSV and YML might
    be necessary.
    """
    testdata_dir = os.path.join(os.path.dirname(__file__), "testdata_ertobs")
    tmpdir.chdir()
    arguments = [
        "ertobs",
        "--includedir",
        str(testdata_dir),
        "--verbose",
        "--csv",
        "output.csv",
        "--yml",
        "output.yml",
        "--resinsight",
        "ri_output.csv",
        os.path.join(testdata_dir, "ert-doc.obs"),
    ]
    monkeypatch.setattr(sys, "argv", arguments)
    main()
    assert os.path.exists("output.csv")
    assert os.path.exists("output.yml")
    assert os.path.exists("ri_output.csv")
    dframe_from_csv_on_disk = pd.read_csv("output.csv")
    reference_dframe_from_disk = pd.read_csv(os.path.join(testdata_dir, "ert-doc.csv"))
    pd.testing.assert_frame_equal(
        dframe_from_csv_on_disk.sort_index(axis=1),
        reference_dframe_from_disk.sort_index(axis=1),
    )

    dict_from_yml_on_disk = yaml.safe_load(open("output.yml"))
    reference_dict_from_yml = yaml.safe_load(
        open(os.path.join(testdata_dir, "ert-doc.yml"))
    )
    assert dict_from_yml_on_disk == reference_dict_from_yml

    ri_from_csv_on_disk = pd.read_csv("ri_output.csv")
    reference_ri_from_disk = pd.read_csv(os.path.join(testdata_dir, "ri-obs.csv"))
    pd.testing.assert_frame_equal(
        # Enforce correct column order
        ri_from_csv_on_disk,
        reference_ri_from_disk,
    )

    # Test CSV to stdout:
    arguments = [
        "ertobs",
        "--includedir",
        str(testdata_dir),
        "--csv",
        "-",  # ertobs.__MAGIC_STDOUT__
        os.path.join(testdata_dir, "ert-doc.obs"),
    ]
    run_result = subprocess.run(arguments, check=True, stdout=subprocess.PIPE)
    dframe_from_stdout = pd.read_csv(io.StringIO(run_result.stdout.decode("utf-8")))
    pd.testing.assert_frame_equal(
        dframe_from_stdout.sort_index(axis=1),
        reference_dframe_from_disk.sort_index(axis=1),
    )


@pytest.mark.integration
@pytest.mark.skipif(not HAVE_ERT, reason="Requires ERT to be installed")
def test_ert_hook(tmpdir):
    """Mock an ERT config with ERTOBS2YML as a FORWARD_MODEL and run it"""
    # pylint: disable=redefined-outer-name
    # pylint: disable=unused-argument
    testdata_dir = os.path.join(os.path.dirname(__file__), "testdata_ertobs")
    obs_file = os.path.join(testdata_dir, "ert-doc.obs")
    tmpdir.chdir()

    with open("FOO.DATA", "w") as file_h:
        file_h.write("--Empty")

    ert_config = [
        "ECLBASE FOO.DATA",
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH .",
        "FORWARD_MODEL ERTOBS(<INPUT_FILE>="
        + obs_file
        + ", "
        + "<CSV_OUTPUT>=ert-obs.csv, "
        + "<YML_OUTPUT>=ert-obs.yml, "
        + "<RESINSIGHT_OUTPUT>=ri-obs.csv, "
        + "<INCLUDEDIR>="
        + testdata_dir
        + ")",  # noqa
    ]

    ert_config_fname = "test.ert"
    with open(ert_config_fname, "w") as file_h:
        file_h.write("\n".join(ert_config))

    subprocess.run(["ert", "test_run", ert_config_fname], check=True)

    assert os.path.exists("ert-obs.csv")
    assert os.path.exists("ert-obs.yml")
    assert os.path.exists("ri-obs.csv")
