from __future__ import absolute_import

import pytest  # noqa: F401
import os
import sys

from .. import presentvalue


def test_main():
    ecldir = os.path.join(os.path.dirname(__file__), "data/reek/eclipse/model")
    parameterstxt_fname = os.path.join(ecldir, "parameters.txt")
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
        os.path.join(ecldir, "2_R001_REEK-0.DATA"),
    ]
    presentvalue.main()
    parametersline = open(parameterstxt_fname).readlines()[0].strip()
    assert parametersline.split()[0] == "PresentValue"
    assert round(float(parametersline.split()[1]), 1) == 11653.9
