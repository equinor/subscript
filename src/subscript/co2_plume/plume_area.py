#!/usr/bin/env python


################################################################################
# Script calculating the area extent of the plume depending on which map / date
# are present in the share/results/maps folder
#
# Created by : Jorge Sicacha (NR), Oct 2022
# Modified by: Floriane Mortier (fmmo), Nov 2022 - To fit FMU workflow
#
################################################################################

import argparse
import glob
import os
import pathlib
import sys
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import xtgeo


def __make_parser():
    parser = argparse.ArgumentParser(description="Calculate plume area")
    parser.add_argument("input", help="Path to maps created through XTGeoapp")
    parser.add_argument(
        "--output",
        help="Path to output CSV file",
        default=None,
    )

    return parser


def __find_formations(search_path: str, rskey: str) -> Optional[Tuple[np.ndarray, str]]:
    # Try different capitalizations of rskey:
    file_names_1 = glob.glob(search_path + "*max_" + rskey + "*.gri")
    file_names_2 = glob.glob(search_path + "*max_" + rskey.lower() + "*.gri")
    file_names_3 = glob.glob(search_path + "*max_" + rskey.upper() + "*.gri")

    if file_names_1:
        rskey_updated = rskey
    elif file_names_2:
        rskey_updated = rskey.lower()
    elif file_names_3:
        rskey_updated = rskey.upper()
    else:
        print("No surface files found.")
        return None

    formation_list = []
    for file in glob.glob(search_path + "*max_" + rskey_updated + "*.gri"):
        fm_name = pathlib.Path(file).stem.split("--")[0]

        if fm_name in formation_list:
            pass
        else:
            formation_list.append(fm_name)

    return np.array(formation_list), rskey_updated


def __find_years(search_path: str, fm: np.ndarray, rskey: str) -> List[str]:
    years_list = []

    for file in glob.glob(search_path + fm[0] + "*max_" + rskey + "*.gri"):
        full_date = pathlib.Path(file).stem.split("--")[2]
        year = full_date[0:4]

        if year in years_list:
            pass
        else:
            years_list.append(year)

    return years_list


def __neigh_nodes(x: Tuple[np.int64, np.int64]) -> set:
    # If all the four nodes of the cell are not masked we count the area
    sq_vert = {(x[0] + 1, x[1]), (x[0], int(x[1]) + 1), (x[0] + 1, x[1] + 1)}

    return sq_vert


def calc_plume_area(path: str, rskey: str) -> Optional[List[List[float]]]:
    """
    Finds plume area for each formation and year for a given rskey (for instance
    SGAS or AMFG). The plume areas are found using data from surface files (.gri).
    """
    print("*** Calculating plume area for: " + rskey + " ***")

    if path[-1] != "/":
        path = path + "/"
    out = __find_formations(path, rskey)
    if not out:
        return None
    else:
        formations, rskey_updated = out
        print("Formations found: ", formations)

    years = np.array(__find_years(path, formations, rskey_updated))
    print("Dates found: ", years)

    var = "max_" + rskey_updated
    list_out = []
    for fm in formations:
        for year in years:
            path_file = glob.glob(path + fm + "--" + var + "--" + year + "*.gri")
            mysurf = xtgeo.surface_from_file(path_file[0])
            use_nodes = np.ma.nonzero(mysurf.values)  # Indexes of the existing nodes
            use_nodes = set(list(tuple(zip(use_nodes[0], use_nodes[1]))))
            all_neigh_nodes = list(map(__neigh_nodes, use_nodes))
            test0 = [xx.issubset(use_nodes) for xx in all_neigh_nodes]
            list_out_temp = [
                float(year),
                float(sum(t * mysurf.xinc * mysurf.yinc for t in test0)),
                fm,
            ]
            list_out.append(list_out_temp)

    return list_out


def __read_args() -> Tuple[str, str]:
    args = __make_parser().parse_args()
    input_path = args.input
    output_path = args.output

    if not os.path.isdir(input_path):
        text = f"Input surface directory not found: {input_path}"
        raise FileNotFoundError(text)

    return input_path, output_path


def __convert_to_data_frame(results: List[List[float]], rskey: str) -> pd.DataFrame:
    # Convert into Pandas DataFrame
    df = pd.DataFrame.from_records(
        results, columns=["DATE", "AREA_" + rskey, "FORMATION_" + rskey]
    )
    df = df.pivot(index="DATE", columns="FORMATION_" + rskey, values="AREA_" + rskey)
    df.reset_index(inplace=True)
    df.columns.name = None
    df.columns = [x + "_" + rskey if x != "DATE" else x for x in df.columns]
    return df


def main():
    """
    Reads directory of input surface files (.gri) and calculates plume area
    for SGAS and AMFG per formation and year. Collects the results into a CSV
    file.
    """
    input_path, output_path = __read_args()

    if output_path is None:
        p = pathlib.Path("share") / "results" / "tables" / "plume_area.csv"
        output_path = str(p)

    sgas_df, amfg_df, xmf2_df = None, None, None
    sgas_results = calc_plume_area(input_path, "sgas")
    if sgas_results:
        print("SGAS plume areas sucessfully collected.")
        sgas_df = __convert_to_data_frame(sgas_results, "SGAS")

    amfg_results = calc_plume_area(input_path, "amfg")
    if amfg_results:
        print("AMFG plume areas sucessfully collected.")
        amfg_df = __convert_to_data_frame(amfg_results, "AMFG")

    xmf2_results = calc_plume_area(input_path, "xmf2")
    if xmf2_results:
        print("XMF2 plume areas sucessfully collected.")
        xmf2_df = __convert_to_data_frame(xmf2_results, "XMF2")

    # Merge them together
    if sgas_df is not None:
        if amfg_df is not None:
            df = pd.merge(sgas_df, amfg_df)
            df.to_csv(output_path, index=False)
        elif xmf2_df is not None:
            df = pd.merge(sgas_df, xmf2_df)
            df.to_csv(output_path, index=False)
        else:
            sgas_df.to_csv(output_path, index=False)

    return 0


if __name__ == "__main__":
    sys.exit(main())
