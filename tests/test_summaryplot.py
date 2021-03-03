import subprocess
from pathlib import Path
import shutil

import ecl

import pytest

from subscript.summaryplot import summaryplot

DATAFILE = Path(__file__).parent / "data/reek/eclipse/model/2_R001_REEK-0.DATA"


@pytest.mark.parametrize(
    "cmd_args",
    [
        ["FOPR"],
        ["-H", "FOPR"],
        ["--hist", "FOPR"],
        ["SWAT:30,50,10"],
        ["SOIL:30,50,10"],
        ["-e", "FOPT"],
        ["--nolegend", "FOPT"],
        ["--verbose", "FOPT"],
        ["--maxlabels", "100", "--verbose", "FOPR"],
        ["--maxlabels", "0", "--verbose", "FOPR"],
        ["--normalize", "FWCT"],
        ["--normalize", "--singleplot", "FGPR", "FOPR"],
    ],
)
def test_summaryplotter(cmd_args, tmpdir, mocker):
    """Test multiple command line invocations"""
    tmpdir.chdir()
    mocker.patch(
        "sys.argv",
        ["summaryplot", "--dumpimages"] + cmd_args + [str(DATAFILE), str(DATAFILE)],
        # DATAFILE is repeated, or else colourby will not be triggered.
    )
    summaryplot.main()
    assert Path("summaryplotdump.png").exists()
    assert Path("summaryplotdump.pdf").exists()


@pytest.mark.parametrize(
    "cmd_args",
    [
        ["--colourby", "FOO", "FOPT"],
        ["--logcolourby", "FOO", "FOPT"],
        ["--colourby", "FOO", "--normalize", "--singleplot", "FGPR", "FOPR"],
        ["--logcolourby", "FOO", "--normalize", "--singleplot", "FGPR", "FOPR"],
    ],
)
def test_two_datafiles(cmd_args, tmpdir, mocker):
    """Mock two different runs. Need different values in parameters.txt
    to trigger particular test lines."""
    tmpdir.chdir()
    Path("realization-0").mkdir()
    Path("realization-1").mkdir()
    for filename in DATAFILE.parent.glob("*"):
        if not filename.is_dir():
            shutil.copy(filename, "realization-0/")
            shutil.copy(filename, "realization-1/")

    Path("realization-0/parameters.txt").write_text("FOO 1\nSAME 10")
    Path("realization-1/parameters.txt").write_text("FOO 2\nSAME 10")
    mocker.patch(
        "sys.argv",
        ["summaryplot", "--dumpimages"]
        + cmd_args
        + [
            str(Path("realization-0") / DATAFILE.name),
            str(Path("realization-1") / DATAFILE.name),
        ],
    )
    summaryplot.main()
    assert Path("summaryplotdump.png").exists()
    assert Path("summaryplotdump.pdf").exists()


@pytest.mark.parametrize(
    "cmd_args, match",
    [
        (
            ["--colourby", "FOO", "FOPT", str(DATAFILE)],
            "Not colouring by parameter when only one DATA file is loaded",
        ),
        (
            ["--colourby", "BAR", "FOPT", str(DATAFILE), str(DATAFILE)],
            "are you sure you typed BAR correctly?",
        ),
        (
            ["--normalize", "-H", "FOPT", str(DATAFILE)],
            "Historical data is not normalized equally to simulated data",
        ),
        (
            # This test is not really a warning, just testing that we have INFO
            # logging turned on when in verbose mode
            ["--verbose", "FOPT", str(DATAFILE)],
            "INFO",
        ),
    ],
)
def test_warnings(cmd_args, match, tmpdir, mocker, caplog):
    """Run command line arguments that give warning"""
    tmpdir.chdir()
    mocker.patch("sys.argv", ["summaryplot", "--dumpimages"] + cmd_args)
    summaryplot.main()
    assert match in caplog.text
    assert Path("summaryplotdump.png").exists()
    assert Path("summaryplotdump.pdf").exists()


@pytest.mark.parametrize(
    "cmd_args",
    [
        ["FOPR", "NOTEXISTING.DATA"],
        ["WOPT:NONE", str(DATAFILE)],
        ["--colourby", "FOO", "--logcolourby", "BAR", "FOPT", str(DATAFILE)],
        ["--colourby", "FOO", "--ensemblemode", "FOPT", str(DATAFILE)],
    ],
)
def test_sysexit(cmd_args, tmpdir, mocker):
    """Run command line arguments that should end in failure"""
    tmpdir.chdir()
    mocker.patch("sys.argv", ["summaryplot", "--dumpimages"] + cmd_args)
    with pytest.raises(SystemExit):
        summaryplot.main()
    assert not Path("summaryplotdump.png").exists()
    assert not Path("summaryplotdump.pdf").exists()


def test_splitvectorsdatafiles():
    result = summaryplot.split_vectorsdatafiles(["FOPT", "FOPR", str(DATAFILE)])
    assert isinstance(result[0][0], ecl.summary.EclSum)
    print(result)
    assert result[1:] == (
        [str(DATAFILE)],
        ["FOPT", "FOPR"],
        [str(DATAFILE.parent.parent.parent / "parameters.txt")],
    )

    # Summary vector order is preserved
    assert summaryplot.split_vectorsdatafiles(["FOPR", "FOPT", str(DATAFILE)])[2] == (
        ["FOPR", "FOPT"]
    )

    # Mix vectors and datafiles:
    assert summaryplot.split_vectorsdatafiles(["FOPR", str(DATAFILE), "FOPT"])[2] == (
        ["FOPR", "FOPT"]
    )


def test_find_parameterstxt_in_current(tmpdir):
    tmpdir.chdir()
    shutil.copy(DATAFILE, "FOO.DATA")
    shutil.copy(str(DATAFILE).replace("DATA", "UNSMRY"), "FOO.UNSMRY")
    shutil.copy(str(DATAFILE).replace("DATA", "SMSPEC"), "FOO.SMSPEC")
    Path("parameters.txt").write_text("FOO 1")
    print(summaryplot.split_vectorsdatafiles(["FOO.DATA"]))
    assert summaryplot.split_vectorsdatafiles(["FOO.DATA"])[3] == [
        str(Path("FOO.DATA").absolute().parent / "parameters.txt")
    ]


def test_find_parameterstxt_two_levels_up(tmpdir):
    tmpdir.chdir()
    tmpdir.mkdir("eclipse")
    tmpdir.mkdir("eclipse/model")
    shutil.copy(DATAFILE, "eclipse/model/FOO.DATA")
    shutil.copy(str(DATAFILE).replace("DATA", "UNSMRY"), "eclipse/model/FOO.UNSMRY")
    shutil.copy(str(DATAFILE).replace("DATA", "SMSPEC"), "eclipse/model/FOO.SMSPEC")
    Path("parameters.txt").write_text("FOO 1")
    assert summaryplot.split_vectorsdatafiles(["eclipse/model/FOO.DATA"])[3] == [
        str(
            Path("eclipse/model/FOO.DATA").absolute().parent.parent.parent
            / "parameters.txt"
        )
    ]


def test_find_parameterstxt_one_level_up(tmpdir):
    tmpdir.chdir()
    tmpdir.mkdir("eclipse")
    shutil.copy(DATAFILE, "eclipse/FOO.DATA")
    shutil.copy(str(DATAFILE).replace("DATA", "UNSMRY"), "eclipse/FOO.UNSMRY")
    shutil.copy(str(DATAFILE).replace("DATA", "SMSPEC"), "eclipse/FOO.SMSPEC")
    Path("parameters.txt").write_text("FOO 1")
    assert summaryplot.split_vectorsdatafiles(["eclipse/FOO.DATA"])[3] == [
        str(Path("eclipse/FOO.DATA").absolute().parent.parent / "parameters.txt")
    ]


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["summaryplot", "-h"])
