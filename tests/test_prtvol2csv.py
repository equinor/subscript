"""Test prtvol2csv, both as library and as command line"""

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml
from fmu.tools.fipmapper.fipmapper import FipMapper
from subscript.prtvol2csv import prtvol2csv

TESTDATADIR = Path(__file__).absolute().parent / "data/reek/eclipse/model"


def test_currently_in_place_from_prt(tmp_path):
    """Test parsing of PRT to find currently in place"""
    os.chdir(tmp_path)
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
    """,  # noqa
        encoding="utf8",
    )
    expected_dframe = pd.DataFrame(
        columns=["PORV_TOTAL", "HCPV_OIL", "WATPV_TOTAL", "HCPV_GAS", "HCPV_TOTAL"],
        data=[[8, 9, 10, 11, 12], [13, 14, 15, 16, 17]],
        index=[1, 2],
    )
    expected_dframe.index.name = "FIPNUM"

    pd.testing.assert_frame_equal(
        prtvol2csv.reservoir_volumes_from_prt("FOO.PRT"),
        expected_dframe,
        check_dtype=False,
    )


def test_prtvol2csv(tmp_path, mocker):
    """Test invocation from command line"""
    prtfile = TESTDATADIR / "2_R001_REEK-0.PRT"

    os.chdir(tmp_path)
    with pytest.warns(FutureWarning, match="Output directories"):
        mocker.patch("sys.argv", ["prtvol2csv", "--debug", str(prtfile)])
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
            "WIIP_TOTAL": {
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
            "WATPV_TOTAL": {
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


def test_find_prtfile(tmp_path):
    """Test location service for PRT files"""
    os.chdir(tmp_path)

    # When nothing is in the current dir, it will not find it:
    assert prtvol2csv.find_prtfile("FOO") == "FOO"
    assert prtvol2csv.find_prtfile("FOO.DATA") == "FOO.DATA"
    assert prtvol2csv.find_prtfile("FOO.") == "FOO."

    # When we have some files there, it works:
    Path("FOO.PRT").write_text("dummy", encoding="utf8")
    assert prtvol2csv.find_prtfile("FOO") == "FOO.PRT"
    assert prtvol2csv.find_prtfile("FOO.DATA") == "FOO.PRT"
    assert prtvol2csv.find_prtfile("FOO.") == "FOO.PRT"
    assert prtvol2csv.find_prtfile("FOO.PRT") == "FOO.PRT"


def test_prtvol2df(tmp_path):
    """Test concatenation of dtaframes with volumes"""
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
    os.chdir(tmp_path)
    Path("z2f_int.yml").write_text(
        yaml.dump({"zone2fipnum": {"Upper": 1}}), encoding="utf8"
    )
    assert prtvol2csv.prtvol2df(simv, resv, FipMapper(yamlfile="z2f_int.yml"))[
        "ZONE"
    ].values == ["Upper"]
    prtvol2csv.prtvol2df(simv, resv, FipMapper(yamlfile="z2f_int.yml")).to_csv(
        "foo.csv"
    )

    # Both zone and regions at the same time:
    volumes = prtvol2csv.prtvol2df(
        simv,
        resv,
        FipMapper(mapdata={"fipnum2region": {1: "West"}, "zone2fipnum": {"Upper": 1}}),
    )
    assert volumes["REGION"].values == ["West"]
    assert volumes["ZONE"].values == ["Upper"]

    # fipnummaps referring to non-existing fipnums:
    volumes = prtvol2csv.prtvol2df(
        simv,
        resv,
        FipMapper(
            mapdata={
                "fipnum2region": {1: "West", 50: "Antarctica"},
                "zone2fipnum": {"Upper": 1, "Mantel": 100},
            }
        ),
    )
    assert "Antarctica" not in volumes["REGION"]
    assert "Mantel" not in volumes["ZONE"]

    # Simple global_master_config support:
    Path("global_master_config.yml").write_text(
        yaml.dump({"global": {"zone2fipnum": {"Upper": 1}}}), encoding="utf8"
    )
    assert prtvol2csv.prtvol2df(
        simv, resv, FipMapper(yamlfile="global_master_config.yml")
    )["ZONE"].values == ["Upper"]


def test_webviz_regiontofipnum_format(tmp_path):
    """Test that the webviz format for mapping regions to fipnums also works"""
    os.chdir(tmp_path)
    simv = pd.DataFrame([{"STOIIP_OIL": 1000}], index=[1])
    resv = pd.DataFrame([{"PORV_TOTAL": 1000}], index=[1])
    Path("webviz_fip.yml").write_text(
        yaml.dump(
            {"FIPNUM": {"groups": {"REGION": {"West": [1]}, "ZONE": {"Volon": [1]}}}}
        ),
        encoding="utf8",
    )
    dframe = prtvol2csv.prtvol2df(simv, resv, FipMapper(yamlfile="webviz_fip.yml"))
    assert dframe["ZONE"].values == ["Volon"]
    assert dframe["REGION"].values == ["West"]


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["prtvol2csv", "-h"])


@pytest.mark.skipif(
    sys.version_info < (3, 7), reason="Test function requires Python 3.7 or higher"
)
@pytest.mark.integration
def test_prtvol2csv_regions(tmp_path, mocker):
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

    expected_fip_reg_dframe = pd.DataFrame(
        [
            {"FIPNUM": 1, "REGION": "RegionA", "ZONE": "Upper"},
            {"FIPNUM": 2, "REGION": "RegionB", "ZONE": "Upper"},
            {"FIPNUM": 3, "REGION": np.nan, "ZONE": "Mid"},
            {"FIPNUM": 4, "REGION": "RegionA", "ZONE": "Mid"},
            {"FIPNUM": 5, "REGION": "RegionB", "ZONE": "Lower"},
            {"FIPNUM": 6, "REGION": "RegionA", "ZONE": "Lower"},
        ]
    )
    os.chdir(tmp_path)
    Path("regions.yml").write_text(yaml.dump(yamlexample), encoding="utf8")
    mocker.patch("sys.argv", ["prtvol2csv", str(prtfile), "--yaml", "regions.yml"])
    with pytest.warns(FutureWarning):
        prtvol2csv.main()

    dframe = pd.read_csv("share/results/volumes/simulator_volume_fipnum.csv")
    print("Computed:")
    print(dframe)
    pd.testing.assert_frame_equal(
        dframe[["FIPNUM", "REGION", "ZONE"]], expected_fip_reg_dframe
    )


@pytest.mark.integration
@pytest.mark.skipif(
    sys.version_info < (3, 7), reason="Test function requires Python 3.7 or higher"
)
def test_prtvol2csv_backwards_compat(tmp_path):
    """Test that we  have managed to keep backwards compatibility at least in
    the deprecation period"""
    prtfile = TESTDATADIR / "2_R001_REEK-0.PRT"
    os.chdir(tmp_path)

    result = subprocess.run(
        ["prtvol2csv", str(prtfile)],
        check=True,
        capture_output=True,
    )
    output = result.stdout.decode() + result.stderr.decode()
    assert "You MUST set the directory option to" in output
    assert (
        "Output directories for prtvol2csv should be created upfront"
        in result.stderr.decode()
    )
    assert Path("share/results/volumes/simulator_volume_fipnum.csv").is_file()


@pytest.mark.integration
def test_prtvol2csv_regions_typemix(tmp_path, mocker):
    """Test merging in region data, getting data from yaml"""
    prtfile = TESTDATADIR / "2_R001_REEK-0.PRT"

    yamlexample = {
        "region2fipnum": {
            "RegionA": [1, 4, 6],
            8: [2, 5],
        }
    }

    os.chdir(tmp_path)
    Path("regions.yml").write_text(yaml.dump(yamlexample), encoding="utf8")
    mocker.patch("sys.argv", ["prtvol2csv", str(prtfile), "--yaml", "regions.yml"])
    mocker.patch("sys.argv", ["prtvol2csv", str(prtfile), "--yaml", "regions.yml"])
    with pytest.warns(FutureWarning, match="Output directories"):
        prtvol2csv.main()
    dframe = pd.read_csv("share/results/volumes/simulator_volume_fipnum.csv")
    # pylint: disable=unsubscriptable-object
    assert not dframe.empty
    assert "REGION" in dframe
    assert "ZONE" not in dframe
    assert "RegionA" in dframe["REGION"].values
    assert "8" in dframe["REGION"].values
    assert len(dframe) == 6


@pytest.mark.integration
def test_prtvol2csv_webvizyaml(tmp_path, mocker):
    """Test region2fipnum-map in webviz-yaml-format"""
    os.chdir(tmp_path)

    prtfile = TESTDATADIR / "2_R001_REEK-0.PRT"

    webvizmap = {
        "FIPNUM": {
            "groups": {
                "REGION": {"RegionA": [1, 3, 5], "RegionB": [2, 4, 6]},
                "ZONE": {
                    "Upper": [1, 2],
                    "Middle": [3, 4],
                    "Lower": [5, 6],
                },
            }
        }
    }
    Path("regions.yml").write_text(yaml.dump(webvizmap), encoding="utf8")
    mocker.patch(
        "sys.argv",
        ["prtvol2csv", str(prtfile), "--yaml", "regions.yml", "--dir", "."],
    )
    prtvol2csv.main()
    dframe = pd.read_csv("simulator_volume_fipnum.csv")
    pd.testing.assert_frame_equal(
        dframe[["FIPNUM", "REGION", "ZONE"]],
        pd.DataFrame(
            [
                {"FIPNUM": 1, "REGION": "RegionA", "ZONE": "Upper"},
                {"FIPNUM": 2, "REGION": "RegionB", "ZONE": "Upper"},
                {"FIPNUM": 3, "REGION": "RegionA", "ZONE": "Middle"},
                {"FIPNUM": 4, "REGION": "RegionB", "ZONE": "Middle"},
                {"FIPNUM": 5, "REGION": "RegionA", "ZONE": "Lower"},
                {"FIPNUM": 6, "REGION": "RegionB", "ZONE": "Lower"},
            ]
        ),
    )


@pytest.mark.integration
def test_prtvol2csv_noresvol(tmp_path, mocker):
    """Test when FIPRESV is not included

    Perform the test by just fiddling with the test PRT file
    """
    prtfile = TESTDATADIR / "2_R001_REEK-0.PRT"

    os.chdir(tmp_path)
    prtlines = (
        Path(prtfile)
        .read_text(encoding="utf8")
        .replace("RESERVOIR VOLUMES", "foobar volumes")
    )
    Path("MODIFIED.PRT").write_text(prtlines, encoding="utf8")
    mocker.patch("sys.argv", ["prtvol2csv", "MODIFIED.PRT"])
    with pytest.warns(FutureWarning, match="Output directories"):
        prtvol2csv.main()
    dframe = pd.read_csv("share/results/volumes/simulator_volume_fipnum.csv")
    assert not dframe.empty
    assert len(dframe) == 6
    assert "PORV_TOTAL" not in dframe


@pytest.mark.integration
def test_ert_forward_model(tmp_path):
    """Run ERT with the registered forward model PRTVOL2CSV"""
    os.chdir(tmp_path)

    prtfile = TESTDATADIR / "2_R001_REEK-0.PRT"

    Path("FOO.DATA").write_text("--Empty", encoding="utf8")

    yamlexample = {
        "region2fipnum": {
            "RegionA": [1, 4, 6],
            8: [2, 5],
        }
    }
    Path("regions.yml").write_text(yaml.dump(yamlexample), encoding="utf8")

    Path("test.ert").write_text(
        "\n".join(
            [
                "ECLBASE FOO.DATA",
                "QUEUE_SYSTEM LOCAL",
                "NUM_REALIZATIONS 1",
                "RUNPATH <CONFIG_PATH>",
                "",
                (
                    "FORWARD_MODEL PRTVOL2CSV("
                    "<DATAFILE>="
                    + str(prtfile)
                    + ', <REGIONS>=regions.yml, <DIR>=".",<OUTPUTFILENAME>=sim.csv)'  # noqa
                ),
            ]
        ),
        encoding="utf8",
    )
    subprocess.run(["ert", "test_run", "test.ert"], check=True)
    assert Path("sim.csv").is_file()


@pytest.mark.integration
def test_ert_forward_model_backwards_compat_deprecation(tmp_path):
    """Test that the deprecated behaviour still works for backwards compat"""
    os.chdir(tmp_path)

    prtfile = TESTDATADIR / "2_R001_REEK-0.PRT"

    Path("FOO.DATA").write_text("--Empty", encoding="utf8")

    yamlexample = {
        "region2fipnum": {
            "RegionA": [1, 4, 6],
            8: [2, 5],
        }
    }
    Path("regions.yml").write_text(yaml.dump(yamlexample), encoding="utf8")

    Path("test.ert").write_text(
        "\n".join(
            [
                "ECLBASE FOO.DATA",
                "QUEUE_SYSTEM LOCAL",
                "NUM_REALIZATIONS 1",
                "RUNPATH <CONFIG_PATH>",
                "",
                (
                    "FORWARD_MODEL PRTVOL2CSV(" "<DATAFILE>=" + str(prtfile) + ")"  # noqa
                ),
            ]
        ),
        encoding="utf8",
    )
    subprocess.run(["ert", "test_run", "test.ert"], check=True)
    assert Path("share/results/volumes/simulator_volume_fipnum.csv").is_file()
    stdout = Path("PRTVOL2CSV.stdout.0").read_text(encoding="utf8")
    stderr = Path("PRTVOL2CSV.stderr.0").read_text(encoding="utf8")
    assert "You MUST set the directory option" in stdout
    assert (
        "FutureWarning: Output directories for prtvol2csv should be created upfront"
        in stderr
    )
