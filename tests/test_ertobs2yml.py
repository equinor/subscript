"""Test that ERT observations represented as dataframes can be exported to
other formats, and test the ERT hook"""

import os
import io
import sys
import datetime
import subprocess

import pandas as pd
import yaml

import pytest


from subscript.ertobs2yml.ertobs2yml import (
    df2obsdict,
    df2resinsight_df,
    main,
)


try:
    # pylint: disable=unused-import
    import ert_shared  # noqa

    HAVE_ERT = True
except ImportError:
    HAVE_ERT = False


@pytest.mark.parametrize(
    "obs_df, expected_dict",
    [
        (pd.DataFrame(), {}),
        (pd.DataFrame([{"FOO": "BAR"}]), {}),
        #################################################################
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "KEY": "WOPR:OP1",
                        "DATE": datetime.date(2025, 1, 1),
                    },
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "KEY": "WOPR:OP1",
                        "DATE": datetime.date(2026, 1, 1),
                    },
                ]
            ),
            {
                "smry": [
                    {
                        "key": "WOPR:OP1",
                        "observations": [
                            {"date": "2025-01-01"},
                            {"date": "2026-01-01"},
                        ],
                    }
                ]
            },
        ),
        #################################################################
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "KEY": "WOPR:OP1",
                        "DATE": "2025-01-01",
                    },
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "KEY": "WOPR:OP2",
                        "DATE": "2026-01-01",
                    },
                ]
            ),
            {
                "smry": [
                    {"key": "WOPR:OP1", "observations": [{"date": "2025-01-01"}]},
                    {"key": "WOPR:OP2", "observations": [{"date": "2026-01-01"}]},
                ]
            },
        ),
        #################################################################
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "RFT_2006_OP1",
                        "DATE": "1986-04-05",
                    },
                ]
            ),
            {
                "rft": [
                    {
                        "well": "RFT_2006_OP1",
                        "date": "1986-04-05",
                        "observations": [{}],
                    },
                ]
            },
        ),
        #################################################################
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "RFT_2006_OP1",
                        "DATE": "1986-04-05",
                        "VALUE": 100,
                        "K": 4,
                    },
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "RFT_2006_OP1",
                        "DATE": "1986-04-05",
                        "VALUE": 101,
                        "K": 5,
                    },
                ]
            ),
            {
                "rft": [
                    {
                        "well": "RFT_2006_OP1",
                        "date": "1986-04-05",
                        "observations": [
                            {"k": 4, "value": 100},
                            {"k": 5, "value": 101},
                        ],
                    },
                ]
            },
        ),
    ],
)
def test_df2obsdict(obs_df, expected_dict):
    """Test converting from dataframe representation to the dictionary
    representation designed for yaml output"""
    assert df2obsdict(obs_df) == expected_dict


@pytest.mark.parametrize(
    "obs_df, expected_ri_df",
    [
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "KEY": "WOPR:OP1",
                        "DATE": "2025-01-01",
                        "VALUE": 2222.3,
                        "ERROR": 100,
                    },
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "KEY": "WOPR:OP2",
                        "DATE": "2026-01-01",
                        "VALUE": 222.3,
                        "ERROR": 10,
                    },
                    {
                        # This row triggers a warning and is ignored.
                        "CLASS": "SUMMARY_OBSERVATION",
                        "KEY": "FOPT",
                        "RESTART": 32,
                        "VALUE": 2033320,
                        "ERROR": 1000,
                    },
                    {
                        # This row is not supported by ri, and is ignored.
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "RFT_2006_OP1",
                        "DATE": "1986-04-05",
                        "VALUE": 100,
                        "K": 4,
                    },
                ]
            ),
            pd.DataFrame(
                [
                    {
                        "DATE": "2025-01-01",
                        "VECTOR": "WOPR:OP1",
                        "VALUE": 2222.3,
                        "ERROR": 100.0,
                    },
                    {
                        "DATE": "2026-01-01",
                        "VECTOR": "WOPR:OP2",
                        "VALUE": 222.3,
                        "ERROR": 10,
                    },
                ]
            ),
        )
    ],
)
def test_df2resinsight_df(obs_df, expected_ri_df):
    """Test that we can go from internal dataframe representation
    to the resinsight dataframe representation of observations
    (which only supports a subset of ERT observations)"""
    pd.testing.assert_frame_equal(df2resinsight_df(obs_df), expected_ri_df)


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["ertobs2yml", "-h"])


@pytest.mark.integration
def test_commandline(tmpdir, monkeypatch):
    """Test the executable versus on the ERT doc observation data
    and compare to precomputed CSV and YML.

    When code changes, updates to the CSV and YML might
    be necessary.
    """
    testdata_dir = os.path.join(os.path.dirname(__file__), "testdata_ertobs2yml")
    tmpdir.chdir()
    arguments = [
        "ertobs2yml",
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
        "ertobs2yml",
        "--includedir",
        str(testdata_dir),
        "--csv",
        "-",  # ertobs2yml.__MAGIC_STDOUT__
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
    testdata_dir = os.path.join(os.path.dirname(__file__), "testdata_ertobs2yml")
    obs_file = os.path.join(testdata_dir, "ert-doc.obs")
    tmpdir.chdir()

    with open("FOO.DATA", "w") as file_h:
        file_h.write("--Empty")

    ert_config = [
        "ECLBASE FOO.DATA",
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH .",
        "FORWARD_MODEL ERTOBS2YML(<OBS_FILE>="
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
