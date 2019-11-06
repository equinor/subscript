from __future__ import absolute_import

import pytest  # noqa: F401
import os
import sys

from subscript.pack_sim import pack_sim


def test_main():
    ecldir = os.path.join(os.path.dirname(__file__), "data/reek/eclipse/model")

    sys.argv = [
        "pack_sim",
        os.path.join(ecldir, "2_R001_REEK-0.DATA"),
    ]
    pack_sim.main()