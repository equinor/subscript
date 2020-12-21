import pytest

from subscript.prtvol2csv import fipmapper


@pytest.mark.parametrize(
    "input_dict, expected_inverse",
    [
        ({}, {}),
        ({"foo": "bar"}, {"bar": "foo"}),
        ({"foo": "1", "bar": "2"}, {"1": "foo", "2": "bar"}),
        ({"foo": "1", "bar": "1"}, {"1": "bar,foo"}),
        ({"foo": 1, "bar": 1}, {1: "bar,foo"}),
        ({1: "foo", 2: "foo"}, {"foo": "1,2"}),
        ({2: "foo", 1: "foo"}, {"foo": "1,2"}),
        ({"foo": [1, 2], "bar": [3, 4]}, {1: "foo", 2: "foo", 3: "bar", 4: "bar"}),
        (
            {"foo": [1, 2], "bar": [3, 4], "Totals": [1, 2, 3, 4]},
            {1: "Totals,foo", 2: "Totals,foo", 3: "Totals,bar", 4: "Totals,bar"},
        ),
    ],
)
def test_invert_map(input_dict, expected_inverse):
    assert fipmapper.invert_map(input_dict) == expected_inverse


def test_invert_map_skipstring():
    input_dict = {"foo": [1, 2], "bar": [3, 4], "Totals": [1, 2, 3, 4]}
    assert fipmapper.invert_map(input_dict, skipstring="Totals") == {
        1: "foo",
        2: "foo",
        3: "bar",
        4: "bar",
    }


def test_fipmapper_empty():
    mapper = fipmapper.FipMapper()
    assert mapper.has_region2fip is False
    assert mapper.has_zone2fip is False
    assert mapper.has_fip2region is False
    assert mapper.has_fip2zone is False


def test_fipmapper():
    mapper = fipmapper.FipMapper(
        mapdata={"fipnum2region": {1: "West-Brent", 2: "East-Sognefjord"}}
    )
    assert mapper.fip2region(1) == "West-Brent"
    assert mapper.fip2region(2) == "East-Sognefjord"
    assert mapper.fip2region([1, 2]) == ["West-Brent", "East-Sognefjord"]
    assert mapper.region2fip("West-Brent") == 1
    assert mapper.region2fip(["West-Brent"]) == [1]
    assert mapper.region2fip(["West-Brent", "East-Sognefjord"]) == [1, 2]
