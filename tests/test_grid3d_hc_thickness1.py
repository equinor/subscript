import os
import shutil
import glob
import warnings

import numpy as np

from xtgeo.common import XTGeoDialog
from xtgeo.surface import RegularSurface as RS

import xtgeoapp_grd3dmaps.avghc.grid3d_hc_thickness as xx
from .test_grid3d_hc_thickness2 import assert_almostequal

xtg = XTGeoDialog()

xtg = XTGeoDialog()
logger = xtg.basiclogger(__name__)

if not xtg.testsetup():
    raise SystemExit

td = xtg.tmpdir
testpath = xtg.testpath
ojoin = os.path.join

# =============================================================================
# Do tests
# =============================================================================


def test_hc_thickness1a():
    """Test HC thickness with YAML config example 1a"""
    dmp = ojoin(td, "hc1a_dump.yml")
    xx.main(["--config", "tests/yaml/hc_thickness1a.yml", "--dump", dmp])

    allz = RS(ojoin(td, "all--oilthickness--20010101_19991201.gri"))
    val = allz.values1d

    print(np.nanmean(val), np.nanstd(val))

    # -0.0574 in RMS volumetrics, but within range as different approach
    assert_almostequal(np.nanmean(val), -0.03653, 0.001)
    assert_almostequal(np.nanstd(val), 0.199886, 0.001)

    # # legacy date format:
    # xx.main(['--legacydateformat', '--config',
    #          'tests/yaml/hc_thickness1a.yml'])


def test_hc_thickness1b():
    """HC thickness with YAML config example 1b; zonation in own YAML file"""
    xx.main(["--config", "tests/yaml/hc_thickness1b.yml"])
    imgs = glob.glob(ojoin(td, "*hc1b*.png"))
    print(imgs)
    for img in imgs:
        shutil.copy2(img, "docs/test_images/.")


def test_hc_thickness1c():
    """HC thickness with YAML config example 1c; no map settings"""
    xx.main(["--config", "tests/yaml/hc_thickness1c.yml"])


def test_hc_thickness1d():
    """HC thickness with YAML config example 1d; as 1c but use_porv instead"""
    warnings.simplefilter("error")
    xx.main(["--config", "tests/yaml/hc_thickness1d.yml"])

    x1d = RS(ojoin(td, "all--hc1d_oilthickness--19991201.gri"))

    assert_almostequal(x1d.values.mean(), 0.516, 0.001)


def test_hc_thickness1e():
    """HC thickness with YAML config 1e; as 1d but use ROFF grid input"""
    xx.main(["--config", "tests/yaml/hc_thickness1e.yml"])

    x1e = RS(ojoin(td, "all--hc1e_oilthickness--19991201.gri"))
    logger.info(x1e.values.mean())
    assert_almostequal(x1e.values.mean(), 0.516, 0.001)


def test_hc_thickness1f():
    """HC thickness with YAML config 1f; use rotated template map"""
    xx.main(["--config", "tests/yaml/hc_thickness1f.yml"])

    x1f = RS(ojoin(td, "all--hc1f_oilthickness--19991201.gri"))
    logger.info(x1f.values.mean())
    # other mean as the map is smaller; checked in RMS
    assert_almostequal(x1f.values.mean(), 1.0999, 0.0001)


def test_hc_thickness1g():
    """HC thickness with YAML config 1g; use rotated template map and both
    oil and gas"""
    xx.main(["--config", "tests/yaml/hc_thickness1g.yml"])

    x1g1 = RS(ojoin(td, "all--hc1g_oilthickness--19991201.gri"))
    logger.info(x1g1.values.mean())
    assert_almostequal(x1g1.values.mean(), 1.0999, 0.0001)

    x1g2 = RS(ojoin(td, "all--hc1g_gasthickness--19991201.gri"))
    logger.info(x1g1.values.mean())
    assert_almostequal(x1g2.values.mean(), 0.000, 0.0001)


def test_hc_thickness1h():
    """Test HC thickness with YAML copy from 1a, with tuning to speed up"""
    xx.main(["--config", "tests/yaml/hc_thickness1h.yml"])

    # now read in result and check avg value
    # x = RegularSurface('TMP/gull_1985_10_01.gri')
    # avg = float("{:4.3f}".format(float(x.values.mean())))
    # logger.info("AVG is " + str(avg))
    # assert avg == 3.649

    allz = RS(ojoin(td, "all--tuning_oilthickness--20010101_19991201.gri"))
    val = allz.values1d

    print(np.nanmean(val), np.nanstd(val))

    # -0.0574 in RMS volumetrics, but within range as different approach
    assert_almostequal(np.nanmean(val), -0.0336, 0.005)
    assert_almostequal(np.nanstd(val), 0.1717, 0.005)


def test_hc_thickness1i():
    """Test HC thickness with YAML config example 1i, based on 1a"""
    xx.main(["--config", "tests/yaml/hc_thickness1i.yml"])

    # now read in result and check avg value
    # x = RegularSurface('TMP/gull_1985_10_01.gri')
    # avg = float("{:4.3f}".format(float(x.values.mean())))
    # logger.info("AVG is " + str(avg))
    # assert avg == 3.649

    allz = RS(ojoin(td, "all--hc1i_oilthickness--20010101_19991201.gri"))
    val = allz.values

    print(val.mean())

    # -0.0574 in RMS volumetrics, but within range as different approach
    assert_almostequal(val.mean(), -0.06, 0.01)
