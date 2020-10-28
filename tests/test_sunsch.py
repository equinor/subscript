import os
import sys
import shutil
import datetime
import subprocess

import yaml

import pytest  # noqa: F401

import configsuite
from subscript.sunsch import sunsch

DATADIR = os.path.join(os.path.dirname(__file__), "testdata_sunsch")


def test_main(tmpdir, caplog):
    """Test command line sunsch, loading a yaml file"""

    tmpdir.chdir()
    shutil.copytree(DATADIR, "testdata_sunsch")
    tmpdir.join("testdata_sunsch").chdir()

    outfile = "schedule.inc"  # also in config_v2.yml

    if os.path.exists(outfile):
        os.unlink(outfile)
    sys.argv = ["sunsch", "config_v2.yml"]
    sunsch.main()
    assert "DEPRECATED" not in caplog.text
    assert os.path.exists(outfile)

    schlines = open(outfile).readlines()
    assert len(schlines) > 70

    # Check footemplate.sch was included:
    assert any(["A-90" in x for x in schlines])

    # Sample check for mergeme.sch:
    assert any(["WRFTPLT" in x for x in schlines])

    # Check for foo1.sch, A-1 should occur twice
    assert sum(["A-1" in x for x in schlines]) == 2

    # Check for substitutetest:
    assert any(["400000" in x for x in schlines])

    # Check for randomid:
    assert any(["A-4" in x for x in schlines])

    # Test that we can have statements in the init file
    # before the first DATES that are kept:

    sch_conf = yaml.safe_load(open("config_v2.yml"))
    print(sch_conf)
    sch_conf["init"] = "initwithdates.sch"
    sunsch.process_sch_config(sch_conf)

    # BAR-FOO is a magic string that occurs before any DATES in initwithdates.sch
    assert "BAR-FOO" in "".join(open(outfile).readlines())


def test_main_configv1(tmpdir, caplog):
    """Test command line sunsch, loading a yaml file.

    This is run on a v1 config file, which will be autoconverted to v2.

    This format is to be deprecated, and should be removed in the future
    """

    tmpdir.chdir()
    shutil.copytree(DATADIR, "testdata_sunsch")
    tmpdir.join("testdata_sunsch").chdir()

    outfile = "schedule.sch"  # also in config_v1.yml

    if os.path.exists(outfile):
        os.unlink(outfile)
    sys.argv = ["sunsch", "config_v1.yml"]
    sunsch.main()
    assert "DEPRECATED" in caplog.text
    assert os.path.exists(outfile)

    schlines = open(outfile).readlines()
    assert len(schlines) > 70

    # Check footemplate.sch was included:
    assert any(["A-90" in x for x in schlines])

    # Sample check for mergeme.sch:
    assert any(["WRFTPLT" in x for x in schlines])

    # Check for foo1.sch, A-1 should occur twice
    assert sum(["A-1" in x for x in schlines]) == 2

    # Check for substitutetest:
    assert any(["400000" in x for x in schlines])

    # Check for randomid:
    assert any(["A-4" in x for x in schlines])

    # Test that we can have statements in the init file
    # before the first DATES that are kept:

    sch_conf = yaml.safe_load(open("config_v1.yml"))
    print(sch_conf)
    sch_conf["init"] = "initwithdates.sch"
    sunsch.process_sch_config(sch_conf)

    # BAR-FOO is a magic string that occurs before any DATES in initwithdates.sch
    assert "BAR-FOO" in "".join(open(outfile).readlines())


def test_config_schema(tmpdir):
    """Test the implementation of configsuite"""
    tmpdir.chdir()
    cfg = {"init": "existingfile.sch", "output": "newfile.sch"}
    cfg_suite = configsuite.ConfigSuite(
        cfg, sunsch.CONFIG_SCHEMA_V2, deduce_required=True
    )
    assert not cfg_suite.valid  # file missing

    with open("existingfile.sch", "w") as handle:
        handle.write("foo")
    cfg_suite = configsuite.ConfigSuite(
        cfg, sunsch.CONFIG_SCHEMA_V2, deduce_required=True
    )
    print(cfg_suite.errors)
    assert cfg_suite.valid

    cfg = {"init": "existingfile.sch", "insert": []}  # missing output
    cfg_suite = configsuite.ConfigSuite(
        cfg, sunsch.CONFIG_SCHEMA_V2, deduce_required=True
    )
    assert cfg_suite.valid  # (missing output is allowed)

    cfg = {
        "init": "existingfile.sch",
        "output": "newfile.sch",
        "startdate": datetime.date(2018, 2, 2),
        "insert": [],
    }
    cfg_suite = configsuite.ConfigSuite(
        cfg, sunsch.CONFIG_SCHEMA_V2, deduce_required=True
    )
    print(cfg_suite.errors)
    assert cfg_suite.valid


def test_v1_to_v2():
    """Test the auto-converter from V1 to V2 config"""
    # pylint: disable=protected-access

    conv = sunsch._v1_content_to_v2

    assert conv({}) == {}
    assert conv({"init": "foo"}) == {"files": ["foo"]}
    assert conv({"merge": "foo"}) == {"files": ["foo"]}
    assert conv({"merge": ["foo"]}) == {"files": ["foo"]}
    assert conv({"init": "bar", "merge": ["foo"]}) == {"files": ["bar", "foo"]}
    assert conv({"init": "bar", "merge": ["foo", "com"]}) == {
        "files": ["bar", "foo", "com"]
    }

    assert conv({"insert": [{"foo.sch": {"days": 100}}]}) == {
        "insert": [{"days": 100, "filename": "foo.sch", "substitute": {}}]
    }

    # Check that V2 syntax is not altered:
    assert conv({"files": ["a", "b"]}) == {"files": ["a", "b"]}
    assert conv({"insert": [{"filename": "foo.sch", "days": 100}]}) == {
        "insert": [{"days": 100, "filename": "foo.sch"}]
    }


def test_templating(tmpdir):
    """Test templating"""
    tmpdir.chdir()
    with open("template.tmpl", "w") as handle:
        handle.write("WCONHIST\n<WELLNAME> OPEN ORAT <ORAT> <GRAT> /\n/")

    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [
            {
                "template": "template.tmpl",
                "days": 10,
                "substitute": dict(WELLNAME="A-007", ORAT=200.3, GRAT=1.4e6),
            }
        ],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert "A-007" in str(sch)
    assert "200.3" in str(sch)
    assert "1400000" in str(sch)
    cfg_suite = configsuite.ConfigSuite(
        sunschconf, sunsch.CONFIG_SCHEMA_V2, deduce_required=True
    )
    assert cfg_suite.valid

    # Let some of the valued be undefined:
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [
            {
                "template": "template.tmpl",
                "days": 10,
                "substitute": dict(WELLNAME="A-007"),
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
        "insert": [{"template": "template.tmpl", "substitute": dict(WELLNAME="A-007")}],
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
    with open("empty.tmpl", "w") as handle:
        handle.write("")
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "insert": [
            {
                "template": "empty.tmpl",
                "days": 10,
                "substitute": dict(WELLNAME="A-007", ORAT=200.3, GRAT=1.4e6),
            }
        ],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert str(sch) == ""


def test_days_integer():
    """Test that we can insert stuff a certain number of days
    after startup"""
    os.chdir(DATADIR)
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


def test_days_float():
    """Test that we can insert stuff a certain number of
    floating point days after startup"""
    os.chdir(DATADIR)
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [{"filename": "foo1.sch", "days": 10.1}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    # The TimeVector object has the "correct" date including time,
    # being 0.1 days after 2020-1-11
    assert datetime.datetime(2020, 1, 11, 2, 24, 0) in sch.dates
    # However, the clocktime is not included when the TimeVector
    # object is stringified:
    assert "11 'JAN' 2020/" in str(sch)

    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [{"filename": "foo1.sch", "days": 10.9}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert datetime.datetime(2020, 1, 11, 21, 36, 0) in sch.dates
    # Rounding is downwards:
    assert "11 'JAN' 2020/" in str(sch)


def test_dateclip():
    """Test dateclipping"""

    # This test function do not write to this directory:
    os.chdir(DATADIR)

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


def test_nonisodate():
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
        # Beware that using a ISO-string for a date in this config
        # will give a wrong error message, since the code assumes
        # all string dates are already parsed into datimes by the
        # yaml loader.
        # "startdate": "2020-01-01",
        "startdate": datetime.date(2020, 1, 1),
        "enddate": "01-01-2020",
        "insert": [{"filename": "foo1.sch", "date": datetime.date(2030, 1, 1)}],
    }
    with pytest.raises(TypeError):
        sunsch.process_sch_config(sunschconf)


def test_merge_include_nonexist(tmpdir):
    """If a user merges in a sch file which contains INCLUDE
    statements, these files may not exist yet (or only for a
    different path and so on.

    The way to get around this, is to do string insertions
    in the insert section.
    """
    tmpdir.chdir()
    open("mergewithexistinginclude.sch", "w").write(
        """
DATES
  1 'JAN' 2030 /
/

INCLUDE
  'something.sch' /
"""
    )
    open("something.sch", "w").write(
        """
WRFTPLT
  2 /
/
"""
    )

    sunschconf = {
        "startdate": datetime.date(2000, 1, 1),
        "files": ["mergewithexistinginclude.sch"],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert "WRFTPLT" in str(sch)

    # Now if it does not exist:
    open("mergewithnonexistinginclude.sch", "w").write(
        """
DATES
  1 'JAN' 2030 /
/

INCLUDE
  'somethingnotexistingyet.sch' /
"""
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


def test_merge_paths_in_use(tmpdir, caplog):
    """If the PATHS keyword is in use for getting includes,
    there will be "variables" in use in INCLUDE-statements.

    These variables are defined in the DATA file and outside
    sunsch's scope, but we should ensure a proper error message"""
    tmpdir.chdir()
    open("pathsinclude.sch", "w").write(
        """
DATES
  1 'JAN' 2030 /
/

INCLUDE
  '$MYSCHFILES/something.sch' /
"""
    )

    sunschconf = {
        "startdate": datetime.date(2000, 1, 1),
        "files": ["pathsinclude.sch"],
    }
    with pytest.raises(SystemExit):
        sunsch.process_sch_config(sunschconf)
    assert "PATHS variables in INCLUDE" in caplog.text


def test_merge():
    """Test that merge can be both a list and a string, that
    allows both syntaxes in yaml:

    merge: filename.sch

    and

    merge:
      - filename1.sch
      - filename2.sch
    """
    os.chdir(DATADIR)

    sunschconf = {"startdate": datetime.date(2000, 1, 1), "files": ["mergeme.sch"]}
    sch = sunsch.process_sch_config(sunschconf)
    assert "WRFTPLT" in str(sch)
    sunschconf = {"startdate": datetime.date(2000, 1, 1), "files": ["mergeme.sch"]}
    sch = sunsch.process_sch_config(sunschconf)
    assert "WRFTPLT" in str(sch)


def test_sch_file_nonempty(tmpdir):
    """Test that we can detect empty files"""
    tmpdir.chdir()

    with open("empty.sch", "w") as file_h:
        file_h.write("")
    assert not sunsch.sch_file_nonempty("empty.sch")

    with open("commentonly.sch", "w") as file_h:
        file_h.write("-- an Eclipse comment")
    assert not sunsch.sch_file_nonempty("commentonly.sch")

    with open("dates.sch", "w") as file_h:
        file_h.write("DATES\n 1 NOV 2080 / \n/")
    assert sunsch.sch_file_nonempty("dates.sch")

    with open("wconprod.sch", "w") as file_h:
        file_h.write("WCONPROD\n A ORAT 0 / \n/")
    assert sunsch.sch_file_nonempty("wconprod.sch")

    with open("bogus.sch", "w") as file_h:
        file_h.write("BOGUSrn A ORAT 0 / \n/")
    # Such a bogus file will give errors later, but
    # it should be treated as nonempty to be able
    # to catch the error elsewhere.
    assert sunsch.sch_file_nonempty("wconprod.sch")


def test_emptyfiles(tmpdir):
    """Test that we don't crash when we try to include files
    which are empty (or only contains comments)"""
    tmpdir.chdir()
    with open("empty.sch", "w") as file_h:
        file_h.write("")
    sunschconf = {"startdate": datetime.date(2000, 1, 1), "files": ["empty.sch"]}
    sch = sunsch.process_sch_config(sunschconf)
    assert str(sch) == ""

    with open("commentonly.sch", "w") as file_h:
        file_h.write("-- an Eclipse comment")
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

    # Redo the same test through a yaml string, the empty
    # identificator "" used here probably illustrates a bad
    # layout for the configuration file.
    conf_str = (
        """
startdate: 2020-01-01
insert:
  - "":
      days: 1
      string: """
        + mycomment
    )
    conf = yaml.safe_load(conf_str)
    assert mycomment in str(sunsch.process_sch_config(conf))


def test_weltarg_uda(tmpdir):
    """WELTARG does not support UDA in opm-common 2020.04/rc2

    It will maybe support it later
    """
    tmpdir.chdir()
    weltargkeyword = """WELTARG
  'OP-1' ORAT SOMEUDA /
/
"""
    with open("weltarg.sch", "w") as file_h:
        file_h.write(
            """DATES
  1 'NOV' 2022 /
/
"""
            + weltargkeyword
        )
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "files": ["weltarg.sch"],
    }
    # Whenever this test fails, a fix has been merged in OPM-common, then
    # remove pytest.raises.
    with pytest.raises(ValueError):
        sch = sunsch.process_sch_config(sunschconf)
        assert "ORAT" in str(sch)

    # But it is possible to workaround using an insert statement:
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "insert": [{"date": datetime.date(2022, 11, 1), "string": weltargkeyword}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert "ORAT" in str(sch)
    assert "SOMEUDA" in str(sch)


def test_file_startswith_dates():
    """Test file_startswith_dates function"""
    os.chdir(DATADIR)

    assert not sunsch.file_startswith_dates("emptyinit.sch")
    assert not sunsch.file_startswith_dates("initwithdates.sch")
    assert sunsch.file_startswith_dates("mergeme.sch")
    assert sunsch.file_startswith_dates("merge2.sch")


def test_e300_keywords():
    """Test a keyword newly added to opm-common"""
    os.chdir(os.path.join(os.path.dirname(__file__), "testdata_sunsch"))
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
