"""Test prtvol2csv, both as library and as command line"""
import sys
from pathlib import Path

import subprocess
import pytest

import pandas as pd
import yaml

from subscript.prtvol2csv import prtvol2csv
from subscript.prtvol2csv.fipmapper import FipMapper

TESTDATADIR = Path(__file__).absolute().parent / "data/reek/eclipse/model"


def test_currently_in_place_from_prt(tmpdir):
    """Test parsing of PRT to find currently in place"""
    tmpdir.chdir()
    Path("FOO.PRT").write_text(
        """

                                                          ===================================
                                                          :  RESERVOIR VOLUMES      RM3     :
      :---------:---------------:---------------:---------------:---------------:---------------:
      : REGION  :  TOTAL PORE   :  PORE VOLUME  :  PORE VOLUME  : PORE VOLUME   :  PORE VOLUME  :
      :         :   VOLUME      :  CONTAINING   :  CONTAINING   : CONTAINING    :  CONTAINING   :
      :         :               :     OIL       :    WATER      :    GAS        :  HYDRO-CARBON :
      :---------:---------------:---------------:---------------:---------------:---------------:
      :   FIELD :             3.:             4.:             5.:             6.:             7.:
      :       1 :             8.:             9.:            10.:            11.:            12.:
      :       2 :            13.:            14.:            15.:            16.:            17.:
      ===========================================================================================
    """  # noqa
    )
    expected_dframe = pd.DataFrame(
        columns=["PORV_TOTAL", "HCPV_OIL", "WATER_PORV", "HCPV_GAS", "HCPV_TOTAL"],
        data=[[8, 9, 10, 11, 12], [13, 14, 15, 16, 17]],
        index=[1, 2],
    )
    expected_dframe.index.name = "FIPNUM"

    pd.testing.assert_frame_equal(
        prtvol2csv.reservoir_volumes_from_prt("FOO.PRT"),
        expected_dframe,
        check_dtype=False,
    )


def test_prtvol2csv(tmpdir):
    """Test invocation from command line"""
    prtfile = TESTDATADIR / "2_R001_REEK-0.PRT"

    tmpdir.chdir()
    sys.argv = ["prtvol2csv", "--debug", str(prtfile)]
    prtvol2csv.main()
    dframe = pd.read_csv("share/results/volumes/simulator_volume_fipnum.csv")

    expected = pd.DataFrame.from_dict(
        {
            "FIPNUM": {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6},
            "STOIIP_OIL": {
                0: 10656981.0,
                1: 0.0,
                2: 10720095.0,
                3: 0.0,
                4: 6976894.0,
                5: 0.0,
            },
            "ASSOCIATEDOIL_GAS": {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0},
            "STOIIP_TOTAL": {
                0: 10656981.0,
                1: 0.0,
                2: 10720095.0,
                3: 0.0,
                4: 6976894.0,
                5: 0.0,
            },
            "WATER_TOTAL": {
                0: 59957809.0,
                1: 77110073.0,
                2: 56914143.0,
                3: 72699051.0,
                4: 37834559.0,
                5: 38919965.0,
            },
            "GIIP_GAS": {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0},
            "ASSOCIATEDGAS_OIL": {
                0: 1960884420.0,
                1: 0.0,
                2: 1972497390.0,
                3: 0.0,
                4: 1283748490.0,
                5: 0.0,
            },
            "GIIP_TOTAL": {
                0: 1960884420.0,
                1: 0.0,
                2: 1972497390.0,
                3: 0.0,
                4: 1283748490.0,
                5: 0.0,
            },
            "PORV_TOTAL": {
                0: 78802733.0,
                1: 79481140.0,
                2: 75757104.0,
                3: 74929403.0,
                4: 50120783.0,
                5: 40111683.0,
            },
            "HCPV_OIL": {
                0: 17000359.0,
                1: 0.0,
                2: 17096867.0,
                3: 0.0,
                4: 11127443.0,
                5: 0.0,
            },
            "WATER_PORV": {
                0: 61802374.0,
                1: 79481140.0,
                2: 58660238.0,
                3: 74929403.0,
                4: 38993340.0,
                5: 40111683.0,
            },
            "HCPV_GAS": {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0},
            "HCPV_TOTAL": {
                0: 17000359.0,
                1: 0.0,
                2: 17096867.0,
                3: 0.0,
                4: 11127443.0,
                5: 0.0,
            },
        }
    )
    pd.testing.assert_frame_equal(dframe, expected)


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


def test_prtvol2df(tmpdir):
    simv = pd.DataFrame([{"STOIIP_OIL": 1000}], index=[1])
    resv = pd.DataFrame([{"PORV_TOTAL": 1000}], index=[1])

    # This function is simple concatenation horizontally:
    volumes = prtvol2csv.prtvol2df(simv, resv)
    pd.testing.assert_frame_equal(
        volumes, pd.DataFrame([{"STOIIP_OIL": 1000, "PORV_TOTAL": 1000}], index=[1])
    )
    # Index is [1] implicitly, and refers to FIPNUM.
    assert "REGION" not in prtvol2csv.prtvol2df(simv, resv, FipMapper())
    assert "ZONE" not in prtvol2csv.prtvol2df(simv, resv, FipMapper())

    # Add a non-trivial FipMapper:
    print(
        prtvol2csv.prtvol2df(
            simv, resv, FipMapper(mapdata={"region2fipnum": {"West": 1}})
        )
    )

    assert prtvol2csv.prtvol2df(
        simv, resv, FipMapper(mapdata={"region2fipnum": {"West": 1}})
    )["REGION"].values == ["West"]

    # Reverse the supplied map, should give the same:
    assert prtvol2csv.prtvol2df(
        simv, resv, FipMapper(mapdata={"fipnum2region": {1: "West"}})
    )["REGION"].values == ["West"]

    # And then for zones:
    assert prtvol2csv.prtvol2df(
        simv, resv, FipMapper(mapdata={"fipnum2zone": {1: "Upper"}})
    )["ZONE"].values == ["Upper"]
    assert prtvol2csv.prtvol2df(
        simv, resv, FipMapper(mapdata={"zone2fipnum": {"Upper": 1}})
    )["ZONE"].values == ["Upper"]
    # if we use {"Upper": "1"} it will fail, but no pytest.raises on
    # that yet, perhaps it will be fixed later.

    # Check integer handling through yaml:
    tmpdir.chdir()
    Path("z2f_int.yml").write_text(yaml.dump({"zone2fipnum": {"Upper": 1}}))
    assert prtvol2csv.prtvol2df(simv, resv, FipMapper(yamlfile="z2f_int.yml"))[
        "ZONE"
    ].values == ["Upper"]

    # Both zone and regions at the same time:
    volumes = prtvol2csv.prtvol2df(
        simv,
        resv,
        FipMapper(mapdata={"fipnum2region": {1: "West"}, "zone2fipnum": {"Upper": 1}}),
    )
    assert volumes["REGION"].values == ["West"]
    assert volumes["ZONE"].values == ["Upper"]

    # Simple global_master_config support:
    Path("global_master_config.yml").write_text(
        yaml.dump({"global": {"zone2fipnum": {"Upper": 1}}})
    )
    assert prtvol2csv.prtvol2df(
        simv, resv, FipMapper(yamlfile="global_master_config.yml")
    )["ZONE"].values == ["Upper"]


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["prtvol2csv", "-h"])


@pytest.mark.skipif(
    sys.version_info < (3, 7), reason="Test function requires Python 3.7 or higher"
)
@pytest.mark.integration
def test_prtvol2csv_regions(tmpdir):
    """Test region support, getting data from yaml.

    The functionality of writing CSV data grouped by regions will
    be removed later from prtvol2csv.
    """
    prtfile = TESTDATADIR / "2_R001_REEK-0.PRT"

    yamlexample = {
        "region2fipnum": {
            "RegionA": [1, 4, 6],
            "RegionB": [2, 5],
            "Totals": [1, 2, 3, 4, 5, 6],
        },
        "zone2fipnum": {"Upper": [1, 2], "Mid": [3, 4], "Lower": [5, 6]},
    }

    expected_dframe = pd.DataFrame.from_dict(
        {
            "REGION": {0: "RegionA", 1: "RegionB", 2: "Totals"},
            "STOIIP_OIL": {0: 10656981.0, 1: 6976894.0, 2: 28353970.0},
            "ASSOCIATEDOIL_GAS": {0: 0.0, 1: 0.0, 2: 0.0},
            "STOIIP_TOTAL": {0: 10656981.0, 1: 6976894.0, 2: 28353970.0},
            "WATER_TOTAL": {0: 171576825.0, 1: 114944632.0, 2: 343435600.0},
            "GIIP_GAS": {0: 0.0, 1: 0.0, 2: 0.0},
            "ASSOCIATEDGAS_OIL": {0: 1960884420.0, 1: 1283748490.0, 2: 5217130300.0},
            "GIIP_TOTAL": {0: 1960884420.0, 1: 1283748490.0, 2: 5217130300.0},
            "PORV_TOTAL": {0: 193843819.0, 1: 129601923.0, 2: 399202846.0},
            "HCPV_OIL": {0: 17000359.0, 1: 11127443.0, 2: 45224669.0},
            "WATER_PORV": {0: 176843460.0, 1: 118474480.0, 2: 353978178.0},
            "HCPV_GAS": {0: 0.0, 1: 0.0, 2: 0.0},
            "HCPV_TOTAL": {0: 17000359.0, 1: 11127443.0, 2: 45224669.0},
            "FIPNUM": {0: "1 4 6", 1: "2 5", 2: "1 2 3 4 5 6"},
        }
    )
    tmpdir.chdir()
    with open("regions.yml", "w") as reg_fh:
        reg_fh.write(yaml.dump(yamlexample))
    result = subprocess.run(
        ["prtvol2csv", str(prtfile), "--regions", "regions.yml"],
        check=True,
        capture_output=True,
    )
    output = result.stdout.decode() + result.stderr.decode()
    assert "FutureWarning" in output
    prtvol2csv.main()
    dframe = pd.read_csv("share/results/volumes/simulator_volume_region.csv")
    print("Computed:")
    print(dframe)
    print("Reference")
    print(expected_dframe)
    pd.testing.assert_frame_equal(dframe, expected_dframe)


@pytest.mark.integration
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
    Path("regions.yml").write_text(yaml.dump(yamlexample))
    sys.argv = ["prtvol2csv", str(prtfile), "--regions", "regions.yml"]
    prtvol2csv.main()
    dframe = pd.read_csv("share/results/volumes/simulator_volume_region.csv")
    assert not dframe.empty
    assert "REGION" in dframe
    assert "ZONE" not in dframe
    assert "RegionA" in dframe["REGION"].values
    assert "8" in dframe["REGION"].values
    assert len(dframe) == 2


@pytest.mark.integration
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
