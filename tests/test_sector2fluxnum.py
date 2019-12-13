#!/usr/bin/env python
import sys
import subprocess
import shlex
import shutil
import os

from ert.test import TestAreaContext

def test_sector2fluxnum():
    input_path = "data/sector"
    root = "/private/trams/GitHub/subscript"
#    with TestAreaContext("Coarse_FLUX_generation"):
    script = "src/subscript/sector2fluxnum/sector2fluxnum.py"
    
    input_ECL_CASE = os.path.join(input_path, "TEST.DATA")
    input_OUTPUT_FLUX = os.path.join(input_path, "OUT_COARSE.FLUX")
    input_RESTART = "-r" + os.path.join(input_path, "TEST.UNRST")
    input_i = "-i 2-10"
    input_j = "-j 2-9"
    input_k = "-k 1-1"
    
    p = subprocess.check_call(['python',
                               os.path.join(root, script),
                               input_ECL_CASE,
                               input_OUTPUT_FLUX,
                               input_i,
                               input_j,
                               input_k,
                               input_RESTART])
    
    #(output, err) = p.communicate()
    #assertFalse(err)
    assert(os.path.isfile("USEFLUX_TEST.DATA")) 
    
