import subprocess
from pathlib import Path

import pytest


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
        ["-e", "FOPT"],
        ["--nolegend", "FOPT"],
        ["--verbose", "FOPT"],
        ["--maxlabels", "100", "--verbose", "FOPR"],
        ["--maxlabels", "0", "--verbose", "FOPR"],
        ["--normalize", "FWCT"],
        ["--normalize", "--singleplot", "FGPR", "FOPR"],
    ],
)
def test_summaryplotter(cmd_args, tmpdir):
    """Test multiple command line invocations"""
    tmpdir.chdir()
    result = subprocess.run(
        ["summaryplot", "--dumpimages"] + cmd_args + [str(DATAFILE)],
        check=True,
    )
    assert result.returncode == 0
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
def test_sysexit(cmd_args, tmpdir):
    """Run command line arguments that should end in failure code"""
    tmpdir.chdir()
    result = subprocess.run(["summaryplot", "--dumpimages"] + cmd_args, shell=True)
    assert result.returncode > 0
    assert not Path("summaryplotdump.png").exists()
    assert not Path("summaryplotdump.pdf").exists()


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["summaryplot", "-h"])
