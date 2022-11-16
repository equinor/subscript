from pathlib import Path

import numpy as np
import pytest
import scipy.ndimage
import shapely.geometry
import xtgeo

from subscript.co2containment.calculate import (
    calculate_co2_containment,
    calculate_co2_mass,
    SourceData,
)


def _random_prop(dims, rng, low, high):
    white = rng.normal(size=dims)
    smooth = scipy.ndimage.gaussian_filter(white, max(dims) / 10)
    values = smooth - np.min(smooth)
    values /= np.max(values)
    values *= high
    values += low
    return values.flatten()


def _xy_and_volume(grid: xtgeo.Grid):
    xyz = grid.get_xyz()
    vol = grid.get_bulk_volume().values1d.compressed()
    return xyz[0].values1d.compressed(), xyz[1].values1d.compressed(), vol


@pytest.fixture
def dummy_co2_grid():
    dims = (11, 13, 7)
    return xtgeo.create_box_grid(dims)


@pytest.fixture
def dummy_co2_masses(dummy_co2_grid):
    dims = dummy_co2_grid.dimensions
    nt = 10
    rng = np.random.RandomState(123)
    poro = _random_prop(dims, rng, 0.1, 0.3)
    swat = [_random_prop(dims, rng, 0.05, 0.6) for _ in range(nt)]
    dwat = [_random_prop(dims, rng, 950, 1050) for _ in range(nt)]
    dgas = [_random_prop(dims, rng, 700, 850) for _ in range(nt)]
    sgas = [_random_prop(dims, rng, 0.05, 0.6) for _ in range(nt)]
    amfg = [_random_prop(dims, rng, 0.001, 0.01) for _ in range(nt)]
    ymfg = [_random_prop(dims, rng, 0.001, 0.01) for _ in range(nt)]
    x, y, vol = _xy_and_volume(dummy_co2_grid)
    dates = [str(2020 + i) for i in range(nt)]
    source_data = SourceData(x, y, poro, vol, dates, swat, dwat, sgas, dgas, amfg, ymfg)
    return calculate_co2_mass(source_data)


def _calc_and_compare(poly, grid, masses):
    total = [m.total_weight() for m in masses]
    mu = np.mean([np.mean(d) for d in total])
    totals = np.array([np.sum(d) for d in total])
    xyz = grid.get_xyz()
    contained = calculate_co2_containment(
        xyz[0].values1d.compressed(), xyz[1].values1d.compressed(), masses, poly
    )
    assert np.allclose(np.array([c.total() for c in contained]), totals, rtol=1e-5, atol=1e-8)
    assert (
        pytest.approx(
            np.mean([(c.inside() for c in contained)]),
            rel=0.10,
        )
        == (poly.area * grid.nlay * mu)
    )


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
    ).values1d.compressed()
    x, y, vol = _xy_and_volume(grid)
    source_data = SourceData(
        x,
        y,
        np.ones_like(poro) * 0.1,
        vol,
        ["2042"],
        [np.ones_like(poro) * 0.1],
        [np.ones_like(poro) * 1000.0],
        [np.ones_like(poro) * 0.1],
        [np.ones_like(poro) * 100.0],
        [np.ones_like(poro) * 0.1],
        [np.ones_like(poro) * 0.1],
    )
    mass = calculate_co2_mass(source_data)
    table = calculate_co2_containment(
        source_data.x, source_data.y, mass, reek_poly
    )
    assert table[0].inside() == pytest.approx(89498504)
