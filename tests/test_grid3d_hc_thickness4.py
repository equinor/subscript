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


def test_hc_thickness4a():
    """HC thickness with external configfiles, HC 4a"""
    dump = os.path.join(td, "hc4a.yml")
    xxx.main(["--config", "tests/yaml/hc_thickness4a.yml", "--dump", dump])

    # check result
    mapfile = os.path.join(td, "all--hc4a_rockthickness.gri")
    mymap = RegularSurface(mapfile)

    assert_almostequal(mymap.values.mean(), 0.76590, 0.001)
