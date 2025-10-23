import datetime
import io
import sys
import textwrap

from subscript.create_date_files import create_date_files


def test_is_iso_date_item_with_date_object():
    assert create_date_files.is_iso_date_item(datetime.date(2020, 7, 1))


def test_is_iso_date_item_with_datetime_object():
    assert create_date_files.is_iso_date_item(datetime.datetime(2020, 7, 1, 12, 0))


def test_is_iso_date_item_with_valid_string():
    assert create_date_files.is_iso_date_item("2020-07-01")


def test_is_iso_date_item_with_invalid_string():
    assert not create_date_files.is_iso_date_item("2020/07/01")
    assert not create_date_files.is_iso_date_item("not-a-date")
    assert not create_date_files.is_iso_date_item("2020-13-01")  # invalid month


def test_is_iso_date_list_accepts_date_objects_and_strings():
    lst = [datetime.date(2018, 1, 1), "2020-07-01"]
    assert create_date_files.is_iso_date_list(lst)


def test_is_iso_date_list_rejects_non_sequences():
    assert not create_date_files.is_iso_date_list(
        "2020-07-01"
    )  # string is not acceptable here
    assert not create_date_files.is_iso_date_list(123)


def test_is_iso_diffdate_list_accepts_pairs_mixed_types():
    good = [
        [datetime.date(2020, 7, 1), datetime.date(2018, 1, 1)],
        ["2020-07-01", "2018-01-01"],
        ["2020-07-01", datetime.date(2018, 1, 1)],
    ]
    assert create_date_files.is_iso_diffdate_list(good)


def test_is_iso_diffdate_list_rejects_bad_pairs():
    bad1 = [["2020-07-01"]]  # wrong length
    bad2 = [["2020-07-01", "not-a-date"]]
    bad3 = "not-a-list"
    assert not create_date_files.is_iso_diffdate_list(bad1)
    assert not create_date_files.is_iso_diffdate_list(bad2)
    assert not create_date_files.is_iso_diffdate_list(bad3)


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


def test_validate_cfg_missing_global_dates():
    cfg = {}
    assert not create_date_files.validate_cfg(cfg, "S", "D")


def test_main(monkeypatch, tmp_path):
    # Prepare paths
    globvar_file = tmp_path / "global_variables.yml"
    single_out = tmp_path / "single_dates.txt"
    diff_out = tmp_path / "diff_dates.txt"

    # Write a minimal YAML file for testing
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

    # Ensure hardcoded output files are created in tmp_path
    monkeypatch.chdir(tmp_path)

    # Pass the YAML file plus the *key names* using the correct flags
    args = [
        "create_date_files",
        str(globvar_file),
        "--single-dates",
        "SEISMIC_HIST_DATES",
        "--diff-dates",
        "SEISMIC_HIST_DIFFDATES",
    ]
    monkeypatch.setattr(sys, "argv", args)

    # Capture stdout (optional)
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)

    # Call main (should not raise SystemExit with correct args)
    create_date_files.main()

    # Assert the hardcoded output files exist in tmp_path
    assert single_out.exists()
    assert diff_out.exists()

    # Check file contents more strictly
    single_text = single_out.read_text()
    assert "2018-01-01" in single_text
    assert "2018-07-01" in single_text

    diff_text = diff_out.read_text()
    assert "2018-07-01" in diff_text
    assert "2018-01-01" in diff_text
