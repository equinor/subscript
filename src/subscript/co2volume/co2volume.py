import pandas
import xtgeo
import argparse
import glob
import sys
import pathlib
import numpy as np
import tqdm


def calculate_containment(xp, yp, poly_xy):
    try:
        import pygeos
        print("Calculating containment using pygeos")
        points = pygeos.points(xp, yp)
        poly = pygeos.polygons(poly_xy)
        return pygeos.contains(poly, points)
    except ImportError:
        import shapely.geometry as sg
        poly = sg.Polygon(poly_xy)
        return np.array([
            poly.contains(sg.Point(x, y))
            for x, y in tqdm.tqdm(zip(xp, yp), desc="Calculating containment")
        ])


def calculate_out_of_bounds_co2(grid_file, unrst_file, init_file, polygon_file):
    """
    This is a temporarty function for calculating CO2 volune. It needs to be verified or
    replaced by some other functionality to ensure correctness.
    """
    print("*** Reading Grid ***")
    grid = xtgeo.grid_from_file(grid_file)
    print("*** Reading Properties ***")
    densities = _effective_densities(grid, unrst_file)
    try:
        poro = xtgeo.gridproperty_from_file(init_file, grid=grid, name="PORO", date="first")
    except (TypeError, ValueError):
        poro = xtgeo.gridproperty_from_file(init_file)
    xyz = grid.get_xyz()
    xp = xyz[0].values1d[grid.actnum_indices]
    yp = xyz[1].values1d[grid.actnum_indices]
    poly_xy = np.genfromtxt(polygon_file, skip_header=1, delimiter=",")[:, :2]
    outside = ~calculate_containment(xp, yp, poly_xy)
    print("*** Calculating volumes ***")
    vols = grid.get_bulk_volume()
    vols = vols.values1d[grid.actnum_indices] * poro.values1d[grid.actnum_indices]
    co2_vol = {
        s.date: (vols * s.values1d[grid.actnum_indices])
        for s in densities
    }
    records = [
        (d, np.sum(v[~outside]), np.sum(v[outside]))
        for d, v in co2_vol.items()
    ]
    df = pandas.DataFrame.from_records(records, columns=("date", "co2_inside", "co2_outside"))
    print("*** Done ***")
    return df


def _effective_densities(grid, unrst_file):
    if not unrst_file.lower().endswith('.unrst'):
        dens = [
            xtgeo.gridproperty_from_file(f, grid=grid, name="SGAS")
            for f in glob.glob(unrst_file)
        ]
        for s in dens:
            if s.date is None and "--" in s.filesrc.stem:
                s.date = s.filesrc.stem.split('--')[1]
        return dens
    else:
        props = xtgeo.gridproperties_from_file(
            unrst_file, grid=grid, names=["SGAS", "SWAT", "DGAS", "DWAT", "AMFG", "YMFG"], dates="all"
        )
        dens = []
        for d in props.dates:
            swat = _fetch_prop(props, "SWAT", d)
            dwat = _fetch_prop(props, "DWAT", d)
            sgas = _fetch_prop(props, "SGAS", d)
            dgas = _fetch_prop(props, "DGAS", d)
            amfg = _fetch_prop(props, "AMFG", d)
            ymfg = _fetch_prop(props, "YMFG", d)

            w_gas = sgas * dgas * _mole_to_mass_fraction(ymfg)
            w_aqu = swat * dwat * _mole_to_mass_fraction(amfg)

            dens.append(props.props[0].copy("tmp"))
            dens[-1].values = w_gas + w_aqu
            dens[-1].date = d
        return dens


def _mole_to_mass_fraction(x):
    m_co2 = 44
    m_h20 = 18
    return x * m_co2 / (m_h20 + (m_co2 - m_h20) * x)



def _fetch_prop(grid_props: xtgeo.GridProperties, name, date):
    search = [p for p in grid_props.props if p.date == date and p.name.startswith(name)]
    assert len(search) == 1
    return search[0].values


def make_parser():
    pn = pathlib.Path(__file__).name
    parser = argparse.ArgumentParser(pn)
    parser.add_argument("grid", help="Grid (.EGRID) from which maps are generated")
    parser.add_argument("polygon", help="Polygon that determines the bounds")
    parser.add_argument("outfile", help="Output filename")
    parser.add_argument("--unrst", help="Path to UNRST file. Will assume same base name as grid if not provided", default=None)
    parser.add_argument("--init", help="Path to INIT file. Will assume same base name as grid if not provided", default=None)
    # parser.add_argument("--zone", help="Path to zone property file", default=None)
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
        arguments.polygon
    )
    df.to_csv(arguments.outfile, index=False)


if __name__ == '__main__':
    main(sys.argv[:])
