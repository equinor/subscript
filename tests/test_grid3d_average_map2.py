import os
import pytest

from xtgeo.common import XTGeoDialog
from xtgeo.surface import RegularSurface

import xtgeoapp_grd3dmaps.avghc.grid3d_average_map as xxx

xtg = XTGeoDialog()
logger = xtg.basiclogger(__name__)

if not xtg.testsetup():
    raise SystemExit

td = xtg.tmpdir
testpath = xtg.testpath

skiplargetest = pytest.mark.skipif(xtg.bigtest is False, reason="Big tests skip")

# =============================================================================
# Do tests
# =============================================================================


def test_average_map2a():
    """Test AVG with YAML config example 2a ECL based with filters"""
    dump = os.path.join(td, "avg2a.yml")
    xxx.main(["--config", "tests/yaml/avg2a.yml", "--dump", dump])


def test_average_map2b():
    """Test AVG with YAML config example 2b, filters, zonation from prop"""
    dump = os.path.join(td, "avg2b.yml")
    xxx.main(["--config", "tests/yaml/avg2b.yml", "--dump", dump])

    pfile = os.path.join(td, "myzone1--avg2b_average_pressure--20010101.gri")
    pres = RegularSurface(pfile)

    assert pres.values.mean() == pytest.approx(301.689869690714, abs=0.01)


def test_average_map2c():
    """Test AVG with YAML config example 2c, filters, zonation from prop"""
    dump = os.path.join(td, "avg2c.yml")
    xxx.main(["--config", "tests/yaml/avg2c.yml", "--dump", dump])

    pfile = os.path.join(td, "myzone1--avg2c_average_pressure--20010101.gri")
    pres = RegularSurface(pfile)

    assert pres.values.mean() == pytest.approx(301.689869690714, abs=0.01)
