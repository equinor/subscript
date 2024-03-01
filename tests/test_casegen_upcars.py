"""Test that casegen_upcars is installed and launched with given demo cases"""

import os
import shutil
import subprocess
from pathlib import Path

import opm.io
import pandas as pd
import pytest
from subscript.casegen_upcars import casegen_upcars

TESTDATA = "testdata_casegen_upcars"
DATADIR = Path(__file__).absolute().parent / TESTDATA

# pylint: disable=no-member  # false positive on Pandas dataframe


@pytest.mark.integration
def test_installed():
    """Test that the endpoint is installed, use -h as it required one parameter"""
    assert subprocess.check_output(["casegen_upcars", "-h"])


def test_demo_small_scale(tmp_path, mocker):
    """Test casegen_upcars on demo_small_scale.yaml"""
    shutil.copytree(DATADIR, tmp_path / TESTDATA)
    os.chdir(tmp_path / TESTDATA)

    base_name = "TEST_SMALL"
    mocker.patch(
        "sys.argv",
        [
            "casegen_upcars",
            "demo_small_scale.yaml",
            "--et",
            "dump_value.tmpl",
            "--base",
            base_name,
        ],
    )
    casegen_upcars.main()

    # check that all output files are generated
    for pre, suf in zip(
        ["", "fipnum_", "gridinc_", "satnum_", "swat_"],
        [".DATA", ".INC", ".GRDECL", ".INC", ".INC"],
    ):
        assert Path(pre + base_name + suf).exists()
        if suf != ".DATA":
            assert opm.io.Parser().parse(pre + base_name + suf)

    # check some key parameters in output file
    data_frame = pd.read_csv(base_name + ".DATA", index_col=0)
    assert data_frame.Values["nx"] == 53
    assert data_frame.Values["ny"] == 53
    assert data_frame.Values["nz"] == 50
    assert data_frame.Values["lx"] == 4.15
    assert data_frame.Values["ly"] == 4.15
    assert data_frame.Values["lz"] == 1.03
    assert data_frame.Values["poro"] == 0.0912


def test_demo_small_scale_with_no_streaks(tmp_path, mocker):
    """Test casegen_upcars on demo_small_scale.yaml"""
    shutil.copytree(DATADIR, tmp_path / TESTDATA)
    os.chdir(tmp_path / TESTDATA)

    base_name = "TEST_SMALL_NO_STREAKS"
    mocker.patch(
        "sys.argv",
        [
            "casegen_upcars",
            "demo_small_scale.yaml",
            "--et",
            "dump_value.tmpl",
            "--base",
            base_name,
        ],
    )
    casegen_upcars.main()

    # check that all output files are generated
    for pre, suf in zip(
        ["", "fipnum_", "gridinc_", "satnum_", "swat_"],
        [".DATA", ".INC", ".GRDECL", ".INC", ".INC"],
    ):
        assert Path(pre + base_name + suf).exists()
        if suf != ".DATA":
            assert opm.io.Parser().parse(pre + base_name + suf)

    # check some key parameters in output file
    data_frame = pd.read_csv(base_name + ".DATA", index_col=0)
    assert data_frame.Values["nx"] == 53
    assert data_frame.Values["ny"] == 53
    assert data_frame.Values["nz"] == 50
    assert data_frame.Values["lx"] == 4.15
    assert data_frame.Values["ly"] == 4.15
    assert data_frame.Values["lz"] == 1.03
    assert data_frame.Values["poro"] == 0.0912


def test_demo_small_scale_with_vugs(tmp_path, mocker):
    """Test casegen_upcars on demo_small_scale.yaml with random vugs"""
    shutil.copytree(DATADIR, tmp_path / TESTDATA)
    os.chdir(tmp_path / TESTDATA)

    base_name = "TEST_SMALL_WITH_VUGS"
    mocker.patch(
        "sys.argv",
        [
            "casegen_upcars",
            "demo_small_scale.yaml",
            "--et",
            "dump_value.tmpl",
            "--vug1Volume",
            "0.1",
            "0.1",
            "--vug2Volume",
            "0.1",
            "0.1",
            "--vug3Volume",
            "0.1",
            "0.1",
            "--base",
            base_name,
        ],
    )
    casegen_upcars.main()

    # check that all output files are generated
    for pre, suf in zip(
        ["", "fipnum_", "gridinc_", "satnum_", "swat_"],
        [".DATA", ".INC", ".GRDECL", ".INC", ".INC"],
    ):
        assert Path(pre + base_name + suf).exists()
        if suf != ".DATA":
            assert opm.io.Parser().parse(pre + base_name + suf)

    # check some key parameters in output file
    data_frame = pd.read_csv(base_name + ".DATA", index_col=0)
    assert data_frame.Values["nx"] == 53
    assert data_frame.Values["ny"] == 53
    assert data_frame.Values["nz"] == 50
    assert data_frame.Values["lx"] == 4.15
    assert data_frame.Values["ly"] == 4.15
    assert data_frame.Values["lz"] == 1.03
    assert data_frame.Values["poro"] == 0.1749


def test_demo_large_scale(tmp_path, mocker):
    """Test casegen_upcars on demo_large_scale.yaml"""
    shutil.copytree(DATADIR, tmp_path / TESTDATA)
    os.chdir(tmp_path / TESTDATA)

    base_name = "TEST_LARGE"
    mocker.patch(
        "sys.argv",
        [
            "casegen_upcars",
            "demo_large_scale.yaml",
            "--et",
            "dump_value.tmpl",
            "--base",
            base_name,
        ],
    )
    casegen_upcars.main()

    # check that all output files are generated
    for pre, suf in zip(
        ["", "fipnum_", "gridinc_", "satnum_", "swat_"],
        [".DATA", ".INC", ".GRDECL", ".INC", ".INC"],
    ):
        assert Path(pre + base_name + suf).exists()
        if suf != ".DATA":
            assert opm.io.Parser().parse(str(pre + base_name + suf))

    # check some key parameters in output file
    data_frame = pd.read_csv(base_name + ".DATA", index_col=0)
    assert data_frame.Values["nx"] == 77
    assert data_frame.Values["ny"] == 72
    assert data_frame.Values["nz"] == 27
    assert data_frame.Values["lx"] == 7700.0
    assert data_frame.Values["ly"] == 7200.0
    assert data_frame.Values["lz"] == 355.0
    assert data_frame.Values["poro"] == 0.1711


def test_demo_large_scale_with_coordinate_transformation(tmp_path, mocker):
    """Test casegen_upcars on demo_large_scale.yaml with coordinate transformation"""
    shutil.copytree(DATADIR, tmp_path / TESTDATA)
    os.chdir(tmp_path / TESTDATA)

    base_name = "TEST_LARGE_WITH_TRANFORMATION"
    mocker.patch(
        "sys.argv",
        [
            "casegen_upcars",
            "demo_large_scale.yaml",
            "--et",
            "dump_value.tmpl",
            "--originX",
            "1000.0",
            "--originY",
            "2000.0",
            "--rotation",
            "15",
            "--base",
            base_name,
        ],
    )
    casegen_upcars.main()

    # check that all output files are generated
    for pre, suf in zip(
        ["", "fipnum_", "gridinc_", "satnum_", "swat_"],
        [".DATA", ".INC", ".GRDECL", ".INC", ".INC"],
    ):
        assert Path(pre + base_name + suf).exists()
        if suf != ".DATA":
            assert opm.io.Parser().parse(str(pre + base_name + suf))

    # check some key parameters in output file
    data_frame = pd.read_csv(base_name + ".DATA", index_col=0)
    assert data_frame.Values["nx"] == 77
    assert data_frame.Values["ny"] == 72
    assert data_frame.Values["nz"] == 27
    assert data_frame.Values["lx"] == 7700.0
    assert data_frame.Values["ly"] == 7200.0
    assert data_frame.Values["lz"] == 355.0
    assert data_frame.Values["poro"] == 0.1711
    assert data_frame.Values["originX"] == 1000.0
    assert data_frame.Values["originY"] == 2000.0
    assert data_frame.Values["rotation"] == 15.0


def test_demo_large_scale_with_origin_shifting(tmp_path, mocker):
    """Test casegen_upcars on demo_large_scale.yaml with coordinate transformation"""
    shutil.copytree(DATADIR, tmp_path / TESTDATA)
    os.chdir(tmp_path / TESTDATA)

    base_name = "TEST_LARGE_WITH_ORIGIN_SHIFTING"
    mocker.patch(
        "sys.argv",
        [
            "casegen_upcars",
            "demo_large_scale.yaml",
            "--et",
            "dump_value.tmpl",
            "--origin_x_pos",
            "0.1",
            "--origin_y_pos",
            "0.8",
            "--origin_top",
            "1000.0",
            "--base",
            base_name,
        ],
    )
    casegen_upcars.main()

    # check that all output files are generated
    for pre, suf in zip(
        ["", "fipnum_", "gridinc_", "satnum_", "swat_"],
        [".DATA", ".INC", ".GRDECL", ".INC", ".INC"],
    ):
        assert Path(pre + base_name + suf).exists()
        if suf != ".DATA":
            assert opm.io.Parser().parse(str(pre + base_name + suf))

    # check some key parameters in output file
    data_frame = pd.read_csv(base_name + ".DATA", index_col=0)
    assert data_frame.Values["nx"] == 77
    assert data_frame.Values["ny"] == 72
    assert data_frame.Values["nz"] == 27
    assert data_frame.Values["lx"] == 7700.0
    assert data_frame.Values["ly"] == 7200.0
    assert data_frame.Values["lz"] == 355.0
    assert data_frame.Values["poro"] == 0.1711
    assert data_frame.Values["originX"] == 0.0
    assert data_frame.Values["originY"] == 0.0
    assert data_frame.Values["rotation"] == 0.0
    assert data_frame.Values["top"] == 1000.0
    assert data_frame.Values["bottom"] == 1355.0


def test_demo_large_scale_with_cmdline_streaks(tmp_path, mocker):
    """Test casegen_upcars on demo_large_scale.yaml with some streaks"""
    shutil.copytree(DATADIR, tmp_path / TESTDATA)
    os.chdir(tmp_path / TESTDATA)

    base_name = "TEST_LARGE_WITH_STREAKS"
    mocker.patch(
        "sys.argv",
        [
            "casegen_upcars",
            "demo_large_scale.yaml",
            "--et",
            "dump_value.tmpl",
            "--streak_box",
            "1",
            "77",
            "1",
            "72",
            "--streak_nz",
            "10",
            "--base",
            base_name,
        ],
    )
    casegen_upcars.main()

    # check that all output files are generated
    for pre, suf in zip(
        ["", "fipnum_", "gridinc_", "satnum_", "swat_"],
        [".DATA", ".INC", ".GRDECL", ".INC", ".INC"],
    ):
        assert Path(pre + base_name + suf).exists()
        if suf != ".DATA":
            assert opm.io.Parser().parse(str(pre + base_name + suf))

    # check some key parameters in output file
    data_frame = pd.read_csv(base_name + ".DATA", index_col=0)
    assert data_frame.Values["nx"] == 77
    assert data_frame.Values["ny"] == 72
    assert data_frame.Values["nz"] == 27
    assert data_frame.Values["lx"] == 7700.0
    assert data_frame.Values["ly"] == 7200.0
    assert data_frame.Values["lz"] == 195.0
    assert data_frame.Values["poro"] == 0.3243
    assert data_frame.Values["originX"] == 0.0
    assert data_frame.Values["originY"] == 0.0
    assert data_frame.Values["rotation"] == 0.0


def test_demo_large_scale_with_cmdline_throws(tmp_path, mocker):
    """Test casegen_upcars on demo_large_scale.yaml with throw"""
    shutil.copytree(DATADIR, tmp_path / TESTDATA)
    os.chdir(tmp_path / TESTDATA)

    base_name = "TEST_LARGE_WITH_THROW"
    mocker.patch(
        "sys.argv",
        [
            "casegen_upcars",
            "demo_large_scale.yaml",
            "--et",
            "dump_value.tmpl",
            "--throw",
            "5",
            "25",
            "1",
            "72",
            "20",
            "--base",
            base_name,
        ],
    )
    casegen_upcars.main()

    # check that all output files are generated
    for pre, suf in zip(
        ["", "fipnum_", "gridinc_", "satnum_", "swat_"],
        [".DATA", ".INC", ".GRDECL", ".INC", ".INC"],
    ):
        assert Path(pre + base_name + suf).exists()
        if suf != ".DATA":
            assert opm.io.Parser().parse(str(pre + base_name + suf))

    # check some key parameters in output file
    data_frame = pd.read_csv(base_name + ".DATA", index_col=0)
    assert data_frame.Values["nx"] == 77
    assert data_frame.Values["ny"] == 72
    assert data_frame.Values["nz"] == 27
    assert data_frame.Values["lx"] == 7700.0
    assert data_frame.Values["ly"] == 7200.0
    assert data_frame.Values["lz"] == 355.0
    assert data_frame.Values["poro"] == 0.1711
    assert data_frame.Values["originX"] == 0.0
    assert data_frame.Values["originY"] == 0.0
    assert data_frame.Values["rotation"] == 0.0
    assert data_frame.Values["top"] == 1500.0
    assert data_frame.Values["bottom"] == 1875.0
