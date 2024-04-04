"""Fixtures for genertobs"""

import logging
from pathlib import Path
import yaml
import pandas as pd
import pytest

# logging.basicConfig(level="DEBUG")
LOGGER = logging.getLogger(__name__)


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
    config_path = Path(__file__).parent / "data/expected_results.yml"
    string_config = str(config_path)
    assert config_path.exists(), f"{string_config} does not exist"
    return string_config


@pytest.fixture(scope="session", name="rft_as_frame")
def _fix_rft_as_frame():

    return pd.read_csv(Path(__file__).parent / "data/rft_as_frame.csv")


@pytest.fixture(scope="session", name="yaml_config")
def _fix_yaml_config(yaml_config_file):
    config = {}
    with open(yaml_config_file, "r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream)

    return config
