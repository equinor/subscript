import datetime

from subscript.create_date_files import create_date_files as cdf


def test_is_iso_date_item_with_date_object():
    assert cdf.is_iso_date_item(datetime.date(2020, 7, 1))


def test_is_iso_date_item_with_datetime_object():
    assert cdf.is_iso_date_item(datetime.datetime(2020, 7, 1, 12, 0))


def test_is_iso_date_item_with_valid_string():
    assert cdf.is_iso_date_item("2020-07-01")


def test_is_iso_date_item_with_invalid_string():
    assert not cdf.is_iso_date_item("2020/07/01")
    assert not cdf.is_iso_date_item("not-a-date")
    assert not cdf.is_iso_date_item("2020-13-01")  # invalid month


def test_is_iso_date_list_accepts_date_objects_and_strings():
    lst = [datetime.date(2018, 1, 1), "2020-07-01"]
    assert cdf.is_iso_date_list(lst)


def test_is_iso_date_list_rejects_non_sequences():
    assert not cdf.is_iso_date_list("2020-07-01")  # string is not acceptable here
    assert not cdf.is_iso_date_list(123)


def test_is_iso_diffdate_list_accepts_pairs_mixed_types():
    good = [
        [datetime.date(2020, 7, 1), datetime.date(2018, 1, 1)],
        ["2020-07-01", "2018-01-01"],
        ["2020-07-01", datetime.date(2018, 1, 1)],
    ]
    assert cdf.is_iso_diffdate_list(good)


def test_is_iso_diffdate_list_rejects_bad_pairs():
    bad1 = [["2020-07-01"]]  # wrong length
    bad2 = [["2020-07-01", "not-a-date"]]
    bad3 = "not-a-list"
    assert not cdf.is_iso_diffdate_list(bad1)
    assert not cdf.is_iso_diffdate_list(bad2)
    assert not cdf.is_iso_diffdate_list(bad3)


def test_validate_cfg_success_single_and_diff(tmp_path):
    cfg = {
        "global": {
            "dates": {
                "S": ["2018-01-01", datetime.date(2020, 7, 1)],
                "D": [["2020-07-01", "2018-01-01"]],
            }
        }
    }
    assert cdf.validate_cfg(cfg, "S", "D") is True


def test_validate_cfg_handles_optional_none():
    cfg = {
        "global": {
            "dates": {
                "D": [["2020-07-01", "2018-01-01"]],
            }
        }
    }
    # single_dates omitted (None), diff_dates present -> should pass
    assert cdf.validate_cfg(cfg, None, "D") is True


def test_validate_cfg_missing_global_dates():
    cfg = {}
    assert cdf.validate_cfg(cfg, "S", "D") is False
