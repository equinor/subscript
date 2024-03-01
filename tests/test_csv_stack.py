"""Test module for csv_stack"""

import os
import re
import subprocess
from pathlib import Path

import pandas as pd
import pytest
from subscript.csv_stack import csv_stack

try:
    # pylint: disable=unused-import
    import ert.shared  # noqa

    HAVE_ERT = True
except ImportError:
    HAVE_ERT = False


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


def test_drop_constants():
    """Testing that we can drop constants and obey keepminimal"""
    const_drop = csv_stack.drop_constants(TESTFRAME, False, re.compile("W[A-Z]*:.*"))
    assert "CONST" not in const_drop
    assert "RPR:1" in const_drop
    assert "WOPT:A1" in const_drop

    minimal_well = csv_stack.drop_constants(TESTFRAME, True, re.compile("W[A-Z]*:.*"))
    assert "CONST" not in minimal_well
    assert "RPR:1" not in minimal_well
    assert "WOPT:A1" in minimal_well

    minimal_region = csv_stack.drop_constants(TESTFRAME, True, re.compile("R[A-Z]*:.*"))
    assert "CONST" not in minimal_region
    assert "RPR:1" in minimal_region
    assert "WOPT:A1" not in minimal_region


@pytest.mark.parametrize(
    "dframe, regexp, newcol, expected",
    [
        (
            pd.DataFrame([{"WOPT:A": 1, "WOPT:B": 2}]),
            "W[A-Z]*:.*",
            "WELLNAME",
            pd.DataFrame([{"WELLNAME": "A", "WOPT": 1}, {"WELLNAME": "B", "WOPT": 2}]),
        ),
        (
            pd.DataFrame([{"WOPT:A": 1, "WOPT:B": 2}]),
            "B[A-Z]*:.*",
            "WELLNAME",
            pd.DataFrame([{"WOPT:A": 1, "WOPT:B": 2}]),
        ),
    ],
)
def test_csv_stack_parametrized(dframe, regexp, newcol, expected):
    """Parametrized test of the stacking operation"""
    pd.testing.assert_frame_equal(
        csv_stack.csv_stack(dframe, re.compile(regexp), ":", newcol),
        expected,
        check_names=False,
    )


def test_csv_stack():
    """Unparametrized test of the TESTFRAME frame"""
    well_stacked = csv_stack.csv_stack(
        TESTFRAME.copy(), re.compile("W[A-Z]*:.*"), ":", "WELL"
    )
    assert "WELL" in well_stacked
    assert "WOPT:A1" not in well_stacked
    assert "RPR:1" in well_stacked
    assert "CONST" in well_stacked

    region_stacked = csv_stack.csv_stack(
        TESTFRAME.copy(), re.compile("R[A-Z]*:.*"), ":", "REGION"
    )
    assert "REGION" in region_stacked
    assert "WOPT:A1" in region_stacked
    assert "RPR:1" not in region_stacked
    assert "RPR" in region_stacked
    assert "CONST" in region_stacked


def test_stack_library():
    """Test that all stacking operations mentioned in the so called
    stack library will run on TESTFRAME without errors"""

    dframe = TESTFRAME.copy()

    # Add some extra columns to test all:
    dframe["GPR:1"] = range(30, 37)
    dframe["GPR:2"] = range(40, 47)
    dframe["BPR:1,2,3"] = range(50, 57)
    dframe["BPR:4,5,6"] = range(60, 67)
    for _, stackargs in csv_stack.STACK_LIBRARY.items():
        stacked = csv_stack.csv_stack(
            dframe.copy(), stackargs[0], stackargs[1], stackargs[2]
        )
        assert isinstance(stacked, pd.DataFrame)
        assert not stacked.empty
        assert stackargs[2] in stacked
        assert not stacked[stackargs[2]].dropna().empty


def test_numbers_in_vectornames():
    """Eclipse vectors can have numbers in them, most typical is WBP9, but
    this applies field, groups as well"""
    dframe = TESTFRAME.copy()

    dframe["WBP9:A-1"] = range(90, 97)

    regexp, colon, col_name = csv_stack.STACK_LIBRARY["well"]
    well_stacked = csv_stack.csv_stack(dframe, regexp, colon, col_name)
    assert "WBP9" in well_stacked


def test_csv_no_columns():
    """Test what  happens when we stack on columns that are not in the input"""
    regexp, colon, col_name = csv_stack.STACK_LIBRARY["block"]
    # (assert there are no BPR columns in TESTFRAME)
    block_stacked = csv_stack.csv_stack(TESTFRAME.copy(), regexp, colon, col_name)
    # Returned frame should be untouched
    pd.testing.assert_frame_equal(block_stacked, TESTFRAME)


def test_csv_stack_all():
    """Test that can stack "all" columns colons in them"""
    regexp, colon, col_name = csv_stack.STACK_LIBRARY["all"]
    dframe = TESTFRAME.copy()
    dframe["WOPR:A1"] = [10, 11, 12, 13, 14, 15, 17]
    dframe["WOPR:A2"] = [20, 21, 22, 23, 24, 25, 27]
    all_stacked = csv_stack.csv_stack(dframe, regexp, colon, col_name)
    assert len(all_stacked) == 28
    assert set(all_stacked["IDENTIFIER"].unique()) == {"1", "2", "A1", "A2"}


@pytest.mark.integration
def test_commandlinetool(tmp_path, mocker):
    """Test command line interface for csv_stack"""

    assert subprocess.check_output(["csv_stack", "-h"])  # nosec

    os.chdir(tmp_path)
    TESTFRAME.to_csv("testframe.csv", index=False)

    mocker.patch("sys.argv", ["csv_stack", "testframe.csv", "-o", "stacked.csv"])
    csv_stack.main()
    stacked = pd.read_csv("stacked.csv")
    assert isinstance(stacked, pd.DataFrame)
    assert "WELL" in stacked
    assert "WOPT:A1" not in stacked
    assert "WOPT" in stacked
    assert "A1" in stacked["WELL"].values
    assert "A2" in stacked["WELL"].values
    assert "CONST" not in stacked

    mocker.patch(
        "sys.argv",
        [
            "csv_stack",
            "testframe.csv",
            "--keepconstantcolumns",
            "-o",
            "stacked.csv",
        ],
    )
    csv_stack.main()
    stacked = pd.read_csv("stacked.csv")
    assert isinstance(stacked, pd.DataFrame)
    assert "WELL" in stacked
    assert "CONST" in stacked

    mocker.patch(
        "sys.argv", ["csv_stack", "testframe.csv", "--keepminimal", "-o", "stacked.csv"]
    )
    csv_stack.main()
    stacked = pd.read_csv("stacked.csv")
    assert isinstance(stacked, pd.DataFrame)
    assert "WELL" in stacked
    assert "CONST" not in stacked
    assert "PORO" not in stacked

    mocker.patch(
        "sys.argv",
        ["csv_stack", "testframe.csv", "--split", "region", "-o", "stacked.csv"],
    )
    csv_stack.main()
    stacked = pd.read_csv("stacked.csv")
    assert isinstance(stacked, pd.DataFrame)
    assert "REGION" in stacked
    assert "CONST" not in stacked
    assert "RPR" in stacked
    assert 1 in stacked["REGION"].astype(int).values
    assert 2 in stacked["REGION"].astype(int).values


@pytest.mark.parametrize("verbose", [False, True])
def test_csv_stack_verbose(tmp_path, verbose):
    """Test that --verbose gives INFO logging to stdout"""
    os.chdir(tmp_path)
    TESTFRAME.to_csv("testframe.csv", index=False)

    commands = ["csv_stack", "testframe.csv", "--output", "stacked.csv"]
    if verbose:
        commands.append("-v")

    result = subprocess.run(commands, check=True, capture_output=True)
    output = result.stdout.decode() + result.stderr.decode()

    if verbose:
        assert "INFO:" in output
    else:
        assert "INFO:" not in output


def test_csv_stack_stdout(tmp_path):
    """Test that csv output can be dumped to stdout"""
    os.chdir(tmp_path)
    TESTFRAME.to_csv("testframe.csv", index=False)
    commands = ["csv_stack", "testframe.csv", "--output", csv_stack.__MAGIC_STDOUT__]
    result = subprocess.run(commands, check=True, capture_output=True)
    output = result.stdout.decode()
    assert "WELL" in output
    assert "A2" in output
    assert "2015" in output


@pytest.mark.integration
@pytest.mark.skipif(not HAVE_ERT, reason="Requires ERT to be installed")
def test_ert_forward_model(tmp_path):
    """Test that the ERT hook can run on a mocked case"""
    # pylint: disable=redefined-outer-name
    # pylint: disable=unused-argument
    os.chdir(tmp_path)
    TESTFRAME.to_csv("stackme.csv", index=False)
    Path("FOO.DATA").write_text("--Empty", encoding="utf8")
    ert_config = [
        "ECLBASE FOO.DATA",
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH <CONFIG_PATH>",
        "FORWARD_MODEL CSV_STACK(<CSVFILE>=stackme.csv, <OUTPUT>=stacked.csv)",
    ]

    ert_config_fname = "stacktest.ert"
    Path(ert_config_fname).write_text("\n".join(ert_config), encoding="utf8")

    subprocess.run(["ert", "test_run", ert_config_fname], check=True)

    dframe = pd.read_csv("stacked.csv")
    assert not dframe.empty
    assert "RPR:1" in dframe
    assert "CONST" not in dframe


@pytest.mark.integration
@pytest.mark.skipif(not HAVE_ERT, reason="Requires ERT to be installed")
def test_ert_forward_model_keepminimal(tmp_path):
    """Test that the ERT hook can run on a mocked case"""
    # pylint: disable=redefined-outer-name
    # pylint: disable=unused-argument
    os.chdir(tmp_path)
    TESTFRAME.to_csv("stackme.csv", index=False)
    Path("FOO.DATA").write_text("--Empty", encoding="utf8")
    ert_config = [
        "ECLBASE FOO.DATA",
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH <CONFIG_PATH>",
        (
            "FORWARD_MODEL CSV_STACK("
            '<CSVFILE>=stackme.csv, <OUTPUT>=stacked.csv, <OPTION>="--keepminimal")'
        ),
    ]

    ert_config_fname = "stacktest.ert"
    Path(ert_config_fname).write_text("\n".join(ert_config), encoding="utf8")

    subprocess.run(["ert", "test_run", ert_config_fname], check=True)

    dframe = pd.read_csv("stacked.csv")
    assert not dframe.empty
    assert "RPR:1" not in dframe
    assert "CONST" not in dframe


@pytest.mark.integration
@pytest.mark.skipif(not HAVE_ERT, reason="Requires ERT to be installed")
def test_ert_forward_model_keepconstants(tmp_path):
    """Test that the ERT hook can run on a mocked case"""
    # pylint: disable=redefined-outer-name
    # pylint: disable=unused-argument
    os.chdir(tmp_path)
    TESTFRAME.to_csv("stackme.csv", index=False)
    Path("FOO.DATA").write_text("--Empty", encoding="utf8")
    ert_config = [
        "ECLBASE FOO.DATA",
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH <CONFIG_PATH>",
        (
            "FORWARD_MODEL CSV_STACK("
            '<CSVFILE>=stackme.csv, <OUTPUT>=stacked.csv, <OPTION>="--keepconstantcolumns")'  # noqa
        ),
    ]

    ert_config_fname = "stacktest.ert"
    Path(ert_config_fname).write_text("\n".join(ert_config), encoding="utf8")

    subprocess.run(["ert", "test_run", ert_config_fname], check=True)

    dframe = pd.read_csv("stacked.csv")
    assert not dframe.empty
    assert "RPR:1" in dframe
    assert "CONST" in dframe


@pytest.mark.integration
@pytest.mark.skipif(not HAVE_ERT, reason="Requires ERT to be installed")
def test_csv_stack_ert_workflow(tmp_path):
    """Test that CSV_STACK can be run as an ERT workflow/plugin"""
    os.chdir(tmp_path)

    csvfile = "some_ensemble/share/results/tables/unsmry--monthly.csv"
    Path(csvfile).parent.mkdir(parents=True)

    pd.DataFrame([{"WOPT:A": 1, "WOPT:B": 2}]).to_csv(csvfile, index=False)

    Path("CSV_STACK_WELLS").write_text(
        (
            'CSV_STACK "<CASEDIR>/share/results/tables/unsmry--monthly.csv" '
            '"--split" well "--output" stacked.csv "--keepconstantcolumns"'
        )
    )

    Path("test.ert").write_text(
        "\n".join(
            [
                "ECLBASE FOO.DATA",
                "DEFINE <CASEDIR> some_ensemble",
                "QUEUE_SYSTEM LOCAL",
                "NUM_REALIZATIONS 1",
                "RUNPATH <CONFIG_PATH>",
                "",
                "LOAD_WORKFLOW CSV_STACK_WELLS",
                "HOOK_WORKFLOW CSV_STACK_WELLS POST_SIMULATION",
            ]
        ),
        encoding="utf8",
    )
    subprocess.run(["ert", "test_run", "test.ert"], check=True)

    assert Path("stacked.csv").is_file()
    pd.testing.assert_frame_equal(
        pd.read_csv("stacked.csv"),
        pd.DataFrame([{"WELL": "A", "WOPT": 1}, {"WELL": "B", "WOPT": 2}]),
    )
