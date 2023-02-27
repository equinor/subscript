import argparse
import dataclasses
import pathlib
import sys
from typing import Dict, List, Optional, Union, Tuple

import numpy as np
import pandas as pd
import shapely.geometry
import xtgeo
from ecl.eclfile import EclFile
from ecl.grid import EclGrid
from subscript.co2containment.co2_mass_calculation.co2_mass_calculation import calculate_co2_mass
from subscript.co2containment.co2_mass_calculation.co2_mass_calculation import CO2WeightData

from .calculate import (
    # calculate_co2_mass,
    calculate_co2_containment,
    SourceData,
    ContainedCo2,
)


def calculate_out_of_bounds_co2(
    grid_file: str,
    unrst_file: str,
    init_file: str,
    polygon_file: str,
    poro_keyword: str,
    compact: bool,
    zone_file: Optional[str] = None,
) -> pd.DataFrame:
    # source_data = _extract_source_data(
    #     grid_file, unrst_file, init_file, poro_keyword, zone_file
    # )
    print("Start calculating co2_mass_data")
    co2_mass_data = calculate_co2_mass(grid_file,
                                       unrst_file,
                                       init_file,
                                       "PORO")
    print("Done calculating co2_mass_data")
    poly = _read_polygon(polygon_file)
    return calculate_from_source_data(co2_mass_data, poly, compact)


def calculate_from_source_data(
    co2_mass_data: CO2WeightData,
    polygon: shapely.geometry.Polygon,
    compact: bool,
) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
    contained_mass = calculate_co2_containment(
        co2_mass_data, polygon  #  co2_mass_data.x, co2_mass_data.y,  , source_data.zone
    )
    df = _construct_containment_table(contained_mass)
    if compact:
        return df
    if True:  # source_data.zone is None:
        return _merge_date_rows(df)
    return {
        z: _merge_date_rows(g)
        for z, g in df.groupby("zone")
    }


def _fetch_properties(  # xxx
    grid: EclGrid,
    unrst: EclFile,
) -> Tuple[Dict[str, List[np.ndarray]], List[str]]:
    prop_names = dict.fromkeys(["sgas", "swat", "dgas", "dwat", "amfg", "ymfg"])
    for p in prop_names:
        prop_names[p] = []
    dates = [d.strftime("%Y%m%d") for d in unrst.report_dates]
    return {
        p: _read_props(grid, unrst, p)
        for p in prop_names
    }, dates


def _find_c_order(grid: EclGrid):  # xxx
    actnum = grid.export_actnum().numpy_copy()
    actnum[actnum == 0] = -1
    actnum[actnum == 1] = np.arange(grid.get_num_active())
    actnum3d = actnum.reshape(grid.get_dims()[:3], order="F")
    order = actnum3d.flatten()
    return order[order != -1]


def _read_props(  # xxx
    grid: EclGrid,
    unrst: EclFile,
    prop: str,
) -> List[np.ndarray]:
    c_order = _find_c_order(grid)
    return [p.numpy_view()[c_order].astype(float) for p in unrst[prop.upper()]]


def _extract_source_data(  # xxx
    grid_file: str,
    unrst_file: str,
    init_file: str,
    poro_keyword: str,
    zone_file: Optional[str],
) -> SourceData:
    grid = xtgeo.grid_from_file(grid_file)
    ecl_grid = EclGrid(grid_file)
    unrst = EclFile(unrst_file)
    props, dates = _fetch_properties(ecl_grid, unrst)
    poro = xtgeo.gridproperty_from_file(
        init_file, grid=grid, name=poro_keyword, date="first"
    )
    gasless = _identify_gas_less_cells(props["sgas"], props["amfg"])
    _contract_actnum(grid, ~gasless)
    xyz = grid.get_xyz()
    vols = grid.get_bulk_volume()
    active = grid.actnum_array.astype(bool)
    zone = None
    if zone_file is not None:
        zone = xtgeo.gridproperty_from_file(zone_file, grid=grid)
        zone = zone.values.data[active]
    sd = SourceData(
        xyz[0].values.data[active],
        xyz[1].values.data[active],
        poro.values.data[active],
        vols.values.data[active],
        dates,
        zone=zone,
        **{
            p: [_v[~gasless] for _v in v]
            for p, v in props.items()
        },
    )
    return sd


def _identify_gas_less_cells(  # xxx
    sgases: List[np.ndarray],
    amfgs: List[np.ndarray]
) -> np.ndarray:
    gas_less = np.logical_and.reduce([np.abs(s) < 1e-16 for s in sgases])
    gas_less &= np.logical_and.reduce([np.abs(a) < 1e-16 for a in amfgs])
    return gas_less


def _contract_actnum(  # xxx
    grid: xtgeo.Grid,
    is_active: np.ndarray,
):
    actnum = grid.get_actnum().copy()
    actnum.values[grid.actnum_array.astype(bool)] = is_active.astype(int)
    grid.set_actnum(actnum)


def _read_polygon(polygon_file: str) -> shapely.geometry.Polygon:
    poly_xy = np.genfromtxt(polygon_file, skip_header=1, delimiter=",")[:, :2]
    return shapely.geometry.Polygon(poly_xy)


def _construct_containment_table(
    contained_co2: List[ContainedCo2],
) -> pd.DataFrame:
    records = [
        dataclasses.asdict(c)
        for c in contained_co2
    ]
    return pd.DataFrame.from_records(records)


def _merge_date_rows(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop("zone", axis=1)
    # Total
    akg = "amount_kg"
    df1 = (
        df
        .drop(["phase", "inside_boundary"], axis=1)
        .groupby(["date"])
        .sum()
        .rename(columns={akg: "total"})
    )
    # Total by phase
    df2 = (
        df
        .drop("inside_boundary", axis=1)
        .groupby(["phase", "date"])
        .sum()
    )
    df2a = df2.loc["gas"].rename(columns={akg: "total_gas"})
    df2b = df2.loc["aqueous"].rename(columns={akg: "total_aqueous"})
    # Total by containment
    df3 = (
        df
        .drop("phase", axis=1)
        .groupby(["inside_boundary", "date"])
        .sum()
    )
    df3a = df3.loc[(True,)].rename(columns={akg: "total_inside"})
    df3b = df3.loc[(False,)].rename(columns={akg: "total_outside"})
    # Total by containment and phase
    df4 = (
        df
        .groupby(["phase", "inside_boundary", "date"])
        .sum()
    )
    df4a = df4.loc["gas", True].rename(columns={akg: "total_gas_inside"})
    df4b = df4.loc["aqueous", True].rename(columns={akg: "total_aqueous_inside"})
    df4c = df4.loc["gas", False].rename(columns={akg: "total_gas_outside"})
    df4d = df4.loc["aqueous", False].rename(columns={akg: "total_aqueous_outside"})
    # Merge data frames and append normalized values
    total_df = df1.copy()
    for _df in [df2a, df2b, df3a, df3b, df4a, df4b, df4c, df4d]:
        total_df = total_df.merge(_df, on="date", how="left")
    return total_df.reset_index()


def make_parser():
    pn = pathlib.Path(__file__).name
    parser = argparse.ArgumentParser(pn)
    parser.add_argument("grid", help="Grid (.EGRID) from which maps are generated")
    parser.add_argument("polygon", help="Polygon that determines the bounds")
    parser.add_argument("outfile", help="Output filename")
    parser.add_argument("--unrst", help="Path to UNRST file. Will assume same base name as grid if not provided", default=None)
    parser.add_argument("--init", help="Path to INIT file. Will assume same base name as grid if not provided", default=None)
    parser.add_argument("--poro", help="Name of porosity parameter to look for in the INIT file", default="PORO")
    parser.add_argument("--zonefile", help="Path to file containing zone information", default=None)
    parser.add_argument("--compact", help="Write the output to a single file as compact as possible", action="store_true")
    return parser


def process_args(arguments):
    args = make_parser().parse_args(arguments)
    if args.unrst is None:
        args.unrst = args.grid.replace(".EGRID", ".UNRST")
    if args.init is None:
        args.init = args.grid.replace(".EGRID", ".INIT")
    return args


def main(arguments):
    arguments = process_args(arguments)
    df = calculate_out_of_bounds_co2(
        arguments.grid,
        arguments.unrst,
        arguments.init,
        arguments.polygon,
        arguments.poro,
        arguments.compact,
        arguments.zonefile,
    )
    if isinstance(df, dict):
        of = pathlib.Path(arguments.outfile)
        [
            _df.to_csv(of.with_name(f"{of.stem}_{z}{of.suffix}"), index=False)
            for z, _df in df.items()
        ]
    else:
        df.to_csv(arguments.outfile, index=False)


if __name__ == '__main__':
    main(sys.argv[1:])
