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
    main,
)


try:
    # pylint: disable=unused-import
    import ert_shared  # noqa

    HAVE_ERT = True
except ImportError:
    HAVE_ERT = False


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
