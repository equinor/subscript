
import os
import subprocess

import pandas as pd

import pytest

from subscript.casegen_upcars import casegen_upcars

def test_installed():
    """Test that the endpoint is installed, use -h as it required one parameter"""
    assert subprocess.check_output(["casegen_upcars", "-h"])

def test_demo_small_scale():
    """Test casegen_upcars on demo_small_scale.yaml"""
    testdatadir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata_casegen_upcars")
    os.chdir(testdatadir)
    assert subprocess.check_output(["casegen_upcars", "demo_small_scale.yaml"])

def test_demo_large_scale():
    """Test casegen_upcars on demo_large_scale.yaml"""
    testdatadir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata_casegen_upcars")
    os.chdir(testdatadir)
    assert subprocess.check_output(["casegen_upcars", "demo_large_scale.yaml"])


