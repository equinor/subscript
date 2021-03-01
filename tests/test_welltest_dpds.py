import os
import subprocess
import pytest
import numpy as np
from ecl.summary import EclSum
from subscript.welltest_dpds import welltest_dpds

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
    os.unlink("welltest_output.csv")

    # test --outfilessuffix
    mocker.patch(
        "sys.argv",
        ["welltest_dpds", datafilepath, "55_33-1", "--outfilessuffix", "blabla"],
    )
    welltest_dpds.main()
    assert os.path.exists("welltest_output_blabla.csv")
    os.unlink("welltest_output_blabla.csv")

    # test --outputdirectory
    mocker.patch(
        "sys.argv",
        ["welltest_dpds", datafilepath, "55_33-1", "-o", "blabla"],
    )

    welltest_dpds.main()
    assert os.path.exists("./blabla/welltest_output.csv")

    # test --phase
    mocker.patch(
        "sys.argv", ["welltest_dpds", datafilepath, "55_33-1", "--phase", "GAS"]
    )
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


def test_gendata_vec(tmpdir):
    mockfcont = """
    Time\tdTime
    (hr)\t(hr)
    0\t0
    1\t1
    """
    fileh = open("index.txt", "w")
    fileh.write(mockfcont)
    fileh.close()

    vec = np.array([0, 0.5, 1, 2])
    time = np.array([0, 1, 2, 3])
    gendata_vec = welltest_dpds.gendata_vec("index.txt", vec, time)
    os.unlink("index.txt")

    assert len(gendata_vec) == 2
    assert gendata_vec[1] == pytest.approx(0.5)
