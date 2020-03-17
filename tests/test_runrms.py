"""Test runrms script"""

from subscript.runrms import runrms
import subscript.runrms.runrms as runrmsexe


def test_main_no_project():
    cmd = runrmsexe.main(["--dryrun"])
    print(cmd)


def test_main_projects():
    cmd = runrmsexe.main(["data/reek/rms/reek.rms10.1.3", "--dryrun"])
    print(cmd)


def test_do_parse_args(tmpdir):

    runner = runrms.RunRMS()

    runner.runloggerfile = tmpdir.mkdir("runner1").join("runrms_usage.log")
    assert runner.args is None

    args = ["--dryrun"]
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
