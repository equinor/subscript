from dataclasses import dataclass
from typing import List, Union, Literal, Optional

import numpy as np
from shapely.geometry import Polygon, MultiPolygon

from subscript.co2containment.co2_mass_calculation.co2_mass_calculation import CO2WeightData

DEFAULT_CO2_MOLAR_MASS = 44
DEFAULT_WATER_MOLAR_MASS = 18


@dataclass
class ContainedCo2:
    date: str
    amount_kg: float
    phase: Literal["gas", "aqueous"]
    inside_boundary: bool
    zone: Optional[str] = None

    def __post_init__(self):
        if "-" not in self.date:
            d = self.date
            self.date = f"{d[:4]}-{d[4:6]}-{d[6:]}"


def calculate_co2_containment(
    weights: List[CO2WeightData],
    polygon: Union[Polygon, MultiPolygon],
    zones: Optional[np.ndarray] = None,
) -> List[ContainedCo2]:
    x = weights[0].x
    y = weights[0].y
    outside = ~_calculate_containment(x, y, polygon)
    if zones is None:
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
    else:
        zone_map = {z: zones == z for z in np.unique(zones)}
        return [
            c
            for w in weights
            for zn, zm in zone_map.items()
            for c in [
                ContainedCo2(
                    w.date, w.gas_phase_kg[outside & zm].sum(), "gas", False, zn
                ),
                ContainedCo2(
                    w.date, w.gas_phase_kg[(~outside) & zm].sum(), "gas", True, zn
                ),
                ContainedCo2(
                    w.date, w.aqu_phase_kg[outside & zm].sum(), "aqueous", False, zn
                ),
                ContainedCo2(
                    w.date, w.aqu_phase_kg[(~outside) & zm].sum(), "aqueous", True, zn
                ),
            ]
        ]


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
