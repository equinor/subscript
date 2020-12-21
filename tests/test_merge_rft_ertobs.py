import os
import logging
import shutil
import subprocess

import numpy as np
import pandas as pd

import pytest

from subscript import getLogger
from subscript.merge_rft_ertobs.merge_rft_ertobs import (
    split_wellname_reportstep,
    get_observations,
    merge_rft_ertobs,
)

try:
    # pylint: disable=unused-import
    import ert_shared  # noqa

    HAVE_ERT = True
except ImportError:
    HAVE_ERT = False

logger = getLogger("subscript.merge_rft_ertobs.merge_rft_ertobs")
logger.setLevel(logging.INFO)


@pytest.fixture
def drogondata(tmpdir):
    """Prepare a directory with Drogon testdata"""
    # pylint: disable=unused-argument
    drogondir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "testdata_merge_rft_ertobs/drogon"
    )

    drogondest = os.path.join(tmpdir.strpath, "drogondata")
    shutil.copytree(drogondir, drogondest)
    cwd = os.getcwd()
    os.chdir(drogondest)

    try:
        yield

    finally:
        os.chdir(cwd)


def test_get_observations(drogondata):
    """Try to parse observations"""
    # pylint: disable=redefined-outer-name
    # pylint: disable=unused-argument
    dframe = get_observations("rft")
    expected = pd.DataFrame(
        columns=["order", "well", "report_step", "observed", "error"],
        data=[
            [0, "R_A2", 1, 299.23, 3.0],
            [0, "R_A3", 1, 298.52, 3.0],
            [1, "R_A3", 1, 280.43, 3.0],
            [0, "R_A4", 1, 288.60, 3.0],
            [1, "R_A4", 1, 282.13, 3.0],
            [0, "R_A5", 1, 278.70, 3.0],
            [1, "R_A5", 1, 286.55, 3.0],
            [0, "R_A6", 1, 280.85, 3.0],
            [1, "R_A6", 1, 286.41, 3.0],
        ],
    )
    pd.testing.assert_frame_equal(dframe, expected)


@pytest.mark.parametrize(
    "obsstring, validlength",
    [
        ("", 0),
        ("12", 0),
        ("12  3", 1),
        ("hei", 0),
        ("hei hopp", 0),
        ("12 hei", 0),
        ("hei 3", 0),
        ("3 4 5", 1),  # Extra column is ignored
        ("12 -1", 1),  # Might change later. -1 as error does not make sense
    ],
)
def test_get_observations_invalid(obsstring, validlength, tmpdir):
    """Check observation parsing"""
    tmpdir.chdir()
    with open("foo.obs", "w") as file_h:
        file_h.write(obsstring)
    assert len(get_observations(".")) == validlength


@pytest.mark.parametrize(
    "well_step, expected",
    [
        ("", ("", 1)),
        ("foo", ("foo", 1)),
        ("F_A-3", ("F_A-3", 1)),
        ("F_A-4_1", ("F_A-4", 1)),
        ("F_A-4_2", ("F_A-4", 2)),
        ("A-4", ("A-4", 1)),
        ("A-5_99", ("A-5_99", 1)),  # report steps more than 10 not supported.
        ("R_A4_1", ("R_A4", 1)),
        ("R_A4", ("R_A4", 1)),
        ("R_A_4", ("R_A", 4)),  # Warning, this is probably unintended!
    ],
)
def test_split_wellname_reportstep(well_step, expected):
    assert split_wellname_reportstep(well_step) == expected


def test_merge_drogon(drogondata):
    """Test main merge functionality"""
    # pylint: disable=redefined-outer-name
    # pylint: disable=unused-argument
    dframe = merge_rft_ertobs("gendata_rft.csv", "rft")
    assert not dframe.empty
    assert {"pressure", "observed", "error", "well", "time"}.issubset(dframe.columns)
    assert np.isclose((dframe["observed"] - dframe["pressure"]).abs().mean(), 6.2141156)
    assert set(dframe["error"].values) == {3.0}


def test_merge_drogon_inactive(drogondata):
    """Check that inactive cells are taken care of as such"""
    # Modify simulated data:
    # pylint: disable=redefined-outer-name
    # pylint: disable=unused-argument

    # Modify simulated data:
    gdata = pd.read_csv("gendata_rft.csv")
    gdata.loc[0, "pressure"] = -1.0
    gdata.to_csv("gendata_rft.csv")

    dframe = merge_rft_ertobs("gendata_rft.csv", "rft")
    assert not dframe.empty
    assert {"pressure", "observed", "error", "well", "time"}.issubset(dframe.columns)
    assert sum(dframe["pressure"].isnull()) == 1
    assert not np.isclose(
        (dframe["observed"] - dframe["pressure"]).abs().mean(), 6.2141156
    )


def test_extra_obs_file(drogondata):
    """Test that we will not bail on a stray file"""
    # pylint: disable=redefined-outer-name
    # pylint: disable=unused-argument
    with open("rft/FOO.obs", "w") as file_h:
        file_h.write("FOBOBAR")
    dframe = merge_rft_ertobs("gendata_rft.csv", "rft")
    assert len(dframe) == 9


@pytest.mark.integration
def test_endpoint(drogondata):
    """Test that the endpoint is installed"""
    # pylint: disable=redefined-outer-name
    # pylint: disable=unused-argument
    subprocess.run(
        "merge_rft_ertobs gendata_rft.csv rft --output mergedrft.csv",
        shell=True,
        check=True,
    )
    dframe = pd.read_csv("mergedrft.csv")
    assert not dframe.empty
    assert {
        "pressure",
        "observed",
        "error",
        "well",
        "report_step",
        "report_step",
        "time",
    }.issubset(dframe.columns)


@pytest.mark.integration
@pytest.mark.skipif(not HAVE_ERT, reason="Requires ERT to be installed")
def test_ert_hook(drogondata):
    """Test that the ERT hook can run on a mocked case"""
    # pylint: disable=redefined-outer-name
    # pylint: disable=unused-argument
    with open("DROGON.DATA", "w") as file_h:
        file_h.write("--Empty")
    ert_config = [
        "ECLBASE DROGON.DATA",
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH .",
        (
            "FORWARD_MODEL MERGE_RFT_ERTOBS("
            "<GENDATACSV>=gendata_rft.csv, <OBSDIR>=rft, <OUTPUT>=mergedrft.csv)"
        ),
    ]

    ert_config_fname = "mergetest.ert"
    with open(ert_config_fname, "w") as file_h:
        file_h.write("\n".join(ert_config))

    subprocess.run(["ert", "test_run", ert_config_fname], check=True)

    dframe = pd.read_csv("mergedrft.csv")
    assert not dframe.empty
    assert {"pressure", "observed", "error", "well", "report_step", "time"}.issubset(
        dframe.columns
    )
