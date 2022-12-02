import numpy as np
import shapely.geometry

from subscript.co2containment.calculate import SourceData
from subscript.co2containment.co2containment import calculate_from_source_data


def test_simple_cube_grid():
    dims = (13, 17, 19)
    mx, my, mz = np.meshgrid(
        np.linspace(-1, 1, dims[0]),
        np.linspace(-1, 1, dims[1]),
        np.linspace(-1, 1, dims[2]),
        indexing="ij"
    )
    dates = [f"{d}0101" for d in range(2030, 2050)]
    dists = np.sqrt(mx ** 2 + my ** 2 + mz ** 2)
    gas_saturations = [
        np.maximum(np.exp(-3 * (dists.flatten() / ((i + 1) / len(dates))) ** 2) - 0.05, 0.0)
        for i in range(len(dates))
    ]
    size = np.prod(dims)
    source_data = SourceData(
        mx.flatten(),
        my.flatten(),
        poro=np.ones(size) * 0.3,
        volumes=np.ones(size) * (8 / size),
        dates=dates,
        swat=[1 - s for s in gas_saturations],
        dwat=[np.ones(size) * 1000.0] * len(dates),
        sgas=gas_saturations,
        dgas=[np.ones(size) * 100.0] * len(dates),
        amfg=[np.ones(size) * 0.02 * s for s in gas_saturations],
        ymfg=[np.ones(size) * 0.99] * len(dates),
    )
    poly = shapely.geometry.Polygon(np.array([
        [-0.45, -0.38],
        [0.41, -0.39],
        [0.33, 0.76],
        [-0.27, 0.75],
        [-0.45, -0.38],
    ]))
    df = calculate_from_source_data(source_data, poly, False)
    assert len(df["date"].unique()) == len(dates)
    totals = df.groupby("date").sum()["amount_kg"]
    assert np.all(np.diff(totals.values, axis=0) >= 0)
