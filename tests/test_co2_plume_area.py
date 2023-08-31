import os
from pathlib import Path

import pandas
import pytest

from subscript.co2_plume.plume_area import calc_plume_area, main


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


def test_plume_area(mocker):
    input_path = str(
        Path(__file__).parents[1] / "tests" / "testdata_co2_plume" / "surfaces"
    )
    output_path = str(
        Path(__file__).parents[1] / "tests" / "testdata_co2_plume" / "plume_area.csv"
    )
    mocker.patch("sys.argv", ["--input", input_path, "--output", output_path])
    main()

    df = pandas.read_csv(output_path)
    assert "formation_SGAS" in df.keys()
    assert "formation_AMFG" not in df.keys()
    assert df["formation_SGAS"].iloc[-1] == pytest.approx(285000.0)
    os.remove(output_path)
