import os
import sys
import shutil

import subprocess
import pytest

from subscript.presentvalue import presentvalue

ECLDIR = os.path.join(os.path.dirname(__file__), "data/reek/eclipse/model")


def test_main(tmpdir):
    """Test the main functionality of presentvalue as endpoint script, writing
    back results to parameters.txt in the original runpath"""
    tmpdir.chdir()
    shutil.copytree(
        ECLDIR,
        "model"
        # This is somewhat spacious, 39M, but the test will fail
        # if you try with a symlink (presentvalue.py looks through symlinks)
    )
    tmpdir.join("model").chdir()

    parameterstxt_fname = "parameters.txt"

    # Remove the potential copy we have got in our tmpdir:
    if os.path.exists(parameterstxt_fname):
        os.unlink(parameterstxt_fname)

    # Create an empty file called parameters.txt, otherwise
    # the presentvalue script will not write to it.
    with open(parameterstxt_fname, "w"):
        pass
    sys.argv = [
        "presentvalue",
        "--writetoparams",
        "--discountto",
        "2001",
        "2_R001_REEK-0.DATA",
    ]
    presentvalue.main()
    parametersline = open(parameterstxt_fname).readlines()[0].strip()
    assert parametersline.split()[0] == "PresentValue"
    assert round(float(parametersline.split()[1]), 1) == 11653.9


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    subprocess.check_output(["presentvalue", "-h"])
