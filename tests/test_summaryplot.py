import subprocess
from pathlib import Path

import pytest

from subscript.summaryplot import summaryplot

DATAFILE = Path(__file__).parent / "data/reek/eclipse/model/2_R001_REEK-0.DATA"


@pytest.mark.parametrize(
    "cmd_args",
    [
        ["FOPR"],
        ["-H", "FOPR"],
        ["--hist", "FOPR"],
        ["--colourby", "FOO", "FOPT"],
        ["--logcolourby", "FOO", "FOPT"],
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


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["summaryplot", "-h"])
