import os
import sys
import datetime
import shutil
import subprocess

import pandas as pd

import pytest

from subscript.ofmvol2csv import ofmvol2csv
from subscript.csv2ofmvol import csv2ofmvol

try:
    # pylint: disable=unused-import
    import ert_shared  # noqa

    HAVE_ERT = True
except ImportError:
    HAVE_ERT = False


# pylint: disable=redefined-outer-name  # conflict with fixtures
# pylint: disable=unused-argument  # conflict with fixtures
# pylint: disable=missing-function-docstring  # docstrings not needed here.


@pytest.mark.parametrize(
    "filelines, expected",
    [
        ([""], []),
        ([], []),
        (["-- foo"], []),
        (["-- foo", "hei"], ["HEI"]),
        (["hei\r"], ["HEI"]),
        (["12\t44"], ["12 44"]),
        (["12\t   44"], ["12    44"]),
    ],
)
def test_cleanse_ofm_lines(filelines, expected):
    assert ofmvol2csv.cleanse_ofm_lines(filelines) == expected


@pytest.mark.parametrize(
    "filelines, expected",
    [(["*DAY *MONTH *YEAR", "24 12 2020 x"], ["*DATE", "24.12.2020 x"])],
)
def test_unify_dateformat(filelines, expected):
    assert ofmvol2csv.unify_dateformat(filelines) == expected


@pytest.mark.parametrize(
    "filelines, expected",
    [
        ([], []),
        ([""], []),
        (["*DATE"], ["DATE"]),
        (["*DATE FOPR FGPR"], ["DATE", "FOPR", "FGPR"]),
        (["*DATE FOPR FGPR", "10 11 12"], ["DATE", "FOPR", "FGPR"]),
        (["bogus line", "*DATE FOPR FGPR"], ["DATE", "FOPR", "FGPR"]),
        (["*DATE FOPR", "*DATE FGPR"], ValueError),
    ],
)
def test_extract_columnnames(filelines, expected):
    if isinstance(expected, list):
        assert ofmvol2csv.extract_columnnames(filelines) == expected
    else:
        with pytest.raises(expected):
            ofmvol2csv.extract_columnnames(filelines)


@pytest.mark.parametrize(
    "inputlist, splitidxs, expected",
    [
        ([], [], [[]]),
        (["a"], [], [["a"]]),
        (["a"], [0], [["a"]]),
        (["a"], [0, 0], [["a"]]),
        (["a"], [1], [["a"]]),
        (["a"], [1, 1], [["a"]]),
        (["a", "b"], [], [["a", "b"]]),
        (["a", "b"], [0], [["a", "b"]]),
        (["a", "b"], [1], [["a"], ["b"]]),
        (["a", "b"], [2], [["a", "b"]]),
        (["a", "b", "c"], [0, 1], [["a"], ["b", "c"]]),
        (["a", "b", "c"], [1, 2], [["a"], ["b"], ["c"]]),
        (["a", "b", "c"], [1, 1, 1, 2], [["a"], ["b"], ["c"]]),
        (["a", "b", "c"], [1, 2, 2, 2, 2], [["a"], ["b"], ["c"]]),
        (["a", "b", "c"], [2, 2], [["a", "b"], ["c"]]),
        (["a", "b", "c"], [2, 0], ValueError),
    ],
)
def test_split_list(inputlist, splitidxs, expected):
    if isinstance(expected, list):
        assert ofmvol2csv.split_list(inputlist, splitidxs) == expected
    else:
        with pytest.raises(expected):
            ofmvol2csv.split_list(inputlist, splitidxs)


@pytest.mark.parametrize(
    "inputlines, expected",
    [
        ([], []),
        ([""], []),
        (["FOO"], []),
        (["*NAME FOO"], [0]),
        (["FOO", "*NAME BAR"], [1]),
        (["FOO", "*NAME  BAR", "*NAME  BART"], [1, 2]),
    ],
)
def test_find_wellstart_indices(inputlines, expected):
    if isinstance(expected, list):
        assert ofmvol2csv.find_wellstart_indices(inputlines) == expected
    else:
        with pytest.raises(expected):
            ofmvol2csv.find_wellstart_indices(inputlines)


@pytest.mark.parametrize(
    "inputlines, expected",
    [
        (
            # Simplest test:
            ["*DATE OPR", "*NAME A-1", "24.12.2020 100"],
            pd.DataFrame(
                columns=["WELL", "DATE", "OPR"],
                data=[["A-1", datetime.date(2020, 12, 24), 100]],
            ).set_index(["WELL", "DATE"]),
        ),
        (
            # ISO date:
            ["*DATE OPR", "*NAME A-1", "2020-12-24 100"],
            pd.DataFrame(
                columns=["WELL", "DATE", "OPR"],
                data=[["A-1", datetime.date(2020, 12, 24), 100]],
            ).set_index(["WELL", "DATE"]),
        ),
        (
            # More rows:
            ["*DATE OPR", "*NAME A-1", "2020-12-24 100", "2020-12-25 200"],
            pd.DataFrame(
                columns=["WELL", "DATE", "OPR"],
                data=[
                    ["A-1", datetime.date(2020, 12, 24), 100],
                    ["A-1", datetime.date(2020, 12, 25), 200],
                ],
            ).set_index(["WELL", "DATE"]),
        ),
        (
            # More columns:
            [
                "*DATE *OPR *gas",
                "*NAME A-1",
                "2020-12-24 100 10000",
                "2020-12-25 200\t  20000",
            ],
            pd.DataFrame(
                columns=["WELL", "DATE", "OPR", "GAS"],
                data=[
                    ["A-1", datetime.date(2020, 12, 24), 100, 10000],
                    ["A-1", datetime.date(2020, 12, 25), 200, 20000],
                ],
            ).set_index(["WELL", "DATE"]),
        ),
        (
            # Check that output is sorted on DATE:
            [
                "*DATE *OPR",
                "*NAME A-1",
                "2020-12-25 200",
                "2020-12-24 100",
            ],
            pd.DataFrame(
                columns=["WELL", "DATE", "OPR"],
                data=[
                    ["A-1", datetime.date(2020, 12, 24), 100],
                    ["A-1", datetime.date(2020, 12, 25), 200],
                ],
            ).set_index(["WELL", "DATE"]),
        ),
    ],
)
def test_parse_well(inputlines, expected):
    # Assume there is DATE line in the test input
    inputlines = ofmvol2csv.cleanse_ofm_lines(inputlines)
    colnames = ofmvol2csv.extract_columnnames(inputlines)
    dframe = ofmvol2csv.parse_well(inputlines[1:], colnames)
    pd.testing.assert_frame_equal(dframe, expected)


@pytest.mark.integration
def test_cmdline():
    assert subprocess.check_output(["ofmvol2csv", "-h"])


@pytest.fixture
def datadir(tmpdir):
    data = os.path.join(os.path.dirname(__file__), "testdata_ofmvol2csv")
    tmpdir.chdir()
    shutil.copytree(data, "data")
    os.chdir("data")
    yield


def test_main(datadir):
    ofmvol2csv.ofmvol2csv_main(
        "ofm_example.vol", "volfiles.csv", includefileorigin=True
    )

    output = pd.read_csv("volfiles.csv")
    assert isinstance(output, pd.DataFrame)
    assert not output.empty
    assert len(output) == 4379
    assert set(output.columns) == {
        "WELL",
        "DATE",
        "OIL",
        "GAS",
        "WATER",
        "GINJ",
        "DAYS",
        "OFMVOLFILE",
    }
    assert set(output["WELL"].unique()) == {
        "WELL_A",
        "WELL_B",
        "WELL_C",
        "WELL_D",
        "WELL_E",
    }
    assert round(output["OIL"].sum(), 0) == 3243320
    assert round(output["GAS"].sum(), 0) == 545934037
    assert round(output["WATER"].sum(), 0) == 447465
    assert round(output["GINJ"].sum(), 0) == 92701411
    assert int(output["DAYS"].mean()) == 24


def test_cmdline_globbing(datadir):
    ofmvol2csv.ofmvol2csv_main("file*.vol", "volfiles.csv", includefileorigin=True)
    output = pd.read_csv("volfiles.csv")
    assert isinstance(output, pd.DataFrame)
    assert not output.empty
    assert set(output["OFMVOLFILE"]) == {"fileA.vol", "fileB.vol"}
    assert len(output) == 15
    assert output["WELL"].is_monotonic

    ofmvol2csv.ofmvol2csv_main(
        ["fileA.vol", "fileB.vol"], "volfiles-alt.csv", includefileorigin=True
    )
    output_alt = pd.read_csv("volfiles-alt.csv")
    pd.testing.assert_frame_equal(output, output_alt)


def test_no_files(tmpdir):
    tmpdir.chdir()
    ofmvol2csv.ofmvol2csv_main("bogus*.vol", "volfiles.csv")
    assert not os.path.exists("volfiles.csv")


def test_roundtrip(datadir):
    """Test that ofmvol2csv and csv2ofmvol can work together as inverses
    of each other."""
    ofmvol2csv.ofmvol2csv_main(
        ["ofm_example.vol"], "volfiles.csv", includefileorigin=False
    )

    first_frame = pd.read_csv("volfiles.csv")

    sys.argv = ["csv2ofmvol", "volfiles.csv", "--output", "backagain.vol"]
    csv2ofmvol.main()

    ofmvol2csv.ofmvol2csv_main(["backagain.vol"], "take2.csv", includefileorigin=False)
    second_frame = pd.read_csv("take2.csv")

    print(first_frame.head())
    print(second_frame.head())

    pd.testing.assert_frame_equal(first_frame, second_frame)


def test_bogusfiles(tmpdir):
    tmpdir.chdir()
    with open("bogus.vol", "w") as file_h:
        file_h.write("Nothing here")
    ofmvol2csv.ofmvol2csv_main("bogus.vol", "bogus.csv")
    assert not os.path.exists("bogus.csv")

    with open("emptydata.vol", "w") as file_h:
        file_h.write("*DATE *OIL\n")
        file_h.write("*NAME WELL-NODATA\n")

    ofmvol2csv.ofmvol2csv_main("emptydata.vol", "empty.csv")
    assert not os.path.exists("empty.csv")


def test_wrongdateformat(tmpdir):
    tmpdir.chdir()

    with open("date.vol", "w") as file_h:
        file_h.write("*DATE *OIL\n")
        file_h.write("*NAME WELLNAME\n")
        file_h.write("33.33.3333 100")
    ofmvol2csv.ofmvol2csv_main("date.vol", "nodate.csv")
    assert os.path.exists("nodate.csv")
    # This currently goes through, pandas reads the erroneous
    # date as a string/object, and is outputted untouched to the CSV
    # Maybe fair enough to let another downstream tool pick up the error.


@pytest.mark.integration
@pytest.mark.skipif(not HAVE_ERT, reason="Requires ERT to be installed")
def test_ert_hook(datadir):
    with open("FOO.DATA", "w") as file_h:
        file_h.write("--Empty")
    ert_config = [
        "ECLBASE FOO.DATA",
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH .",
        "FORWARD_MODEL OFMVOL2CSV(<VOLFILES>=file*.vol, <OUTPUT>=proddata.csv)",
    ]

    ert_config_fname = "test.ert"
    with open(ert_config_fname, "w") as file_h:
        file_h.write("\n".join(ert_config))

    subprocess.run(["ert", "test_run", ert_config_fname], check=True)

    assert os.path.exists("proddata.csv")
    print(pd.read_csv("proddata.csv"))
