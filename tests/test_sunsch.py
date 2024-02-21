import datetime
import os
import shutil
import subprocess
from pathlib import Path

import pytest  # noqa: F401
import yaml
from pydantic import ValidationError
from subscript.sunsch import sunsch

DATADIR = Path(__file__).absolute().parent / "testdata_sunsch"

# pylint: disable=unused-argument


@pytest.fixture(name="readonly_datadir")
def fixture_readonly_datadir():
    """When used as a fixture, the test function will run in the testdata
    directory. Do not write new or temporary files in here"""
    cwd = Path.cwd()
    try:
        os.chdir(DATADIR)
        yield
    finally:
        os.chdir(cwd)


@pytest.fixture(name="testdata")
def fixture_testdata(tmp_path):
    """Fixture providing test data for test functions"""
    os.chdir(tmp_path)
    cwd = os.getcwd()
    shutil.copytree(DATADIR, "testdata_sunsch")
    try:
        os.chdir("testdata_sunsch")
        yield
    finally:
        os.chdir(cwd)


def test_main(testdata, caplog, mocker):
    """Test command line sunsch, loading a yaml file"""
    outfile = "schedule.inc"  # also in config.yml

    mocker.patch("sys.argv", ["sunsch", "config.yml"])
    sunsch.main()
    assert "DEPRECATED" not in caplog.text
    assert Path(outfile).exists()

    schlines = Path(outfile).read_text(encoding="utf8").splitlines()
    assert len(schlines) > 70

    # Check footemplate.sch was included:
    assert any("A-90" in x for x in schlines)

    # Sample check for mergeme.sch:
    assert any("WRFTPLT" in x for x in schlines)

    # Check for foo1.sch, A-1 should occur twice
    assert sum("A-1" in x for x in schlines) == 2

    # Check for substitutetest, the last 1 has to be integer as it is a table index:
    assert any("'A-90' 'OPEN' 'ORAT' 3000 0 400000 1 /" in x for x in schlines)

    # Check for randomid:
    assert any("A-4" in x for x in schlines)

    # Test that we can have statements in the init file
    # before the first DATES that are kept:

    sch_conf = yaml.safe_load(Path("config.yml").read_text(encoding="utf8"))
    print(sch_conf)
    sch_conf["init"] = "initwithdates.sch"
    sunsch.process_sch_config(sch_conf)

    # BAR-FOO is a magic string that occurs before any DATES in initwithdates.sch
    assert "BAR-FOO" in "".join(Path(outfile).read_text(encoding="utf8").splitlines())


def test_cmdline_output(testdata, mocker):
    """Test that command line options can override configuration file"""
    mocker.patch(
        "sys.argv", ["sunsch", "--output", "subdir/schedule.inc", "config.yml"]
    )
    Path("subdir").mkdir()
    sunsch.main()
    assert Path("subdir/schedule.inc").exists()


def test_cmdline_startdate(testdata, mocker):
    """Test that --startdate on command line overrides config"""
    mocker.patch("sys.argv", ["sunsch", "--startdate", "2020-01-01", "config.yml"])
    sunsch.main()
    assert "2018" not in Path("schedule.inc").read_text(encoding="utf8")


def test_cmdline_enddate(testdata, mocker):
    """Test that --enddate on command line overrides config"""
    mocker.patch("sys.argv", ["sunsch", "--enddate", "2020-01-01", "config.yml"])
    sunsch.main()
    assert "2021" not in Path("schedule.inc").read_text(encoding="utf8")


def test_cmdline_refdate(testdata, mocker):
    """Test that --refdate on command line overrides config"""
    # Baseline run, proving refdate follows refdate in config yaml:
    mocker.patch("sys.argv", ["sunsch", "config.yml"])
    sunsch.main()
    # 40 days after refdate, which is 2018-01-01 in yaml:
    assert "10 'FEB' 2018" in Path("schedule.inc").read_text(encoding="utf8")

    mocker.patch("sys.argv", ["sunsch", "--refdate", "2019-01-01", "config.yml"])
    sunsch.main()
    # It  should not be 40 days after startdate,
    assert "10 'FEB' 2018" not in Path("schedule.inc").read_text(encoding="utf8")
    # but 40 days after command line refdate:
    assert "10 'FEB' 2019" in Path("schedule.inc").read_text(encoding="utf8")


def test_cmdline_dategrid(testdata, mocker):
    """Test that dategrid can be overridden on command line"""
    mocker.patch("sys.argv", ["sunsch", "--dategrid", "daily", "config.yml"])
    sunsch.main()
    assert "6 'JAN' 2017" in Path("schedule.inc").read_text(encoding="utf8")
    assert "7 'JAN' 2017" in Path("schedule.inc").read_text(encoding="utf8")
    assert "8 'JAN' 2017" in Path("schedule.inc").read_text(encoding="utf8")
    assert "9 'JAN' 2017" in Path("schedule.inc").read_text(encoding="utf8")


def test_dump_stdout(testdata, mocker):
    """Test that we can write to stdout"""
    result = subprocess.run(
        ["sunsch", "--output", "-", "config.yml"], check=True, stdout=subprocess.PIPE
    )
    assert "1 'FEB' 2020" in result.stdout.decode()
    assert "subscript" not in result.stdout.decode()

    # Verify that INFO logging is not included while writing to stdout:
    result = subprocess.run(
        ["sunsch", "--verbose", "--output", "-", "config.yml"],
        check=True,
        stdout=subprocess.PIPE,
    )
    assert "1 'FEB' 2020" in result.stdout.decode()
    # (we would accept log messages to stderr)
    assert "INFO:subscript" not in result.stdout.decode()

    # Verify that DEBUG logging is not included while writing to stdout:
    result = subprocess.run(
        ["sunsch", "--debug", "--output", "-", "config.yml"],
        check=True,
        stdout=subprocess.PIPE,
    )
    assert "1 'FEB' 2020" in result.stdout.decode()
    # (we would accept log messages to stderr)
    assert "INFO:subscript" not in result.stdout.decode()
    assert "DEBUG:subscript" not in result.stdout.decode()


def test_templating(tmp_path):
    """Test templating"""
    os.chdir(tmp_path)
    Path("template.tmpl").write_text(
        "WCONHIST\n<WELLNAME> OPEN ORAT <ORAT> <GRAT> /\n/", encoding="utf8"
    )

    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [
            {
                "template": "template.tmpl",
                "days": 10,
                "substitute": {"WELLNAME": "A-007", "ORAT": 200.3, "GRAT": 1.4e6},
            }
        ],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert "A-007" in str(sch)
    assert "200.3" in str(sch)
    assert "1400000" in str(sch)

    # Let some of the valued be undefined:
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [
            {
                "template": "template.tmpl",
                "days": 10,
                "substitute": {"WELLNAME": "A-007"},
            }
        ],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert "A-007" in str(sch)
    assert "<ORAT>" in str(sch)
    # (this error is let through sunsch)

    # Let the date be undefined.
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [{"template": "template.tmpl", "substitute": {"WELLNAME": "A-007"}}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    # sunsch logs this as an error that there is no date defined for the template.
    assert "A-007" not in str(sch)

    # Skip defining substitute:
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [{"template": "template.tmpl", "days": 100}],
    }

    sch = sunsch.process_sch_config(sunschconf)
    assert "A-007" not in str(sch)
    # Sunsch lets this though, but logs an error.

    # Let the template file be empty:
    Path("empty.tmpl").write_text("", encoding="utf8")
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "insert": [
            {
                "template": "empty.tmpl",
                "days": 10,
                "substitute": {"WELLNAM": "A-007", "ORAT": 200.3, "GRAT": 1.4e6},
            }
        ],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert str(sch) == ""


def test_days_integer(readonly_datadir):
    """Test that we can insert stuff a certain number of days
    after startup"""
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [{"filename": "foo1.sch", "days": 10}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert datetime.datetime(2020, 1, 11, 0, 0, 0) in sch.dates

    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [{"filename": "foo1.sch", "days": 10.0}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert datetime.datetime(2020, 1, 11, 0, 0, 0) in sch.dates


def test_days_float(readonly_datadir):
    """Test that we can insert stuff a certain number of
    floating point days after startup"""
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [{"filename": "foo1.sch", "days": 10.1}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    # The TimeVector object has the "correct" date including time,
    # being 0.1 days after 2020-1-11
    assert datetime.datetime(2020, 1, 11, 2, 24, 0) in sch.dates
    # Now also the clocktime is stringified (using updated TimeVector)
    assert "11 'JAN' 2020 02:24:00" in str(sch)

    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [{"filename": "foo1.sch", "days": 10.9}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert datetime.datetime(2020, 1, 11, 21, 36, 0) in sch.dates
    # TimeVector now support clocktimes
    assert "11 'JAN' 2020 21:36:00" in str(sch)
    # Check that microsecs do not leak into string unless required
    assert "21:36:00 " in str(sch) or "21:36:00/" in str(sch)


def test_starttime(readonly_datadir):
    """Test the starttime feature"""
    sunschconf = {
        "starttime": datetime.datetime(2020, 2, 1, 0, 0, 0),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [{"filename": "foo1.sch", "days": 10}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert "11 'FEB' 2020 00:00:00" in str(sch)

    sunschconf = {
        "starttime": datetime.datetime(2020, 2, 1, 23, 59, 59),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [{"filename": "foo1.sch", "days": 10}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    # Dates are rounded down, clock-times are now supported
    assert "11 'FEB' 2020 23:59:59" in str(sch)


def test_microsecs(readonly_datadir):
    """Test that microsecs are formatted correctly"""
    sunschconf = {
        "starttime": datetime.datetime(2020, 1, 1, 1, 2, 3),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [{"filename": "foo1.sch", "days": 10}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert "01:02:03 " in str(sch) or "01:02:03/" in str(sch)
    sunschconf = {
        "starttime": datetime.datetime(2020, 1, 1, 1, 2, 3, 123400),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [{"filename": "foo1.sch", "days": 10}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert "01:02:03.1234" in str(sch)


def test_dateclip(readonly_datadir):
    """Test dateclipping"""
    # Clip dates after enddate:
    sunschconf = {
        "startdate": datetime.date(1900, 1, 1),
        "enddate": datetime.date(2020, 1, 1),
        "files": ["mergeme.sch"],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert datetime.datetime(2019, 2, 9, 0, 0) in sch.dates
    assert datetime.datetime(2020, 10, 1, 0, 0) not in sch.dates

    # Nothing to clip here:
    sunschconf = {
        "startdate": datetime.date(1900, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "files": ["mergeme.sch"],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert datetime.datetime(2020, 10, 1, 0, 0) in sch.dates
    assert datetime.datetime(2019, 2, 9, 0, 0) in sch.dates

    # Clip events before startdate:
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "files": ["mergeme.sch"],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert datetime.datetime(2019, 2, 9, 0, 0) not in sch.dates
    assert datetime.datetime(2020, 10, 1, 0, 0) in sch.dates

    # Inserting before end-date should not be clipped.
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2041, 1, 1),
        "insert": [{"filename": "foo1.sch", "date": datetime.date(2030, 1, 1)}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert datetime.datetime(2030, 1, 1, 0, 0) in sch.dates

    # Inserting after end-date should be clipped.
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [{"filename": "foo1.sch", "date": datetime.date(2030, 1, 1)}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert datetime.datetime(2030, 1, 1, 0, 0) not in sch.dates

    # Inserting before start-date should be clipped.
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [{"filename": "foo1.sch", "date": datetime.date(2000, 1, 1)}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert datetime.datetime(2000, 1, 1, 0, 0) not in sch.dates


def test_nonisodate(readonly_datadir):
    """Test behaviour when users use non-ISO-dates"""
    sunschconf = {
        "startdate": "01-01-2020",  # Look, this is not how to write dates!
        "insert": [{"filename": "foo1.sch", "date": datetime.date(2030, 1, 1)}],
    }
    with pytest.raises(ValueError):
        sunsch.process_sch_config(sunschconf)

    # Check also for refdate:
    sunschconf = {
        "refdate": "01-01-2020",
        "insert": [{"filename": "foo1.sch", "date": datetime.date(2030, 1, 1)}],
    }
    with pytest.raises(ValueError):
        sunsch.process_sch_config(sunschconf)

    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": "01-01-2020",
        "insert": [{"filename": "foo1.sch", "date": datetime.date(2030, 1, 1)}],
    }
    with pytest.raises(ValidationError):
        sunsch.process_sch_config(sunschconf)


def test_merge_include_nonexist(tmp_path):
    """If a user merges in a sch file which contains INCLUDE
    statements, these files may not exist yet (or only for a
    different path and so on.

    The way to get around this, is to do string insertions
    in the insert section.
    """
    os.chdir(tmp_path)
    Path("mergewithexistinginclude.sch").write_text(
        """
DATES
  1 'JAN' 2030 /
/

INCLUDE
  'something.sch' /
""",
        encoding="utf8",
    )
    Path("something.sch").write_text(
        """
WRFTPLT
  2 /
/
""",
        encoding="utf8",
    )

    sunschconf = {
        "startdate": datetime.date(2000, 1, 1),
        "files": ["mergewithexistinginclude.sch"],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert "WRFTPLT" in str(sch)

    # Now if it does not exist:
    Path("mergewithnonexistinginclude.sch").write_text(
        """
DATES
  1 'JAN' 2030 /
/

INCLUDE
  'somethingnotexistingyet.sch' /
""",
        encoding="utf8",
    )
    sunschconf = {
        "startdate": datetime.date(2000, 1, 1),
        "merge": "mergewithnonexistinginclude.sch",
    }
    # This crashes in C-code and exits, can't catch it using pytest:
    # "A fatal error has occured and the application will stop"
    # "Could not open file: ....somethingnotexistingyet.sch"

    # sch = sunsch.process_sch_config(sunschconf)

    sunschconf = {
        "startdate": datetime.date(2000, 1, 1),
        "insert": [{"days": 2, "string": "INCLUDE\n  'something.sch'/\n"}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert "something.sch" in str(sch)


def test_merge_paths_in_use(tmp_path, caplog):
    """If the PATHS keyword is in use for getting includes,
    there will be "variables" in use in INCLUDE-statements.

    These variables are defined in the DATA file and outside
    sunsch's scope, but we should ensure a proper error message"""
    os.chdir(tmp_path)
    Path("pathsinclude.sch").write_text(
        """
DATES
  1 'JAN' 2030 /
/

INCLUDE
  '$MYSCHFILES/something.sch' /
""",
        encoding="utf8",
    )

    sunschconf = {
        "startdate": datetime.date(2000, 1, 1),
        "files": ["pathsinclude.sch"],
    }
    with pytest.raises(SystemExit):
        sunsch.process_sch_config(sunschconf)
    assert "PATHS variables in INCLUDE" in caplog.text


def test_merge(readonly_datadir):
    """Test that merge can be both a list and a string, that
    allows both syntaxes in yaml:

    merge: filename.sch

    and

    merge:
      - filename1.sch
      - filename2.sch
    """
    sunschconf = {"startdate": datetime.date(2000, 1, 1), "files": ["mergeme.sch"]}
    sch = sunsch.process_sch_config(sunschconf)
    assert "WRFTPLT" in str(sch)
    sunschconf = {"startdate": datetime.date(2000, 1, 1), "files": ["mergeme.sch"]}
    sch = sunsch.process_sch_config(sunschconf)
    assert "WRFTPLT" in str(sch)


def test_sch_file_nonempty(tmp_path):
    """Test that we can detect empty files"""
    os.chdir(tmp_path)

    Path("empty.sch").write_text("", encoding="utf8")
    assert not sunsch.sch_file_nonempty("empty.sch")

    Path("commentonly.sch").write_text("-- an Eclipse comment", encoding="utf8")
    assert not sunsch.sch_file_nonempty("commentonly.sch")

    Path("dates.sch").write_text("DATES\n 1 NOV 2080 / \n/", encoding="utf8")
    assert sunsch.sch_file_nonempty("dates.sch")

    Path("wconprod.sch").write_text("WCONPROD\n A ORAT 0 / \n/", encoding="utf8")
    assert sunsch.sch_file_nonempty("wconprod.sch")

    Path("bogus.sch").write_text("BOGUSrn A ORAT 0 / \n/", encoding="utf8")
    # Such a bogus file will give errors later, but
    # it should be treated as nonempty to be able
    # to catch the error elsewhere.
    assert sunsch.sch_file_nonempty("wconprod.sch")


def test_emptyfiles(tmp_path):
    """Test that we don't crash when we try to include files
    which are empty (or only contains comments)"""
    os.chdir(tmp_path)
    Path("empty.sch").write_text("", encoding="utf8")
    sunschconf = {"startdate": datetime.date(2000, 1, 1), "files": ["empty.sch"]}
    sch = sunsch.process_sch_config(sunschconf)
    assert str(sch) == ""

    Path("commentonly.sch").write_text("-- an Eclipse comment", encoding="utf8")
    sunschconf = {"startdate": datetime.date(2000, 1, 1), "files": ["commentonly.sch"]}
    sch = sunsch.process_sch_config(sunschconf)
    assert str(sch) == ""

    sunschconf = {
        "startdate": datetime.date(2000, 1, 1),
        "insert": [{"filename": "commentonly.sch", "days": 1}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert str(sch) == ""


def test_dategrid():
    """Test dategrid generation support in sunsch"""
    # Daily
    sch = sunsch.process_sch_config(
        {
            "startdate": datetime.date(2021, 1, 1),
            "enddate": datetime.date(2022, 1, 1),
            "dategrid": "daily",
        }
    )
    assert len(sch) == 366
    assert datetime.datetime(2021, 1, 1, 0, 0) in sch.dates
    assert datetime.datetime(2021, 6, 6, 0, 0) in sch.dates
    assert datetime.datetime(2022, 1, 1, 0, 0) in sch.dates

    # Yearly
    sch = sunsch.process_sch_config(
        {
            "startdate": datetime.date(2020, 1, 1),
            "enddate": datetime.date(2021, 1, 1),
            "dategrid": "yearly",
        }
    )
    assert len(sch) == 2
    assert datetime.datetime(2020, 1, 1, 0, 0) in sch.dates
    assert datetime.datetime(2021, 1, 1, 0, 0) in sch.dates

    # Monthly
    sch = sunsch.process_sch_config(
        {
            "startdate": datetime.date(2020, 1, 1),
            "enddate": datetime.date(2021, 1, 1),
            "dategrid": "monthly",
        }
    )
    assert datetime.datetime(2020, 1, 1, 0, 0) in sch.dates
    assert datetime.datetime(2020, 2, 1, 0, 0) in sch.dates
    assert datetime.datetime(2020, 12, 1, 0, 0) in sch.dates
    assert datetime.datetime(2021, 1, 1, 0, 0) in sch.dates
    assert max(sch.dates) == datetime.datetime(2021, 1, 1, 0, 0)
    assert min(sch.dates) == datetime.datetime(2020, 1, 1, 0, 0)

    # Bi-Monthly
    sch = sunsch.process_sch_config(
        {
            "startdate": datetime.date(2020, 1, 1),
            "enddate": datetime.date(2021, 1, 1),
            "dategrid": "bimonthly",
        }
    )
    assert datetime.datetime(2020, 1, 1, 0, 0) in sch.dates
    assert datetime.datetime(2020, 2, 1, 0, 0) not in sch.dates
    assert datetime.datetime(2020, 3, 1, 0, 0) in sch.dates
    assert datetime.datetime(2020, 11, 1, 0, 0) in sch.dates
    assert datetime.datetime(2020, 12, 1, 0, 0) not in sch.dates
    assert datetime.datetime(2021, 1, 1, 0, 0) in sch.dates
    assert max(sch.dates) == datetime.datetime(2021, 1, 1, 0, 0)
    assert min(sch.dates) == datetime.datetime(2020, 1, 1, 0, 0)

    # Weekly
    sch = sunsch.process_sch_config(
        {
            "startdate": datetime.date(2020, 1, 1),
            "enddate": datetime.date(2021, 1, 1),
            "dategrid": "weekly",
        }
    )
    assert len(sch) == 54
    assert datetime.datetime(2020, 1, 1, 0, 0) in sch.dates
    assert datetime.datetime(2020, 1, 8, 0, 0) in sch.dates
    assert datetime.datetime(2020, 12, 30, 0, 0) in sch.dates
    assert datetime.datetime(2021, 1, 1, 0, 0) in sch.dates
    assert max(sch.dates) == datetime.datetime(2021, 1, 1, 0, 0)
    assert min(sch.dates) == datetime.datetime(2020, 1, 1, 0, 0)

    # Bi-Weekly
    sch = sunsch.process_sch_config(
        {
            "startdate": datetime.date(2020, 1, 1),
            "enddate": datetime.date(2021, 1, 1),
            "dategrid": "biweekly",
        }
    )
    assert len(sch) == 28
    assert datetime.datetime(2020, 1, 1, 0, 0) in sch.dates
    assert datetime.datetime(2020, 1, 15, 0, 0) in sch.dates
    assert datetime.datetime(2020, 12, 16, 0, 0) in sch.dates
    assert datetime.datetime(2021, 1, 1, 0, 0) in sch.dates
    assert max(sch.dates) == datetime.datetime(2021, 1, 1, 0, 0)
    assert min(sch.dates) == datetime.datetime(2020, 1, 1, 0, 0)

    # Unknown dategrid
    with pytest.raises(ValidationError):
        sch = sunsch.process_sch_config(
            {
                "startdate": datetime.date(2020, 1, 1),
                "enddate": datetime.date(2021, 1, 1),
                "dategrid": "biyearly",
            }
        )


def test_wrap_long_lines():
    """Test that lines that are excessively long gets wrapped.

    Eclipse allows lines at atmost 128 characters length."""
    assert sunsch.wrap_long_lines("") == ""
    assert sunsch.wrap_long_lines("foo") == "foo"
    assert sunsch.wrap_long_lines("\n") == ""
    assert sunsch.wrap_long_lines("foo\n") == "foo"
    assert sunsch.wrap_long_lines("x" * 127) == "x" * 127
    assert sunsch.wrap_long_lines("x" * 128) == "x" * 128

    # We don't break long "words", let these error in Eclipse:
    assert sunsch.wrap_long_lines("x" * 129) == "x" * 129
    assert sunsch.wrap_long_lines("x x x x x", maxchars=3) == "x x\nx x\nx"

    # Whitespace is collapsed before wrapping:
    assert sunsch.wrap_long_lines("x         x", maxchars=3) == "x x"
    assert sunsch.wrap_long_lines("       x         x", maxchars=3) == "x x"
    # But whitespace in short enough line is not touched:
    assert sunsch.wrap_long_lines("x     x", maxchars=9) == "x     x"

    # Check that minus signs are not treated as hyphens (at which to break lines):
    assert sunsch.wrap_long_lines("-1.2 -4.5", maxchars=6) == "-1.2\n-4.5"
    assert sunsch.wrap_long_lines("1.00e-5 1.111e-6", maxchars=6) == "1.00e-5\n1.111e-6"

    # Comments must never be wrapped, and whitespace untouched:
    assert sunsch.wrap_long_lines("-- foo bar   com", maxchars=6) == "-- foo bar   com"
    assert (
        sunsch.wrap_long_lines("1 3 5 4 5 -- long line", maxchars=13)
        == "1 3 5 4 5 -- long line"
    )
    assert (
        sunsch.wrap_long_lines("1 3 5 4 5 -- long line", maxchars=5)
        == "1 3 5\n4 5-- long line"
    )


def test_long_vfp_lines(tmp_path, caplog, mocker):
    """Make sure that lines can't get too long for Eclipse"""
    os.chdir(tmp_path)
    Path("vfp.inc").write_text(
        """VFPPROD
1 100 'GAS' 'WGR' 'GOR' 'THP' ' ' 'METRIC' 'BHP' /
100000 300000 1000000 2000000 3000000 4000000 5000000
6000000 7000000 8000000 9000000 10000000
/
30 50 /
0 /
5000 /
0 /
-- This two-line record might get emitted as one long line by opm-common
-- This will error in Eclipse
1 1 1 1 35.4324212 37.234245 39.2343242 40.4324234 43.23523546 45.54676535
        47.3242356 49.345345 50.2342343 52.4353456 54.24342344 56.32424324
/
2 1 1 1 55.4324212 57.234245 59.2343242 60.4324234 63.23523546 65.54676535
        67.3242356 69.345345 70.2342343 72.4353456 74.24342344 76.32424324
/""",
        encoding="utf-8",
    )

    Path("conf.yml").write_text(
        "files:\n  - vfp.inc\noutput: sch.inc", encoding="utf-8"
    )
    mocker.patch("sys.argv", ["sunsch", "conf.yml"])
    sunsch.main()
    schinc = Path("sch.inc").read_text(encoding="utf8")
    assert max([len(line) for line in schinc.split("\n")]) <= 129
    # assert "Line 7 had length 146, wrapped" in caplog.text


def test_comments():
    """Comments in files that are parsed by opm-common
    prior to piecing together will be lost, mentioned as
    a caveat in the documentation.

    But can we inject comments through insert statements

    (we can actually inject anything using this, it will not
    be attempted validated through opm-common)
    """
    mycomment = "-- A comment at a specific date"
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "insert": [{"days": 1, "string": mycomment}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert mycomment in str(sch)

    # Redo the same test through a yaml string
    # (the linebreak after the dash is optional)
    conf_str = (
        """
startdate: 2020-01-01
insert:
  -
    days: 1
    string: """
        + mycomment
    )
    conf = yaml.safe_load(conf_str)
    assert mycomment in str(sunsch.process_sch_config(conf))


def test_weltarg_uda(tmp_path):
    """WELTARG supports UDA from opm-common 2020.10"""
    os.chdir(tmp_path)
    weltargkeyword = """WELTARG
  'OP-1' ORAT SOMEUDA /
/
"""
    Path("weltarg.sch").write_text(
        """DATES
  1 'NOV' 2022 /
/
"""
        + weltargkeyword,
        encoding="utf8",
    )
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "files": ["weltarg.sch"],
    }
    # This raises a ValueError in opm-common 2020.04
    sch = sunsch.process_sch_config(sunschconf)
    assert "ORAT" in str(sch)

    # Can anyways be injected using an insert statement:
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "insert": [{"date": datetime.date(2022, 11, 1), "string": weltargkeyword}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert "ORAT" in str(sch)
    assert "SOMEUDA" in str(sch)


def test_long_udq_lines(tmp_path):
    """UDQ statements must not be line-wrapped, there is special code in OPM to
    avoid that."""
    inputstr = """UDQ

DEFINE FU_PWRI1 WWIR 'A_01' i WWIR 'A_02' + WWIR 'A_03' + WWIR 'A_04' + WWIR 'A_05' + WWIR 'A_06' + WWIR 'A_07' + WWIR 'A_08' + WWIR 'A_09' + WWIR 'A_10'  + WWIR 'A_11' + WWIR 'A_12' + WWIR 'A_13' + WWIR 'A_14' + WWIR 'A_15'/

/"""  # noqa
    assert len(inputstr.split("\n")) == 5  # Avoid editor-spoiled test.

    Path("longudq.sch").write_text(inputstr, encoding="utf8")
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "insert": [{"date": datetime.date(2020, 2, 1), "filename": "longudq.sch"}],
    }

    sch = sunsch.process_sch_config(sunschconf)
    schstr = str(sch)

    # the DEFINE line must be on its own line, so line count should be 9:
    assert len(schstr.split("\n")) == 9

    # Ensure unwanted space in front of well-names does not occur:
    assert "' A" not in schstr

    # Redo test without quotes in the input string:
    Path("longudq-noquotes.sch").write_text(inputstr.replace("'", ""), encoding="utf8")
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "insert": [
            {"date": datetime.date(2020, 2, 1), "filename": "longudq-noquotes.sch"}
        ],
    }
    schstr_noquotes = str(sunsch.process_sch_config(sunschconf))
    assert len(schstr_noquotes.split("\n")) == 9
    assert "' A" not in schstr_noquotes


def test_file_startswith_dates(readonly_datadir):
    """Test file_startswith_dates function"""
    assert not sunsch.file_startswith_dates("emptyinit.sch")
    assert not sunsch.file_startswith_dates("initwithdates.sch")
    assert sunsch.file_startswith_dates("mergeme.sch")
    assert sunsch.file_startswith_dates("merge2.sch")


def test_e300_keywords(readonly_datadir):
    """Test a keyword newly added to opm-common"""
    sunschconf = {
        "startdate": datetime.date(1900, 1, 1),
        "enddate": datetime.date(2020, 1, 1),
        "files": ["options3.sch"],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert "OPTIONS3" in str(sch)


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["sunsch", "-h"])


@pytest.mark.integration
def test_ert_forward_model(testdata):
    """Test that the ERT forward model configuration is correct"""
    Path("FOO.DATA").write_text("--Empty", encoding="utf8")

    Path("test.ert").write_text(
        "\n".join(
            [
                "ECLBASE FOO.DATA",
                "QUEUE_SYSTEM LOCAL",
                "NUM_REALIZATIONS 1",
                "RUNPATH <CONFIG_PATH>",
                "",
                "FORWARD_MODEL SUNSCH(<config>=config.yml)",
            ]
        ),
        encoding="utf8",
    )
    subprocess.run(["ert", "test_run", "test.ert"], check=True)
    assert Path("schedule.inc").is_file()
