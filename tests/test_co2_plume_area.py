import pytest

from subscript.co2_plume.plume_area import calc_plume_area


def test_calc_plume_area():
    out = calc_plume_area("tests/testdata_co2_plume/surfaces", "SGAS")
    assert len(out) == 3
    results = [x[1] for x in out]
    results.sort()
    assert results[0] == 0.0
    assert results[1] == pytest.approx(120000.0)
    assert results[2] == pytest.approx(285000.0)
