import os
import shutil
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from subscript.grav_subs_maps import grav_subs_maps
from subscript.grav_subs_maps.grav_subs_maps import GravMapsConfig

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
                    "coarsening": 8,
                    "phases": ["gas", "oil", "water", "total"],
                }
            },
            "Input should be less than",
        ),
        (
            {
                "calculations": {
                    "poisson_ratio": -1,
                    "coarsening": 8,
                    "phases": ["gas", "oil", "water", "total"],
                }
            },
            "Input should be greater than",
        ),
        (
            {
                "calculations": {
                    "poisson_ratio": 0.45,
                    "coarsening": 0,
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
                    "coarsening": 8,
                    "phases": ["gas", "oil", "water", "total"],
                }
            },
            "Field required",
        ),
        (
            {
                "input": {
                    "diffdates": [["2020-7-01", "2018-01-01"]],
                    "seabed_map": "./seabed.gri",
                }
            },
            "Input should be a valid date",
        ),
        (
            {
                "input": {
                    "diffdates": [["2020-07-01", "2018-01-01"]],
                    "seabed_map": "./no_seabed.gri",
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
            "seabed_map": "./seabed.gri",
        },
        "calculations": {
            "poisson_ratio": 0.45,
            "coarsening": 8,
            "phases": ["gas", "oil", "water", "total"],
        },
    }
    cfg.update(dictupdates)

    if expected_error is not None:
        with pytest.raises(ValidationError) as validation_error:
            GravMapsConfig(**cfg)
        assert expected_error in str(validation_error)
    else:
        GravMapsConfig(**cfg)


@pytest.mark.integration
def test_integration():
    """Test that endpoint is installed"""
    assert subprocess.check_output(["grav_subs_maps", "-h"])


@pytest.mark.integration
def test_main(res_data, mocker):
    """Test invocation from command line"""

    assert subprocess.check_output(["grav_subs_maps", "-h"])

    test_cfg = "grav_subs_maps.yml"
    test_resfile = "HIST.UNRST"

    mocker.patch(
        "sys.argv",
        [__file__, test_resfile, "--configfile", str(test_cfg), "--outputdir", "./"],
    )
    grav_subs_maps.main()

    assert Path("all--delta_gravity_total--20200701_20180101.gri").exists()
    assert Path("all--delta_gravity_gas--20200701_20180101.gri").exists()
    assert Path("all--delta_gravity_oil--20200701_20180101.gri").exists()
    assert Path("all--delta_gravity_water--20200701_20180101.gri").exists()
    assert Path("all--subsidence--20200701_20180101.gri").exists()


@pytest.mark.integration
def test_ert_integration(res_data):
    """Test that the ERT forward model configuration is correct"""

    Path("test.ert").write_text(
        "\n".join(
            [
                "ECLBASE HIST",
                "QUEUE_SYSTEM LOCAL",
                "NUM_REALISATIONS 1",
                "RUNPATH <CONFIG_PATH>",
                "",
                "FORWARD_MODEL GRAV_SUBS_MAPS(<UNRST_FILE>=<ECLBASE>.UNRST, \
                <GRAVMAPS_CONFIG>=grav_subs_maps.yml, <OUTPUT_DIR>=./)",
            ]
        ),
        encoding="utf8",
    )
    subprocess.run(["ert", "test_run", "test.ert"], check=True)
    assert Path("all--subsidence--20200701_20180101.gri").is_file()
