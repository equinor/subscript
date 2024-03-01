"""Test csv_merge"""

import os
import subprocess
from pathlib import Path

import pandas as pd
import pytest
from subscript.csv_merge import csv_merge

try:
    # pylint: disable=unused-import
    import ert.shared  # noqa

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


def test_main_merge(tmp_path, mocker):
    """Test command line interface for csv_merge"""

    assert subprocess.check_output(["csv_merge", "-h"])

    os.chdir(tmp_path)

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

    mocker.patch("sys.argv", ["csv_merge", test_csv_1, test_csv_2, "-o", merged_csv])
    csv_merge.main()
    merged = pd.read_csv(merged_csv)
    # pylint: disable=unsubscriptable-object  # false positive on Pandas dataframe
    assert len(merged) == 4
    assert len(merged.columns) == 5  # 4 unique in input, and 1 FILENAME-col
    assert test_csv_1 in merged["FILENAME"].unique()
    assert test_csv_2 in merged["FILENAME"].unique()
    assert len(merged["FILENAME"].unique()) == 2

    # Test --dropconstantcolumns
    mocker.patch(
        "sys.argv",
        [
            "csv_merge",
            test_csv_1,
            test_csv_2,
            "--dropconstantcolumns",
            "-o",
            merged_csv,
        ],
    )
    csv_merge.main()
    merged = pd.read_csv(merged_csv)
    # pylint: disable=no-member  # false positive on Pandas dataframe
    assert len(merged) == 4
    assert "CONST" not in merged.columns
    assert len(merged.columns) == 4

    # Test --memoryconservative
    mocker.patch(
        "sys.argv",
        [
            "csv_merge",
            test_csv_1,
            test_csv_2,
            "--memoryconservative",
            "-o",
            merged_csv,
        ],
    )
    csv_merge.main()
    merged = pd.read_csv(merged_csv)
    assert len(merged) == 4
    assert len(merged.columns) == 5

    # Test --filecolumn
    mocker.patch(
        "sys.argv",
        [
            "csv_merge",
            test_csv_1,
            test_csv_2,
            "--filecolumn",
            "FILETYPE",
            "-o",
            merged_csv,
        ],
    )
    csv_merge.main()
    merged = pd.read_csv(merged_csv)
    assert "FILETYPE" in merged
    assert set(merged["FILETYPE"].unique()) == {test_csv_1, test_csv_2}


@pytest.mark.parametrize(
    "options, expected, not_expected",
    [
        ([], None, "writing to merged.csv"),
        (["--verbose"], "writing to merged.csv", "Loading foo.csv"),
        (["-v"], "writing to merged.csv", "Loading foo.csv"),
        (["--debug"], "Loading foo.csv", None),
        (["-v", "--debug"], "Loading foo.csv", None),
        (["--debug", "-v"], "Loading foo.csv", None),
    ],
)
def test_logging(options, expected, not_expected, tmp_path, mocker, caplog):
    """Check that --verbose and --debug on the command line works as expected.

    Warning: This test is fragile if the other test functions manipulate
    the loglevel"""
    # pylint: disable=too-many-arguments
    os.chdir(tmp_path)
    pd.DataFrame(
        columns=["REAL", "FOO", "CONST"], data=[[0, 10, 1], [1, 20, 1]]
    ).to_csv("foo.csv", index=False)
    pd.DataFrame(
        columns=["REAL", "BAR", "CONST"], data=[[0, 30, 1], [1, 40, 1]]
    ).to_csv("bar.csv", index=False)
    mocker.patch(
        "sys.argv",
        ["csv_merge", "foo.csv", "bar.csv", "--filecolumn", "FILETYPE"]
        + options
        + [
            "-o",
            "merged.csv",
        ],
    )
    csv_merge.main()
    output = caplog.text
    if not options:
        # By default, it is a very quiet script.
        assert output == ""
    else:
        assert expected in output
    if not_expected is not None:
        assert not_expected not in output


def test_empty_files(tmp_path):
    """Test behaviour when some files are missing or are empty"""
    os.chdir(tmp_path)
    # Empty but existing file:
    pd.DataFrame().to_csv("real1.csv", index=False)
    pd.DataFrame([{"FOO": 1.0}]).to_csv("real2.csv", index=False)
    merged_df = csv_merge.merge_csvfiles(
        ["real1.csv", "real2.csv"], tags={"FILENAME": ["real1.csv", "real2.csv"]}
    )
    pd.testing.assert_frame_equal(
        merged_df,
        pd.DataFrame([{"FOO": 1.0, "FILENAME": "real2.csv"}]),
        check_like=True,
    )
    # Same check, but in memoryconservative mode (different code path)
    merged_df = csv_merge.merge_csvfiles(
        ["real1.csv", "real2.csv"],
        tags={"FILENAME": ["real1.csv", "real2.csv"]},
        memoryconservative=True,
    )
    pd.testing.assert_frame_equal(
        merged_df,
        pd.DataFrame([{"FOO": 1.0, "FILENAME": "real2.csv"}]),
        check_like=True,
    )

    # Non-existing file:
    merged_df = csv_merge.merge_csvfiles(
        ["real2.csv", "real3.csv"], tags={"FILENAME": ["real2.csv", "real3.csv"]}
    )
    pd.testing.assert_frame_equal(
        merged_df,
        pd.DataFrame([{"FOO": 1.0, "FILENAME": "real2.csv"}]),
        check_like=True,
    )
    merged_df = csv_merge.merge_csvfiles(
        ["real2.csv", "real3.csv"],
        tags={"FILENAME": ["real2.csv", "real3.csv"]},
        memoryconservative=True,
    )
    pd.testing.assert_frame_equal(
        merged_df,
        pd.DataFrame([{"FOO": 1.0, "FILENAME": "real2.csv"}]),
        check_like=True,
    )


@pytest.mark.integration
@pytest.mark.skipif(not HAVE_ERT, reason="Requires ERT to be installed")
def test_ert_hook(tmp_path):
    """Mock an ERT run that calls csv_merge as a workflow foo.csv in two
    realizations"""
    os.chdir(tmp_path)
    Path("realization-0/iter-0").mkdir(parents=True)
    Path("realization-1/iter-0").mkdir(parents=True)
    Path("realization-0/iter-0/foo.csv").write_text("FOO\nreal0", encoding="utf8")
    Path("realization-1/iter-0/foo.csv").write_text("FOO\nreal1", encoding="utf8")

    Path("MERGE_FOO").write_text(
        "CSV_MERGE realization-*/iter-*/foo.csv merged.csv", encoding="utf8"
    )

    ert_config = [
        "ECLBASE FOO.DATA",
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH <CONFIG_PATH>",
        "",
        "LOAD_WORKFLOW MERGE_FOO",
        "HOOK_WORKFLOW MERGE_FOO POST_SIMULATION",
    ]

    ert_config_fname = "test.ert"
    Path(ert_config_fname).write_text("\n".join(ert_config), encoding="utf8")

    subprocess.run(["ert", "test_run", ert_config_fname], check=True)

    assert Path("merged.csv").exists()
    dframe = pd.read_csv("merged.csv")
    assert set(dframe["REAL"].astype(str).values) == {"0", "1"}
    assert set(dframe["FOO"].values) == {"real0", "real1"}
