import sys
from pathlib import Path

import subprocess
import pytest

import pandas as pd
import yaml

from subscript.prtvol2csv import prtvol2csv

TESTDATADIR = Path(__file__).absolute().parent / "data/reek/eclipse/model"


def test_prtvol2csv(tmpdir):
    """Test invocation from command line"""
    prtfile = TESTDATADIR / "2_R001_REEK-0.PRT"

    tmpdir.chdir()
    sys.argv = ["prtvol2csv", "--debug", str(prtfile)]
    prtvol2csv.main()
    dframe = pd.read_csv("share/results/volumes/simulator_volume_fipnum.csv")
    assert "FIPNUM" in dframe
    assert "STOIIP_OIL" in dframe
    assert "HCPV_TOTAL" in dframe  # This comes from the resvol extraction
    assert "PORV_TOTAL" in dframe  # also
    assert not dframe.empty
    assert len(dframe) == 6


def test_find_prtfile(tmpdir):
    """Test location service for PRT files"""
    tmpdir.chdir()

    # When nothing is in the current dir, it will not find it:
    assert prtvol2csv.find_prtfile("FOO") == "FOO"
    assert prtvol2csv.find_prtfile("FOO.DATA") == "FOO.DATA"
    assert prtvol2csv.find_prtfile("FOO.") == "FOO."

    # When we have some files there, it works:
    with open("FOO.PRT", "w") as file_h:
        file_h.write("dummy")
    assert prtvol2csv.find_prtfile("FOO") == "FOO.PRT"
    assert prtvol2csv.find_prtfile("FOO.DATA") == "FOO.PRT"
    assert prtvol2csv.find_prtfile("FOO.") == "FOO.PRT"
    assert prtvol2csv.find_prtfile("FOO.PRT") == "FOO.PRT"


def test_perl_runner(tmpdir):
    """Test that we can run perl script and return what
    it writes to disk"""
    tmpdir.chdir()
    with open("perlscript.pl", "w") as file_h:
        file_h.write(
            """#!/usr/bin/perl
open(FILE_H, ">", "$ARGV[1]");
print FILE_H "foo\n";
close(FILE_H);
"""
        )
    # Need to give full path to perl script for the runner to locate it
    assert prtvol2csv.perl_runner(tmpdir / "perlscript.pl", "dummy") == "foo\n"


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["prtvol2csv", "-h"])


def test_prtvol2csv_regions(tmpdir):
    """Test region support, getting data from yaml"""
    prtfile = TESTDATADIR / "2_R001_REEK-0.PRT"

    yamlexample = {
        "region2fipnum": {
            "RegionA": [1, 4, 6],
            "RegionB": [2, 5],
            "Totals": [1, 2, 3, 4, 5, 6],
        }
    }

    tmpdir.chdir()
    with open("regions.yml", "w") as reg_fh:
        reg_fh.write(yaml.dump(yamlexample))
    sys.argv = ["prtvol2csv", str(prtfile), "--regions", "regions.yml"]
    prtvol2csv.main()
    dframe = pd.read_csv("share/results/volumes/simulator_volume_region.csv")
    assert not dframe.empty
    assert "REGION" in dframe
    assert "Totals" in dframe["REGION"].values
    assert "RegionA" in dframe["REGION"].values
    assert "RegionB" in dframe["REGION"].values
    assert len(dframe) == 3


def test_prtvol2csv_regions_typemix(tmpdir):
    """Test region support, getting data from yaml"""
    prtfile = TESTDATADIR / "2_R001_REEK-0.PRT"

    yamlexample = {
        "region2fipnum": {
            "RegionA": [1, 4, 6],
            8: [2, 5],
        }
    }

    tmpdir.chdir()
    with open("regions.yml", "w") as reg_fh:
        reg_fh.write(yaml.dump(yamlexample))
    sys.argv = ["prtvol2csv", str(prtfile), "--regions", "regions.yml"]
    prtvol2csv.main()
    dframe = pd.read_csv("share/results/volumes/simulator_volume_region.csv")
    assert not dframe.empty
    assert "REGION" in dframe
    assert "RegionA" in dframe["REGION"].values
    assert "8" in dframe["REGION"].values
    assert len(dframe) == 2


def test_prtvol2csv_noresvol(tmpdir):
    """Test when FIPRESV is not included

    Perform the test by just fiddling with the test PRT file
    """
    prtfile = TESTDATADIR / "2_R001_REEK-0.PRT"

    tmpdir.chdir()
    prtlines = open(prtfile).read().replace("RESERVOIR VOLUMES", "foobar volumes")
    with open("MODIFIED.PRT", "w") as mod_fh:
        mod_fh.write(prtlines)
    sys.argv = ["prtvol2csv", "MODIFIED.PRT"]
    prtvol2csv.main()
    dframe = pd.read_csv("share/results/volumes/simulator_volume_fipnum.csv")
    assert not dframe.empty
    assert len(dframe) == 6
    assert "PORV_TOTAL" not in dframe
