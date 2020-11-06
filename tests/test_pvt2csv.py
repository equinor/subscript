import subprocess
import pytest


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    with pytest.raises(subprocess.CalledProcessError):
        subprocess.check_output(["pvt2csv"])
