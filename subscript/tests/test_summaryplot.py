#!/bin/env python

from __future__ import absolute_import
from .. import summaryplot
import os
#import unittest


#class TestSummaryplot(unittest.TestCase):
def test_summaryploter():

    datafn = os.path.join(
        os.path.dirname(__file__), "data/reek/eclipse/model/2_R001_REEK-0.DATA"
    )
    args = ["./blabla", datafn, "FOPR", "-d"]
    summaryplot.summaryplotter(*args)
    pngfn = "summaryplotdump.png"
    pdffn = "summaryplotdump.pdf"

    assert os.path.exists(pngfn)
    assert os.path.exists(pdffn)

    if os.path.exists(pngfn):
        os.unlink(pngfn)

    if os.path.exists(pdffn):
        os.unlink(pdffn)


