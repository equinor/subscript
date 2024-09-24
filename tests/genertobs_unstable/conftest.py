"""Fixtures for genertobs"""

import logging
import os
import pickle
from pathlib import Path

import pandas as pd
import pytest
import yaml
from fmu.config.utilities import yaml_load

from subscript.genertobs_unstable.parse_config import read_yaml_config

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
    with open(yaml_file_name, "r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


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
    return config_path


@pytest.fixture(scope="session", name="masterdata_config")
def _fix_yaml_master():
    return Path(__file__).parent / "data/drogon/fmuconfig/output/global_variables.yml"


@pytest.fixture(scope="session", name="rft_as_frame")
def _fix_rft_as_frame():
    return pd.read_csv(Path(__file__).parent / "data/rft_as_frame.csv")


@pytest.fixture(scope="session", name="summary_as_frame")
def _fix_sum_as_frame():
    frame = pd.read_csv(
        Path(__file__).parent
        / "data/drogon/ert/input/observations/drogon_summary_input.txt",
        sep=r"\s+",
    )
    frame.columns = [name.lower() for name in frame.columns]
    return frame


@pytest.fixture(scope="session", name="observation_config")
def _fix_config(yaml_config_file):
    cwd = Path().cwd()
    os.chdir(yaml_config_file.parent)
    config = read_yaml_config(yaml_config_file)
    os.chdir(cwd)
    return config


@pytest.fixture(scope="session", name="expected_results")
def _fix_results():
    with open(Path(__file__).parent / "data/pickled_data.pkl", "rb") as stream:
        return pickle.load(stream)


@pytest.fixture(scope="session", name="fmuconfig")
def _fix_fmu_config(drogon_project):
    config_path = drogon_project / "fmuconfig/output/global_variables.yml"
    return yaml_load(config_path)
