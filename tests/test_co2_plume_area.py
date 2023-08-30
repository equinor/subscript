from pathlib import Path

import pytest

from subscript.co2_plume.plume_area import calc_plume_area


def test_calc_plume_area():
    input_path = str(
        Path(__file__).parents[1] / "tests" / "testdata_co2_plume" / "surfaces"
    )
    out = calc_plume_area(input_path, "SGAS")
    assert len(out) == 3
    results = [x[1] for x in out]
    results.sort()
    assert results[0] == 0.0
    assert results[1] == pytest.approx(120000.0)
    assert results[2] == pytest.approx(285000.0)
