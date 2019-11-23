"""Test csv_stack"""
from __future__ import absolute_import

import os
import sys

import pandas as pd

from subscript.csv_stack import csv_stack

TESTFRAME = pd.DataFrame(
    columns=["REAL", "DATE", "PORO", "WOPT:A1", "WOPT:A2", "RPR:1", "RPR:2", "CONST"],
    data=[
        [1, "2015-01-01", 6, 1, 2, 3, 4, 1],
        [1, "2015-02-01", 7, 2, 3, 4, 5, 1],
        [1, "2015-02-03", 8, 3, 4, 5, 6, 1],
        [2, "2015-01-01", 9, 4, 5, 6, 7, 1],
        [2, "2015-02-01", 10, 5, 6, 7, 8, 1],
        [2, "2015-03-01", 4, 3, 2, 4, 5, 1],
        [2, "2015-04-01", 11, 6, 7, 8, 9, 1],
    ],
)


def test_main_csv_stack(tmpdir):
    """Test command line interface for csvMergeEnsembles/csv_merge_ensembles"""
    tmpdir.chdir()
    TESTFRAME.to_csv("testframe.csv", index=False)

    sys.argv = ["csv_stack", "testframe.csv", "-o", "stacked.csv"]
    csv_stack.main()
    stacked = pd.read_csv("stacked.csv")
    assert isinstance(stacked, pd.DataFrame)
    assert "WELL" in stacked
    assert "WOPT:A1" not in stacked
    assert "WOPT" in stacked
    assert "A1" in stacked["WELL"].values
    assert "A2" in stacked["WELL"].values
    assert "CONST" not in stacked

    sys.argv = [
        "csv_stack",
        "testframe.csv",
        "--keepconstantcolumns",
        "-o",
        "stacked.csv",
    ]
    csv_stack.main()
    stacked = pd.read_csv("stacked.csv")
    assert isinstance(stacked, pd.DataFrame)
    assert "WELL" in stacked
    assert "CONST" in stacked

    sys.argv = ["csv_stack", "testframe.csv", "--keepminimal", "-o", "stacked.csv"]
    csv_stack.main()
    stacked = pd.read_csv("stacked.csv")
    assert isinstance(stacked, pd.DataFrame)
    assert "WELL" in stacked
    assert "CONST" not in stacked
    assert "PORO" not in stacked

    sys.argv = ["csv_stack", "testframe.csv", "--split", "region", "-o", "stacked.csv"]
    csv_stack.main()
    stacked = pd.read_csv("stacked.csv")
    assert isinstance(stacked, pd.DataFrame)
    assert "REGION" in stacked
    assert "CONST" not in stacked
    assert "RPR" in stacked
    assert 1 in stacked["REGION"].astype(int).values
    assert 2 in stacked["REGION"].astype(int).values
