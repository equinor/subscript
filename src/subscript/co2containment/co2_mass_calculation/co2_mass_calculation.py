from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import sys

import numpy as np
import xtgeo
from ecl.eclfile import EclFile
from ecl.grid import EclGrid

TRESHOLD_SGAS = 1e-16
TRESHOLD_AMFG = 1e-16
DEFAULT_CO2_MOLAR_MASS = 44.0
DEFAULT_WATER_MOLAR_MASS = 18.0


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
    zone: Optional[np.ndarray] = None


@dataclass
class Co2MassDataAtTimeStep:
    date: str
    gas_phase_kg: np.ndarray
    aqu_phase_kg: np.ndarray

    def total_weight(self) -> np.ndarray:
        return self.aqu_phase_kg + self.gas_phase_kg


@dataclass
class Co2MassData:
    x: np.ndarray
    y: np.ndarray
    data_list: List[Co2MassDataAtTimeStep]
    zone: Optional[np.ndarray] = None


@dataclass
class Co2VolumeDataAtTimeStep:
    date: str
    volume_coverage: np.ndarray  # Or volume_extent ?
    volume_actual_co2: np.ndarray

    def total_weight(self) -> np.ndarray:
        return self.aqu_phase_kg + self.gas_phase_kg


@dataclass
class Co2VolumeData:
    x: np.ndarray
    y: np.ndarray
    data_list: List[Co2VolumeDataAtTimeStep]
    zone: Optional[np.ndarray] = None


def _identify_gas_less_cells(
    sgases: List[np.ndarray],
    amfgs: List[np.ndarray]
) -> np.ndarray:
    gas_less = np.logical_and.reduce([np.abs(s) < TRESHOLD_SGAS for s in sgases])
    gas_less &= np.logical_and.reduce([np.abs(a) < TRESHOLD_AMFG for a in amfgs])
    return gas_less


def _contract_actnum(
    grid: xtgeo.Grid,
    is_active: np.ndarray,
):
    actnum = grid.get_actnum().copy()
    actnum.values[grid.actnum_array.astype(bool)] = is_active.astype(int)
    grid.set_actnum(actnum)


def _find_c_order(grid: EclGrid):
    actnum = grid.export_actnum().numpy_copy()
    actnum[actnum == 0] = -1
    actnum[actnum == 1] = np.arange(grid.get_num_active())
    actnum3d = actnum.reshape(grid.get_dims()[:3], order="F")
    order = actnum3d.flatten()
    return order[order != -1]


def _read_props(
    grid: EclGrid,
    unrst: EclFile,
    prop: str,
) -> List[np.ndarray]:
    c_order = _find_c_order(grid)
    return [p.numpy_view()[c_order].astype(float) for p in unrst[prop.upper()]]


def _fetch_properties(
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


def _extract_source_data(
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


def _mole_to_mass_fraction(x, m_co2, m_h20):
    return x * m_co2 / (m_h20 + (m_co2 - m_h20) * x)


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


def _calculate_co2_mass_from_source_data(
    source_data: SourceData,
    co2_molar_mass: float = DEFAULT_CO2_MOLAR_MASS,
    water_molar_mass: float = DEFAULT_WATER_MOLAR_MASS
) -> Co2MassData:
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
    co2_mass_data = Co2MassData(
        source_data.x,
        source_data.y,
        [
            Co2MassDataAtTimeStep(
                date,
                wg * eff_vols,
                wa * eff_vols
            )
            for date, (wg, wa) in eff_dens
        ],
        source_data.zone
    )

    return co2_mass_data


def _calculate_co2_volume_from_source_data(
    source_data: SourceData,
    co2_molar_mass: float = DEFAULT_CO2_MOLAR_MASS,  # Not needed ?
    water_molar_mass: float = DEFAULT_WATER_MOLAR_MASS  # Not needed ?
) -> Co2VolumeData:
    # Similar to _calculate_co2_mass_from_source_data
    pass


def calculate_co2_mass(
    grid_file: str,
    unrst_file: str,
    init_file: str,
    poro_keyword: str,
    zone_file: Optional[str] = None
) -> Co2MassData:
    source_data = _extract_source_data(
        grid_file, unrst_file, init_file, poro_keyword, zone_file
    )
    co2_mass_data = _calculate_co2_mass_from_source_data(source_data)
    return co2_mass_data


def calculate_co2_volume(
    grid_file: str,
    unrst_file: str,
    init_file: str,
    poro_keyword: str,
    zone_file: Optional[str] = None
) -> Co2VolumeData:
    source_data = _extract_source_data(
        grid_file, unrst_file, init_file, poro_keyword, zone_file
    )
    co2_volume_data = _calculate_co2_volume_from_source_data(source_data)
    return co2_volume_data


def main(arguments):
    # Not implemented (yet)
    # Use calculate_co2_mass() or calculate_co2_volume() directly
    pass


if __name__ == '__main__':
    main(sys.argv[1:])
