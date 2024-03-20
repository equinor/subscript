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
