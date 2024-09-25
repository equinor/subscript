import os
import shutil
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from subscript.grav_subs_points import grav_subs_points
from subscript.grav_subs_points.grav_subs_points import GravPointsConfig

TESTDATA = Path(__file__).absolute().parent / "testdata_gravity"


@pytest.fixture(name="res_data")
def fixture_res_data(tmp_path):
    """Prepare a data directory with Eclipse binary output"""

    resdatadest = tmp_path / "resdata"
    shutil.copytree(TESTDATA, resdatadest, copy_function=os.symlink)
    cwd = os.getcwd()
    os.chdir(resdatadest)

    try:
        yield

    finally:
        os.chdir(cwd)


@pytest.mark.parametrize(
    "dictupdates, expected_error",
    [
        (
            {
                "calculations": {
                    "poisson_ratio": 1,
                    "phases": ["gas", "oil", "water", "total"],
                }
            },
            "Input should be less than",
        ),
        (
            {
                "calculations": {
                    "poisson_ratio": -1,
                    "phases": ["gas", "oil", "water", "total"],
                }
            },
            "Input should be greater than",
        ),
        (
            {
                "calculations": {
                    "poisson_ratio": 0.45,
                    "coarsening": 8,
                    "phases": ["wrong_phase"],
                }
            },
            "Assertion failed, allowed phases are",
        ),
        (
            {
                "calculations": {
                    "poisson_ratio": 0.45,
                    "phases": ["gas", "oil", "water", "total"],
                }
            },
            None,
        ),
        (
            {
                "calculations": {
                    "phases": ["gas", "oil", "water", "total"],
                }
            },
            "Field required",
        ),
        (
            {
                "input": {
                    "diffdates": [["2020-7-01", "2018-01-01"]],
                }
            },
            "Input should be a valid date",
        ),
        (
            {
                "stations": {
                    "grav": {"2020_2018": "./station_coordinates.csv"},
                    "subs": {"2020_2018": "./station_coordinates.csv"},
                }
            },
            None,
        ),
        (
            {
                "stations": {
                    "grav": {"2020_2018": "./station_coordinates.csv"},
                    "subs": {"2020_2018": "./wrong_file.csv"},
                }
            },
            "Path does not point to a file",
        ),
    ],
)
def test_config_errors(dictupdates, expected_error):
    """Test for error in configuration file"""

    os.chdir(TESTDATA)
    cfg = {
        "input": {
            "diffdates": [["2020-07-01", "2018-01-01"]],
        },
        "stations": {
            "grav": {"2020_2018": "./station_coordinates.csv"},
            "subs": {"2020_2018": "./station_coordinates.csv"},
        },
        "calculations": {
            "poisson_ratio": 0.45,
            "phases": ["gas", "oil", "water", "total"],
        },
    }

    cfg.update(dictupdates)

    if expected_error is not None:
        with pytest.raises(ValidationError) as validation_error:
            GravPointsConfig(**cfg)
        assert expected_error in str(validation_error)
    else:
        GravPointsConfig(**cfg)


@pytest.mark.parametrize(
    "dictupdates, expected_error",
    [
        (
            {
                "input": {
                    "diffdates": [["2020-07-01", "2018-02-01"]],
                }
            },
            "1",
        ),
    ],
)
def test_unrst_error(dictupdates, expected_error):
    """Test for missing data in UNRST file and system exit"""

    test_resfile = "HIST.UNRST"

    os.chdir(TESTDATA)
    cfg = {
        "input": {
            "diffdates": [["2020-07-01", "2018-01-01"]],
        },
        "stations": {
            "grav": {"2020_2018": "./station_coordinates.csv"},
            "subs": {"2020_2018": "./station_coordinates.csv"},
        },
        "calculations": {
            "poisson_ratio": 0.45,
            "phases": ["gas", "oil", "water", "total"],
        },
    }

    cfg.update(dictupdates)

    if expected_error is not None:
        with pytest.raises(SystemExit) as system_error:
            grav_subs_points.main_gravpoints(
                unrst_file=test_resfile,
                config=cfg,
                output_folder="./",
                pref_gendata="",
                ext_gendata=".txt",
            )
        assert expected_error in str(system_error.value.code)


@pytest.mark.integration
def test_integration():
    """Test that endpoint is installed"""
    assert subprocess.check_output(["grav_subs_points", "-h"])


@pytest.mark.integration
def test_main(res_data, mocker):
    """Test invocation from command line"""

    assert subprocess.check_output(["grav_subs_points", "-h"])

    test_cfg = "grav_subs_points.yml"
    test_resfile = "HIST.UNRST"

    mocker.patch(
        "sys.argv",
        [__file__, test_resfile, "--configfile", str(test_cfg), "--outputdir", "./"],
    )
    grav_subs_points.main()

    assert Path("all--delta_gravity_total--20200701_20180101.poi").exists()
    assert Path("all--delta_gravity_gas--20200701_20180101.poi").exists()
    assert Path("all--delta_gravity_oil--20200701_20180101.poi").exists()
    assert Path("all--delta_gravity_water--20200701_20180101.poi").exists()
    assert Path("all--subsidence--20200701_20180101.poi").exists()
    assert Path("gravity_20200701_20180101.txt").exists()
    assert Path("subsidence_20200701_20180101.txt").exists()


@pytest.mark.integration
def test_ert_integration(res_data):
    """Test that the ERT forward model configuration is correct"""

    # With default arguments
    Path("test.ert").write_text(
        "\n".join(
            [
                "ECLBASE HIST",
                "QUEUE_SYSTEM LOCAL",
                "NUM_REALISATIONS 1",
                "RUNPATH <CONFIG_PATH>",
                "",
                "FORWARD_MODEL GRAV_SUBS_POINTS(<UNRST_FILE>=<ECLBASE>.UNRST, \
                <GRAVPOINTS_CONFIG>=grav_subs_points.yml)",
            ]
        ),
        encoding="utf8",
    )
    subprocess.run(["ert", "test_run", "test.ert"], check=True)
    assert Path("subsidence_20200701_20180101.txt").is_file()

    # Test also with non default arguments for filename and directory
    Path("test.ert").write_text(
        "\n".join(
            [
                "ECLBASE HIST",
                "QUEUE_SYSTEM LOCAL",
                "NUM_REALISATIONS 1",
                "RUNPATH <CONFIG_PATH>",
                "",
                "FORWARD_MODEL MAKE_DIRECTORY(<DIRECTORY>=./results)",
                "FORWARD_MODEL GRAV_SUBS_POINTS(<UNRST_FILE>=<ECLBASE>.UNRST, \
                <GRAVPOINTS_CONFIG>=grav_subs_points.yml, <OUTPUT_DIR>=./results, \
                <ROOT_PATH>=./, <PREFIX_GENDATA>=fieldA_, <EXTENSION_GENDATA>=_10.txt)",
            ]
        ),
        encoding="utf8",
    )
    subprocess.run(["ert", "test_run", "test.ert"], check=True)
    assert Path("./results/fieldA_subsidence_20200701_20180101_10.txt").is_file()
