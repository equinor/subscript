import os

# import shutil
# import glob
# import warnings

from xtgeo.common import XTGeoDialog

import xtgeoapp_grd3dmaps.contact.grid3d_contact_map as xx

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


def test_contact1a():
    """Test HC contacts with YAML config example 1a"""
    xx.main(["--config", "tests/yaml/contact1a.yml"])
