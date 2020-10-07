"""Test csvMergeEnsembles aka csv_merge"""
import os
import sys
import subprocess

import pytest
import pandas as pd

from subscript.csv_merge import csv_merge

try:
    # pylint: disable=unused-import
    import ert_shared  # noqa

    HAVE_ERT = True
except ImportError:
    HAVE_ERT = False


def test_taglist():
    """Test that we extract taglists correctly"""
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
    assert "CONST" not in merged.columns
    assert len(merged.columns) == 4

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

    # Test --filecolumn
    sys.argv = [
        "csv_merge",
        test_csv_1,
        test_csv_2,
        "--filecolumn",
        "FILETYPE",
        "-v",
        "-o",
        merged_csv,
    ]
    csv_merge.main()
    merged = pd.read_csv(merged_csv)
    assert "FILETYPE" in merged
    assert set(merged["FILETYPE"].unique()) == set([test_csv_1, test_csv_2])


@pytest.mark.integration
@pytest.mark.skipif(not HAVE_ERT, reason="Requires ERT to be installed")
def test_ert_hook(tmpdir):
    """Mock an ERT run that calls csv_merge as a workflow foo.csv in two
    realizations"""
    os.makedirs("realization-0/iter-0")
    os.makedirs("realization-1/iter-0")
    with open("realization-0/iter-0/foo.csv", "w") as f_handle:
        f_handle.write("FOO\nreal0")
    with open("realization-1/iter-0/foo.csv", "w") as f_handle:
        f_handle.write("FOO\nreal1")

    with open("MERGE_FOO", "w") as wf_handle:
        wf_handle.write("CSV_MERGE realization-*/iter-*/foo.csv merged.csv")

    ert_config = [
        "ECLBASE FOO.DATA",
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH .",
        "",
        "LOAD_WORKFLOW MERGE_FOO",
        "HOOK_WORKFLOW MERGE_FOO POST_SIMULATION",
    ]

    ert_config_fname = "test.ert"
    with open(ert_config_fname, "w") as file_h:
        file_h.write("\n".join(ert_config))

    subprocess.call(["ert", "test_run", ert_config_fname])

    assert os.path.exists("merged.csv")
    dframe = pd.read_csv("merged.csv")
    assert set(dframe["REAL"].astype(str).values) == {"0", "1"}
    assert set(dframe["FOO"].values) == {"real0", "real1"}
