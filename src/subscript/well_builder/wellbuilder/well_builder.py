#! /prog/sdpsoft/python3.6.4/bin/python3

# -*- coding: utf-8 -*-
"""
This is the main program of WellBuilder.

It reads the user inputs from the command line.
and execute different procedures such as follow:

ReadCasefile -> ReadSchedule -> CreateWells -> CreateOutput
"""

'''
import sys
# TODO: tmp fix...
libpath = '/private/agy/Tools/subscript/src/subscript/well_builder'
if not libpath in sys.path: sys.path.append(libpath)
print('test')
'''


import time
import argparse
from wellbuilder.read_casefile import ReadCasefile
from wellbuilder.read_schedule import ReadSchedule
from wellbuilder.create_wells import CreateWells
from wellbuilder.wb_notes import WBABOUT, WBHELP, WBVERSION
import wellbuilder.wellbuilder_error as err

import wellbuilder.create_output 

def main():
    parser = argparse.ArgumentParser(prog="WellBuilder.py")
    parser.add_argument(
        "-i", "--inputfile", type=str, help="(Compulsory) WellBuilder case file"
    )
    parser.add_argument(
        "-s",
        "--schedulefile",
        type=str,
        help="(Optional) if it is specified in the case file",
    )
    parser.add_argument(
        "-p", "--pvtfile", type=str, help="(Optional) if it is specified in the case file",
    )
    parser.add_argument(
        "-o",
        "--outputfile",
        type=str,
        help="(Optional) if users want to have different names and location for the outputfiles",
    )
    parser.add_argument(
        "-help", action="store_true", help="Showing the procedure on how to run WellBuilder"
    )
    parser.add_argument(
        "-about", action="store_true", help="Showing the WellBuilder description"
    )
    parser.add_argument(
        "-figure",
        action="store_true",
        help="Generating well completion diagrams in pdf format",
    )
    parser.add_argument(
        "-verbose",
        action="store_true",
        help="Will print some extra information"
    )
    inputs = parser.parse_args()
    err.VERBOSE = inputs.verbose
    if inputs.inputfile == None and not inputs.about:
        inputs.help = True
    if inputs.help:
        print(WBHELP)
    if inputs.about:
        print(WBABOUT)
    if inputs.inputfile is not None:
        err.wb_message("Running WellBuilder " + WBVERSION + ". An advanced well modelling tool.")
        err.wb_message("-" * 60)
        start_a = time.time()
        class_case = ReadCasefile(inputs.inputfile, inputs.schedulefile, inputs.pvtfile)
        err.wb_message(
            "Seconds required to read case file "
            + "{0:.2f}".format(time.time() - start_a)
        )
        start_b = time.time()
        class_schedule = ReadSchedule(class_case.sch_file)
        err.wb_message(
            "Seconds required to read schedule file "
            + "{0:.2f}".format(time.time() - start_b)
        )
        start_c = time.time()
        class_well = CreateWells(class_case, class_schedule)
        err.wb_message(
            "Seconds required to read create completion "
            + "{0:.2f}".format(time.time() - start_c)
        )
        finish = wellbuilder.create_output.CreateOutput(
            class_case,
            class_schedule,
            class_well,
            WBVERSION,
            user_output=inputs.outputfile,
            show_figure=inputs.figure,
            verbose=inputs.verbose,
        )
        err.wb_message(
            "Seconds required to create output files "
            + "{0:.2f}".format(time.time() - start_c)
        )
        err.wb_message("-" * 60)

if __name__ == "__main__":
    main()
