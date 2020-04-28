"""
Test the vfp2csv module
"""

from __future__ import absolute_import

import sys
import os

import subprocess
import pytest


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["kmdrun"])
    assert subprocess.check_output(["kmdrun", "echo"])
    assert subprocess.check_output(["kmdrun", "echo", "hei"])
    if os.path.exists("/prog/res/komodo"):
        assert "bleeding" not in subprocess.check_output(
            ["kmdrun", "echo", "$KOMODO_RELEASE"]
        ).decode("utf-8")
        assert "bleeding" in subprocess.check_output(
            ["kmdrun", "--bleeding", "echo", "$KOMODO_RELEASE"]
        ).decode("utf-8")
