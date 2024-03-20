"""Fixtures for genertobs"""

from pathlib import Path
import pytest


@pytest.fixture(scope="session", name="drogon_project")
def _fix_drogon():
    drogon_path = Path(__file__).parent / "data/drogon"
    return drogon_path
