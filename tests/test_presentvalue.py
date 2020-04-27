"""Test presentvalue"""
from __future__ import absolute_import

import os
import sys
import shutil

import subprocess
import pytest

from subscript.presentvalue import presentvalue


def test_main(tmpdir):
    """Test the main functionality of presentvalue as endpoint script, writing
    back results to parameters.txt in the original runpath"""
    ecldir = os.path.join(os.path.dirname(__file__), "data/reek/eclipse/model")
    tmpdir.chdir()
    shutil.copytree(ecldir, "model")
    parameterstxt_fname = "parameters.txt"

    # Create an empty file called parameters.txt, otherwise
    # the presentvalue script will not write to it.
    with open(parameterstxt_fname, "w"):
        pass
    sys.argv = [
        "presentvalue",
        "--writetoparams",
        "--discountto",
        "2001",
        os.path.join("model", "2_R001_REEK-0.DATA"),
    ]
    presentvalue.main()
    parametersline = open(parameterstxt_fname).readlines()[0].strip()
    assert parametersline.split()[0] == "PresentValue"
    assert round(float(parametersline.split()[1]), 1) == 11653.9


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    subprocess.check_output(["presentvalue", "-h"])
