"""Test runrms script, but manual interactive testing is also needed."""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
import yaml
from subscript.runrms import runrms as rr

# the resolve().as_posix() for pytest tmp_path fixture (workaround)
TESTRMS1 = (Path(__file__).parent / "data/reek/rms/reek.rms10.1.3").resolve().as_posix()
TESTRMS2 = (Path(__file__).parent / "data/reek/rms/reek.rms11.1.0").resolve().as_posix()
TESTSETUP = (Path(__file__).parent / "testdata_runrms/runrms.yml").resolve().as_posix()


def test_main_no_project():
    """Will only see effect of this when running pytest -s."""
    print(rr.main(["--dryrun", "--setup", TESTSETUP]))


def test_main_projects():
    """Will only see effect of this when running pytest -s."""
    print(rr.main([TESTRMS2, "--dryrun", "--setup", TESTSETUP]))


def test_do_parse_args(tmp_path):
    """Test runrms parsing args."""
    runner = rr.RunRMS()

    (tmp_path / "runner1").mkdir()
    runner.runloggerfile = tmp_path / "runner1" / "runrms_usage.log"
    assert runner.args is None

    args = ["--dryrun", "--setup", TESTSETUP]
    runner.do_parse_args(args)

    print(runner.args)

    assert "dryrun=True" in str(runner.args)


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed."""
    assert subprocess.check_output(["runrms", "-h"])


def test_scan_rms(tmp_path):
    """Scan master files in RMS."""
    runner = rr.RunRMS()

    (tmp_path / "runner2").mkdir()
    runner.runloggerfile = tmp_path / "runner2" / "runrms_usage.log"
    runner.project = TESTRMS1

    runner.scan_rms()

    assert runner.version_fromproject == "10.1.3"


def test_scan_mocked_rms(tmp_path):
    """Test RMS project scanning on mocked projects"""
    os.chdir(tmp_path)
    runner = rr.RunRMS()
    runner.project = "notexisting"
    runner.scan_rms()

    mocked_rms = "mockedproject.rms18.0.0"
    os.mkdir(mocked_rms)
    runner.project = mocked_rms
    with pytest.raises(SystemExit):
        # Empty dir is an invalid RMS project:
        runner.scan_rms()

    # Mock a .master:
    dot_master = Path(mocked_rms) / ".master"
    dot_master.write_text("", encoding="utf8")
    runner.scan_rms()  # No errors from this
    assert runner.version_fromproject is None

    # Add version to the .master:
    dot_master.write_text("release : 18.0.0", encoding="utf8")
    runner.scan_rms()
    assert runner.version_fromproject == "18.0.0"

    # Add version in wrong place to the .master:
    dot_master.write_text("End GEOMATIC\nrelease : 18.0.0", encoding="utf8")
    runner = rr.RunRMS()
    runner.project = mocked_rms
    runner.scan_rms()
    assert runner.version_fromproject is None

    # Test mkeys:
    dot_master.write_text(
        "fileversion : foo\nuser : foobert\nvariant : bogus bogus bogus",
        encoding="utf8",
    )
    runner = rr.RunRMS()
    runner.project = mocked_rms
    runner.scan_rms()
    assert runner.fileversion == "foo"
    assert runner.user == "foobert"
    assert runner.variant == "unknown"  # Too many strings provided in .master


def test_runlogger(tmp_path):
    """Test that we can log to files"""
    os.chdir(tmp_path)

    runner = rr.RunRMS()
    runner.runloggerfile = "not-existing"
    # Nothing happens, skipped because it does not exist
    runner.runlogger()

    # Make an empty file and prove that it will be logged to:
    Path("foo-log").write_text("", encoding="utf8")
    assert not Path("foo-log").read_text(encoding="utf8")
    runner.runloggerfile = "foo-log"
    runner.runlogger()
    assert Path("foo-log").read_text(encoding="utf8")


@pytest.mark.parametrize(
    "os_id, expected",
    [
        ("Red Hat Enterprise Linux Server release 6.0 (bar)", "x86_64_RH_6"),
        ("Red Hat Enterprise Linux Server release 7.2 (Maipo)", "x86_64_RH_7"),
        ("Red Hat Enterprise Linux Server release 8.2 (foo)", "x86_64_RH_8"),
        ("Red Hat Enterprise Linux release 8.9 (Ootpa)", "x86_64_RH_8"),
        pytest.param("foobar", None, marks=pytest.mark.xfail(raises=ValueError)),
    ],
)
def test_detect_os(os_id, expected, tmp_path, mocker):
    """Test parsing of Redhat release text file"""
    os.chdir(tmp_path)
    release_file = Path("redhat-release")
    release_file.write_text(os_id, encoding="utf8")
    mocker.patch("subscript.runrms.runrms.RHEL_ID", release_file)
    runner = rr.RunRMS()
    assert runner.osver == expected


def test_detect_os_default(tmp_path, mocker):
    """Test the default OS if we don't find a redhat release file"""
    os.chdir(tmp_path)
    release_file = Path("not-existing-file")
    mocker.patch("subscript.runrms.runrms.RHEL_ID", release_file)
    runner = rr.RunRMS()
    assert runner.osver == "x86_64_RH_7"


def test_store_pythonpath(mocker):
    """Test that the PYTHONPATH env variable will be stored by the script"""
    mocker.patch("os.environ", {"PYTHONPATH": "foo/bar/com"})
    runner = rr.RunRMS()
    assert "foo/bar/com" in runner.oldpythonpath
    assert runner.pythonpath is None

    mocker.patch("os.environ", {"PYTHONPATH": ""})
    runner = rr.RunRMS()
    assert runner.oldpythonpath == ""
    assert runner.pythonpath is None

    mocker.patch("os.environ", {"PYTHONdummyPATH": "foo/bar/com"})
    runner = rr.RunRMS()
    assert runner.oldpythonpath == ""
    assert runner.pythonpath is None


def test_store_rmspluginpath(mocker):
    """Test that the RMS_PLUGINS_LIBRARY env variable will be stored by the script"""
    mocker.patch("os.environ", {"RMS_PLUGINS_LIBRARY": "foo/bar/com"})
    runner = rr.RunRMS()
    assert "foo/bar/com" in runner.oldpluginspath
    assert runner.pluginspath is None

    mocker.patch("os.environ", {"PYTHONbarfPATH": "foo/bar/com"})
    runner = rr.RunRMS()
    assert runner.oldpythonpath == ""
    assert runner.pythonpath is None


def test_parse_setup(tmp_path, mocker):
    """Test parsing of a setup yaml file"""
    os.chdir(tmp_path)
    setupfile = "foo.yml"
    mocker.patch("subscript.runrms.runrms.SETUP", setupfile)
    runner = rr.RunRMS()
    runner.do_parse_args(["runrms", "--debug"])
    with pytest.raises(FileNotFoundError):
        runner.parse_setup()

    # Write dummy file:
    Path(setupfile).write_text(yaml.dump({}), encoding="utf8")
    # No errors from this, even if the setup is empty:
    runner.parse_setup()
    assert runner.setup == {}
    assert runner.setupfile == setupfile


def test_requested_rms_version(tmp_path, mocker):
    """Test handling of a requested RMS version (in yaml setup file)"""
    os.chdir(tmp_path)
    setupfile = "setup.yml"
    mocker.patch("subscript.runrms.runrms.SETUP", setupfile)
    runner = rr.RunRMS()
    runner.do_parse_args(["runrms", "--debug"])

    with pytest.raises(KeyError, match="rms"):
        Path(setupfile).write_text(yaml.dump({}), encoding="utf8")
        runner.parse_setup()
        runner.requested_rms_version()

    with pytest.raises(RuntimeError, match="Executable is not found"):
        Path(setupfile).write_text(
            yaml.dump({"rms": {"18.0.0": {"default": True}}}), encoding="utf8"
        )
        runner.parse_setup()
        runner.requested_rms_version()

    with pytest.raises(KeyError, match="rms_nonstandard"):
        Path(setupfile).write_text(
            yaml.dump({"rms": {"18.0.0": {"default": True}}}), encoding="utf8"
        )
        runner.parse_setup()
        runner.version_fromproject = "17.0.0"
        runner.requested_rms_version()

    Path(setupfile).write_text(
        yaml.dump(
            {"rms": {"18.0.0": {"default": True, "exe": "somefile", "pythonpath": ""}}}
        ),
        encoding="utf8",
    )
    runner.parse_setup()
    runner.version_fromproject = "18.0.0"
    runner.requested_rms_version()
    assert runner.version_requested == "18.0.0"


@pytest.mark.skipif(
    not shutil.which("disable_komodo_exec"),
    reason="The executable disable_komodo_exec is not available",
)
def test_runrms_disable_komodo_exec(tmp_path, monkeypatch):
    """Testing integration with Komodo."""
    os.chdir(tmp_path)
    Path("rms_fake").write_text(
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
if PATH_PREFIX != "/prog/res/roxapi/bin":
    errors.append(f"The path for run_external is not correct {PATH_PREFIX}")

if "KOMODO_RELEASE" in os.environ:
    errors.append(f"komodo release set: {os.environ['KOMODO_RELEASE']}")

if errors:
    for e in errors:
        print(e)
    sys.exit(1)
sys.exit(0)
""",
        encoding="utf8",
    )

    os.chmod("rms_fake", os.stat("rms_fake").st_mode | stat.S_IEXEC)
    monkeypatch.setenv("KOMODO_RELEASE", f"{os.getcwd()}/bleeding")
    monkeypatch.setenv("_PRE_KOMODO_MANPATH", "some/man/path")
    monkeypatch.setenv("_PRE_KOMODO_LD_LIBRARY_PATH", "some/ld/path")
    runner = rr.RunRMS()
    runner.do_parse_args(["-v", "10.1.3"])
    runner.parse_setup()
    runner.version_requested = "10.1.3"
    runner.exe = "./rms_fake"
    runner.pythonpath = ""
    runner.pluginspath = "rms/plugins/path"

    return_code = runner.launch_rms(empty=True)
    assert return_code == 0
