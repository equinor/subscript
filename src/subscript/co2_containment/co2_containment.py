"""
Calculates the amount of CO2 inside and outside a given perimeter,
and separates the result per formation and phase (gas/dissolved).
Output is a table on CSV format.
"""
import argparse
import dataclasses
import os
import pathlib
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
import shapely.geometry

from subscript.co2_containment.calculate import ContainedCo2, calculate_co2_containment
from subscript.co2_containment.co2_calculation import (
    CalculationType,
    Co2Data,
    _set_calc_type_from_input_string,
    calculate_co2,
)


# pylint: disable=too-many-arguments
def calculate_out_of_bounds_co2(
    grid_file: str,
    unrst_file: str,
    init_file: str,
    compact: bool,
    calc_type_input: str,
    file_containment_polygon: Optional[str] = None,
    file_hazardous_polygon: Optional[str] = None,
    zone_file: Optional[str] = None,
) -> pd.DataFrame:
    """
    Calculates sum of co2 mass or volume at each time step. Use polygons
    to divide into different categories (inside / outside / hazardous). Result
    is a data frame.

    Args:
        grid_file (str): Path to EGRID-file
        unrst_file (str): Path to UNRST-file
        init_file (str): Path to INIT-file
        compact (bool): Write the output to a single file as compact as possible
        calc_type_input (str): Choose mass / cell_volume / actual_volume /
            actual_volume_simplified
        file_containment_polygon (str): Path to polygon defining the
            containment area
        file_hazardous_polygon (str): Path to polygon defining the
            hazardous area
        zone_file (str):

    Returns:
        pd.DataFrame
    """
    co2_data = calculate_co2(
        grid_file, unrst_file, calc_type_input, init_file, zone_file
    )
    print("Done calculating CO2 data for all active grid cells")
    if file_containment_polygon is not None:
        containment_polygon = _read_polygon(file_containment_polygon)
    else:
        containment_polygon = None
    if file_hazardous_polygon is not None:
        hazardous_polygon = _read_polygon(file_hazardous_polygon)
    else:
        hazardous_polygon = None
    return calculate_from_co2_data(
        co2_data, containment_polygon, hazardous_polygon, compact, calc_type_input
    )


def calculate_from_co2_data(
    co2_data: Co2Data,
    containment_polygon: shapely.geometry.Polygon,
    hazardous_polygon: Union[shapely.geometry.Polygon, None],
    compact: bool,
    calc_type_input: str,
) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """
    Use polygons to divide co2 mass or volume into different categories
    (inside / outside / hazardous). Result is a data frame.

    Args:
        co2_data (Co2Data): Mass/volume of CO2 at each time step
        containment_polygon (shapely.geometry.Polygon): Polygon defining the
            containment area
        hazardous_polygon (shapely.geometry.Polygon): Polygon defining the
            hazardous area
        compact (bool):
        calc_type_input (str): Choose mass / cell_volume / actual_volume /
            actual_volume_simplified

    Returns:
        pd.DataFrame
    """
    calc_type = _set_calc_type_from_input_string(calc_type_input.lower())
    print("Calculate contained CO2 using input polygons")
    contained_co2 = calculate_co2_containment(
        co2_data, containment_polygon, hazardous_polygon, calc_type=calc_type
    )
    data_frame = _construct_containment_table(contained_co2)
    if compact:
        return data_frame
    if co2_data.zone is None:
        return _merge_date_rows(data_frame, calc_type)
    return {z: _merge_date_rows(g, calc_type) for z, g in data_frame.groupby("zone")}


def _read_polygon(polygon_file: str) -> shapely.geometry.Polygon:
    """
    Reads a polygon from file.

    Args:
        polygon_file (str): Path to polygon file

    Returns:
        shapely.geometry.Polygon
    """
    poly_xy = np.genfromtxt(polygon_file, skip_header=1, delimiter=",")[:, :2]
    return shapely.geometry.Polygon(poly_xy)


def _construct_containment_table(
    contained_co2: List[ContainedCo2],
) -> pd.DataFrame:
    """
    Creates a data frame from calculated CO2 data.

    Args:
        contained_co2 (list of ContainedCo2): CO2 data divided into phases/locations

    Returns:
        pd.DataFrame
    """
    records = [dataclasses.asdict(c) for c in contained_co2]
    return pd.DataFrame.from_records(records)


# pylint: disable-msg=too-many-locals
def _merge_date_rows(
    data_frame: pd.DataFrame, calc_type: CalculationType
) -> pd.DataFrame:
    """
    Uses input dataframe to calculate various new columns and renames/merges
    some columns.

    Args:
        data_frame (pd.DataFrame): Input data frame
        calc_type (CalculationType): Choose mass / cell_volume /
            actual_volume / actual_volume_simplified from enum CalculationType

    Returns:
        pd.DataFrame: Output data frame
    """
    print("Merging data rows for data frame")
    data_frame = data_frame.drop("zone", axis=1)
    # Total
    df1 = (
        data_frame.drop(["phase", "location"], axis=1)
        .groupby(["date"])
        .sum()
        .rename(columns={"amount": "total"})
    )
    total_df = df1.copy()
    if calc_type == CalculationType.CELL_VOLUME:
        df2 = data_frame.drop("phase", axis=1).groupby(["location", "date"]).sum()
        df2a = df2.loc[("contained",)].rename(columns={"amount": "total_contained"})
        df2b = df2.loc[("outside",)].rename(columns={"amount": "total_outside"})
        df2c = df2.loc[("hazardous",)].rename(columns={"amount": "total_hazardous"})
        for _df in [df2a, df2b, df2c]:
            total_df = total_df.merge(_df, on="date", how="left")
    else:
        df2 = data_frame.drop("location", axis=1).groupby(["phase", "date"]).sum()
        df2a = df2.loc["gas"].rename(columns={"amount": "total_gas"})
        df2b = df2.loc["aqueous"].rename(columns={"amount": "total_aqueous"})
        # Total by containment
        df3 = data_frame.drop("phase", axis=1).groupby(["location", "date"]).sum()
        df3a = df3.loc[("contained",)].rename(columns={"amount": "total_contained"})
        df3b = df3.loc[("outside",)].rename(columns={"amount": "total_outside"})
        df3c = df3.loc[("hazardous",)].rename(columns={"amount": "total_hazardous"})
        # Total by containment and phase
        df4 = data_frame.groupby(["phase", "location", "date"]).sum()
        df4a = df4.loc["gas", "contained"].rename(columns={"amount": "gas_contained"})
        df4b = df4.loc["aqueous", "contained"].rename(
            columns={"amount": "aqueous_contained"}
        )
        df4c = df4.loc["gas", "outside"].rename(columns={"amount": "gas_outside"})
        df4d = df4.loc["aqueous", "outside"].rename(
            columns={"amount": "aqueous_outside"}
        )
        df4e = df4.loc["gas", "hazardous"].rename(columns={"amount": "gas_hazardous"})
        df4f = df4.loc["aqueous", "hazardous"].rename(
            columns={"amount": "aqueous_hazardous"}
        )
        for _df in [df2a, df2b, df3a, df3b, df3c, df4a, df4b, df4c, df4d, df4e, df4f]:
            total_df = total_df.merge(_df, on="date", how="left")
    return total_df.reset_index()


def get_parser() -> argparse.ArgumentParser:
    """
    Make parser and define arguments

    Returns:
        argparse.ArgumentParser
    """
    path_name = pathlib.Path(__file__).name
    parser = argparse.ArgumentParser(path_name)
    parser.add_argument("grid", help="Grid (.EGRID) from which maps are generated")
    parser.add_argument("outfile", help="Output filename")
    parser.add_argument(
        "--containment_polygon",
        help="Polygon that determines the bounds of the containment area."
        "Count all CO2 as contained if polygon is not provided.",
    )
    parser.add_argument(
        "--unrst",
        help="Path to UNRST file. Will assume same base name as grid if not provided",
        default=None,
    )
    parser.add_argument(
        "--init",
        help="Path to INIT file. Will assume same base name as grid if not provided",
        default=None,
    )
    parser.add_argument(
        "--zonefile", help="Path to file containing zone information", default=None
    )
    parser.add_argument(
        "--compact",
        help="Write the output to a single file as compact as possible",
        action="store_true",
    )
    parser.add_argument(
        "--calc_type_input",
        help="CO2 calculation options: mass / cell_volume / actual_volume",
        default="mass",
    )
    parser.add_argument(
        "--hazardous_polygon",
        help="Polygon that determines the bounds of the hazardous area",
        default=None,
    )

    return parser


def process_args() -> argparse.Namespace:
    """
    Process arguments and do some minor conversions.

    Returns:
        argparse.Namespace
    """
    args = get_parser().parse_args()
    if args.unrst is None:
        args.unrst = args.grid.replace(".EGRID", ".UNRST")
    if args.init is None:
        args.init = args.grid.replace(".EGRID", ".INIT")
    args.calc_type_input = args.calc_type_input.lower()
    return args


def check_input(arguments: argparse.Namespace):
    """
    Checks that input arguments are valid. Checks if files exist etc.

    Args:
        arguments (argparse.Namespace): Input arguments

    Raises:
        ValueError: If calc_type_input is invalid
        FileNotFoundError: If one or more input files are not found
    """
    CalculationType.check_for_key(arguments.calc_type_input.upper())

    files_not_found = []
    if not os.path.isfile(arguments.grid):
        files_not_found.append(arguments.grid)
    if not os.path.isfile(arguments.unrst):
        files_not_found.append(arguments.unrst)
    if not os.path.isfile(arguments.init):
        files_not_found.append(arguments.init)
    if arguments.zonefile is not None and not os.path.isfile(arguments.zonefile):
        files_not_found.append(arguments.zonefile)
    if arguments.containment_polygon is not None and not os.path.isfile(
        arguments.containment_polygon
    ):
        files_not_found.append(arguments.containment_polygon)
    if arguments.hazardous_polygon is not None and not os.path.isfile(
        arguments.hazardous_polygon
    ):
        files_not_found.append(arguments.hazardous_polygon)
    if files_not_found:
        error_text = "The following file(s) were not found:"
        for file in files_not_found:
            error_text += "\n  * " + file
        raise FileNotFoundError(error_text)


def main() -> None:
    """
    Takes input arguments and calculates total co2 mass or volume at each time
    step, divided into different phases and locations. Creates a data frame,
    then exports the data frame to a csv file.
    """
    arguments_processed = process_args()
    check_input(arguments_processed)
    data_frame = calculate_out_of_bounds_co2(
        arguments_processed.grid,
        arguments_processed.unrst,
        arguments_processed.init,
        arguments_processed.compact,
        arguments_processed.calc_type_input,
        arguments_processed.containment_polygon,
        arguments_processed.hazardous_polygon,
        arguments_processed.zonefile,
    )
    if isinstance(data_frame, dict):
        out_file = pathlib.Path(arguments_processed.outfile)
        for key, _df in data_frame.items():
            _df.to_csv(
                out_file.with_name(f"{out_file.stem}_{key}{out_file.suffix}"),
                index=False,
            )
    else:
        data_frame.to_csv(arguments_processed.outfile, index=False)


if __name__ == "__main__":
    main()
