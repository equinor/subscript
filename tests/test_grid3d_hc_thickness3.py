import os
import pytest

from xtgeo.common import XTGeoDialog
from xtgeo.surface import RegularSurface

import xtgeoapp_grd3dmaps.avghc.grid3d_hc_thickness as xxx

xtg = XTGeoDialog()

xtg = XTGeoDialog()
logger = xtg.basiclogger(__name__)

if not xtg.testsetup():
    raise SystemExit

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


def test_hc_thickness3a():
    """HC thickness with external configfiles, HC 3a"""
    dump = os.path.join(td, "hc3a.yml")
    xxx.main(["--config", "tests/yaml/hc_thickness3a.yml", "--dump", dump])


def test_hc_thickness3b():
    """HC thickness with external configfiles, HC 3b"""
    dump = os.path.join(td, "hc3b.yml")
    xxx.main(["--config", "tests/yaml/hc_thickness3b.yml", "--dump", dump])


def test_hc_thickness3c():
    """HC thickness with external configfiles, HC 3c"""
    dump = os.path.join(td, "hc3c.yml")
    xxx.main(["--config", "tests/yaml/hc_thickness3c.yml", "--dump", dump])

    result = os.path.join(td, "myfip1--hc3c_oilthickness--19991201.gri")
    res = RegularSurface(result)
    assert res.values.max() == pytest.approx(13.5681, abs=0.001)  # qc'ed RMS

    result = os.path.join(td, "myfip2--hc3c_oilthickness--19991201.gri")
    res = RegularSurface(result)
    assert res.values.max() == pytest.approx(0.0, abs=0.001)  # qc'ed RMS
