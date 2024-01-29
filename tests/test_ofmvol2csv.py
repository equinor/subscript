import datetime
import os
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest
from subscript.csv2ofmvol import csv2ofmvol
from subscript.ofmvol2csv import ofmvol2csv

# pylint: disable=unused-argument  # false positive on fixtures
# pylint: disable=unsubscriptable-object  # false positive on Pandas objects.

try:
    # pylint: disable=unused-import
    import ert.shared  # noqa

    HAVE_ERT = True
except ImportError:
    HAVE_ERT = False


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
    """Test cleanup of lines in OFM file format"""
    assert ofmvol2csv.cleanse_ofm_lines(filelines) == expected


@pytest.mark.parametrize(
    "filelines, expected",
    [(["*DAY *MONTH *YEAR", "24 12 2020 x"], ["*DATE", "24.12.2020 x"])],
)
def test_unify_dateformat(filelines, expected):
    """Test that OFM vol date formats can be unified to something easier to parse"""
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
    """Test the ability to extract columnnames from a string occuring in OFM lines"""
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
    """Test ofmvol specific splitting of lists"""
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
    """Test lookup of where well data starts in strings"""
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
            ),
        ),
        (
            # ISO date:
            ["*DATE OPR", "*NAME A-1", "2020-12-24 100"],
            pd.DataFrame(
                columns=["WELL", "DATE", "OPR"],
                data=[["A-1", datetime.date(2020, 12, 24), 100]],
            ),
        ),
        (
            # Well name with space, no quoutes. Trailing space ignored.
            ["*DATE OPR", "*NAME NO A-1  ", "24.12.2020 100"],
            pd.DataFrame(
                columns=["WELL", "DATE", "OPR"],
                data=[["NO A-1", datetime.date(2020, 12, 24), 100]],
            ),
        ),
        (
            # Well name with space, quouted.
            ["*DATE OPR", "*NAME 'NO A-1'", "24.12.2020 100"],
            pd.DataFrame(
                columns=["WELL", "DATE", "OPR"],
                data=[["NO A-1", datetime.date(2020, 12, 24), 100]],
            ),
        ),
        (
            # Well name with space, quouted v2. Conserve spaces
            # inside quotes, but not spaces outside qoutes.
            ["*DATE OPR", '*NAME  "  NO A-1 W  "  ', "24.12.2020 100"],
            pd.DataFrame(
                columns=["WELL", "DATE", "OPR"],
                data=[["  NO A-1 W  ", datetime.date(2020, 12, 24), 100]],
            ),
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
            ),
        ),
        (
            # More rows, DAYS is hours-pr-day (efficiency factor):
            [
                "*DATE *OIL *DAYS",
                "*NAME A-1",
                "2020-12-24 100 24.0",
                "2020-12-25 200 23.0",
            ],
            pd.DataFrame(
                columns=["WELL", "DATE", "OIL", "DAYS"],
                data=[
                    ["A-1", datetime.date(2020, 12, 24), 100, 24.0],
                    ["A-1", datetime.date(2020, 12, 25), 200, 23.0],
                ],
            ),
        ),
        (
            # More rows, special case for hours-pr-day for injectors
            [
                "*DATE *Winj *WiDay",
                "*NAME A-1",
                "2020-12-24 100 24.0",
                "2020-12-25 200 23.0",
            ],
            pd.DataFrame(
                columns=["WELL", "DATE", "WINJ", "WIDAY"],
                data=[
                    ["A-1", datetime.date(2020, 12, 24), 100, 24.0],
                    ["A-1", datetime.date(2020, 12, 25), 200, 23.0],
                ],
            ),
        ),
        (
            # Test that we guess DD.MM.YYYY by default.
            [
                "*DATE *Days *Oil",
                "*NAME A-1",
                "01.02.1987 8.1 100",
            ],
            pd.DataFrame(
                columns=["WELL", "DATE", "DAYS", "OIL"],
                data=[
                    ["A-1", datetime.date(1987, 2, 1), 8.1, 100],
                ],
            ),
        ),
        (
            # Pandas will try MM.DD.YYYY if DD.MM.YYYY is unfeasible:
            [
                "*DATE *Days *Oil",
                "*NAME A-1",
                "01.20.1987 8.1 100",
            ],
            pd.DataFrame(
                columns=["WELL", "DATE", "DAYS", "OIL"],
                data=[
                    ["A-1", datetime.date(1987, 1, 20), 8.1, 100],
                ],
            ),
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
            ),
        ),
        (
            # Check that output is sorted on DATE:
            ["*DATE *OPR", "*NAME A-1", "2020-12-25 200", "2020-12-24 100"],
            pd.DataFrame(
                columns=["WELL", "DATE", "OPR"],
                data=[
                    ["A-1", datetime.date(2020, 12, 24), 100],
                    ["A-1", datetime.date(2020, 12, 25), 200],
                ],
            ),
        ),
        (
            # Empty dataset
            [
                "*DATE *Days *Oil",
                "*NAME A-1",
            ],
            pd.DataFrame(),
        ),
    ],
)
def test_parse_well(inputlines, expected):
    """Test parsing well data"""
    if "DATE" in expected:
        expected["DATE"] = pd.to_datetime(expected["DATE"])
        expected.set_index(["WELL", "DATE"], inplace=True)
    # Assume there is DATE line in the test input
    inputlines = ofmvol2csv.cleanse_ofm_lines(inputlines)
    colnames = ofmvol2csv.extract_columnnames(inputlines)
    dframe = ofmvol2csv.parse_well(inputlines[1:], colnames)
    pd.testing.assert_frame_equal(dframe, expected)


@pytest.mark.parametrize(
    "inputlines, expected",
    [
        (
            # Separate well input:
            [
                "*DATE *OPR",
                "*NAME A-1",
                "2020-12-25 200",
                "*NAME A-2",
                "2020-12-25 100",
            ],
            pd.DataFrame(
                columns=["WELL", "DATE", "OPR"],
                data=[
                    ["A-1", datetime.date(2020, 12, 25), 200],
                    ["A-2", datetime.date(2020, 12, 25), 100],
                ],
            ),
        ),
        (
            # Well encoded as a column in the table
            [
                "",
                "*WELL  *DATE *OPR",
                "--  comment",
                "A-1 2020-12-25 200",
                '"A-2" 2020-12-25 100',
            ],
            pd.DataFrame(
                columns=["WELL", "DATE", "OPR"],
                data=[
                    ["A-1", datetime.date(2020, 12, 25), 200],
                    ["A-2", datetime.date(2020, 12, 25), 100],
                ],
            ),
        ),
        (
            # Well encoded as second column in the table
            [
                "*DATE *WELL *OPR",
                "2020-12-25 A-1 200",
                "2020-12-25 A-2 100",
            ],
            pd.DataFrame(
                columns=["WELL", "DATE", "OPR"],
                data=[
                    ["A-1", datetime.date(2020, 12, 25), 200],
                    ["A-2", datetime.date(2020, 12, 25), 100],
                ],
            ),
        ),
        (
            # Empty dataset
            [
                "*WELL *DATE *Days *Oil",
            ],
            pd.DataFrame(
                columns=["WELL", "DATE", "DAYS", "OIL"],
                data=[],
            ),
        ),
        (
            # Another empty dataset:
            ["*METRIC", "*DAILY", "*DATE *OIL"],
            pd.DataFrame(),
        ),
        (
            [
                "*METRIC",
                "*DAILY",
                "*DATE *OIL",
                "*NAME A-4",
                "2010-01-01  1000",
            ],
            pd.DataFrame(
                columns=["WELL", "DATE", "OIL"],
                data=[["A-4", datetime.date(2010, 1, 1), 1000]],
            ),
        ),
    ],
)
def test_process_volstr(inputlines, expected):
    """Test processing ofmvol strings, consisting of header data
    and well data"""
    if "DATE" in expected:
        expected["DATE"] = pd.to_datetime(expected["DATE"])
        expected.set_index(["WELL", "DATE"], inplace=True)
    dframe = ofmvol2csv.process_volstr("\n".join(inputlines))
    pd.testing.assert_frame_equal(dframe, expected)


@pytest.mark.parametrize(
    "inputlines, expected_error",
    [
        (
            # Unparseable date:
            ["*DATE OPR", "*NAME A-1", "24.24.2020 100"],
            ValueError,  # pd._libs.tslibs.parsing.DateParseError
        ),
        (
            # Missing DATE/columns line:
            [
                "*DATO OPR",
                "*NAME A-1",
            ],
            ValueError,
        ),
        (
            # Totally bogus:
            [
                "Nothing here..",
            ],
            ValueError,
        ),
    ],
)
def test_errors(inputlines, expected_error):
    """Test some erros from ofmvol"""
    with pytest.raises(expected_error):
        ofmvol2csv.process_volstr("\n".join(inputlines))


@pytest.mark.integration
def test_cmdline():
    """Test that the command line client is installed"""
    assert subprocess.check_output(["ofmvol2csv", "-h"])


@pytest.fixture(name="datadir")
def fixture_datadir(tmp_path):
    """Provide a fixture with a directory with test data"""
    data = Path(__file__).absolute().parent / "testdata_ofmvol2csv"
    os.chdir(tmp_path)
    shutil.copytree(data, "data")
    os.chdir("data")
    yield


def test_main(datadir):
    """Test the main function used by the command line client"""
    ofmvol2csv.ofmvol2csv_main(
        "ofm_example.vol", "volfiles.csv", includefileorigin=True
    )

    output = pd.read_csv("volfiles.csv")
    assert isinstance(output, pd.DataFrame)
    # pylint: disable=no-member
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
    """Test that globbing works (also when globbing is not done by the shell)"""
    ofmvol2csv.ofmvol2csv_main("file*.vol", "volfiles.csv", includefileorigin=True)
    output = pd.read_csv("volfiles.csv")
    assert isinstance(output, pd.DataFrame)
    assert not output.empty
    assert set(output["OFMVOLFILE"]) == {"fileA.vol", "fileB.vol", "fileC.vol"}
    assert len(output) == 17
    assert output["WELL"].is_monotonic_increasing

    ofmvol2csv.ofmvol2csv_main(
        ["fileA.vol", "fileB.vol", "fileC.vol"],
        "volfiles-alt.csv",
        includefileorigin=True,
    )
    output_alt = pd.read_csv("volfiles-alt.csv")
    pd.testing.assert_frame_equal(output, output_alt)


def test_no_files(tmp_path):
    """Test what happens when input does not exist"""
    os.chdir(tmp_path)
    ofmvol2csv.ofmvol2csv_main("bogus*.vol", "volfiles.csv")
    assert not Path("volfiles.csv").exists()


def test_roundtrip(datadir, mocker):
    """Test that ofmvol2csv and csv2ofmvol can work together as inverses
    of each other."""
    ofmvol2csv.ofmvol2csv_main(
        ["ofm_example.vol"], "volfiles.csv", includefileorigin=False
    )

    first_frame = pd.read_csv("volfiles.csv")

    mocker.patch(
        "sys.argv", ["csv2ofmvol", "volfiles.csv", "--output", "backagain.vol"]
    )
    csv2ofmvol.main()

    ofmvol2csv.ofmvol2csv_main(["backagain.vol"], "take2.csv", includefileorigin=False)
    second_frame = pd.read_csv("take2.csv")

    print(first_frame.head())
    print(second_frame.head())

    pd.testing.assert_frame_equal(first_frame, second_frame)


@pytest.mark.integration
@pytest.mark.skipif(not HAVE_ERT, reason="Requires ERT to be installed")
def test_ert_hook(datadir):
    """Test the installed ERT forward model"""
    Path("FOOBAR.DATA").write_text("--Empty", encoding="utf8")
    ert_config = [
        "ECLBASE FOOBAR.DATA",
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH <CONFIG_PATH>",
        "FORWARD_MODEL OFMVOL2CSV(<VOLFILES>=file*.vol, <OUTPUT>=proddata.csv)",
    ]

    ert_config_fname = "test.ert"
    Path(ert_config_fname).write_text("\n".join(ert_config), encoding="utf8")

    subprocess.run(["ert", "test_run", ert_config_fname], check=True)

    assert Path("proddata.csv").exists()

    assert not pd.read_csv("proddata.csv").empty
