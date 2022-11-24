from dataclasses import dataclass
from typing import List, Union, Tuple, Literal, Optional

import numpy as np
from shapely.geometry import Polygon, MultiPolygon

DEFAULT_CO2_MOLAR_MASS = 44
DEFAULT_WATER_MOLAR_MASS = 18


@dataclass
class SourceData:
    x: np.ndarray
    y: np.ndarray
    poro: np.ndarray
    volumes: np.ndarray
    dates: List[str]
    swat: List[np.ndarray]
    dwat: List[np.ndarray]
    sgas: List[np.ndarray]
    dgas: List[np.ndarray]
    amfg: List[np.ndarray]
    ymfg: List[np.ndarray]


@dataclass
class Co2WeightData:
    date: str
    gas_phase_kg: np.ndarray
    aqu_phase_kg: np.ndarray

    def total_weight(self) -> np.ndarray:
        return self.aqu_phase_kg + self.gas_phase_kg


@dataclass
class ContainedCo2:
    date: str
    amount_kg: float
    phase: Literal["gas", "aqueous"]
    inside_boundary: bool
    zone: Optional[str] = None


def calculate_co2_containment(
    x: np.ndarray,
    y: np.ndarray,
    weights: List[Co2WeightData],
    polygon: Union[Polygon, MultiPolygon],
) -> List[ContainedCo2]:
    outside = ~_calculate_containment(x, y, polygon)
    return [
        c
        for w in weights
        for c in [
            ContainedCo2(w.date, w.gas_phase_kg[outside].sum(), "gas", False),
            ContainedCo2(w.date, w.gas_phase_kg[~outside].sum(), "gas", True),
            ContainedCo2(w.date, w.aqu_phase_kg[outside].sum(), "aqueous", False),
            ContainedCo2(w.date, w.aqu_phase_kg[~outside].sum(), "aqueous", True),
        ]
    ]


def calculate_co2_mass(
    source_data: SourceData,
    co2_molar_mass: float = DEFAULT_CO2_MOLAR_MASS,
    water_molar_mass: float = DEFAULT_WATER_MOLAR_MASS,
) -> List[Co2WeightData]:
    eff_dens = [
        (
            d,
            _effective_densities(
                _swat, _dwat, _sgas, _dgas, _amfg, _ymfg, co2_molar_mass, water_molar_mass
            )
        )
        for (d, _swat, _dwat, _sgas, _dgas, _amfg, _ymfg)
        in zip(
            source_data.dates,
            source_data.swat,
            source_data.dwat,
            source_data.sgas,
            source_data.dgas,
            source_data.amfg,
            source_data.ymfg,
        )
    ]
    eff_vols = source_data.volumes * source_data.poro
    weights = [
        Co2WeightData(date, wg * eff_vols, wa * eff_vols)
        for date, (wg, wa) in eff_dens
    ]
    return weights


def _calculate_containment(
    x: np.ndarray,
    y: np.ndarray,
    poly: Union[Polygon, MultiPolygon]
) -> np.ndarray:
    try:
        import pygeos
        points = pygeos.points(x, y)
        poly = pygeos.from_shapely(poly)
        return pygeos.contains(poly, points)
    except ImportError:
        import shapely.geometry as sg
        return np.array([
            poly.contains(sg.Point(_x, _y))
            for _x, _y in zip(x, y)
        ])


def _effective_densities(
    swat: np.ndarray,
    dwat: np.ndarray,
    sgas: np.ndarray,
    dgas: np.ndarray,
    amfg: np.ndarray,
    ymfg: np.ndarray,
    co2_molar_mass: float,
    water_molar_mass: float,
) -> Tuple[np.ndarray, np.ndarray]:
    gas_mass_frac = _mole_to_mass_fraction(ymfg, co2_molar_mass, water_molar_mass)
    aqu_mass_frac = _mole_to_mass_fraction(amfg, co2_molar_mass, water_molar_mass)
    w_gas = sgas * dgas * gas_mass_frac
    w_aqu = swat * dwat * aqu_mass_frac
    return w_gas, w_aqu


def _mole_to_mass_fraction(x, m_co2, m_h20):
    return x * m_co2 / (m_h20 + (m_co2 - m_h20) * x)
