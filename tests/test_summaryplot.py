#!/bin/env python

from __future__ import absolute_import

import os
import sys

import pytest
import subprocess

from subscript.summaryplot import summaryplot


def test_summaryplotter():

    eclipsedeck = os.path.join(
        os.path.dirname(__file__), "data/reek/eclipse/model/2_R001_REEK-0.DATA"
    )

    cmdopts_to_check = [
        # Ensure vector names are at the tail of the lists here
        ["FOPR"],
        ["--colourby", "FOO", "FOPT"],
        ["--logcolourby", "FOO", "FOPT"],
        ["SWAT:30,50,10", "FOPT"],
        ["-e", "FOPT"],
        ["--nolegend", "-v", "FOPT"],
        ["--maxlabels", "100", "--verbose", "FOPR"],
        ["--maxlabels", "0", "--verbose", "FOPR"],
        ["--normalize", "FWCT"],
        ["--normalize", "--singleplot", "FGPR", "FOPR"],
    ]
    for cmdopt in cmdopts_to_check:
        print("Trying combination " + str(cmdopt))
        sys.argv = ["summaryplot", "--dumpimages"] + cmdopt + [eclipsedeck]
        summaryplot.main()
        pngfn = "summaryplotdump.png"
        pdffn = "summaryplotdump.pdf"

        assert os.path.exists(pngfn)
        assert os.path.exists(pdffn)

        if os.path.exists(pngfn):
            os.unlink(pngfn)

        if os.path.exists(pdffn):
            os.unlink(pdffn)


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["summaryplot", "-h"])
