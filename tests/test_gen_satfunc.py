"""Test gen_satfunc.py"""

from __future__ import absolute_import

import os
import sys
import subprocess

import pytest

from subscript.gen_satfunc import gen_satfunc

EXAMPLE = """ --Example Configuration file for gen_satfunc.py

COMMENT Relperm curve for fantasy field
SWOF
RELPERM 4 2 1   3 2 1   0.15 0.10 0.5 20
RELPERM 4 1 1   4 2 1   0.14 0.12 0.3 20
RELPERM 4 3 1   3 3 1   0.13 0.11 0.6 20
RELPERM 4 1 0.5 3 2 0.5 0.16 0.09 0.4 20
"""


@pytest.mark.integration
def test_integration():
    """Test that endpoint is installed"""
    assert subprocess.check_output(["gen_satfunc", "-h"])


def test_gen_satfunc():
    """Test the main function and its args handling"""
    testdir = os.path.join(os.path.dirname(__file__), "testdata_gen_satfunc")
    if not os.path.exists(testdir):
        os.mkdir(testdir)
    os.chdir(testdir)

    with open("relperm.conf", "w") as fh:
        fh.write(EXAMPLE)

    if os.path.exists("swof.inc"):
        os.unlink("swof.inc")
    sys.argv = ["gen_satfunc", "relperm.conf", "swof.inc"]
    gen_satfunc.main()

    assert os.path.exists("swof.inc")
    assert len(open("swof.inc").readlines()) > 50

    with open("relpermpc.conf", "w") as fh:
        fh.write(
            """
SWOF
RELPERM 4 2 1   3 2 1   0.15 0.10 0.5 20 100 0.2 0.22 -0.5 30
"""
        )
    if os.path.exists("swofpc.inc"):
        os.unlink("swofpc.inc")
    sys.argv = ["gen_satfunc", "relpermpc.conf", "swofpc.inc"]
    gen_satfunc.main()
    assert os.path.exists("swofpc.inc")
    swofpclines = open("swofpc.inc").readlines()
    assert len(swofpclines) > 20
    assert any(["sigma_costau=30" in x for x in swofpclines])
