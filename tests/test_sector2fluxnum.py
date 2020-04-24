#!/usr/bin/env python
import sys
import subprocess
import shlex
import shutil
import os
import pytest

from subscript.sector2fluxnum import sector2fluxnum

def test_sector2fluxnum():
    input_path = "data/sector"
    root = "/private/trams/GitHub/subscript"
    script = "src/subscript/sector2fluxnum/sector2fluxnum.py"
    
    input_ECL_CASE = os.path.join(input_path, "TEST.DATA")
    input_OUTPUT_FLUX = os.path.join(input_path, "OUT_COARSE.FLUX")
    input_INPUT_DUMPFLUX = os.path.join(input_path, "DUMPFLUX_TEST.DATA")
    input_RESTART = os.path.join(input_path, "TEST.UNRST")
    
    sys.argv = ["sector2fluxnum",
                "-i", "2-10",
                "-j", "2-9",
                "-k", "1-1",
                "-r", input_RESTART,
                "--test", input_INPUT_DUMPFLUX, 
                input_ECL_CASE, 
                input_OUTPUT_FLUX]
    
    sector2fluxnum.main()

    assert(os.path.isfile("USEFLUX_TEST.DATA")) 
    
