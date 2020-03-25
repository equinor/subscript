"""Test csvMergeEnsembles aka csv_merge"""
from __future__ import absolute_import

import os
import sys

import pandas as pd

from subscript.csv_merge import csv_merge


def test_taglist():
    files = [
        "/a/boo/realization-3/iter-0/",
        "/a/boo/realization-5/iter-1/",
        "/a/com/realization-3/",
    ]  # Trailing slash is important.

    assert csv_merge.taglist(files, csv_merge.REAL_REGEXP) == ["3", "5", "3"]
    assert csv_merge.taglist(files, csv_merge.ITER_REGEXP) == ["0", "1", None]
    assert csv_merge.taglist(files, csv_merge.ENSEMBLE_REGEXP) == [
        "iter-0",
        "iter-1",
        None,
    ]
    assert csv_merge.taglist(files, csv_merge.ENSEMBLESET_REGEXP) == [
        "boo",
        "boo",
        "com",
    ]

    # We should also get the ITER tags even if it is constant
    files2 = [
        "/a/boo/realization-3/iter-0/",
        "/a/boo/realization-5/iter-0/",
        "/a/com/realization-3/",
    ]  # Trailing slash is important.
    assert csv_merge.taglist(files2, csv_merge.ITER_REGEXP) == ["0", "0", None]

    files3 = [
        "/a/boo/realization-3/iter-0/",
        "/a/boo/realization-5/iter-0/",
        "/a/com/realization-3/iter-0/",
    ]  # Trailing slash is important.
    assert csv_merge.taglist(files3, csv_merge.ITER_REGEXP) == ["0", "0", "0"]

    files4 = [
        "/a/boo/realization-3/",
        "/a/boo/realization-5/",
        "/a/com/realization-3/",
    ]  # Trailing slash is important.
    assert csv_merge.taglist(files4, csv_merge.ITER_REGEXP) == []
    assert csv_merge.taglist(files4, csv_merge.ENSEMBLE_REGEXP) == []


def test_main_merge(tmpdir):
    """Test command line interface for csvMergeEnsembles/csv_merge"""

    assert os.system("csv_merge -h") == 0

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

    sys.argv = ["csv_merge", test_csv_1, test_csv_2, "-v", "-o", merged_csv]
    csv_merge.main()
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
    csv_merge.main()
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
    csv_merge.main()
    merged = pd.read_csv(merged_csv)
    assert len(merged) == 4
    assert len(merged.columns) == 5
