from typing import List, Union, Tuple, Iterable

import numpy as np
import xtgeo
from shapely.geometry import Polygon, MultiPolygon


DEFAULT_CO2_MOLAR_MASS = 44
DEFAULT_WATER_MOLAR_MASS = 18


def calculate_co2_containment(
    polygon: Union[Polygon, MultiPolygon],
    grid: xtgeo.Grid,
    co2_mass: Iterable[xtgeo.GridProperty],
) -> List[Tuple[float, float]]:
    outside = ~_calculate_containment(grid, polygon)
    co2_mass_1d = [m.values1d[grid.actnum_indices] for m in co2_mass]
    return [
        (m[outside].sum(), m[~outside].sum())
        for m in co2_mass_1d
    ]


def calculate_co2_mass(
    grid: xtgeo.Grid,
    poro: xtgeo.GridProperty,
    swat: List[xtgeo.GridProperty],
    dwat: List[xtgeo.GridProperty],
    sgas: List[xtgeo.GridProperty],
    dgas: List[xtgeo.GridProperty],
    amfg: List[xtgeo.GridProperty],
    ymfg: List[xtgeo.GridProperty],
    co2_molar_mass: float = DEFAULT_CO2_MOLAR_MASS,
    water_molar_mass: float = DEFAULT_WATER_MOLAR_MASS,
) -> List[xtgeo.GridProperty]:
    # TODO: implementation may be inefficient. May want to use values1d instead of values.
    #  However, reading data may be the actual bottle-neck
    densities = [
        _effective_density(
            _swat, _dwat, _sgas, _dgas, _amfg, _ymfg, co2_molar_mass, water_molar_mass
        )
        for (_swat, _dwat, _sgas, _dgas, _amfg, _ymfg)
        in zip(swat, dwat, sgas, dgas, amfg, ymfg)
    ]
    vols = grid.get_bulk_volume()
    eff_vols = vols.values * poro.values
    for d in densities:
        d.values *= eff_vols
        d.name = "mass"
    return densities


def _calculate_containment(
    grid: xtgeo.Grid,
    poly: Union[Polygon, MultiPolygon]
):
    xyz = grid.get_xyz()
    xp = xyz[0].values1d[grid.actnum_indices]
    yp = xyz[1].values1d[grid.actnum_indices]
    try:
        import pygeos
        print("Calculating containment using pygeos")
        points = pygeos.points(xp, yp)
        poly = pygeos.from_shapely(poly)
        return pygeos.contains(poly, points)
    except ImportError:
        import shapely.geometry as sg
        import tqdm
        return np.array([
            poly.contains(sg.Point(x, y))
            for x, y in tqdm.tqdm(zip(xp, yp), desc="Calculating containment")
        ])


def _effective_density(
    swat: xtgeo.GridProperty,
    dwat: xtgeo.GridProperty,
    sgas: xtgeo.GridProperty,
    dgas: xtgeo.GridProperty,
    amfg: xtgeo.GridProperty,
    ymfg: xtgeo.GridProperty,
    co2_molar_mass: float,
    water_molar_mass: float,
):
    w_gas = sgas.values * dgas.values * _mole_to_mass_fraction(ymfg.values, co2_molar_mass, water_molar_mass)
    w_aqu = swat.values * dwat.values * _mole_to_mass_fraction(amfg.values, co2_molar_mass, water_molar_mass)
    e_dens = swat.copy("effective-density")
    e_dens.values = w_gas + w_aqu
    return e_dens


def _mole_to_mass_fraction(x, m_co2, m_h20):
    return x * m_co2 / (m_h20 + (m_co2 - m_h20) * x)
