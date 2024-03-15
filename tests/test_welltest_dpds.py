import os
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from resdata.summary import Summary
from subscript.welltest_dpds import welltest_dpds

ECLDIR = Path(__file__).parent.absolute() / Path("data/welltest/eclipse/model")
ECLCASE = "DROGON_DST_PLT-0"
DATAFILEPATH = Path(ECLDIR / ECLCASE).as_posix()


@pytest.mark.integration
def test_integration():
    """Test that endpoint is installed"""
    assert subprocess.check_output(["welltest_dpds", "-h"])


@pytest.mark.integration
def test_main(tmp_path, mocker):
    """Test invocation from command line"""
    os.chdir(tmp_path)

    # defaults only
    mocker.patch("sys.argv", ["welltest_dpds", DATAFILEPATH, "55_33-1"])
    welltest_dpds.main()
    assert Path("welltest_output.csv").exists()
    assert Path("dpdspt_lag1.csv").exists()
    assert Path("dpdspt_lag2.csv").exists()
    assert Path("spt.csv").exists()
    Path("welltest_output.csv").unlink()

    # test --outfilessuffix
    mocker.patch(
        "sys.argv",
        ["welltest_dpds", DATAFILEPATH, "55_33-1", "--outfilessuffix", "blabla"],
    )
    welltest_dpds.main()

    assert Path("welltest_output_blabla.csv").exists()

    # test --outputdirectory
    mocker.patch(
        "sys.argv",
        ["welltest_dpds", DATAFILEPATH, "55_33-1", "-o", "blabla"],
    )
    with pytest.raises(FileNotFoundError, match=r".*No such outputdirectory.*"):
        welltest_dpds.main()

    Path("blabla").mkdir()
    welltest_dpds.main()
    assert Path("blabla/welltest_output.csv").exists()

    # test --phase
    mocker.patch(
        "sys.argv", ["welltest_dpds", DATAFILEPATH, "55_33-1", "--phase", "GAS"]
    )
    welltest_dpds.main()
    assert Path("welltest_output.csv").exists()
    Path("welltest_output.csv").unlink()
    # test --phase
    mocker.patch(
        "sys.argv", ["welltest_dpds", DATAFILEPATH, "55_33-1", "--phase", "WATER"]
    )
    welltest_dpds.main()
    assert Path("welltest_output.csv").exists()
    suptimew = pd.read_csv("spt.csv")
    # pylint: disable=no-member
    # (false positive)
    assert suptimew.iloc[0, 0] == pytest.approx(-9.87037983)
    assert suptimew.iloc[-1, 0] == pytest.approx(-0.65693308)
    Path("welltest_output.csv").unlink()

    # test --genobs_resultfile
    mocker.patch(
        "sys.argv",
        [
            "welltest_dpds",
            DATAFILEPATH,
            "55_33-1",
            "--genobs_resultfile",
            "results.txt",
        ],
    )
    with pytest.raises(FileNotFoundError, match=r".*No such file.*"):
        welltest_dpds.main()

    mockcsv = """
    Time\tdTime
    (hr)\t(hr)
    0\t0
    1\t1
    """
    Path("results.txt").write_text(mockcsv, encoding="utf8")
    welltest_dpds.main()
    assert Path("welltest_output.csv").exists()


def test_summary_vec():
    """Test that summary reading is handled correctly"""

    summary = Summary(DATAFILEPATH)
    with pytest.raises(KeyError, match=r".*No such key.*"):
        welltest_dpds.summary_vec(summary, "no_well")
        welltest_dpds.summary_vec(summary, "NOVEC:55_33-1")

    wopr = welltest_dpds.summary_vec(summary, "WOPR:55_33-1")
    assert len(wopr) == 556


def test_get_buildup_indices():
    """Test that buildup periods are identified correct"""

    wbhp = np.array([1, 0])
    bu_start, bu_end = welltest_dpds.get_buildup_indices(wbhp)
    assert bu_start == [1]
    assert bu_end == [1]

    wbhp = np.array([0, 1])
    bu_start, bu_end = welltest_dpds.get_buildup_indices(wbhp)
    assert bu_start == []
    assert bu_end == []

    wbhp = np.array([0, 1, 0])
    bu_start, bu_end = welltest_dpds.get_buildup_indices(wbhp)
    assert bu_start == [2]
    assert bu_end == [2]

    wbhp = np.array([0, 1, 0, 1, 0, 0])
    bu_start, bu_end = welltest_dpds.get_buildup_indices(wbhp)
    assert bu_start == [2, 4]
    assert bu_end == [2, 5]

    wbhp = np.array([0, 1, 0, 1, 0, 0, 1])
    bu_start, bu_end = welltest_dpds.get_buildup_indices(wbhp)
    assert bu_start == [2, 4]
    assert bu_end == [2, 5]

    summary = Summary(DATAFILEPATH)

    wbhp = welltest_dpds.summary_vec(summary, "WBHP:55_33-1")
    bu_start, bu_end = welltest_dpds.get_buildup_indices(wbhp)
    assert bu_start == []
    assert bu_end == []

    wopr = welltest_dpds.summary_vec(summary, "WOPR:55_33-1")
    bu_start, bu_end = welltest_dpds.get_buildup_indices(wopr)
    assert bu_start == [7, 260]
    assert bu_end == [254, 555]


def test_supertime():
    """Test that superpositied time is calculated correctly"""

    summary = Summary(DATAFILEPATH)

    rate = welltest_dpds.summary_vec(summary, "WOPR:55_33-1")
    time = np.array(summary.days) * 24.0
    bu_start, bu_end = welltest_dpds.get_buildup_indices(rate)

    supertime = welltest_dpds.supertime(time, rate, bu_start[0], bu_end[0])

    assert len(supertime) == 247
    assert supertime[0] == pytest.approx(-9.83777733)
    assert supertime[-1] == pytest.approx(-0.65295189)


def test_weighted_avg_press_time_derivative_lag1():
    """Test that weighted_avg_press_time_derivative_lag1 is calculated correctly"""

    summary = Summary(DATAFILEPATH)

    wbhp = welltest_dpds.summary_vec(summary, "WBHP:55_33-1")
    rate = welltest_dpds.summary_vec(summary, "WOPR:55_33-1")
    time = np.array(summary.days) * 24.0
    bu_start, bu_end = welltest_dpds.get_buildup_indices(rate)

    supertime = welltest_dpds.supertime(time, rate, bu_start[0], bu_end[0])

    d_press = np.diff(wbhp[bu_start[0] + 1 : bu_end[0] + 1])
    dspt = np.diff(supertime)

    dpdspt = welltest_dpds.weighted_avg_press_time_derivative_lag1(d_press, dspt)

    assert len(dpdspt) == 247
    assert dpdspt[0] == pytest.approx(0.46972867)
    assert dpdspt[-1] == pytest.approx(0.12725929)


def test_get_weighted_avg_press_time_derivative_lag2():
    """Test that weighted_avg_press_time_derivative_lag2 is calcuated correctly"""

    summary = Summary(DATAFILEPATH)

    wbhp = welltest_dpds.summary_vec(summary, "WBHP:55_33-1")
    rate = welltest_dpds.summary_vec(summary, "WOPR:55_33-1")
    time = np.array(summary.days) * 24.0
    bu_start, bu_end = welltest_dpds.get_buildup_indices(rate)

    supertime = welltest_dpds.supertime(time, rate, bu_start[0], bu_end[0])

    d_press = np.diff(wbhp[bu_start[0] + 1 : bu_end[0] + 1])
    dspt = np.diff(supertime)
    dpdspt_w_lag2 = welltest_dpds.weighted_avg_press_time_derivative_lag2(
        d_press,
        dspt,
        supertime,
        wbhp,
        bu_start[0],
        bu_end[0],
    )
    print(len(dpdspt_w_lag2))
    print(dpdspt_w_lag2)

    assert len(dpdspt_w_lag2) == 247
    assert dpdspt_w_lag2[0] == pytest.approx(0.43083638)
    assert dpdspt_w_lag2[-1] == pytest.approx(0.12729989)


def test_genobs_vec(tmp_path):
    """Test genobs_vec"""

    os.chdir(tmp_path)
    mockcsv = """
    Time\tdTime
    (hr)\t(hr)
    0\t0
    1\t1
    """
    Path("index.txt").write_text(mockcsv, encoding="utf8")

    vec = np.array([0, 0.5, 1, 2])
    time = np.array([0, 1, 2, 3])
    genobs_vec = welltest_dpds.genobs_vec("index.txt", vec, time)

    assert len(genobs_vec) == 2
    assert genobs_vec[1] == pytest.approx(0.5)


def test_to_csv(tmp_path):
    """Test to_csv"""

    os.chdir(tmp_path)

    vec = np.array([0, 0.5, 1, 2])
    welltest_dpds.to_csv("mock.csv", [vec])
    assert Path("mock.csv").exists()
    lines = Path("mock.csv").read_text(encoding="utf8").splitlines()
    assert len(lines) == 4

    welltest_dpds.to_csv("mock.csv", [vec], ["vec"])
    assert Path("mock.csv").exists()
    lines = Path("mock.csv").read_text(encoding="utf8").splitlines()
    assert len(lines) == 5

    vecb = np.array([1, 0.5, 3, 100])
    welltest_dpds.to_csv("mock.csv", [vec, vecb], ["vec", "vecb"])
    assert Path("mock.csv").exists()
    lines = Path("mock.csv").read_text(encoding="utf8").splitlines()
    assert len(lines) == 5

    dframe = pd.read_csv("mock.csv", skipinitialspace=True)
    assert dframe["vec"].size == 4
    assert dframe["vecb"].iloc[-1] == pytest.approx(100)
