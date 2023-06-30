import numpy as np
import pytest
import shapely.geometry

from subscript.co2_containment.co2_calculation import (
    CalculationType,
    Co2Data,
    SourceData,
    _calculate_co2_data_from_source_data,
)


def _simple_cube_grid():
    """
    Create simple cube grid
    """
    dims = (13, 17, 19)
    m_x, m_y, m_z = np.meshgrid(
        np.linspace(-1, 1, dims[0]),
        np.linspace(-1, 1, dims[1]),
        np.linspace(-1, 1, dims[2]),
        indexing="ij",
    )
    dates = [f"{d}0101" for d in range(2030, 2050)]
    dists = np.sqrt(m_x**2 + m_y**2 + m_z**2)
    gas_saturations = {}
    for count, date in enumerate(dates):
        gas_saturations[date] = np.maximum(
            np.exp(-3 * (dists.flatten() / ((count + 1) / len(dates))) ** 2) - 0.05, 0.0
        )
    size = np.prod(dims)
    return SourceData(
        m_x.flatten(),
        m_y.flatten(),
        PORV={date: np.ones(size) * 0.3 for date in dates},
        VOL={date: np.ones(size) * (8 / size) for date in dates},
        DATES=dates,
        DWAT={date: np.ones(size) * 1000.0 for date in dates},
        SWAT={date: 1 - value for date, value in gas_saturations.items()},
        SGAS=gas_saturations,
        DGAS={date: np.ones(size) * 100.0 for date in dates},
        AMFG={
            date: np.ones(size) * 0.02 * value
            for date, value in gas_saturations.items()
        },
        YMFG={date: np.ones(size) * 0.99 for date in dates},
    )


def _simple_cube_grid_eclipse():
    """
    Create simple cube grid, eclipse properties
    """
    dims = (13, 17, 19)
    m_x, m_y, m_z = np.meshgrid(
        np.linspace(-1, 1, dims[0]),
        np.linspace(-1, 1, dims[1]),
        np.linspace(-1, 1, dims[2]),
        indexing="ij",
    )
    dates = [f"{d}0101" for d in range(2030, 2050)]
    dists = np.sqrt(m_x**2 + m_y**2 + m_z**2)
    gas_saturations = {}
    for count, date in enumerate(dates):
        gas_saturations[date] = np.maximum(
            np.exp(-3 * (dists.flatten() / ((count + 1) / len(dates))) ** 2) - 0.05, 0.0
        )
    size = np.prod(dims)
    return SourceData(
        m_x.flatten(),
        m_y.flatten(),
        RPORV={date: np.ones(size) * 0.3 for date in dates},
        VOL={date: np.ones(size) * (8 / size) for date in dates},
        DATES=dates,
        BWAT={date: np.ones(size) * 1000.0 for date in dates},
        SWAT={date: 1 - value for date, value in gas_saturations.items()},
        SGAS=gas_saturations,
        BGAS={date: np.ones(size) * 100.0 for date in dates},
        XMF2={
            date: np.ones(size) * 0.02 * value
            for date, value in gas_saturations.items()
        },
        YMF2={date: np.ones(size) * 0.99 for date in dates},
    )


def _simple_poly():
    """
    Create simple polygon
    """
    return shapely.geometry.Polygon(
        np.array(
            [
                [-0.45, -0.38],
                [0.41, -0.39],
                [0.33, 0.76],
                [-0.27, 0.75],
                [-0.45, -0.38],
            ]
        )
    )


def test_simple_cube_grid():
    """
    Test simple cube grid. Testing result for last date.
    """
    simple_cube_grid = _simple_cube_grid()

    co2_data = _calculate_co2_data_from_source_data(
        simple_cube_grid,
        CalculationType.MASS,
    )
    assert len(co2_data.data_list) == len(simple_cube_grid.DATES)
    assert co2_data.units == "kg"
    assert co2_data.data_list[-1].date == "20490101"
    assert co2_data.data_list[-1].gas_phase.sum() == pytest.approx(9585.032869548137)
    assert co2_data.data_list[-1].aqu_phase.sum() == pytest.approx(2834.956447728449)

    simple_cube_grid_eclipse = _simple_cube_grid_eclipse()

    co2_data_eclipse = _calculate_co2_data_from_source_data(
        simple_cube_grid_eclipse,
        CalculationType.MASS,
    )
    assert len(co2_data_eclipse.data_list) == len(simple_cube_grid_eclipse.DATES)
    assert co2_data_eclipse.units == "kg"
    assert co2_data_eclipse.data_list[-1].date == "20490101"
    assert co2_data_eclipse.data_list[-1].gas_phase.sum() == pytest.approx(
        419249.33771403536
    )
    assert co2_data_eclipse.data_list[-1].aqu_phase.sum() == pytest.approx(
        51468.54223011175
    )


def test_zoned_simple_cube_grid():
    """
    Create simple cube grid, zoned. Testing result for last date.
    """
    simple_cube_grid = _simple_cube_grid()

    # pylint: disable-next=no-member
    random_state = np.random.RandomState(123)
    zone = random_state.choice([1, 2, 3], size=simple_cube_grid.PORV["20300101"].shape)
    simple_cube_grid.zone = zone
    co2_data = _calculate_co2_data_from_source_data(
        simple_cube_grid,
        CalculationType.MASS,
    )
    assert isinstance(co2_data, Co2Data)
    assert co2_data.data_list[-1].date == "20490101"
    assert co2_data.data_list[-1].gas_phase.sum() == pytest.approx(9585.032869548137)
    assert co2_data.data_list[-1].aqu_phase.sum() == pytest.approx(2834.956447728449)
