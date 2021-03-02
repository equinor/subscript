import os
import os.path
from pathlib import Path

import subprocess
import pytest

from subscript.ri_wellmod import ri_wellmod

RUNPATH = Path(os.path.dirname(__file__)) / "data/drogon"

@pytest.mark.integration
def test_integration():
    """Test that endpoint is installed"""
    assert subprocess.check_output(["ri_wellmod", "-h"])


