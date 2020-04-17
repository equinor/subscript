"""Test sunsch"""
from __future__ import absolute_import


import os
import sys
import datetime
import subprocess

import yaml

import pytest  # noqa: F401

from subscript.sunsch import sunsch


def test_main():
    """Test command line sunsch, loading a yaml file"""

    os.chdir(os.path.join(os.path.dirname(__file__), "testdata_sunsch"))

    outfile = "schedule.sch"  # also in config.yml

    if os.path.exists(outfile):
        os.unlink(outfile)
    sys.argv = ["sunsch", "config.yml"]
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

    sch_conf = yaml.safe_load(open("config.yml"))
    print(sch_conf)
    sch_conf["init"] = "initwithdates.sch"
    sunsch.process_sch_config(sch_conf, quiet=False)

    # BAR-FOO is a magic string that occurs before any DATES in initwithdates.sch
    assert "BAR-FOO" in "".join(open(outfile).readlines())


def test_dateclip():
    """Test dateclipping"""
    os.chdir(os.path.join(os.path.dirname(__file__), "testdata_sunsch"))

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


def test_file_startswith_dates():
    """Test file_startswith_dates function"""
    os.chdir(os.path.join(os.path.dirname(__file__), "testdata_sunsch"))

    assert not sunsch.file_startswith_dates("emptyinit.sch")
    assert not sunsch.file_startswith_dates("initwithdates.sch")
    assert sunsch.file_startswith_dates("mergeme.sch")
    assert sunsch.file_startswith_dates("merge2.sch")


def test_e300_keywords():
    os.chdir(os.path.join(os.path.dirname(__file__), "testdata_sunsch"))
    sunschconf = {
        "startdate": datetime.date(1900, 1, 1),
        "enddate": datetime.date(2020, 1, 1),
        "merge": ["options3.sch"],
    }
    sch = sunsch.process_sch_config(sunschconf)
    print(sch)


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["sunsch", "-h"])
