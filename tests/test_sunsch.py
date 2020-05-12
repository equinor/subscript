"""Test sunsch"""
from __future__ import absolute_import


import os
import sys
import datetime
import shutil
import subprocess

import yaml

import pytest  # noqa: F401

import configsuite
from subscript.sunsch import sunsch

DATADIR = os.path.join(os.path.dirname(__file__), "testdata_sunsch")


def test_main(tmpdir):
    """Test command line sunsch, loading a yaml file"""

    tmpdir.chdir()
    shutil.copytree(DATADIR, "testdata_sunsch")
    tmpdir.join("testdata_sunsch").chdir()

    outfile = "schedule.inc"  # also in config_v2.yml

    if os.path.exists(outfile):
        os.unlink(outfile)
    sys.argv = ["sunsch", "config_v2.yml"]
    sunsch.main()
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


def test_main_configv1(tmpdir):
    """Test command line sunsch, loading a yaml file"""

    tmpdir.chdir()
    shutil.copytree(DATADIR, "testdata_sunsch")
    tmpdir.join("testdata_sunsch").chdir()

    outfile = "schedule.sch"  # also in config_v1.yml

    if os.path.exists(outfile):
        os.unlink(outfile)
    sys.argv = ["sunsch", "config_v1.yml"]
    sunsch.main()
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
    cfg_suite = configsuite.ConfigSuite(cfg, sunsch.CONFIG_SCHEMA_V2)
    assert not cfg_suite.valid  # file missing

    with open("existingfile.sch", "w") as handle:
        handle.write("foo")
    cfg_suite = configsuite.ConfigSuite(cfg, sunsch.CONFIG_SCHEMA_V2)
    assert cfg_suite.valid

    cfg = {"init": "existingfile.sch"}  # missing output
    cfg_suite = configsuite.ConfigSuite(cfg, sunsch.CONFIG_SCHEMA_V2)
    assert cfg_suite.valid  # (missing output is allowed)

    import datetime

    cfg = {
        "init": "existingfile.sch",
        "output": "newfile.sch",
        "startdate": datetime.date(2018, 2, 2),
    }  # i'2018-02-02'}
    cfg_suite = configsuite.ConfigSuite(cfg, sunsch.CONFIG_SCHEMA_V2)
    print(cfg_suite.errors)
    assert cfg_suite.valid


def test_dateclip():
    """Test dateclipping"""

    # This test function do not write to this directory:
    os.chdir(DATADIR)

    # Clip dates after enddate:
    sunschconf = {
        "startdate": datetime.date(1900, 1, 1),
        "enddate": datetime.date(2020, 1, 1),
        "merge": ["mergeme.sch"],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert datetime.datetime(2019, 2, 9, 0, 0) in sch.dates
    assert datetime.datetime(2020, 10, 1, 0, 0) not in sch.dates

    # Nothing to clip here:
    sunschconf = {
        "startdate": datetime.date(1900, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "merge": ["mergeme.sch"],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert datetime.datetime(2020, 10, 1, 0, 0) in sch.dates
    assert datetime.datetime(2019, 2, 9, 0, 0) in sch.dates

    # Clip events before startdate:
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "merge": ["mergeme.sch"],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert datetime.datetime(2019, 2, 9, 0, 0) not in sch.dates
    assert datetime.datetime(2020, 10, 1, 0, 0) in sch.dates

    # Inserting before end-date should not be clipped.
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2041, 1, 1),
        "insert": [{"foo1.sch": {"date": datetime.date(2030, 1, 1)}}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert datetime.datetime(2030, 1, 1, 0, 0) in sch.dates

    # Inserting after end-date should be clipped.
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [{"foo1.sch": {"date": datetime.date(2030, 1, 1)}}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert datetime.datetime(2030, 1, 1, 0, 0) not in sch.dates

    # Inserting before start-date should be clipped.
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "enddate": datetime.date(2021, 1, 1),
        "insert": [{"foo1.sch": {"date": datetime.date(2000, 1, 1)}}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert datetime.datetime(2000, 1, 1, 0, 0) not in sch.dates


def test_nonisodate():
    """Test behaviour when users use non-ISO-dates"""
    sunschconf = {
        "startdate": "01-01-2020",
        "insert": [{"foo1.sch": {"date": datetime.date(2030, 1, 1)}}],
    }
    with pytest.raises(TypeError):
        sunsch.process_sch_config(sunschconf)

    sunschconf = {
        "refdate": "01-01-2020",
        "insert": [{"foo1.sch": {"date": datetime.date(2030, 1, 1)}}],
    }
    with pytest.raises(TypeError):
        sunsch.process_sch_config(sunschconf)

    sunschconf = {
        # Beware that using a ISO-string for a date in this config
        # will give a wrong error message, since the code assumes
        # all string dates are already parsed into datimes by the
        # yaml loader.
        # "startdate": "2020-01-01",
        "startdate": datetime.date(2020, 1, 1),
        "enddate": "01-01-2020",
        "insert": [{"foo1.sch": {"date": datetime.date(2030, 1, 1)}}],
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
        "merge": "mergewithexistinginclude.sch",
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
        "insert": [{"": {"days": 2, "string": "INCLUDE\n  'something.sch'/\n"}}],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert "something.sch" in str(sch)


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

    sunschconf = {"startdate": datetime.date(2000, 1, 1), "merge": "mergeme.sch"}
    sch = sunsch.process_sch_config(sunschconf)
    assert "WRFTPLT" in str(sch)
    sunschconf = {"startdate": datetime.date(2000, 1, 1), "merge": ["mergeme.sch"]}
    sch = sunsch.process_sch_config(sunschconf)
    assert "WRFTPLT" in str(sch)


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


def test_comments(tmpdir):
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
        "insert": [{"": {"days": 1, "string": mycomment}}],
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
        "merge": ["weltarg.sch"],
    }
    # Whenever this test fails, a fix has been merged in OPM-common, then
    # remove pytest.raises.
    with pytest.raises(ValueError):
        sch = sunsch.process_sch_config(sunschconf)
        assert "ORAT" in str(sch)

    # But it is possible to workaround using an insert statement:
    sunschconf = {
        "startdate": datetime.date(2020, 1, 1),
        "insert": [
            {"": {"date": datetime.date(2022, 11, 1), "string": weltargkeyword}}
        ],
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
        "merge": ["options3.sch"],
    }
    sch = sunsch.process_sch_config(sunschconf)
    assert "OPTIONS3" in str(sch)


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["sunsch", "-h"])
