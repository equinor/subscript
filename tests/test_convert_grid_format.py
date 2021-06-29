"""Test the convert_grid_format script"""

import subprocess
from pathlib import Path

import pytest
import xtgeo

import subscript.convert_grid_format.convert_grid_format as cgf
from subscript import getLogger

logger = getLogger(__name__)

RFILE1 = (
    Path(__file__).absolute().parent
    / "data"
    / "reek"
    / "eclipse"
    / "model"
    / "2_R001_REEK-0.EGRID"
)
RFILE2 = (
    Path(__file__).absolute().parent
    / "data"
    / "reek"
    / "eclipse"
    / "model"
    / "2_R001_REEK-0.UNRST"
)


def test_convert_grid_format_egrid(tmpdir, mocker):
    """Convert an ECLIPSE egrid to roff"""

    outfile = tmpdir / "reek_grid.roff"

    mocker.patch(
        "sys.argv",
        [
            "convert_grid_format",
            "--file",
            str(RFILE1),
            "--output",
            str(outfile),
            "--mode",
            "grid",
            "--standardfmu",
        ],
    )
    cgf.main()

    # check number of active cells
    geogrid = xtgeo.Grid(str(outfile))
    assert geogrid.nactive == 35817


def test_convert_grid_format_restart(tmpdir, mocker):
    """Convert an ECLIPSE SOIL from restart to roff"""

    outfile = tmpdir / "reek_grid.roff"

    mocker.patch(
        "sys.argv",
        [
            "convert_grid_format",
            "--file",
            str(RFILE2),
            "--output",
            str(outfile),
            "--mode",
            "restart",
            "--propnames",
            "SOIL",
            "--dates",
            "20000701",
            "--standardfmu",
        ],
    )
    cgf.main()

    actual_outfile = tmpdir / "reek_grid--soil--20000701.roff"

    gprop = xtgeo.GridProperty(str(actual_outfile))

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
def test_datesfile(dates, date_mode, expected_files, tmpdir, mocker):
    """Test invocation with a filename to the dates"""

    outfile = tmpdir / "reek_grid.roff"

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

    mocker.patch(
        "sys.argv",
        [
            "convert_grid_format",
            "--file",
            str(RFILE2),
            "--output",
            str(outfile),
            "--mode",
            "restart",
            "--propnames",
            "SOIL",
            "--dates",
            dateargument,
            "--standardfmu",
        ],
    )
    cgf.main()
    for expected_file in expected_files:
        assert (tmpdir / expected_file).exists()


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["convert_grid_format", "-h"])
