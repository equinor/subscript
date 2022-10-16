from pathlib import Path

import numpy as np
import pytest
import scipy.ndimage
import shapely.geometry
import xtgeo

from subscript.co2containment.calculate import (
    calculate_co2_containment,
    calculate_co2_mass,
)


def _random_prop(pname, dims, rng, low, high):
    white = rng.normal(size=dims)
    smooth = scipy.ndimage.gaussian_filter(white, max(dims) / 10)
    values = smooth - np.min(smooth)
    values /= np.max(values)
    values *= high
    values += low
    return xtgeo.GridProperty(
        ncol=dims[0], nrow=dims[1], nlay=dims[2], name=pname, values=values
    )


@pytest.fixture
def dummy_co2_grid():
    dims = (11, 13, 7)
    return xtgeo.create_box_grid(dims)


@pytest.fixture
def dummy_co2_masses(dummy_co2_grid):
    dims = dummy_co2_grid.dimensions
    nt = 10
    rng = np.random.RandomState(123)
    poro = _random_prop("poro", dims, rng, 0.1, 0.3)
    swat = [_random_prop("swat", dims, rng, 0.05, 0.6) for _ in range(nt)]
    dwat = [_random_prop("dwat", dims, rng, 950, 1050) for _ in range(nt)]
    dgas = [_random_prop("dgas", dims, rng, 700, 850) for _ in range(nt)]
    sgas = [_random_prop("sgas", dims, rng, 0.05, 0.6) for _ in range(nt)]
    amfg = [_random_prop("amfg", dims, rng, 0.001, 0.01) for _ in range(nt)]
    ymfg = [_random_prop("ymfg", dims, rng, 0.001, 0.01) for _ in range(nt)]
    return calculate_co2_mass(dummy_co2_grid, poro, swat, dwat, sgas, dgas, amfg, ymfg)


def _calc_and_compare(poly, grid, masses):
    mu = np.mean([np.mean(d.values) for d in masses])
    totals = np.array([np.sum(d.values) for d in masses])
    containment = np.array(
        calculate_co2_containment(poly, grid, masses)
    )
    assert np.allclose(containment.sum(axis=1), totals, rtol=1e-5, atol=1e-8)
    assert (
        pytest.approx(np.mean(containment[:, 1]), rel=0.10)
        == (poly.area * grid.nlay * mu)
    )


def _copy_prop_and_set_value(orig_prop, new_name, value):
    prop = orig_prop.copy(new_name)
    prop.values1d[~prop.values1d.mask] = value
    return prop


def test_single_poly_co2_containment(dummy_co2_grid, dummy_co2_masses):
    assert len(dummy_co2_masses) == 10
    poly = shapely.geometry.Polygon([
        [7.1, 7.0],
        [9.1, 9.0],
        [7.1, 11.0],
        [5.1, 9.0],
        [7.1, 7.0],
    ])
    _calc_and_compare(poly, dummy_co2_grid, dummy_co2_masses)


def test_multi_poly_co2_containment(dummy_co2_grid, dummy_co2_masses):
    poly = shapely.geometry.MultiPolygon([
        shapely.geometry.Polygon([
            [7.1, 7.0],
            [9.1, 9.0],
            [7.1, 11.0],
            [5.1, 9.0],
            [7.1, 7.0],
        ]),
        shapely.geometry.Polygon([
            [1.0, 1.0],
            [3.0, 1.0],
            [3.0, 3.0],
            [1.0, 3.0],
            [1.0, 1.0],
        ]),
    ])
    _calc_and_compare(poly, dummy_co2_grid, dummy_co2_masses)


def test_reek_grid():
    reek_gridfile = (
        Path(__file__).absolute().parent
        / "data"
        / "reek"
        / "eclipse"
        / "model"
        / "2_R001_REEK-0.EGRID"
    )
    reek_poly = shapely.geometry.Polygon([
        [461339, 5932377],
        [461339 + 1000, 5932377],
        [461339 + 1000, 5932377 + 1000],
        [461339, 5932377 + 1000],
    ])
    grid = xtgeo.grid_from_file(reek_gridfile)
    poro = xtgeo.gridproperty_from_file(
        reek_gridfile.with_suffix(".INIT"), name="PORO", grid=grid
    )
    mass = calculate_co2_mass(
        grid,
        _copy_prop_and_set_value(poro, "poro", 0.1),
        [_copy_prop_and_set_value(poro, "swat", 0.1)],
        [_copy_prop_and_set_value(poro, "dwat", 1000.0)],
        [_copy_prop_and_set_value(poro, "sgas", 0.1)],
        [_copy_prop_and_set_value(poro, "dgas", 100.0)],
        [_copy_prop_and_set_value(poro, "amfg", 0.1)],
        [_copy_prop_and_set_value(poro, "ymfg", 0.1)],
    )
    table = calculate_co2_containment(reek_poly, grid, mass)
    assert table[0][1] == pytest.approx(89498504)
