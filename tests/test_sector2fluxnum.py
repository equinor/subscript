#!/bin/env python

from __future__ import absolute_import

import sys
import os

from subscript.sector2fluxnum import sector2fluxnum


def test_sector2fluxnum():

    TESTDATA = os.path.join(os.path.dirname(__file__), "data/sector")

    testdir = os.path.join(os.path.dirname(__file__), "testdata_sector2fluxnum")
    if not os.path.exists(testdir):
        os.mkdir(testdir)
    os.chdir(testdir)

    input_ECL_CASE = os.path.join(TESTDATA, "TEST.DATA")
    input_OUTPUT_FLUX = os.path.join(TESTDATA, "OUT_COARSE.FLUX")
    input_INPUT_DUMPFLUX = os.path.join(TESTDATA, "DUMPFLUX_TEST.DATA")
    input_RESTART = os.path.join(TESTDATA, "TEST.UNRST")

    sys.argv = [
        "sector2fluxnum",
        "-i",
        "2-10",
        "-j",
        "2-9",
        "-k",
        "1-1",
        "-r",
        input_RESTART,
        "--test",
        input_INPUT_DUMPFLUX,
        input_ECL_CASE,
        input_OUTPUT_FLUX,
    ]

    sector2fluxnum.main()

    assert os.path.isfile("USEFLUX_TEST.DATA")
