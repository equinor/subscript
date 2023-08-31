#!/usr/bin/env python

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from ecl.eclfile import EclFile
from ecl.grid import EclGrid

DEFAULT_THRESHOLD_SGAS = 0.2
DEFAULT_THRESHOLD_AMFG = 0.0005


def __make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Calculate plume extent (distance)")
    parser.add_argument("case", help="Name of Eclipse case")
    parser.add_argument(
        "--well_name",
        help="Name of injection well to calculate plume extent from",
        default=None,
    )
    parser.add_argument(
        "--x_coord",
        help="Value of x coordinate to calculate plume extent from. \
            Can be used instead of --well_name.",
    )
    parser.add_argument(
        "--y_coord",
        help="Value of y coordinate to calculate plume extent from. \
            Can be used instead of --well_name.",
    )
    parser.add_argument(
        "--output",
        help="Path to output CSV file",
        default=None,
    )
    parser.add_argument(
        "--threshold_sgas",
        default=DEFAULT_THRESHOLD_SGAS,
        type=float,
        help="Threshold for SGAS",
    )
    parser.add_argument(
        "--threshold_amfg",
        default=DEFAULT_THRESHOLD_AMFG,
        type=float,
        help="Threshold for AMFG",
    )

    return parser


def calc_plume_extents(
    case: str,
    injxy: Tuple[float, float],
    threshold_sgas: float = DEFAULT_THRESHOLD_SGAS,
    threshold_amfg: float = DEFAULT_THRESHOLD_AMFG,
) -> Tuple[List[List], Optional[List[List]], str]:
    """
    Find plume extents per date for SGAS and AMFG/XMF2.
    """
    grid = EclGrid("{}.EGRID".format(case))
    unrst = EclFile("{}.UNRST".format(case))

    # First calculate distance from injection point to center of all cells
    nactive = grid.get_num_active()
    dist = np.zeros(shape=(nactive,))
    for i in range(nactive):
        center = grid.get_xyz(active_index=i)
        dist[i] = np.sqrt((center[0] - injxy[0]) ** 2 + (center[1] - injxy[1]) ** 2)

    sgas_results = __find_max_distances_per_time_step(
        "SGAS", threshold_sgas, unrst, dist
    )
    print(sgas_results)

    if "AMFG" in unrst:
        amfg_results = __find_max_distances_per_time_step(
            "AMFG", threshold_amfg, unrst, dist
        )
        amfg_key = "AMFG"
    elif "XMF2" in unrst:
        amfg_results = __find_max_distances_per_time_step(
            "XMF2", threshold_amfg, unrst, dist
        )
        amfg_key = "XMF2"
    else:
        amfg_results = None
        amfg_key = "-"
    print(amfg_results)

    return (sgas_results, amfg_results, amfg_key)


def __find_max_distances_per_time_step(
    attribute_key: str, threshold: float, unrst: EclFile, dist: np.ndarray
) -> List[List]:
    """
    Find max plume distance for each step
    """
    nsteps = len(unrst.report_steps)
    dist_vs_date = np.zeros(shape=(nsteps,))
    for i in range(nsteps):
        data = unrst[attribute_key][i].numpy_view()
        plumeix = np.where(data > threshold)[0]
        maxdist = 0.0
        if len(plumeix) > 0:
            maxdist = dist[plumeix].max()

        dist_vs_date[i] = maxdist

    output = []
    for i, d in enumerate(unrst.report_dates):
        temp = [d.strftime("%Y-%m-%d"), dist_vs_date[i]]
        output.append(temp)

    return output


def __export_to_csv(
    sgas_results: List[List],
    amfg_results: Optional[List[List]],
    amfg_key: str,
    output_file: str,
):
    # Convert into Pandas DataFrames
    sgas_df = pd.DataFrame.from_records(
        sgas_results, columns=["DATE", "MAX_DISTANCE_SGAS"]
    )
    if amfg_results is not None:
        amfg_df = pd.DataFrame.from_records(
            amfg_results, columns=["DATE", "MAX_DISTANCE_" + amfg_key]
        )

        # Merge them together
        df = pd.merge(sgas_df, amfg_df, on="DATE")
    else:
        df = sgas_df

    # Export to CSV
    df.to_csv(output_file, index=False)


def __calculate_well_coordinates(
    case: str, well_name: str, well_picks_path: Optional[str] = None
) -> Tuple[float, float]:
    """
    Find coordinates of injection point
    """
    if well_picks_path is None:
        p = Path(case).parents[2]
        p2 = p / "share" / "results" / "wells" / "well_picks.csv"
    else:
        p2 = Path(well_picks_path)

    df = pd.read_csv(p2)

    df = df[df["WELL"] == well_name]

    df = df[df["X_UTME"].notna()]
    df = df[df["Y_UTMN"].notna()]

    max_id = df["MD"].idxmax()
    max_md_row = df.loc[max_id]
    x = max_md_row["X_UTME"]
    y = max_md_row["Y_UTMN"]

    return (x, y)


def main():
    """
    Calculate plume extent using EGRID and UNRST-files. Calculated for SGAS
    and AMFG/XMF2. Output is plume extent per date written to a CSV file.
    """
    args = __make_parser().parse_args()

    if args.x_coord and args.y_coord:
        injxy = (float(args.x_coord), float(args.y_coord))
    elif args.well_name:
        injxy = __calculate_well_coordinates(
            args.case,
            args.well_name,
        )
    else:
        print(
            "Invalid input. Specify either --well_name or \
            provide both --x_coord and --y_coord."
        )
        exit()

    (sgas_results, amfg_results, amfg_key) = calc_plume_extents(
        args.case,
        injxy,
        args.threshold_sgas,
        args.threshold_amfg,
    )

    if args.output is None:
        p = Path(args.case).parents[2]
        p2 = p / "share" / "results" / "tables" / "plume_extent.csv"
        output_file = str(p2)
    else:
        output_file = args.output

    __export_to_csv(sgas_results, amfg_results, amfg_key, output_file)

    return 0


if __name__ == "__main__":
    sys.exit(main())
