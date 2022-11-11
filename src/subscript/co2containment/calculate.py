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
    weights = [
        _effective_density(
            grid, _swat, _dwat, _sgas, _dgas, _amfg, _ymfg, co2_molar_mass, water_molar_mass
        )
        for (_swat, _dwat, _sgas, _dgas, _amfg, _ymfg)
        in zip(swat, dwat, sgas, dgas, amfg, ymfg)
    ]
    vols = grid.get_bulk_volume()
    active = grid.actnum_array.astype(bool)
    eff_vols = vols.values[active] * poro.values[active]
    for w in weights:
        w.values[active] *= eff_vols
        w.name = "mass"
    return weights


def _calculate_containment(
    grid: xtgeo.Grid,
    poly: Union[Polygon, MultiPolygon]
) -> np.ndarray:
    xyz = grid.get_xyz()
    xp = xyz[0].values1d[grid.actnum_indices]
    yp = xyz[1].values1d[grid.actnum_indices]
    try:
        import pygeos
        # raise ImportError
        print("Calculating containment using pygeos")
        points = pygeos.points(xp, yp)
        poly = pygeos.from_shapely(poly)
        return pygeos.contains(poly, points)
    except ImportError:
        import shapely.geometry as sg
        import tqdm
        return np.array([
            poly.contains(sg.Point(x, y))
            for x, y in tqdm(zip(xp, yp), desc="Calculating containment using shapely", totel=len(xp))
        ])


def _effective_density(
    grid: xtgeo.Grid,
    swat: xtgeo.GridProperty,
    dwat: xtgeo.GridProperty,
    sgas: xtgeo.GridProperty,
    dgas: xtgeo.GridProperty,
    amfg: xtgeo.GridProperty,
    ymfg: xtgeo.GridProperty,
    co2_molar_mass: float,
    water_molar_mass: float,
) -> xtgeo.GridProperty:
    active = grid.actnum_array.astype(bool)
    gas_mass_frac = _mole_to_mass_fraction(ymfg.values[active], co2_molar_mass, water_molar_mass)
    aqu_mass_frac = _mole_to_mass_fraction(amfg.values[active], co2_molar_mass, water_molar_mass)
    w_gas = sgas.values[active] * dgas.values[active] * gas_mass_frac
    w_aqu = swat.values[active] * dwat.values[active] * aqu_mass_frac
    e_dens = swat.copy("effective-density")
    e_dens.values[~active] = 0.0
    e_dens.values[active] = w_gas + w_aqu
    return e_dens


def _mole_to_mass_fraction(x, m_co2, m_h20):
    return x * m_co2 / (m_h20 + (m_co2 - m_h20) * x)
