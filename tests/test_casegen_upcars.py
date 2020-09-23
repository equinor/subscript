"""Test that casegen_upcars is installed and launched with given demo cases"""
# pylint:disable=bad-continuation
import os
import subprocess
import shutil

import pandas as pd

import opm.io

TESTDATA = "testdata_casegen_upcars"
DATADIR = os.path.join(os.path.dirname(__file__), TESTDATA)


def test_installed():
    """Test that the endpoint is installed, use -h as it required one parameter"""
    assert subprocess.check_output(["casegen_upcars", "-h"])


def test_demo_small_scale(tmpdir):
    """Test casegen_upcars on demo_small_scale.yaml"""
    tmpdir.chdir()
    shutil.copytree(DATADIR, TESTDATA)
    tmpdir.join(TESTDATA).chdir()

    base_name = "TEST_SMALL"
    assert subprocess.check_output(
        [
            "casegen_upcars",
            "demo_small_scale.yaml",
            "--et",
            "dump_value.tmpl",
            "--base",
            base_name,
        ]
    )

    # check that all output files are generated
    for pre, suf in zip(
        ["", "fipnum_", "gridinc_", "satnum_", "swat_"],
        [".DATA", ".INC", ".GRDECL", ".INC", ".INC"],
    ):
        assert os.path.exists(pre + base_name + suf)
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


def test_demo_large_scale(tmpdir):
    """Test casegen_upcars on demo_large_scale.yaml"""
    tmpdir.chdir()
    shutil.copytree(DATADIR, TESTDATA)
    tmpdir.join(TESTDATA).chdir()

    base_name = "TEST_SMALL"
    assert subprocess.check_output(
        [
            "casegen_upcars",
            "demo_large_scale.yaml",
            "--et",
            "dump_value.tmpl",
            "--base",
            base_name,
        ]
    )

    # check that all output files are generated
    for pre, suf in zip(
        ["", "fipnum_", "gridinc_", "satnum_", "swat_"],
        [".DATA", ".INC", ".GRDECL", ".INC", ".INC"],
    ):
        assert os.path.exists(pre + base_name + suf)
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
