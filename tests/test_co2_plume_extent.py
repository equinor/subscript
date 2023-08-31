import os
from pathlib import Path

import pandas
import pytest

from subscript.co2_plume.plume_extent import (
    __calculate_well_coordinates,
    __export_to_csv,
    calc_plume_extents,
    main,
)


def test_calculate_well_coordinates():
    well_picks_path = str(
        Path(__file__).parents[1] / "tests" / "testdata_co2_plume" / "well_picks.csv"
    )
    x1, y1 = __calculate_well_coordinates("dummmy", "well1", well_picks_path)
    assert x1 == pytest.approx(4050.0)
    assert y1 == pytest.approx(4050.0)
    x2, y2 = __calculate_well_coordinates("dummmy", "well2", well_picks_path)
    assert x2 == pytest.approx(3000.0)
    assert y2 == pytest.approx(3000.0)


def test_calc_plume_extents():
    case_path = str(
        Path(__file__).parents[1]
        / "tests"
        / "data"
        / "reek"
        / "eclipse"
        / "model"
        / "2_R001_REEK-0"
    )
    sgas_results, _, _ = calc_plume_extents(
        case_path,
        (462500.0, 5933100.0),
        threshold_sgas=0.1,
    )
    assert len(sgas_results) == 4
    assert sgas_results[0][1] == 0.0
    assert sgas_results[-1][1] == pytest.approx(1269.1237856341113)

    sgas_results_2, _, _ = calc_plume_extents(
        case_path,
        (462500.0, 5933100.0),
    )
    assert len(sgas_results_2) == 4
    assert sgas_results_2[-1][1] == 0.0

    sgas_results_3, _, _ = calc_plume_extents(
        case_path,
        (462500.0, 5933100.0),
        threshold_sgas=0.0001,
    )
    assert len(sgas_results_3) == 4
    assert sgas_results_3[-1][1] == pytest.approx(2070.3444680185216)


def test_export_to_csv():
    case_path = str(
        Path(__file__).parents[1]
        / "tests"
        / "data"
        / "reek"
        / "eclipse"
        / "model"
        / "2_R001_REEK-0"
    )
    (sgas_results, amfg_results, amfg_key) = calc_plume_extents(
        case_path,
        (462500.0, 5933100.0),
        threshold_sgas=0.1,
    )

    out_file = "temp.csv"
    __export_to_csv(sgas_results, amfg_results, amfg_key, out_file)
    df = pandas.read_csv(out_file)
    assert "MAX_DISTANCE_SGAS" in df.keys()
    assert "MAX_DISTANCE_AMFG" not in df.keys()
    assert df["MAX_DISTANCE_SGAS"].iloc[-1] == pytest.approx(1269.1237856341113)

    os.remove(out_file)


def test_plume_area(mocker):
    case_path = str(
        Path(__file__).parents[1]
        / "tests"
        / "data"
        / "reek"
        / "eclipse"
        / "model"
        / "2_R001_REEK-0"
    )
    output_path = str(
        Path(__file__).parents[1] / "tests" / "testdata_co2_plume" / "plume_extent.csv"
    )
    mocker.patch(
        "sys.argv",
        [
            "--case",
            case_path,
            "--x_coord",
            "462500.0",
            "--y_coord",
            "5933100.0",
            "--threshold_sgas",
            "0.02",
            "--output",
            output_path,
        ],
    )
    main()

    df = pandas.read_csv(output_path)
    assert "MAX_DISTANCE_SGAS" in df.keys()
    assert "MAX_DISTANCE_AMFG" not in df.keys()
    assert df["MAX_DISTANCE_SGAS"].iloc[-1] == pytest.approx(1915.5936794783647)

    os.remove(output_path)
