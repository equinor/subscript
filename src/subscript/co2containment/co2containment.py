import argparse
import pathlib
import sys
from typing import Dict, Iterable, Tuple

import numpy as np
import pandas
import shapely.geometry
import xtgeo

from .calculate import calculate_co2_mass, calculate_co2_containment


def calculate_out_of_bounds_co2(
    grid_file: str,
    unrst_file: str,
    init_file: str,
    polygon_file: str,
    poro_keyword: str,
) -> pandas.DataFrame:
    grid = xtgeo.grid_from_file(grid_file)
    co2_masses = _extract_co2_mass(grid, unrst_file, init_file, poro_keyword)
    poly = _read_polygon(polygon_file)
    contained_mass = calculate_co2_containment(poly, grid, co2_masses.values())
    return _construct_containment_table(co2_masses.keys(), contained_mass, poly)


def _extract_co2_mass(
    grid: xtgeo.Grid,
    unrst_file: str,
    init_file: str,
    poro_keyword: str,
) -> Dict[str, xtgeo.GridProperty]:
    poro = xtgeo.gridproperty_from_file(
        init_file, grid=grid, name=poro_keyword, date="first"
    )
    return _co2mass_from_unrst(grid, poro, unrst_file)


def _co2mass_from_unrst(
    grid: xtgeo.Grid, poro: xtgeo.GridProperty, unrst_file: str
) -> Dict[str, xtgeo.GridProperty]:
    prop_names = dict.fromkeys(["sgas", "swat", "dgas", "dwat", "amfg", "ymfg"])
    for p in prop_names:
        prop_names[p] = []
    props = xtgeo.gridproperties_from_file(
        unrst_file,
        grid=grid,
        names=[n.upper() for n in prop_names],
        dates="all",
    )
    for d in props.dates:
        for p in prop_names:
            prop_names[p].append(_fetch_prop(props, p.upper(), d))
    return dict(zip(props.dates, calculate_co2_mass(grid, poro, **prop_names)))


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
    dates: Iterable[str],
    contained_mass: Iterable[Tuple[float, float]],
    geometry: shapely.geometry.base.BaseGeometry,
) -> pandas.DataFrame:
    records = [
        (d, out, within, geometry.wkt)
        for d, (out, within) in zip(dates, contained_mass)
    ]
    return pandas.DataFrame.from_records(
        records, columns=("date", "co2_inside", "co2_outside", "geometry")
    )


def make_parser():
    pn = pathlib.Path(__file__).name
    parser = argparse.ArgumentParser(pn)
    parser.add_argument("grid", help="Grid (.EGRID) from which maps are generated")
    parser.add_argument("polygon", help="Polygon that determines the bounds")
    parser.add_argument("outfile", help="Output filename")
    parser.add_argument("--unrst", help="Path to UNRST file. Will assume same base name as grid if not provided", default=None)
    parser.add_argument("--init", help="Path to INIT file. Will assume same base name as grid if not provided", default=None)
    parser.add_argument("--poro", help="Name of porosity parameter to look for in the INIT file", default="PORO")
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
    )
    df.to_csv(arguments.outfile, index=False)


if __name__ == '__main__':
    main(sys.argv[:])
