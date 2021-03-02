import os
import subprocess
import pytest
import numpy as np
import pandas as pd
from ecl.summary import EclSum
from subscript.welltest_dpds import welltest_dpds
from pathlib import Path

ECLDIR = os.path.join(os.path.dirname(__file__), "data/welltest/eclipse/model")
ECLCASE = "DROGON_DST_PLT-0"


@pytest.mark.integration
def test_integration():
    """Test that endpoint is installed"""
    assert subprocess.check_output(["welltest_dpds", "-h"])


@pytest.mark.integration
def test_main(tmpdir, mocker):
    """Test invocation from command line"""
    tmpdir.chdir()

    datafilepath = os.path.join(ECLDIR, ECLCASE)

    # defaults only
    mocker.patch("sys.argv", ["welltest_dpds", datafilepath, "55_33-1"])
    welltest_dpds.main()
    assert os.path.exists("welltest_output.csv")

    # test --outfilessuffix
    mocker.patch(
        "sys.argv",
        ["welltest_dpds", datafilepath, "55_33-1", "--outfilessuffix", "blabla"],
    )
    welltest_dpds.main()
    assert os.path.exists("welltest_output_blabla.csv")

    # test --outputdirectory
    mocker.patch(
        "sys.argv",
        ["welltest_dpds", datafilepath, "55_33-1", "-o", "blabla"],
    )
    with pytest.raises(FileNotFoundError, match=r".*No such outputdirectory.*"):
        welltest_dpds.main()

    os.mkdir("blabla")
    welltest_dpds.main()
    assert os.path.exists("./blabla/welltest_output.csv")

    # test --phase
    mocker.patch(
        "sys.argv", ["welltest_dpds", datafilepath, "55_33-1", "--phase", "GAS"]
    )
    welltest_dpds.main()
    assert os.path.exists("welltest_output.csv")
    os.unlink("welltest_output.csv")

    # test --genobs_resultfile
    mocker.patch(
        "sys.argv",
        [
            "welltest_dpds",
            datafilepath,
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
    Path("results.txt").write_text(mockcsv)
    welltest_dpds.main()
    assert os.path.exists("welltest_output.csv")


def test_summary_vec():
    """Test that summary reading is handled correctly"""

    datafilepath = os.path.join(ECLDIR, ECLCASE)
    summary = EclSum(datafilepath)
    with pytest.raises(KeyError, match=r".*No such key.*"):
        welltest_dpds.summary_vec(summary, "no_well")
        welltest_dpds.summary_vec(summary, "NOVEC:55_33-1")

    wopr = welltest_dpds.summary_vec(summary, "WOPR:55_33-1")
    assert len(wopr) == 556


def test_get_buildup_indices():
    """Test that buildup periods are identified correct """

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

    datafilepath = os.path.join(ECLDIR, ECLCASE)
    summary = EclSum(datafilepath)

    wbhp = welltest_dpds.summary_vec(summary, "WBHP:55_33-1")
    bu_start, bu_end = welltest_dpds.get_buildup_indices(wbhp)
    assert bu_start == []
    assert bu_end == []

    wopr = welltest_dpds.summary_vec(summary, "WOPR:55_33-1")
    bu_start, bu_end = welltest_dpds.get_buildup_indices(wopr)
    assert bu_start == [7, 260]
    assert bu_end == [254, 555]


def test_supertime():
    """ Test that superpositied time is calculated correctly """

    datafilepath = os.path.join(ECLDIR, ECLCASE)
    summary = EclSum(datafilepath)

    rate = welltest_dpds.summary_vec(summary, "WOPR:55_33-1")
    time = np.array(summary.days) * 24.0
    bu_start, bu_end = welltest_dpds.get_buildup_indices(rate)

    supertime = welltest_dpds.supertime(time, rate, bu_start[0], bu_end[0])

    assert len(supertime) == 247
    assert supertime[0] == pytest.approx(-9.83777733)
    assert supertime[-1] == pytest.approx(-0.65295189)


def test_weighted_avg_press_time_derivative_lag1():
    """ Test that weighted_avg_press_time_derivative_lag1 is calculated correctly """

    datafilepath = os.path.join(ECLDIR, ECLCASE)
    summary = EclSum(datafilepath)

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
    """ Test that weighted_avg_press_time_derivative_lag2 is calcuated correctly """

    datafilepath = os.path.join(ECLDIR, ECLCASE)
    summary = EclSum(datafilepath)

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


def test_genobs_vec():
    """ Test genobs_vec """

    mockcsv = """
    Time\tdTime
    (hr)\t(hr)
    0\t0
    1\t1
    """
    Path("index.txt").write_text(mockcsv)

    vec = np.array([0, 0.5, 1, 2])
    time = np.array([0, 1, 2, 3])
    genobs_vec = welltest_dpds.genobs_vec("index.txt", vec, time)

    assert len(genobs_vec) == 2
    assert genobs_vec[1] == pytest.approx(0.5)


def test_to_csv():
    """ Test to_csv """

    vec = np.array([0, 0.5, 1, 2])
    welltest_dpds.to_csv("mock.csv", [vec])
    assert os.path.exists("mock.csv")
    lines = open("mock.csv", "r").readlines()
    assert 4 == len(lines)

    welltest_dpds.to_csv("mock.csv", [vec], ["vec"])
    assert os.path.exists("mock.csv")
    lines = open("mock.csv", "r").readlines()
    assert 5 == len(lines)

    vecb = np.array([1, 0.5, 3, 100])
    welltest_dpds.to_csv("mock.csv", [vec, vecb], ["vec", "vecb"])
    assert os.path.exists("mock.csv")
    lines = open("mock.csv", "r").readlines()
    assert 5 == len(lines)

    df = pd.read_csv("mock.csv", skipinitialspace=True)
    assert df["vec"].size == 4
    assert pytest.approx(df["vecb"].iloc[-1] == 100)
