"""Test runrms script, but manual interactive testing is also needed"""
import subprocess
import os
import stat
import pytest
import shutil

from subscript.runrms import runrms as rr

TESTRMS1 = "tests/data/reek/rms/reek.rms10.1.3"
TESTRMS2 = "tests/data/reek/rms/reek.rms11.1.0"


def test_main_no_project():
    """Will only see effect of this when running pytest -s"""
    print(rr.main(["--dryrun"]))


def test_main_projects():
    """Will only see effect of this when running pytest -s"""
    print(rr.main([TESTRMS2, "--dryrun"]))


def test_do_parse_args(tmpdir):
    """Test runrms parsing args"""

    runner = rr.RunRMS()

    runner.runloggerfile = tmpdir.mkdir("runner1").join("runrms_usage.log")
    assert runner.args is None

    args = ["--dryrun"]
    runner.do_parse_args(args)

    print(runner.args)

    assert "dryrun=True" in str(runner.args)


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["runrms", "-h"])


def test_scan_rms(tmpdir):
    """Scan master files in RMS"""
    runner = rr.RunRMS()

    runner.runloggerfile = tmpdir.mkdir("runner2").join("runrms_usage.log")
    runner.project = TESTRMS1

    runner.scan_rms()

    assert runner.version_fromproject == "10.1.3"


@pytest.mark.skipif(
    not shutil.which("disable_komodo_exec"),
    reason="The executable disable_komodo_exec is not available",
)
def test_runrms_disable_komodo_exec(tmpdir, monkeypatch):
    with tmpdir.as_cwd():
        with open("rms_fake", "w") as f:
            f.write(
                """\
#!/usr/bin/env python3
import os
import sys

errors = []

BACKUPS_check=set([
    "PATH",
    "KOMODO_RELEASE",
    "MANPATH",
    "LD_LIBRARY_PATH",
    "PYTHONPATH"
])
BACKUPS = set(os.environ["BACKUPS"].split(":"))

if BACKUPS != BACKUPS_check:
    errors.append(f"BACKUP error: {BACKUPS} not equal to {BACKUPS_check}")

for backup in BACKUPS:
    if f"{backup}_BACKUP" not in os.environ:
        errors.append(f"The backup for {backup} is not set")

PATH = os.environ["PATH"]
PATH_PREFIX = os.environ["PATH_PREFIX"]
if PATH.split(":")[0] != PATH_PREFIX:
    errors.append(f"PATH_PREFIX ({PATH_PREFIX}), was not prepended to PATH ({PATH})")
if PATH_PREFIX != "/project/res/roxapi/bin":
    errors.append(f"The path for run_external is not corrent {PATH_PREFIX}")

if "KOMODO_RELEASE" in os.environ:
    errors.append(f"komodo release set: {os.environ['KOMODO_RELEASE']}")

if errors:
    for e in errors:
        print(e)
    sys.exit(1)
sys.exit(0)
"""
            )

        st = os.stat("rms_fake")
        os.chmod("rms_fake", st.st_mode | stat.S_IEXEC)
        monkeypatch.setenv("KOMODO_RELEASE", f"{os.getcwd()}/bleeding")
        monkeypatch.setenv("_PRE_KOMODO_MANPATH", "some/man/path")
        monkeypatch.setenv("_PRE_KOMODO_LD_LIBRARY_PATH", "some/ld/path")

        runner = rr.RunRMS()
        runner.do_parse_args(["-v", "10.1.3"])
        runner.version_requested = "10.1.3"
        runner.exe = "./rms_fake"
        runner.pythonpath = ""
        runner.pluginspath = "rms/plugins/path"

        return_code = runner.launch_rms(empty=True)
        assert return_code == 0
