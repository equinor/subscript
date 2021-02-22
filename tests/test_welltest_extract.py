import os
import sys
import subprocess
import pytest
import numpy as np
from ecl.summary import EclSum
from subscript.welltest_extract import welltest_extract

ECLDIR = os.path.join(os.path.dirname(__file__), "data/welltest/eclipse/model")
ECLCASE = "DROGON_DST_PLT-0"


@pytest.mark.integration
def test_integration():
    """Test that endpoint is installed"""
    assert subprocess.check_output(["welltest_extract", "-h"])


@pytest.mark.integration
def test_main(tmpdir):
    """Test invocation from command line"""
    tmpdir.chdir()

    datafilepath = os.path.join(ECLDIR, ECLCASE)
    sys.argv = ["welltest_extract", datafilepath, "55_33-1", "blabla"]
    welltest_extract.main()
    assert os.path.exists('out_wbhp')

def test_get_summary_vec():
    """Test that summary reading is handled correctly"""

    datafilepath = os.path.join(ECLDIR, ECLCASE)
    summary = EclSum(datafilepath)
    with pytest.raises(KeyError, match=r".*No such key.*"):
        welltest_extract.get_summary_vec(summary, "no_well")
        welltest_extract.get_summary_vec(summary, "NOVEC:55_33-1")

    wopr = welltest_extract.get_summary_vec(summary, "WOPR:55_33-1")
    assert len(wopr) == 556


def test_get_buildup_indices():
    """Test that build up periods are identified correct """

    datafilepath = os.path.join(ECLDIR, ECLCASE)
    summary = EclSum(datafilepath)

    wbhp = welltest_extract.get_summary_vec(summary, "WBHP:55_33-1")
    bu_start, bu_end = welltest_extract.get_buildup_indices(wbhp)
    assert bu_start == []
    assert bu_end == []

    wopr = welltest_extract.get_summary_vec(summary, "WOPR:55_33-1")
    bu_start, bu_end = welltest_extract.get_buildup_indices(wopr)
    assert bu_start == [7, 260]
    assert bu_end == [254, 555]


def test_get_supertime():
    """ Test that superpositied time is calcuated correctly """

    datafilepath = os.path.join(ECLDIR, ECLCASE)
    summary = EclSum(datafilepath)

    rate = welltest_extract.get_summary_vec(summary, "WOPR:55_33-1")
    time = np.array(summary.days) * 24.0
    bu_start, bu_end = welltest_extract.get_buildup_indices(rate)

    supertime = welltest_extract.get_supertime(time, rate, bu_start[0], bu_end[0])

    assert len(supertime) == 247
    assert supertime[0] == pytest.approx(-9.83777733)
    assert supertime[-1] == pytest.approx(-0.65295189)


def test_get_weighted_avg_press_time_derivative_lag1():
    """ Test that weighted_avg_press_time_derivative_lag1 is calcuated correctly """

    datafilepath = os.path.join(ECLDIR, ECLCASE)
    summary = EclSum(datafilepath)

    wbhp = welltest_extract.get_summary_vec(summary, "WBHP:55_33-1")
    rate = welltest_extract.get_summary_vec(summary, "WOPR:55_33-1")
    time = np.array(summary.days) * 24.0
    bu_start, bu_end = welltest_extract.get_buildup_indices(rate)

    supertime = welltest_extract.get_supertime(time, rate, bu_start[0], bu_end[0])

    d_press = np.diff(wbhp[bu_start[0] + 1 : bu_end[0] + 1])
    dspt = np.diff(supertime)

    dpdspt = welltest_extract.get_weighted_avg_press_time_derivative_lag1(d_press, dspt)

    assert len(dpdspt) == 247
    assert dpdspt[0] == pytest.approx(0.46972867)
    assert dpdspt[-1] == pytest.approx(0.12725929)


def test_get_weighted_avg_press_time_derivative_lag2():
    """ Test that weighted_avg_press_time_derivative_lag2 is calcuated correctly """

    datafilepath = os.path.join(ECLDIR, ECLCASE)
    summary = EclSum(datafilepath)

    wbhp = welltest_extract.get_summary_vec(summary, "WBHP:55_33-1")
    rate = welltest_extract.get_summary_vec(summary, "WOPR:55_33-1")
    time = np.array(summary.days) * 24.0
    bu_start, bu_end = welltest_extract.get_buildup_indices(rate)

    supertime = welltest_extract.get_supertime(time, rate, bu_start[0], bu_end[0])

    d_press = np.diff(wbhp[bu_start[0] + 1 : bu_end[0] + 1])
    dspt = np.diff(supertime)
    dpdspt_w_lag2 = welltest_extract.get_weighted_avg_press_time_derivative_lag2(
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
