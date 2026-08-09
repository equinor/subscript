"""Test the convert_grid_format script"""

import logging
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


def _create_roff_grid(infile: Path, outfile: Path) -> None:
    xtgeo.grid_from_file(str(infile), fformat="egrid").to_file(
        str(outfile), fformat="roff"
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
    "outformat, suffix, read_format",
    [
        ("grdecl", ".grdecl", "grdecl"),
        ("bgrdecl", ".bgrdecl", "bgrdecl"),
        ("egrid", ".EGRID", "egrid"),
    ],
)
def test_convert_grid_format_roff2ecl_grid(
    tmp_path, mocker, outformat, suffix, read_format
):
    infile = tmp_path / "input.roff"
    _create_roff_grid(RFILE1, infile)
    outfile = tmp_path / f"output{suffix}"

    mocker.patch(
        "sys.argv",
        [
            "convert_grid_format",
            "--conversion",
            "roff2ecl",
            "--file",
            str(infile),
            "--output",
            str(outfile),
            "--outformat",
            outformat,
            "--mode",
            "grid",
        ],
    )
    cgf.main()

    geogrid = xtgeo.grid_from_file(str(outfile), fformat=read_format)
    assert geogrid.nactive == 35817
    if outformat in {"grdecl", "bgrdecl"}:
        grid = xtgeo.grid_from_file(str(RFILE1), fformat="egrid")
        actnum = xtgeo.gridproperty_from_file(
            str(outfile), fformat=outformat, name="ACTNUM", grid=grid
        )
        assert int(actnum.values.sum()) == 35817


def test_convert_grid_format_roff2ecl_grid_infer_outformat(tmp_path, mocker):
    infile = tmp_path / "input.roff"
    _create_roff_grid(RFILE1, infile)
    outfile = tmp_path / "output.bgrdecl"

    mocker.patch(
        "sys.argv",
        [
            "convert_grid_format",
            "--conversion",
            "roff2ecl",
            "--file",
            str(infile),
            "--output",
            str(outfile),
            "--mode",
            "grid",
        ],
    )
    cgf.main()

    geogrid = xtgeo.grid_from_file(str(outfile), fformat="bgrdecl")
    assert geogrid.nactive == 35817


def test_convert_grid_format_roff2ecl_invalid_outformat(tmp_path, mocker):
    infile = tmp_path / "input.roff"
    _create_roff_grid(RFILE1, infile)
    outfile = tmp_path / "output.grdecl"

    mocker.patch(
        "sys.argv",
        [
            "convert_grid_format",
            "--conversion",
            "roff2ecl",
            "--file",
            str(infile),
            "--output",
            str(outfile),
            "--outformat",
            "nope",
            "--mode",
            "grid",
        ],
    )
    with pytest.raises(SystemExit, match="Invalid outformat"):
        cgf.main()


def test_convert_grid_format_roff2ecl_auto_outformat(tmp_path, mocker):
    infile = tmp_path / "input.roff"
    _create_roff_grid(RFILE1, infile)
    outfile = tmp_path / "output.EGRID"

    mocker.patch(
        "sys.argv",
        [
            "convert_grid_format",
            "--conversion",
            "roff2ecl",
            "--file",
            str(infile),
            "--output",
            str(outfile),
            "--outformat",
            "AUTO",
            "--mode",
            "grid",
        ],
    )
    cgf.main()

    geogrid = xtgeo.grid_from_file(str(outfile), fformat="egrid")
    assert geogrid.nactive == 35817


def test_convert_grid_format_roff2ecl_auto_fallback_logs_and_grdecl(
    tmp_path, mocker, caplog
):
    infile = tmp_path / "input.roff"
    _create_roff_grid(RFILE1, infile)
    outfile = tmp_path / "output.unknown"

    mocker.patch(
        "sys.argv",
        [
            "convert_grid_format",
            "--conversion",
            "roff2ecl",
            "--file",
            str(infile),
            "--output",
            str(outfile),
            "--outformat",
            "auto",
            "--mode",
            "grid",
        ],
    )
    with caplog.at_level(logging.INFO):
        cgf.main()

    assert "defaulting to grdecl" in caplog.text
    grid = xtgeo.grid_from_file(str(RFILE1), fformat="egrid")
    actnum = xtgeo.gridproperty_from_file(
        str(outfile), fformat="grdecl", name="ACTNUM", grid=grid
    )
    assert int(actnum.values.sum()) == 35817


def test_convert_grid_format_roff2ecl_invalid_mode(tmp_path, mocker):
    infile = tmp_path / "input.roff"
    _create_roff_grid(RFILE1, infile)
    outfile = tmp_path / "output.grdecl"

    mocker.patch(
        "sys.argv",
        [
            "convert_grid_format",
            "--conversion",
            "roff2ecl",
            "--file",
            str(infile),
            "--output",
            str(outfile),
            "--mode",
            "restart",
        ],
    )
    with pytest.raises(SystemExit, match="Invalid mode for roff2ecl"):
        cgf.main()


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


@pytest.mark.integration
def test_ert_integration_eclgrid2roff(tmp_path, monkeypatch):
    pytest.importorskip("ert")
    monkeypatch.chdir(tmp_path)
    outfile = "reek_grid.roff"
    ert_config = "config.ert"
    Path(ert_config).write_text(
        f"""
        NUM_REALIZATIONS 1
        RUNPATH .
        FORWARD_MODEL ECLGRID2ROFF(<ECLROOT>={RFILE1}, \
            <OUTPUT>={outfile})
    """,
        encoding="utf-8",
    )

    subprocess.run(["ert", "test_run", "--disable-monitor", ert_config], check=True)
    assert Path(outfile).exists()
    # check number of active cells
    geogrid = xtgeo.grid_from_file(str(outfile))
    assert geogrid.nactive == 35817


@pytest.mark.integration
def test_ert_integration_roff2eclgrid(tmp_path, monkeypatch):
    pytest.importorskip("ert")
    monkeypatch.chdir(tmp_path)
    infile = Path("reek_grid.roff")
    _create_roff_grid(RFILE1, infile)
    outfile = "reek_grid.EGRID"
    ert_config = "config_roff2ecl.ert"
    Path(ert_config).write_text(
        f"""
        NUM_REALIZATIONS 1
        RUNPATH .
        FORWARD_MODEL ROFF2ECLGRID(<INPUT>={infile}, \
            <OUTPUT>={outfile}, <OUTFORMAT>=egrid)
    """,
        encoding="utf-8",
    )

    subprocess.run(["ert", "test_run", "--disable-monitor", ert_config], check=True)
    assert Path(outfile).exists()
    geogrid = xtgeo.grid_from_file(str(outfile), fformat="egrid")
    assert geogrid.nactive == 35817
