import os
import sys
import pytest
import numpy as np

from xtgeo.common import XTGeoDialog
from xtgeo.surface import RegularSurface as RS

import xtgeoapp_grd3dmaps.avghc.grid3d_hc_thickness as xx

xtg = XTGeoDialog()

xtg = XTGeoDialog()
logger = xtg.basiclogger(__name__)

if not xtg.testsetup():
    sys.exit(-9)

td = xtg.tmpdir
testpath = xtg.testpath


# =============================================================================
# Some useful functions
# =============================================================================


def assert_equal(this, that, txt=""):
    assert this == that, txt


def assert_almostequal(this, that, tol, txt=""):
    assert this == pytest.approx(that, abs=tol), txt


# =============================================================================
# Do tests
# =============================================================================


def test_hc_thickness2a():
    """HC thickness with YAML config example 2a; use STOOIP prop from RMS"""
    xx.main(["--config", "tests/yaml/hc_thickness2a.yml"])

    # read in result and check statistical values

    allz = RS(os.path.join(td, "all--stoiip_oilthickness--19900101.gri"))

    val = allz.values1d
    val[val <= 0] = np.nan

    # compared with data from RMS:
    assert_almostequal(np.nanmean(val), 1.9521, 0.01)
    assert_almostequal(np.nanstd(val), 1.2873, 0.01)
