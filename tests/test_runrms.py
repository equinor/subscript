"""Test runrms script, but manual interactive testing is also needed"""
import os
from subscript.runrms import runrms as rr

TESTRMS1 = "tests/data/reek/rms/reek.rms10.1.3"
TESTRMS2 = "tests/data/reek/rms/reek.rms11.1.0"

FAKE = ""
if not "KOMODO_RELEASE" in os.environ:
    FAKE = "--fake"  # for travis or similar runs


def test_main_no_project():
    """Will only see effect of this when running pytest -s"""
    print(rr.main(["--dryrun", FAKE]))


def test_main_projects():
    """Will only see effect of this when running pytest -s"""
    print(rr.main([TESTRMS2, "--dryrun", FAKE]))


def test_do_parse_args(tmpdir):
    """Test runrms parsing args"""

    runner = rr.RunRMS()

    runner.runloggerfile = tmpdir.mkdir("runner1").join("runrms_usage.log")
    assert runner.args is None

    args = ["--dryrun", FAKE]
    runner.do_parse_args(args)

    print(runner.args)

    assert "dryrun=True" in str(runner.args)


def test_scan_rms(tmpdir):
    """Scan master files in RMS"""
    runner = runrms.RunRMS()

    runner.runloggerfile = tmpdir.mkdir("runner2").join("runrms_usage.log")
    runner.project = "tests/data/reek/rms/reek.rms10.1.3"

    runner.scan_rms()

    assert runner.version_fromproject == "10.1.3"


# def test_runlogger(tmpdir):
#     """Scan master files in RMS"""
#     runner = runrms.RunRMS()

#     runner.runloggerfile = tmpdir.mkdir("runner3").join("runrms_usage.log")
#     runner.runlogger()

#     with open(runner.runloggerfile, "r") as rlog:
#         all = rlog.readlines()
#         assert "rms" in all[-1]
