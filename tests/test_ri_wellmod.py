import os
import subprocess
import pytest

from subscript.ri_wellmod import ri_wellmod

ECLDIR = os.path.join(os.path.dirname(__file__), "data/welltest/eclipse/model")
ECLCASE = "DROGON_DST_PLT-0"

@pytest.mark.integration
def test_integration():
    """Test that endpoint is installed"""
    assert subprocess.check_output(["welltest_dpds", "-h"])

