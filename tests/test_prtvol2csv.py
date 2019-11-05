from __future__ import absolute_import

import sys
import os
import shutil

import pandas as pd
import yaml

from subscript.prtvol2csv import prtvol2csv


def test_prtvol2csv():
    testdir = os.path.join(os.path.dirname(__file__), "testdata_prtvol2csv")
    if not os.path.exists(testdir):
        os.mkdir(testdir)
    else:
        shutil.rmtree(testdir)  # Total cleanup
        os.mkdir(testdir)
    os.chdir(testdir)

    sys.argv = ["prtvol2csv", "../data/reek/eclipse/model/2_R001_REEK-0.PRT"]
    prtvol2csv.main()
    dframe = pd.read_csv("share/results/volumes/simulator_volume_fipnum.csv")
    assert "FIPNUM" in dframe
    assert "STOIIP_OIL" in dframe
    assert "HCPV_TOTAL" in dframe  # This comes from the resvol extraction
    assert "PORV_TOTAL" in dframe  # also
    assert not dframe.empty
    assert len(dframe) == 6


def test_prtvol2csv_regions():
    yamlexample = {
        "region2fipnum": {
            "RegionA": [1, 4, 6],
            "RegionB": [2, 5],
            "Totals": [1, 2, 3, 4, 5, 6],
        }
    }
    testdir = os.path.join(os.path.dirname(__file__), "testdata_prtvol2csv")
    if not os.path.exists(testdir):
        os.mkdir(testdir)
    else:
        shutil.rmtree(testdir)  # Total cleanup
        os.mkdir(testdir)
    os.chdir(testdir)
    with open("regions.yml", "w") as reg_fh:
        reg_fh.write(yaml.dump(yamlexample))
    sys.argv = [
        "prtvol2csv",
        "../data/reek/eclipse/model/2_R001_REEK-0.PRT",
        "--regions",
        "regions.yml",
    ]
    prtvol2csv.main()
    dframe = pd.read_csv("share/results/volumes/simulator_volume_region.csv")
    assert not dframe.empty
    assert "REGION" in dframe
    assert "Totals" in dframe["REGION"].values
    assert "RegionA" in dframe["REGION"].values
    assert "RegionB" in dframe["REGION"].values
    assert len(dframe) == 3


def test_prtvol2csv_noresvol():
    """Test when FIPRESV is not included

    Perform the test by just fiddling with the test PRT file
    """
    testdir = os.path.join(os.path.dirname(__file__), "testdata_prtvol2csv")
    if not os.path.exists(testdir):
        os.mkdir(testdir)
    else:
        shutil.rmtree(testdir)  # Total cleanup
        os.mkdir(testdir)
    os.chdir(testdir)
    prtlines = (
        open("../data/reek/eclipse/model/2_R001_REEK-0.PRT")
        .read()
        .replace("RESERVOIR VOLUMES", "foobar volumes")
    )
    with open("MODIFIED.PRT", "w") as mod_fh:
        mod_fh.write(prtlines)
    sys.argv = ["prtvol2csv", "MODIFIED.PRT"]
    prtvol2csv.main()
    dframe = pd.read_csv("share/results/volumes/simulator_volume_fipnum.csv")
    assert not dframe.empty
    assert len(dframe) == 6
    assert "PORV_TOTAL" not in dframe
