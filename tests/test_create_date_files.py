import datetime
import sys
import textwrap

import pytest

from subscript.create_date_files import create_date_files


@pytest.mark.parametrize(
    "value,expected",
    [
        (datetime.date(2020, 7, 1), True),
        (datetime.datetime(2020, 7, 1, 12, 0), True),
        ("2020-07-01", True),
        ("2020/07/01", False),
        ("not-a-date", False),
        ("2020-13-01", False),  # invalid month
        (123, False),
        (None, False),
    ],
)
def test_is_iso_date_item(value, expected):
    assert create_date_files.is_iso_date_item(value) == expected


def test_validate_cfg_success_single_and_diff():
    cfg = {
        "global": {
            "dates": {
                "S": ["2018-01-01", datetime.date(2020, 7, 1)],
                "D": [["2020-07-01", "2018-01-01"]],
            }
        }
    }
    assert create_date_files.validate_cfg(cfg, "S", "D") is True


def test_validate_cfg_handles_optional_none():
    cfg = {
        "global": {
            "dates": {
                "D": [["2020-07-01", "2018-01-01"]],
            }
        }
    }
    # single_dates omitted (None), diff_dates present -> should pass
    assert create_date_files.validate_cfg(cfg, None, "D")


@pytest.mark.parametrize(
    "cfg,single,diff,expected_error",
    [
        (None, "S", "D", "Configuration is empty or invalid"),
        ("not a dict", "S", "D", "does not contain a valid dictionary"),
        ({}, "S", "D", "Missing or invalid 'global' section"),
        ({"global": {}}, "S", "D", "Missing or invalid 'global:dates:' section"),
    ],
)
def test_validate_cfg_structure_failures(cfg, single, diff, expected_error, caplog):
    assert not create_date_files.validate_cfg(cfg, single, diff)
    assert expected_error in caplog.text


def test_validate_cfg_single_dates_missing_key(caplog):
    cfg = {"global": {"dates": {}}}
    assert not create_date_files.validate_cfg(cfg, "MISSING", None)
    assert "Key MISSING not found" in caplog.text


def test_validate_cfg_single_dates_not_list(caplog):
    cfg = {"global": {"dates": {"S": "not-a-list"}}}
    assert not create_date_files.validate_cfg(cfg, "S", None)
    assert "Value for S is not a list" in caplog.text


def test_validate_cfg_single_dates_invalid_format(caplog):
    cfg = {"global": {"dates": {"S": ["2020/07/01"]}}}
    assert not create_date_files.validate_cfg(cfg, "S", None)
    assert "is not in the recommended format YYYY-MM-DD" in caplog.text


def test_validate_cfg_diff_dates_missing_key(caplog):
    cfg = {"global": {"dates": {}}}
    assert not create_date_files.validate_cfg(cfg, None, "MISSING")
    assert "Key MISSING not found" in caplog.text


def test_validate_cfg_diff_dates_not_list(caplog):
    cfg = {"global": {"dates": {"D": "not-a-list"}}}
    assert not create_date_files.validate_cfg(cfg, None, "D")
    assert "Value for D is not a list" in caplog.text


def test_validate_cfg_diff_dates_empty_list(caplog):
    cfg = {"global": {"dates": {"D": []}}}
    assert create_date_files.validate_cfg(cfg, None, "D")
    assert "D is empty" in caplog.text


def test_validate_cfg_diff_dates_pair_not_list(caplog):
    cfg = {"global": {"dates": {"D": ["2020-07-01"]}}}
    assert not create_date_files.validate_cfg(cfg, None, "D")
    assert "Each diff date entry must be a list" in caplog.text


def test_validate_cfg_diff_dates_wrong_length(caplog):
    cfg = {"global": {"dates": {"D": [["2020-07-01"]]}}}
    assert not create_date_files.validate_cfg(cfg, None, "D")
    assert "Diff dates must have two dates per item" in caplog.text


def test_validate_cfg_diff_dates_invalid_format(caplog):
    cfg = {"global": {"dates": {"D": [["2020/07/01", "2018-01-01"]]}}}
    assert not create_date_files.validate_cfg(cfg, None, "D")
    assert "is not in the recommended format YYYY-MM-DD" in caplog.text


@pytest.fixture
def sample_yaml(tmp_path):
    """Create a sample YAML file for testing"""
    globvar_file = tmp_path / "global_variables.yml"
    globvar_file.write_text(
        textwrap.dedent("""
        global:
          dates:
            SEISMIC_HIST_DATES:
              - 2018-01-01
              - 2018-07-01
            SEISMIC_HIST_DIFFDATES:
              - - 2018-07-01
                - 2018-01-01
        """)
    )
    return globvar_file


def test_main_both_args(monkeypatch, tmp_path, sample_yaml, caplog):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "create_date_files",
            str(sample_yaml),
            "--single-dates",
            "SEISMIC_HIST_DATES",
            "--diff-dates",
            "SEISMIC_HIST_DIFFDATES",
        ],
    )

    create_date_files.main()

    assert (tmp_path / "single_dates.txt").exists()
    assert (tmp_path / "diff_dates.txt").exists()
    assert (tmp_path / "single_dates.txt").read_text() == "2018-01-01\n2018-07-01\n"
    assert (tmp_path / "diff_dates.txt").read_text() == "2018-07-01 2018-01-01\n"
    assert "Create single_dates.txt" in caplog.text
    assert "Create diff_dates.txt" in caplog.text
    assert "Done." in caplog.text


def test_main_only_single_dates(monkeypatch, tmp_path, sample_yaml):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "create_date_files",
            str(sample_yaml),
            "--single-dates",
            "SEISMIC_HIST_DATES",
        ],
    )

    create_date_files.main()

    assert (tmp_path / "single_dates.txt").exists()
    assert not (tmp_path / "diff_dates.txt").exists()


def test_main_only_diff_dates(monkeypatch, tmp_path, sample_yaml):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "create_date_files",
            str(sample_yaml),
            "--diff-dates",
            "SEISMIC_HIST_DIFFDATES",
        ],
    )

    create_date_files.main()

    assert not (tmp_path / "single_dates.txt").exists()
    assert (tmp_path / "diff_dates.txt").exists()


def test_main_empty_string_treated_as_none(monkeypatch, tmp_path, sample_yaml):
    """Empty strings should be converted to None via 'or None' logic"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "create_date_files",
            str(sample_yaml),
            "--single-dates",
            "SEISMIC_HIST_DATES",
            "--diff-dates",
            "",
        ],
    )

    create_date_files.main()

    assert (tmp_path / "single_dates.txt").exists()
    assert not (tmp_path / "diff_dates.txt").exists()


def test_main_neither_arg_provided(monkeypatch, tmp_path, sample_yaml, caplog):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["create_date_files", str(sample_yaml)])

    create_date_files.main()

    assert (
        "At least one of --single-dates or --diff-dates must be provided" in caplog.text
    )


def test_main_file_not_found(monkeypatch, tmp_path, caplog):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["create_date_files", "nonexistent.yml", "--single-dates", "S"],
    )

    with pytest.raises(SystemExit):
        create_date_files.main()

    assert "Failed to load nonexistent.yml file" in caplog.text


def test_main_validation_fails(monkeypatch, tmp_path, caplog):
    globvar_file = tmp_path / "global_variables.yml"
    globvar_file.write_text("global:\n  dates: {}\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["create_date_files", str(globvar_file), "--single-dates", "MISSING_KEY"],
    )

    with pytest.raises(SystemExit):
        create_date_files.main()

    assert "Key MISSING_KEY not found" in caplog.text
