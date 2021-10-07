import getpass
import os
import subprocess
import time
from pathlib import Path

import pytest

import subscript.fmu_copy_revision.fmu_copy_revision as fcr

SCRIPTNAME = "fmu_copy_revision"

TOPLEVELS = ["r001", "r002", "20.1.1", "19.2.1", "32.1.1", "something", "users"]

# file structure under folders TOPLEVELS
FILESTRUCTURE = [
    "rms/model/workflow.log",
    "rms/input/faults/f1.dat",
    "rms/input/faults/f2.dat",
    "rms/input/faults/f3.dat",
    "rms/output/any_out.dat",
    ".git/some.txt",
    "attic/any.file",
    "backup/whatever.txt",
    "somefolder/any.backup",
    "somefolder/anybackup99.txt",
    "somefolder/attic/any.txt",
]


@pytest.fixture(name="datatree", scope="session", autouse=True)
def fixture_datatree(tmp_path_factory):
    """Create a tmp folder structure for testing."""
    tmppath = tmp_path_factory.mktemp("data")
    for top in TOPLEVELS:
        (tmppath / top).mkdir(parents=True, exist_ok=True)
        for file in FILESTRUCTURE:
            (tmppath / top / file).parent.mkdir(parents=True, exist_ok=True)
            (tmppath / top / file).touch()

    print("Temporary folder: ", tmppath)
    return tmppath


def test_version(capsys):
    """Testing exclude pattern 1."""
    with pytest.raises(SystemExit):
        fcr.main(["--version"])
    out, _ = capsys.readouterr()
    assert "subscript version" in out


def test_rsync_exclude1(datatree):
    """Testing exclude pattern 1."""
    os.chdir(datatree)
    fcr.main(["--source", "20.1.1", "--profile", "1", "--target", "xxx"])
    assert Path(datatree / "xxx/rms/model/workflow.log").is_file()


def test_construct_target(datatree):
    """Test the construct target routine."""

    os.chdir(datatree)
    today = time.strftime("%Y%m%d")
    user = getpass.getuser()
    expected = "some_20.1.1"

    runner = fcr.CopyFMU()
    runner.do_parse_args("")
    runner.verbosity = True
    runner.source = "20.1.1"
    runner.construct_target("some_20.1.1")

    assert str(runner.target) == str(datatree / expected)

    expected = "users/" + user + "/20.1.1/20.1.1_" + today
    runner.construct_default_target()
    assert expected in str(runner.default_target)


def test_construct_target_shall_fail(datatree):
    """Test the construct target routine with non-existing folder."""
    os.chdir(datatree)

    runner = fcr.CopyFMU()
    runner.do_parse_args("")

    runner.source = "nada"
    with pytest.raises(ValueError) as verr:
        runner.construct_default_target()

    assert "Input folder does not exist" in str(verr)


def test_rsync_profile1(datatree):
    """Testing vs filter profile 1."""
    os.chdir(datatree)
    target = "mytest1"
    source = "20.1.1"
    runner = fcr.CopyFMU()
    runner.do_parse_args("")
    runner.profile = 1
    runner.source = source
    runner.construct_target(target)
    runner.define_filterpattern()
    runner.do_rsyncing()

    assert (datatree / target / "rms" / "input" / "faults" / "f1.dat").exists()
    assert not (datatree / target / "rms" / "input" / "faults" / "x.dat").exists()
    assert (datatree / target / "backup").is_dir()


def test_rsync_profile3(datatree):
    """Testing vs filter profile 3."""
    os.chdir(datatree)
    target = "mytest3"
    source = "20.1.1"
    runner = fcr.CopyFMU()
    runner.do_parse_args("")
    runner.profile = 3
    runner.source = source
    runner.construct_target(target)
    runner.define_filterpattern()
    print(runner.filter)
    runner.do_rsyncing()

    assert (datatree / target / "rms" / "input" / "faults" / "f1.dat").exists()
    assert not (datatree / target / "rms" / "input" / "faults" / "x.dat").exists()
    assert not (datatree / target / "backup").is_dir()


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed."""
    assert subprocess.check_output([SCRIPTNAME, "-h"])


def test_choice_profile1(datatree):
    """Test interactive mode, using profile 1."""
    os.chdir(datatree)
    profile = 1
    target = "users/jriv/xx1"
    user_input = bytes(f"1\n{target}\n{profile}\n", encoding="ascii")
    result = subprocess.run(
        ["fmu_copy_revision"], check=True, input=user_input, stdout=subprocess.PIPE
    )
    print(result.stdout.decode())

    assert "Sync files using multiple threads" in result.stdout.decode()
    assert target in result.stdout.decode()
    assert (datatree / target / "rms" / "input" / "faults" / "f1.dat").exists()
    assert (datatree / target / "rms" / "output" / "any_out.dat").exists()
    assert not (datatree / target / "rms" / "input" / "faults" / "x.dat").exists()
    assert (datatree / target / "backup").is_dir()


def test_choice_profile3(datatree):
    """Test interactive mode, using profile 3."""
    os.chdir(datatree)
    profile = 3
    target = "users/jriv/xx3"
    user_input = bytes(f"1\n{target}\n{profile}\n", encoding="ascii")
    result = subprocess.run(
        ["fmu_copy_revision"], check=True, input=user_input, stdout=subprocess.PIPE
    )
    print(result.stdout.decode())

    assert "Sync files using multiple threads" in result.stdout.decode()
    assert target in result.stdout.decode()
    assert (datatree / target / "rms" / "input" / "faults" / "f1.dat").exists()
    assert not (datatree / target / "rms" / "output" / "any_out.dat").exists()
    assert not (datatree / target / "rms" / "input" / "faults" / "x.dat").exists()
    assert not (datatree / target / "backup").is_dir()


def test_profile_via_args(datatree):
    """Test interactive use but with profile specified on command line"""
    os.chdir(datatree)
    target = "users/jriv/xx_cmd_profile"
    user_input = bytes(f"1\n{target}\n", encoding="ascii")
    result = subprocess.run(
        ["fmu_copy_revision", "--profile", "3"],
        check=True,
        input=user_input,
        stdout=subprocess.PIPE,
    )
    print(result.stdout.decode())

    assert "Sync files using multiple threads" in result.stdout.decode()
    assert (datatree / target / "rms" / "input" / "faults" / "f1.dat").exists()


def test_choice_profile3_double_target(datatree):
    """Test interactive mode, using profile 3 trying writing to same target twice."""
    os.chdir(datatree)
    profile = 3
    target = "users/jriv/xxdouble"
    user_input = bytes(f"1\n{target}\n{profile}\n", encoding="ascii")
    result = subprocess.run(
        ["fmu_copy_revision"], check=True, input=user_input, stdout=subprocess.PIPE
    )

    # repeat
    result = subprocess.run(
        ["fmu_copy_revision"], check=True, input=user_input, stdout=subprocess.PIPE
    )
    assert "So have to exit hard" in result.stdout.decode()

    # repeat with cleanup option
    result = subprocess.run(
        ["fmu_copy_revision", "--cleanup"],
        check=True,
        input=user_input,
        stdout=subprocess.PIPE,
    )
    assert "Doing cleanup of current target." in result.stdout.decode()

    # repeat with merge option
    result = subprocess.run(
        ["fmu_copy_revision", "--merge"],
        check=True,
        input=user_input,
        stdout=subprocess.PIPE,
    )
    assert "Doing merge copy of current target." in result.stdout.decode()

    # Combine --cleanup and --merge which shall error
    with pytest.raises(subprocess.CalledProcessError):
        result = subprocess.run(
            ["fmu_copy_revision", "--cleanup", "--merge"],
            check=True,
            input=user_input,
            stdout=subprocess.PIPE,
        )
