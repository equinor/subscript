import os
import logging
import shutil
import subprocess

import pytest

from subscript.ecldiff2roff import ecldiff2roff

from subscript import getLogger

logger = getLogger("subscript.ecldiff2roff.ecldiff2roff")
logger.setLevel(logging.INFO)


@pytest.mark.parametrize(
    "datetxt, expected",
    [
        ("20000101 20010101", [("20000101", "20010101")]),
        ("2000-01-01 2001-01-01", [("20000101", "20010101")]),
        ("20000101 2001-01-01", [("20000101", "20010101")]),
        ("20000101         20010101", [("20000101", "20010101")]),
        ("", []),
        ("    ", []),
        ("\n\n", []),
        ("# a comment", []),
        ("-- a comment", []),
        (
            """

            # foo
            2000-03-01     2008-01-02
            20110707 20120404
            -- bar
            """,
            [("20000301", "20080102"), ("20110707", "20120404")],
        ),
    ],
)
def test_dateparsing(datetxt, expected, tmpdir):
    """Test parsing of dates"""
    # pylint: disable=unused-argument
    with open("datediff.txt", "w") as file_h:
        file_h.write(datetxt)
    assert ecldiff2roff.parse_diff_dates("datediff.txt") == expected


@pytest.fixture
def reek_data(tmpdir):
    """Prepare a data directory with Reek Eclipse binary output"""
    reekdir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data/reek/eclipse/model"
    )

    # This UNRST file contains the report steps and DATES:
    #     0:  2000-01-01
    #     6:  2000-07-01
    #    13:  2001-02-01
    #    19:  2001-08-01

    reekdest = os.path.join(tmpdir.strpath, "reekdata")
    shutil.copytree(reekdir, reekdest, copy_function=os.symlink)
    cwd = os.getcwd()
    os.chdir(reekdest)

    try:
        yield

    finally:
        os.chdir(cwd)


@pytest.mark.parametrize(
    "eclroot, prop, diffdates, outputfilebase, sep, datesep, datefmt, expected_files",
    [
        (  # Regular usage:
            "2_R001_REEK-0",
            "SGAS",
            ("2000-01-01 2000-07-01"),
            "eclgrid",
            "--",
            "_",
            "YYYYMMDD",
            ["eclgrid--sgas--20000101_20000701.roff"],
        ),
        (  # filebase changed
            "2_R001_REEK-0",
            "SGAS",
            ("2000-01-01 2000-07-01"),
            "diffgrid",
            "--",
            "_",
            "YYYYMMDD",
            ["diffgrid--sgas--20000101_20000701.roff"],
        ),
        (  # filesep
            "2_R001_REEK-0",
            "SGAS",
            ("2000-01-01 2000-07-01"),
            "eclgrid",
            "---",
            "_",
            "YYYYMMDD",
            ["eclgrid---sgas---20000101_20000701.roff"],
        ),
        (  # datesep
            "2_R001_REEK-0",
            "SGAS",
            ("2000-01-01 2000-07-01"),
            "eclgrid",
            "--",
            "-",
            "YYYYMMDD",
            ["eclgrid--sgas--20000101-20000701.roff"],
        ),
        (  # datefmt
            "2_R001_REEK-0",
            "SGAS",
            ("2000-01-01 2000-07-01"),
            "eclgrid",
            "--",
            "_",
            "YYYY-MM-DD",
            ["eclgrid--sgas--2000-01-01_2000-07-01.roff"],
        ),
        (  # custom path
            "2_R001_REEK-0",
            "SGAS",
            ("2000-01-01 2000-07-01"),
            "/tmp/eclgrid",
            "--",
            "_",
            "YYYYMMDD",
            ["/tmp/eclgrid--sgas--20000101_20000701.roff"],
        ),
        (  # multiple datepairs
            "2_R001_REEK-0",
            "SGAS",
            ("2000-01-01 2000-07-01\n2000-07-01 2001-02-01"),
            "eclgrid",
            "--",
            "_",
            "YYYYMMDD",
            [
                "eclgrid--sgas--20000101_20000701.roff",
                "eclgrid--sgas--20000701_20010201.roff",
            ],
        ),
    ],
)
def test_mainfunction(
    eclroot,
    prop,
    diffdates,
    outputfilebase,
    sep,
    datesep,
    datefmt,
    expected_files,
    reek_data,
):
    """Test the command line functionality of ecldiff2roff"""
    # pylint: disable=unused-argument
    # pylint: disable=redefined-outer-name
    # pylint: disable=too-many-arguments
    with open("datediff.txt", "w") as file_h:
        file_h.write(diffdates)

    ecldiff2roff.ecldiff2roff_main(
        eclroot, prop, "datediff.txt", outputfilebase, sep, datesep, datefmt
    )
    for expected_file in expected_files:
        assert os.path.exists(expected_file)


def test_errors(reek_data):
    """Test errors from the module"""
    # pylint: disable=unused-argument
    # pylint: disable=redefined-outer-name
    with open("validdates.txt", "w") as file_h:
        file_h.write("2000-01-01 2000-07-01")

    with open("invaliddates.txt", "w") as file_h:
        file_h.write("1860-01-01 2000-07-01")

    with open("singledate.txt", "w") as file_h:
        file_h.write("2000-07-01")

    with pytest.raises(OSError):
        ecldiff2roff.ecldiff2roff_main("NOTEXISTING", "SGAS", "validdates.txt")

    with pytest.raises(OSError):
        ecldiff2roff.ecldiff2roff_main("2_R001_REEK-0", "SGAS", "notexistingdates.txt")

    with pytest.raises(ValueError):
        ecldiff2roff.ecldiff2roff_main("2_R001_REEK-0", "SGAS", "invaliddates.txt")

    with pytest.raises(ValueError):
        ecldiff2roff.ecldiff2roff_main("2_R001_REEK-0", "SFIRE", "validdates.txt")

    with pytest.raises(ValueError):
        ecldiff2roff.ecldiff2roff_main("2_R001_REEK-0", "SGAS", "singledate.txt")


@pytest.mark.integration
def test_integration(reek_data):
    """Test that endpoint is installed and works"""
    # pylint: disable=unused-argument
    # pylint: disable=redefined-outer-name
    assert subprocess.check_output(["ecldiff2roff", "-h"])

    with open("validdates.txt", "w") as file_h:
        file_h.write("2000-01-01 2000-07-01")

    subprocess.run("ecldiff2roff 2_R001_REEK-0 SGAS", shell=True, check=True)

    subprocess.run(
        "ecldiff2roff 2_R001_REEK-0 SGAS --diffdates validdates.txt",
        shell=True,
        check=True,
    )
    assert os.path.exists("eclgrid--sgas--20000101_20000701.roff")
