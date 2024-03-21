"""Fixtures for genertobs"""

import logging
from pathlib import Path
import pytest

logging.basicConfig(level="DEBUG")
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