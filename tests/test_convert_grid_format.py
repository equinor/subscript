"""Test the convert_grid_format script"""

import os
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
    geogrid = xtgeo.Grid(outfile)
    assert geogrid.nactive == 35817


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


@pytest.mark.parametrize(
    "dates, date_mode, expected_files",
    [
        (["20000701"], "space", ["reek_grid--soil--20000701.roff"]),
        (["20000701"], "file", ["reek_grid--soil--20000701.roff"]),
        (
            ["20000101", "20010201"],
            "space",
            ["reek_grid--soil--20000101.roff", "reek_grid--soil--20010201.roff"],
        ),
        (
            ["20000101", "20010201"],
            "colon",
            ["reek_grid--soil--20000101.roff", "reek_grid--soil--20010201.roff"],
        ),
        (
            ["20000101", "20010201"],
            "file",
            ["reek_grid--soil--20000101.roff", "reek_grid--soil--20010201.roff"],
        ),
    ],
)
def test_datesfile(dates, date_mode, expected_files, tmpdir):
    """Test invocation with a filename to the dates"""

    outfile = os.path.join(str(tmpdir), "reek_grid.roff")

    assert date_mode in {"space", "colon", "file"}

    if date_mode == "file":
        with open("dates.txt", "w") as date_f:
            for date in dates:
                date_f.write(date + "\n")
        dateargument = "dates.txt"
    elif date_mode == "space":
        dateargument = " ".join(dates)
    elif date_mode == "colon":
        dateargument = ":".join(dates)
    else:
        raise ValueError

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
            dateargument,
            "--standardfmu",
        ]
    )
    for expected_file in expected_files:
        assert os.path.exists(os.path.join(str(tmpdir), expected_file))


def test_installed():
    """Test that the endpoint is installed"""
    assert os.system("convert_grid_format") == 0
