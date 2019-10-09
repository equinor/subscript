from __future__ import absolute_import


import os
import sys
import datetime

import pytest  # noqa: F401

from .. import sunsch


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


def test_dateclip():
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
