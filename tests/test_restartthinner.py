import datetime
import logging
import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from subscript.restartthinner import restartthinner

ECLDIR = Path(__file__).absolute().parent / "data/reek/eclipse/model"

UNRST_FNAME = "2_R001_REEK-0.UNRST"


def test_dryrun(tmp_path, mocker, monkeypatch):
    """Test dry-run"""
    shutil.copyfile(ECLDIR / UNRST_FNAME, tmp_path / UNRST_FNAME)

    monkeypatch.chdir(tmp_path)

    orig_rstindices = restartthinner.get_restart_indices(UNRST_FNAME)
    assert len(orig_rstindices) == 4

    mocker.patch("sys.argv", ["restartthinner", "-d", "-n", "2", UNRST_FNAME])
    restartthinner.main()

    # Check that dry run did not do anything
    assert Path(UNRST_FNAME).exists()
    assert len(orig_rstindices) == len(restartthinner.get_restart_indices(UNRST_FNAME))


def test_first_and_last(tmp_path, mocker, monkeypatch):
    """Ask for two restart points, this should give us the first and last."""
    shutil.copyfile(ECLDIR / UNRST_FNAME, tmp_path / UNRST_FNAME)

    monkeypatch.chdir(tmp_path)

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


def test_subdirectory(tmp_path, mocker, monkeypatch):
    """Check that we can thin an UNRST file two directory levels down"""
    monkeypatch.chdir(tmp_path)

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


def test_get_restart_indices_filenotfound(tmp_path, monkeypatch):
    """EclFile.file_report_list segfaults unless the code is careful"""
    with pytest.raises(FileNotFoundError, match="foo"):
        restartthinner.get_restart_indices("foo")
    with pytest.raises(FileNotFoundError, match="foo"):
        restartthinner.get_restart_indices(Path("foo"))

    monkeypatch.chdir(tmp_path)
    Path("FOO.UNRST").write_text("this is not an unrst file", encoding="utf8")
    with pytest.raises(TypeError, match="which is not a restart file"):
        restartthinner.get_restart_indices("FOO.UNRST")


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed, and the binary tools are available"""
    assert subprocess.check_output(["restartthinner", "-h"])


def test_single_restart_slice(tmp_path, mocker, monkeypatch):
    """Test requesting only 1 restart (should return just the last date)."""
    shutil.copyfile(ECLDIR / UNRST_FNAME, tmp_path / UNRST_FNAME)
    monkeypatch.chdir(tmp_path)

    orig_rstindices = restartthinner.get_restart_indices(UNRST_FNAME)

    mocker.patch("sys.argv", ["restartthinner", "-n", "1", UNRST_FNAME])
    restartthinner.main()

    new_rstindices = restartthinner.get_restart_indices(UNRST_FNAME)
    assert len(new_rstindices) == 1
    assert new_rstindices[0] == orig_rstindices[-1]  # Should be the last date


def test_negative_restarts_error(tmp_path, mocker, capsys, monkeypatch):
    """Test that negative restart count gives an error."""
    shutil.copyfile(ECLDIR / UNRST_FNAME, tmp_path / UNRST_FNAME)
    monkeypatch.chdir(tmp_path)

    mocker.patch("sys.argv", ["restartthinner", "-n", "-1", UNRST_FNAME])
    with pytest.raises(SystemExit) as excinfo:
        restartthinner.main()

    assert excinfo.value.code == 2  # argparse error exit code
    captured = capsys.readouterr()
    assert "positive number" in captured.err


def test_zero_restarts_error(tmp_path, mocker, capsys, monkeypatch):
    """Test that zero restart count gives an error."""
    shutil.copyfile(ECLDIR / UNRST_FNAME, tmp_path / UNRST_FNAME)
    monkeypatch.chdir(tmp_path)

    mocker.patch("sys.argv", ["restartthinner", "-n", "0", UNRST_FNAME])
    with pytest.raises(SystemExit) as excinfo:
        restartthinner.main()

    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "positive number" in captured.err


def test_data_file_error(tmp_path, mocker, capsys, monkeypatch):
    """Test that providing a DATA file instead of UNRST gives an error."""
    monkeypatch.chdir(tmp_path)
    Path("TEST.DATA").touch()

    mocker.patch("sys.argv", ["restartthinner", "-n", "2", "TEST.DATA"])
    with pytest.raises(SystemExit) as excinfo:
        restartthinner.main()

    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "UNRST file" in captured.err


def test_find_resdata_app_not_found():
    """Test that OSError is raised when resdata tools are not in PATH."""
    with (
        patch.object(shutil, "which", return_value=None),
        pytest.raises(OSError, match="nonexistent_tool not found in PATH"),
    ):
        restartthinner.find_resdata_app("nonexistent_tool")


def test_find_resdata_app_with_suffix():
    """Test that find_resdata_app tries different suffixes."""
    call_count = {"count": 0}

    def mock_which(name):
        call_count["count"] += 1
        # Simulate finding tool with .c.x suffix on second try
        if name == "rd_unpack.c.x":
            return "/usr/bin/rd_unpack.c.x"
        return None

    with patch.object(shutil, "which", side_effect=mock_which):
        result = restartthinner.find_resdata_app("rd_unpack")
        assert result == "/usr/bin/rd_unpack.c.x"
        assert call_count["count"] == 2  # Tried .x first, then .c.x


def test_date_slicer():
    """Test date_slicer matches slicedates to nearest restart dates."""

    # Create test data with 4 restart dates
    restart_dates = [
        datetime.datetime(2020, 1, 1),
        datetime.datetime(2020, 4, 1),
        datetime.datetime(2020, 7, 1),
        datetime.datetime(2020, 10, 1),
    ]
    restart_indices = [0, 1, 2, 3]

    # Slice dates that should match to indices 0, 2, 3
    slice_dates = [
        pd.Timestamp("2020-01-15"),  # Closest to Jan 1 -> index 0
        pd.Timestamp("2020-06-15"),  # Closest to Jul 1 -> index 2
        pd.Timestamp("2020-11-01"),  # Closest to Oct 1 -> index 3
    ]

    result = restartthinner.date_slicer(slice_dates, restart_dates, restart_indices)
    assert result == [0, 2, 3]


def test_quiet_mode(tmp_path, mocker, caplog, monkeypatch):
    """Test that quiet mode suppresses log output."""
    shutil.copyfile(ECLDIR / UNRST_FNAME, tmp_path / UNRST_FNAME)
    monkeypatch.chdir(tmp_path)

    # Run with quiet mode
    with caplog.at_level(logging.INFO, logger="subscript"):
        mocker.patch("sys.argv", ["restartthinner", "-q", "-n", "2", UNRST_FNAME])
        restartthinner.main()

    # Check that log output is empty
    assert len(caplog.text) == 0
