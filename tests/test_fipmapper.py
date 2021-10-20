"""Test the deprecated location of fipmapper in subscript.

It has been moved to fmu-tools. Remove this test function when
src/subscript/prtvol2csv/fipmapper.py is purged"""
import pytest

from subscript.prtvol2csv import fipmapper


@pytest.mark.parametrize(
    "input_dict, expected_inverse",
    [
        ({}, {}),
    ],
)
def test_invert_map(input_dict, expected_inverse):
    with pytest.warns(FutureWarning):
        assert fipmapper.invert_map(input_dict) == expected_inverse


def test_invert_map_skipstring():
    input_dict = {"foo": [1, 2], "bar": [3, 4], "Totals": [1, 2, 3, 4]}
    with pytest.warns(FutureWarning):
        assert fipmapper.invert_map(input_dict, skipstring="Totals") == {
            1: ["foo"],
            2: ["foo"],
            3: ["bar"],
            4: ["bar"],
        }


def test_fipmapper_empty():
    with pytest.warns(FutureWarning):
        mapper = fipmapper.FipMapper()
    assert mapper.has_region2fip is False
    assert mapper.has_zone2fip is False
    assert mapper.has_fip2region is False
    assert mapper.has_fip2zone is False


def test_webviz_to_prtvol2csv():
    with pytest.warns(FutureWarning):
        assert fipmapper.webviz_to_prtvol2csv({}) == {}
