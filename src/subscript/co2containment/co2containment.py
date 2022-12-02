import argparse
import dataclasses
import pathlib
import sys
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
import shapely.geometry
import xtgeo

from .calculate import (
    calculate_co2_mass,
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
    source_data = _extract_source_data(
        grid_file, unrst_file, init_file, poro_keyword, zone_file
    )
    poly = _read_polygon(polygon_file)
    return calculate_from_source_data(source_data, poly, compact)


def calculate_from_source_data(
    source_data: SourceData,
    polygon: shapely.geometry.Polygon,
    compact: bool,
) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
    co2_masses = calculate_co2_mass(source_data)
    contained_mass = calculate_co2_containment(
        source_data.x, source_data.y, co2_masses, polygon, source_data.zone
    )
    df = _construct_containment_table(contained_mass)
    if compact:
        return df
    if source_data.zone is None:
        return _merge_date_rows(df)
    return {
        z: _merge_date_rows(g)
        for z, g in df.groupby("zone")
    }


def _fetch_properties(
    grid: xtgeo.Grid, unrst_file: str
) -> Dict[str, List[xtgeo.GridProperty]]:
    prop_names = dict.fromkeys(["sgas", "swat", "dgas", "dwat", "amfg", "ymfg"])
    for p in prop_names:
        prop_names[p] = []
    props = xtgeo.gridproperties_from_file(
        unrst_file,
        grid=grid,
        names=[n.upper() for n in prop_names],
        dates="all",
    )
    for d in sorted(set(props.dates)):
        for p in prop_names:
            prop_names[p].append(_fetch_prop(props, p.upper(), d))
    return prop_names


def _extract_source_data(
    grid_file: str,
    unrst_file: str,
    init_file: str,
    poro_keyword: str,
    zone_file: Optional[str],
) -> SourceData:
    grid = xtgeo.grid_from_file(grid_file)
    props = _fetch_properties(grid, unrst_file)
    poro = xtgeo.gridproperty_from_file(
        init_file, grid=grid, name=poro_keyword, date="first"
    )
    _deactivate_gas_less_cells(grid, props["sgas"], props["amfg"])
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
        [p.date for p in props["sgas"]],
        zone=zone,
        **{
            p: [_v.values.data[active] for _v in v]
            for p, v in props.items()
        },
    )
    return sd


def _deactivate_gas_less_cells(
    grid: xtgeo.Grid,
    sgases: List[xtgeo.GridProperty],
    amfgs: List[xtgeo.GridProperty]
):
    active = grid.actnum_array.astype(bool)
    gas_less = np.logical_and.reduce([np.abs(s.values[active]) < 1e-16 for s in sgases])
    gas_less &= np.logical_and.reduce([np.abs(a.values[active]) < 1e-16 for a in amfgs])
    actnum = grid.get_actnum().copy()
    actnum.values[grid.actnum_array.astype(bool)] = (~gas_less).astype(int)
    grid.set_actnum(actnum)


def _fetch_prop(
    grid_props: xtgeo.GridProperties,
    name: str,
    date: str,
) -> xtgeo.GridProperty:
    search = [p for p in grid_props.props if p.date == date and p.name.startswith(name)]
    assert len(search) == 1
    return search[0]


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
