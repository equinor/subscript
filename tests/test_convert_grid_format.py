"""Test the convert_grid_format script"""

import subprocess
from pathlib import Path

import pytest
import subscript.convert_grid_format.convert_grid_format as cgf
import xtgeo
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


def test_convert_grid_format_egrid(tmp_path, mocker):
    """Convert an ECLIPSE egrid to roff"""

    outfile = tmp_path / "reek_grid.roff"

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
    geogrid = xtgeo.grid_from_file(str(outfile))
    assert geogrid.nactive == 35817


def test_convert_grid_format_restart(tmp_path, mocker):
    """Convert an ECLIPSE SOIL from restart to roff"""

    outfile = tmp_path / "reek_grid.roff"

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

    actual_outfile = tmp_path / "reek_grid--soil--20000701.roff"

    gprop = xtgeo.gridproperty_from_file(actual_outfile)

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
def test_datesfile(dates, date_mode, expected_files, tmp_path, mocker):
    """Test invocation with a filename to the dates"""

    outfile = tmp_path / "reek_grid.roff"

    assert date_mode in {"space", "colon", "file"}

    if date_mode == "file":
        dateargument = f"{tmp_path}/dates.txt"
        Path(dateargument).write_text("\n".join(dates), encoding="utf8")
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
        assert (tmp_path / expected_file).exists()


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["convert_grid_format", "-h"])
