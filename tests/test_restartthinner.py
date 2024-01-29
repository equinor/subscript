import os
import shutil
import subprocess
from pathlib import Path

import pytest
from subscript.restartthinner import restartthinner

ECLDIR = Path(__file__).absolute().parent / "data/reek/eclipse/model"

UNRST_FNAME = "2_R001_REEK-0.UNRST"


def test_dryrun(tmp_path, mocker):
    """Test dry-run"""
    shutil.copyfile(ECLDIR / UNRST_FNAME, tmp_path / UNRST_FNAME)

    os.chdir(tmp_path)

    orig_rstindices = restartthinner.get_restart_indices(UNRST_FNAME)
    assert len(orig_rstindices) == 4

    mocker.patch("sys.argv", ["restartthinner", "-d", "-n", "2", UNRST_FNAME])
    restartthinner.main()

    # Check that dry run did not do anything
    assert Path(UNRST_FNAME).exists()
    assert len(orig_rstindices) == len(restartthinner.get_restart_indices(UNRST_FNAME))


def test_first_and_last(tmp_path, mocker):
    """Ask for two restart points, this should give us the first and last."""
    shutil.copyfile(ECLDIR / UNRST_FNAME, tmp_path / UNRST_FNAME)

    os.chdir(tmp_path)

    orig_rstindices = restartthinner.get_restart_indices(UNRST_FNAME)

    mocker.patch("sys.argv", ["restartthinner", "-n", "2", UNRST_FNAME, "--keep"])
    restartthinner.main()

    assert Path(UNRST_FNAME).exists()
    assert Path(UNRST_FNAME + ".orig").exists()  # The backed up file

    new_rstindices = restartthinner.get_restart_indices(UNRST_FNAME)
    assert len(new_rstindices) == 2
    assert new_rstindices[0] == orig_rstindices[0]
    assert new_rstindices[-1] == orig_rstindices[-1]
    assert len(restartthinner.get_restart_indices(UNRST_FNAME + ".orig")) == 4


def test_subdirectory(tmp_path, mocker):
    """Check that we can thin an UNRST file two directory levels down"""
    os.chdir(tmp_path)

    subdir = Path("eclipse/model")
    subdir.mkdir(parents=True)

    shutil.copyfile(ECLDIR / UNRST_FNAME, subdir / UNRST_FNAME)
    orig_rstindices = restartthinner.get_restart_indices(subdir / UNRST_FNAME)

    mocker.patch(
        "sys.argv", ["restartthinner", "-n", "3", str(subdir / UNRST_FNAME), "--keep"]
    )
    print(os.getcwd())
    restartthinner.main()
    print(os.getcwd())

    assert (subdir / UNRST_FNAME).exists()
    assert (subdir / (UNRST_FNAME + ".orig")).exists()  # The backed up file

    new_rstindices = restartthinner.get_restart_indices(subdir / UNRST_FNAME)
    assert len(new_rstindices) == 3
    assert new_rstindices[0] == orig_rstindices[0]
    assert new_rstindices[-1] == orig_rstindices[-1]
    assert (
        len(restartthinner.get_restart_indices(subdir / (UNRST_FNAME + ".orig"))) == 4
    )


def test_get_restart_indices_filenotfound(tmp_path):
    """EclFile.file_report_list segfaults unless the code is careful"""
    with pytest.raises(FileNotFoundError, match="foo"):
        restartthinner.get_restart_indices("foo")
    with pytest.raises(FileNotFoundError, match="foo"):
        restartthinner.get_restart_indices(Path("foo"))

    os.chdir(tmp_path)
    Path("FOO.UNRST").write_text("this is not an unrst file", encoding="utf8")
    with pytest.raises(TypeError, match="which is not a restart file"):
        restartthinner.get_restart_indices("FOO.UNRST")


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed, and the binary tools are available"""
    assert subprocess.check_output(["restartthinner", "-h"])
