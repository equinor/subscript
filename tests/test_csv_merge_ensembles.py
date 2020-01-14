"""Test csvMergeEnsembles aka csv_merge_ensembles"""
from __future__ import absolute_import

import sys

import pandas as pd

from subscript.csv_merge_ensembles import csv_merge_ensembles


def test_taglist():
    files = [
        "/a/boo/realization-3/iter-0/",
        "/a/boo/realization-5/iter-1/",
        "/a/com/realization-3/",
    ]  # Trailing slash is important.

    assert csv_merge_ensembles.taglist(files, csv_merge_ensembles.REAL_REGEXP) == [
        "3",
        "5",
        "3",
    ]
    assert csv_merge_ensembles.taglist(files, csv_merge_ensembles.ITER_REGEXP) == [
        "0",
        "1",
        None,
    ]
    assert csv_merge_ensembles.taglist(files, csv_merge_ensembles.ENSEMBLE_REGEXP) == [
        "iter-0",
        "iter-1",
        None,
    ]
    assert csv_merge_ensembles.taglist(
        files, csv_merge_ensembles.ENSEMBLESET_REGEXP
    ) == ["boo", "boo", "com"]


def test_main_merge(tmpdir):
    """Test command line interface for csvMergeEnsembles/csv_merge_ensembles"""
    tmpdir.chdir()

    test_csv_1 = "foo.csv"
    test_csv_2 = "bar.csv"
    merged_csv = "merged.csv"

    # Dump test data to disk as CSV first:
    pd.DataFrame(
        columns=["REAL", "FOO", "CONST"], data=[[0, 10, 1], [1, 20, 1]]
    ).to_csv(test_csv_1, index=False)
    pd.DataFrame(
        columns=["REAL", "BAR", "CONST"], data=[[0, 30, 1], [1, 40, 1]]
    ).to_csv(test_csv_2, index=False)

    sys.argv = ["csv_merge_ensembles", test_csv_1, test_csv_2, "-v", "-o", merged_csv]
    csv_merge_ensembles.main()
    merged = pd.read_csv(merged_csv)

    assert len(merged) == 4
    assert len(merged.columns) == 5  # 4 unique in input, and 1 FILENAME-col
    assert test_csv_1 in merged["FILENAME"].unique()
    assert test_csv_2 in merged["FILENAME"].unique()
    assert len(merged["FILENAME"].unique()) == 2

    # Test --dropconstantcolumns
    sys.argv = [
        "csvMergeEnsembles",
        test_csv_1,
        test_csv_2,
        "--dropconstantcolumns",
        "-v",
        "-o",
        merged_csv,
    ]
    csv_merge_ensembles.main()
    merged = pd.read_csv(merged_csv)

    assert len(merged) == 4
    assert len(merged.columns) == 4  # Also the constant column

    # Test --memoryconservative
    sys.argv = [
        "csvMergeEnsembles",
        test_csv_1,
        test_csv_2,
        "--memoryconservative",
        "-v",
        "-o",
        merged_csv,
    ]
    csv_merge_ensembles.main()
    merged = pd.read_csv(merged_csv)
    assert len(merged) == 4
    assert len(merged.columns) == 5
