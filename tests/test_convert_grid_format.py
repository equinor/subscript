"""Test the convert_grid_format script"""

import os
import shutil
import pytest

import xtgeo
from xtgeo.common import XTGeoDialog

import subscript.convert_grid_format.convert_grid_format as cgf

xtg = XTGeoDialog()
logger = xtg.basiclogger(__name__)


RFILE1 = os.path.join(
    os.path.dirname(__file__), "data/reek/eclipse/model/2_R001_REEK-0.EGRID"
)
RFILE2 = os.path.join(
    os.path.dirname(__file__), "data/reek/eclipse/model/2_R001_REEK-0.UNRST"
)


def test_convert_grid_format_egrid(tmpdir):
    """Convert an ECLIPSE egrid to roff"""

    outfile = os.path.join(str(tmpdir), "reek_grid.roff")

    cgf.main(["--file", RFILE1, "--output", outfile, "--mode", "grid", "--standardfmu"])

    # check number of active cells
    gg = xtgeo.Grid(outfile)
    assert gg.nactive == 35817


def test_convert_grid_format_restart(tmpdir):
    """Convert an ECLIPSE SOIL from restart to roff"""

    outfile = os.path.join(str(tmpdir), "reek_grid.roff")

    cgf.main(
        [
            "--file",
            RFILE2,
            "--output",
            outfile,
            "--mode",
            "restart",
            "--propnames",
            "SOIL",
            "--dates",
            "20000701",
            "--standardfmu",
        ]
    )

    actual_outfile = os.path.join(str(tmpdir), "reek_grid--soil--20000701.roff")

    gprop = xtgeo.GridProperty(actual_outfile)

    assert gprop.values.mean() == pytest.approx(0.0857, abs=0.001)
