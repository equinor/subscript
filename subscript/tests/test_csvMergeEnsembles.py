"""Test csvMergeEnsembles"""
from __future__ import absolute_import

import os
import sys

import pandas as pd

from .. import csvMergeEnsembles


def test_main_merge():
    """Test command line interface for csvMergeEnsembles"""

    test_csv_1 = "foo.csv"
    test_csv_2 = "bar.csv"
    merged_csv = "merged.csv"

    # Dump test data to disk as CSV first:
    pd.DataFrame(
        columns=["Realization", "FOO", "CONST"], data=[[0, 10, 1], [1, 20, 1]]
    ).to_csv(test_csv_1, index=False)
    pd.DataFrame(
        columns=["Realization", "BAR", "CONST"], data=[[0, 30, 1], [1, 40, 1]]
    ).to_csv(test_csv_2, index=False)

    sys.argv = ["csvMergeEnsembles", test_csv_1, test_csv_2, "-q", "-o", merged_csv]
    csvMergeEnsembles.main()
    merged = pd.read_csv(merged_csv)

    assert len(merged) == 4
    assert len(merged.columns) == 4  # 3 unique in input, and 1 extra.
    assert test_csv_1.replace(".csv", "") in merged.ensemble.unique()
    assert test_csv_2.replace(".csv", "") in merged.ensemble.unique()
    assert len(merged.ensemble.unique()) == 2

    # Test --keepconstantcolumns
    sys.argv = [
        "csvMergeEnsembles",
        test_csv_1,
        test_csv_2,
        "--keepconstantcolumns",
        "-q",
        "-o",
        merged_csv,
    ]
    csvMergeEnsembles.main()
    merged = pd.read_csv(merged_csv)

    assert len(merged) == 4
    assert len(merged.columns) == 5  # Also the constant column

    # Cleanup
    if os.path.exists(merged_csv):
        os.unlink(merged_csv)
    if os.path.exists(test_csv_1):
        os.unlink(test_csv_1)
    if os.path.exists(test_csv_2):
        os.unlink(test_csv_2)
