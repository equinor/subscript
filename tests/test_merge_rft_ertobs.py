import logging
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from subscript import getLogger
from subscript.merge_rft_ertobs.merge_rft_ertobs import (
    get_observations,
    merge_rft_ertobs,
    split_wellname_reportstep,
)

# pylint: disable=unused-argument  # false positive on fixtures

try:
    # pylint: disable=unused-import
    import ert.shared  # noqa

    HAVE_ERT = True
except ImportError:
    HAVE_ERT = False

logger = getLogger("subscript.merge_rft_ertobs.merge_rft_ertobs")
logger.setLevel(logging.INFO)


@pytest.fixture(name="drogondata")
def fixture_drogondata(tmp_path):
    """Prepare a directory with Drogon testdata"""
    drogondir = Path(__file__).absolute().parent / "testdata_merge_rft_ertobs/drogon"
    drogondest = tmp_path / "drogondata"
    shutil.copytree(drogondir, drogondest)
    cwd = os.getcwd()
    os.chdir(drogondest)

    try:
        yield

    finally:
        os.chdir(cwd)


def test_invalid_obsdir():
    """Test exception when obsdir is not valid"""
    with pytest.raises(ValueError, match="Observation directory"):
        get_observations("/path/to/random/non-existing/directory")


def test_get_observations(drogondata):
    """Try to parse observations"""
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
def test_get_observations_invalid(obsstring, validlength, tmp_path):
    """Check observation parsing"""
    os.chdir(tmp_path)
    Path("foo.obs").write_text(obsstring, encoding="utf8")
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
    """Check splitting of reportsteps out from wellnames"""
    assert split_wellname_reportstep(well_step) == expected


def test_merge_drogon(drogondata):
    """Test main merge functionality"""
    dframe = merge_rft_ertobs("gendata_rft.csv", "rft")
    assert not dframe.empty
    assert {"pressure", "observed", "error", "well", "time"}.issubset(dframe.columns)
    assert np.isclose((dframe["observed"] - dframe["pressure"]).abs().mean(), 6.2141156)
    assert set(dframe["error"].values) == {3.0}


def test_merge_drogon_inactive(drogondata):
    """Check that inactive cells are taken care of as such"""
    # Modify simulated data:
    gdata = pd.read_csv("gendata_rft.csv")
    # pylint: disable=no-member  # false positive on Pandas objects
    gdata.loc[0, "pressure"] = -1.0
    gdata.to_csv("gendata_rft.csv")

    dframe = merge_rft_ertobs("gendata_rft.csv", "rft")
    assert not dframe.empty
    assert {"pressure", "observed", "error", "well", "time"}.issubset(dframe.columns)
    assert sum(dframe["pressure"].isnull()) == 1
    assert not np.isclose(
        (dframe["observed"] - dframe["pressure"]).abs().mean(), 6.2141156
    )


def test_merge_drogon_missing_observation(drogondata):
    """Check that missing observation points are taken care of as such"""
    # Modify observation data:
    Path("rft/R_A2.obs").write_text("-1.0  0.00", encoding="utf8")
    dframe = merge_rft_ertobs("gendata_rft.csv", "rft")
    assert not dframe.empty
    assert {"pressure", "observed", "error", "well", "time"}.issubset(dframe.columns)
    assert sum(dframe["observed"].isnull()) == 1
    assert not np.isclose(
        (dframe["observed"] - dframe["pressure"]).abs().mean(), 6.2141156
    )


def test_merge_multiple_timesteps(tmp_path):
    """Check that multiple timesteps is handled properly"""
    os.chdir(tmp_path)
    Path("R_A2_1.obs").write_text("299.230  3.000", encoding="utf8")
    Path("R_A2_2.obs").write_text("289.120  3.000", encoding="utf8")
    df_gendata = pd.DataFrame(
        columns=[
            "order",
            "utm_x",
            "utm_y",
            "measured_depth",
            "true_vertical_depth",
            "zone",
            "pressure",
            "valid_zone",
            "is_active",
            "i",
            "j",
            "k",
            "well",
            "time",
            "report_step",
        ],
        data=[
            [
                0,
                460994.9,
                5933813.29,
                1697.9,
                1648.9,
                "Valysar",
                297.59930419921875,
                True,
                True,
                21,
                29,
                2,
                "R_A2",
                "2018-03-01",
                1,
            ],
            [
                0,
                460994.9,
                5933813.29,
                1697.9,
                1648.9,
                "Valysar",
                287.19930419921875,
                True,
                True,
                21,
                29,
                2,
                "R_A2",
                "2019-03-01",
                2,
            ],
        ],
    )
    df_gendata.to_csv("gendata_rft.csv", index=False)
    dframe = merge_rft_ertobs("gendata_rft.csv", ".")
    assert not dframe.empty
    assert {"pressure", "observed", "error", "well", "report_step", "time"}.issubset(
        dframe.columns
    )
    assert len(dframe) == 2


def test_extra_obs_file(drogondata):
    """Test that we will not bail on a stray file"""
    Path("rft/FOO.obs").write_text("FOBOBAR", encoding="utf8")
    dframe = merge_rft_ertobs("gendata_rft.csv", "rft")
    assert len(dframe) == 9


@pytest.mark.integration
def test_endpoint(drogondata):
    """Test that the endpoint is installed"""
    subprocess.run(
        "merge_rft_ertobs gendata_rft.csv rft --output mergedrft.csv",
        shell=True,
        check=True,
    )
    dframe = pd.read_csv("mergedrft.csv")
    assert not dframe.empty
    # pylint: disable=no-member  # false positive on Pandas objects
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
    Path("DROGON.DATA").write_text("--Empty", encoding="utf8")
    ert_config = [
        "ECLBASE DROGON.DATA",
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH <CONFIG_PATH>",
        (
            "FORWARD_MODEL MERGE_RFT_ERTOBS("
            "<GENDATACSV>=gendata_rft.csv, <OBSDIR>=rft, <OUTPUT>=mergedrft.csv)"
        ),
    ]

    ert_config_fname = "mergetest.ert"
    Path(ert_config_fname).write_text("\n".join(ert_config), encoding="utf8")

    subprocess.run(["ert", "test_run", ert_config_fname], check=True)

    dframe = pd.read_csv("mergedrft.csv")
    # pylint: disable=no-member  # false positive on Pandas objects
    assert not dframe.empty
    assert {"pressure", "observed", "error", "well", "report_step", "time"}.issubset(
        dframe.columns
    )
