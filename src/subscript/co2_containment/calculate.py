"""CO2 calculation methods"""
from dataclasses import dataclass
from typing import List, Literal, Optional, Union

import numpy as np
from shapely.geometry import MultiPolygon, Point, Polygon

from subscript.co2_containment.co2_calculation import CalculationType, Co2Data


@dataclass
class ContainedCo2:
    """
    Dataclass with amount of Co2 in/out a given area for a given phase
    at different time steps

    Args:
        date (str): A given time step
        amount (float): Numerical value with the computed amount at "date"
        phase (Literal): One of gas/aqueous/undefined. The phase of "amount".
        location (Literal): One of contained/outside/hazardous. The location
            that "amount" corresponds to.
        zone (str):

    """

    date: str
    amount: float
    phase: Literal["gas", "aqueous", "undefined"]
    location: Literal["contained", "outside", "hazardous"]
    zone: Optional[str] = None

    def __post_init__(self):
        """
        If the slot "data" of a ContainedCo2 object does not contain "-", this
        function converts it to the format yyyy-mm-dd

        """
        if "-" not in self.date:
            date = self.date
            self.date = f"{date[:4]}-{date[4:6]}-{date[6:]}"


def calculate_co2_containment(
    co2_data: Co2Data,
    containment_polygon: Union[Polygon, MultiPolygon],
    hazardous_polygon: Union[Polygon, MultiPolygon, None],
    calc_type: CalculationType,
) -> List[ContainedCo2]:
    """
    Calculates the amount (mass/volume) of CO2 within given boundaries
    (contained/outside/hazardous) at each time step for each phase
    (aqueous/gaseous). Result is a list of ContainedCo2 objects.

    Args:
        co2_data (Co2Data): Information of the amount of CO2 at each cell in
            each time step
        containment_polygon (Union[Polygon,Multipolygon]): The polygon that defines
            the containment area
        hazardous_polygon (Union[Polygon,Multipolygon]): The polygon that defines
             the hazardous area
        calc_type (CalculationType): Which calculation is to be performed
             (mass / cell_volume / actual_volume / actual_volume_simplified)

    Returns:
        List[ContainedCo2]
    """
    if containment_polygon is not None:
        is_contained = _calculate_containment(
            co2_data.x_coord,
            co2_data.y_coord,
            containment_polygon,
        )
    else:
        is_contained = np.array([True] * len(co2_data.x_coord))
    if hazardous_polygon is not None:
        is_hazardous = _calculate_containment(
            co2_data.x_coord,
            co2_data.y_coord,
            hazardous_polygon,
        )
    else:
        is_hazardous = np.array([False] * len(co2_data.x_coord))
    # Count as hazardous if the two boundaries overlap:
    is_inside = [x if not y else False for x, y in zip(is_contained, is_hazardous)]
    is_outside = [not x and not y for x, y in zip(is_contained, is_hazardous)]
    if co2_data.zone is None:
        if calc_type == CalculationType.CELL_VOLUME:
            return [
                c
                for w in co2_data.data_list
                for c in [
                    ContainedCo2(
                        w.date,
                        sum(w.volume_coverage[is_inside]),
                        "undefined",
                        "contained",
                    ),
                    ContainedCo2(
                        w.date,
                        sum(w.volume_coverage[is_outside]),
                        "undefined",
                        "outside",
                    ),
                    ContainedCo2(
                        w.date,
                        sum(w.volume_coverage[is_hazardous]),
                        "undefined",
                        "hazardous",
                    ),
                ]
            ]
        return [
            c
            for w in co2_data.data_list
            for c in [
                ContainedCo2(w.date, sum(w.gas_phase[is_inside]), "gas", "contained"),
                ContainedCo2(w.date, sum(w.gas_phase[is_outside]), "gas", "outside"),
                ContainedCo2(
                    w.date, sum(w.gas_phase[is_hazardous]), "gas", "hazardous"
                ),
                ContainedCo2(
                    w.date, sum(w.aqu_phase[is_inside]), "aqueous", "contained"
                ),
                ContainedCo2(
                    w.date, sum(w.aqu_phase[is_outside]), "aqueous", "outside"
                ),
                ContainedCo2(
                    w.date, sum(w.aqu_phase[is_hazardous]), "aqueous", "hazardous"
                ),
            ]
        ]
    zone_map = {z: co2_data.zone == z for z in np.unique(co2_data.zone)}
    if calc_type == CalculationType.CELL_VOLUME:
        return [
            c
            for w in co2_data.data_list
            for zn, zm in zone_map.items()
            for c in [
                ContainedCo2(
                    w.date,
                    sum(w.volume_coverage[is_inside & zm]),
                    "gas",
                    "contained",
                    zn,
                ),
                ContainedCo2(
                    w.date,
                    sum(w.volume_coverage[is_outside & zm]),
                    "gas",
                    "outside",
                    zn,
                ),
                ContainedCo2(
                    w.date,
                    sum(w.volume_coverage[is_hazardous & zm]),
                    "gas",
                    "hazardous",
                    zn,
                ),
            ]
        ]
    return [
        c
        for w in co2_data.data_list
        for zn, zm in zone_map.items()
        for c in [
            ContainedCo2(
                w.date, sum(w.gas_phase[is_inside & zm]), "gas", "contained", zn
            ),
            ContainedCo2(
                w.date, sum(w.gas_phase[is_outside & zm]), "gas", "outside", zn
            ),
            ContainedCo2(
                w.date, sum(w.gas_phase[is_hazardous & zm]), "gas", "hazardous", zn
            ),
            ContainedCo2(
                w.date, sum(w.aqu_phase[is_inside & zm]), "aqueous", "contained", zn
            ),
            ContainedCo2(
                w.date, sum(w.aqu_phase[is_outside & zm]), "aqueous", "outside", zn
            ),
            ContainedCo2(
                w.date, sum(w.aqu_phase[is_hazardous & zm]), "aqueous", "hazardous", zn
            ),
        ]
    ]


def _calculate_containment(
    x_coord: np.ndarray, y_coord: np.ndarray, poly: Union[Polygon, MultiPolygon]
) -> np.ndarray:
    """
    Determines if (x,y) coordinates belong to a given polygon.

    Args:
        x_coord (np.ndarray): x coordinates
        y_coord (np.ndarray): y coordinates
        poly (Union[Polygon, MultiPolygon]): The polygon that determines the
                                             containment of the (x,y) coordinates

    Returns:
        np.ndarray
    """
    return np.array([poly.contains(Point(_x, _y)) for _x, _y in zip(x_coord, y_coord)])
