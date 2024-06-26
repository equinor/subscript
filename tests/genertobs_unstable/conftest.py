"""Fixtures for genertobs"""

import os
import logging
from pathlib import Path
import yaml
import pandas as pd
import pickle
import pytest
from fmu.config.utilities import yaml_load

# logging.basicConfig(level="DEBUG")
LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="session", name="observations_input")
def _fix_obs_input():
    return Path(__file__).parent / "data/drogon/ert/input/observations/"


@pytest.fixture(scope="function", name="no_github_run")
def _fix_run_github_action():

    in_github_action = os.getenv("GITHUB_ACTIONS") == "true"
    if in_github_action:
        pytest.skip("Not set up for github action")


def read_yaml_file(yaml_file_name):
    yam_contents = {}
    with open(yaml_file_name, "r", encoding="utf-8") as stream:
        yam_contents = yaml.safe_load(stream)
    return yam_contents


@pytest.fixture(scope="function", name="config_element")
def _fix_config_element(observations_input):
    return {
        "name": "This is something other",
        "type": "rft",
        "observation": str(observations_input / "summary_gor.csv"),
        "default_error": 5,
    }


@pytest.fixture(name="mockert_experiment", scope="function")
def _fix_ens_id(monkeypatch):
    monkeypatch.setenv("_ERT_EXPERIMENT_ID", "TUT")


@pytest.fixture(scope="session", name="drogon_project")
def _fix_drogon():
    drogon_path = Path(__file__).parent / "data/drogon"
    LOGGER.debug("Returning %s", str(drogon_path))
    return drogon_path


@pytest.fixture(scope="session", name="csv_config")
def _fix_csv_config(drogon_project):
    config_path = drogon_project / "ert/input/observations/config.csv"
    LOGGER.debug("Returning %s", str(config_path))
    return config_path


@pytest.fixture(scope="session", name="yaml_config_file")
def _fix_yaml_config_file():
    config_path = (
        Path(__file__).parent
        / "data/drogon/ert/input/observations/genertobs_config.yml"
    )
    string_config = str(config_path)
    assert config_path.exists(), f"{string_config} does not exist"
    return string_config


@pytest.fixture(scope="session", name="masterdata_config")
def _fix_yaml_master():
    config_path = (
        Path(__file__).parent / "data/drogon/fmuconfig/output/global_variables.yml"
    )
    return config_path


@pytest.fixture(scope="session", name="rft_as_frame")
def _fix_rft_as_frame():

    return pd.read_csv(Path(__file__).parent / "data/rft_as_frame.csv")


@pytest.fixture(scope="session", name="summary_as_frame")
def _fix_sum_as_frame():

    frame = pd.read_csv(
        Path(__file__).parent
        / "data/drogon/ert/input/observations/drogon_summary_input.txt",
        sep="\s+",
    )
    frame.columns = [name.lower() for name in frame.columns]
    return frame


@pytest.fixture(scope="session", name="observation_config")
def _fix_config():
    with open(Path(__file__).parent / "data/config.pkl", "rb") as stream:
        config = pickle.load(stream)
    return config


@pytest.fixture(scope="session", name="expected_results")
def _fix_results():
    data = None
    with open(Path(__file__).parent / "data/pickled_data.pkl", "rb") as stream:
        data = pickle.load(stream)
    return data


@pytest.fixture(scope="session", name="fmuconfig")
def _fix_fmu_config(drogon_project):
    config_path = drogon_project / "fmuconfig/output/global_variables.yml"
    return yaml_load(config_path)
