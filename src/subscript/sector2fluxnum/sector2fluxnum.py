#!/usr/bin/env python

import argparse
import sys
import os
from cwrap import open
from ecl.grid import EclGrid
from ecl.eclfile import EclFile, FortIO
from ecl.well import WellInfo
import datetime
from subscript.sector2fluxnum import flux_obj
from subscript.sector2fluxnum import fluxfile_obj as ffo
from subscript.sector2fluxnum import datafile_obj as do
from subscript.sector2fluxnum import well_obj as wo
from subscript.sector2fluxnum import completions as comp


DESCRIPTION = """
This is a wrapper script that executes the different
steps in the workflow for generating sector models in ECLIPSE.

The sector models have the same resolution as the full-field model

Further details about usage and howto can be found here:

http://wiki.statoil.no/wiki/index.php/Res:Gen_FLUX_fipnum_region.py

Author: Thomas Ramstad, trams@equinor.com

"""


def header_print():
    """
    """
    sys.stdout.write(
        "*********************************************************************\n"
        "*********************************************************************\n"
        "** This is a wrapper script for making sector models               **\n"
        "** with full field resulution.                                     **\n"
        "**                                                                 **\n"
        "** Never forget to QC results of a script: The user is responsible **\n"
        "** for making sure the output of a script is correct.              **\n"
        "**                                                                 **\n"
        "*********************************************************************\n"
        "*********************************************************************\n"
    )

    print("")


def get_parser():
    """Function to create the argument parser that is going to be served to the user.

    Returns:
        parser (argparse.ArgumentParser): The argument parser to be served

    """

    parser = argparse.ArgumentParser(prog="sector2fluxnum.py", description=DESCRIPTION)
    parser.add_argument("ECLIPSE_CASE", type=str, help="Eclipse input case")
    parser.add_argument("OUTPUT_CASE", type=str, help="Name of output FLUX file")
    parser.add_argument("-i", type=str, help="Example: -i 5-20")
    parser.add_argument("-j", type=str, help="Example: -j 5-20")
    parser.add_argument("-k", type=str, help="Example: -k 5-20")
    parser.add_argument("-f", "--fipnum", type=str, help="Example: -f 46")
    parser.add_argument(
        "-r", "--restart", type=str, help="Restart file read separately"
    )
    parser.add_argument("-e", "--egrid", type=str, help="EGRID file read separately")
    parser.add_argument(
        "-w", "--well", action="store_true", help="Well data read from RST file"
    )
    parser.add_argument("--fipfile", type=str, help="FIPNUM file read separately")
    parser.add_argument("--fluxfile", type=str, help="FLUXNUM file read separately")
    parser.add_argument(
        "--test", type=str, help="Name of predefined DUMPFLUX case for testing"
    )
    parser.add_argument("-v", "--version", type=str, help="ECL version")
    parser.add_argument(
        "--lgr", action="store_true", help="Special feature for LGR treatment"
    )

    return parser


def sector_to_fluxnum(args):

    """
    Wrapper function that generates an ECL DATA file with single FLUXNUM based on
    user Region-of-Interest.

    This is a wrapper script that executes the different
    steps in the workflow for generating sector models in ECLIPSE.
    The sector models have the same resolution as the full-field model

    Further details about usage and howto can be found here:
    @args: Input arguments. Use "sector2fluxnum --help" for more info
    """

    now = datetime.datetime.now()
    args.ECLIPSE_CASE = os.path.abspath(args.ECLIPSE_CASE).split(".")[0:-1]
    if not args.ECLIPSE_CASE:
        print("ERROR: Case does not exist", " ")
        sys.exit(1)

    # Root name for writing to target directory
    ECLIPSE_CASE_ROOT = os.path.basename(args.ECLIPSE_CASE[0])

    args.OUTPUT_CASE = args.OUTPUT_CASE.split(".")[0:-1]
    if not args.OUTPUT_CASE:
        print("ERROR: Specify OUTPUT_NAME of final FLUX file", " ")
        sys.exit(1)

    if args.restart:
        args.restart = os.path.abspath(args.restart).split(".")[0:-1]

    print("Reading grid ...")
    if args.egrid:
        args.egrid = os.path.abspath(args.egrid).split(".")[0:-1]
        grid = EclGrid("%s.EGRID" % args.egrid[0])
    else:
        grid = EclGrid("%s.EGRID" % args.ECLIPSE_CASE[0])

    init = EclFile("%s.INIT" % args.ECLIPSE_CASE[0])

    # Finding well completions
    if args.well:
        print("Reading completions from UNRST ...")
        if args.restart:
            well_info = WellInfo(grid, "%s.UNRST" % args.restart[0])
        else:
            well_info = WellInfo(grid, "%s.UNRST" % args.ECLIPSE_CASE[0])

        wellObject = wo.Wells(well_info)
        wellObject.find_completions()
        well_list = wellObject.get_well_list()
        completion_list = wellObject.get_completion_list()

    else:
        print("Reading completions from DATA file ...")
        sch_file_list = comp.find_schedule_files("%s.DATA" % args.ECLIPSE_CASE[0])

        completion_list, well_list = comp.find_completions(sch_file_list)

    if args.fipfile:
        fluxnum_new = flux_obj.Fluxnum_fipnum(
            grid, init, args.i, args.j, args.k, args.fipnum, args.fipfile
        )
    else:
        fluxnum_new = flux_obj.Fluxnum_fipnum(
            grid, init, args.i, args.j, args.k, args.fipnum
        )

    print("Generating FLUXNUM ...")
    if args.fluxfile:
        print("From input file ...")
        fluxnum_new.set_fluxnum_kw_from_file(args.fluxfile)
    else:
        fluxnum_new.set_fluxnum_kw()
    # #########################################################

    if args.lgr:
        print("Setting LGR box region ...", " ")
        fluxnum_new.setLgrBoxRegion(args.i, args.j, args.k)

        print("Checking completions ...", " ")
        # Checks for well completions in multiple FLUXNUM regions
        print("Including wells ...")
        fluxnum_new.include_well_completions_extra_layer_lgr(completion_list, well_list)
        print("Checking completions ...", " ")

        # Checks for well completions in multiple FLUXNUM regions
        print("Including wells ...")
        fluxnum_new.include_well_completions_extra_layer_lgr(completion_list, well_list)
        print("Creating Dummy LGRs ...")
        fluxnum_new.set_dummy_lgr_well_completions_region_filter(
            completion_list, well_list
        )
        print("Cluster Dummy LGRs vertically ...")
        fluxnum_new.cluster_dummy_lgr_vertical_low_k(args.k)
        fluxnum_new.cluster_dummy_lgr_vertical_high_k(args.k)

        print("Checking NNCs ...")
        if args.egrid:
            EGRID_file = EclFile("%s.EGRID" % args.egrid[0])
        else:
            EGRID_file = EclFile("%s.EGRID" % args.ECLIPSE_CASE[0])

        fluxnum_new.include_nnc(EGRID_file)
        EGRID_file.close()

    else:
        print("Checking completions ...", " ")
        # Checks for well completions in multiple FLUXNUM regions
        print("Including wells ...")
        fluxnum_new.include_well_completions(completion_list, well_list)
        # Second iteration to check for wells completed in multiple cells
        print("Including wells ...")
        fluxnum_new.include_well_completions(completion_list, well_list)

    # ###########################################

    print("Writing FLUXNUM file ...")
    fluxnum_new_kw = fluxnum_new.get_fluxnum_kw()

    FLUXNUM_filename = "FLUXNUM_FIPNUM_%s_%d.grdecl" % (args.fipnum, now.microsecond)

    fileH = open(FLUXNUM_filename, "w")
    fluxnum_new_kw.write_grdecl(fileH)
    fileH.close()

    # ###########################################

    print("Writing DUMPFLUX DATA-file ...")
    new_data_file = do.Datafile("%s.DATA" % args.ECLIPSE_CASE[0])

    if new_data_file.check_DUMPFLUX_kw() or new_data_file.check_USEFLUX_kw():
        print("ERROR: FLUX keywords already present in input ECLCASE")
        sys.exit(1)

    # ###########################################

    if args.lgr:
        print("Writing dummy lgr data to file")
        new_data_file.create_dummy_lgr_GRID_include(
            "DUMMY_LGR.INC",
            args,
            fluxnum_new.dummy_lgr_cell,
            fluxnum_new.dummy_lgr_well,
            fluxnum_new.dummy_lgr_name,
        )

        new_data_file.write_dummy_lgr_data(
            fluxnum_new.dummy_lgr_cell,
            fluxnum_new.dummy_lgr_well,
            fluxnum_new.dummy_lgr_name,
        )

        sch_files = comp.find_schedule_files("%s.DATA" % args.ECLIPSE_CASE[0])

        comp.replace_completions_lgr(
            sch_files,
            fluxnum_new.dummy_lgr_cell,
            fluxnum_new.dummy_lgr_well,
            fluxnum_new.dummy_lgr_name,
        )

    # ###########################################

    new_data_file.create_DUMPFLUX(FLUXNUM_filename)

    # ###########################################

    if args.test:
        args.test = os.path.abspath(args.test).split(".")[0:-1]

        if not os.path.isfile("%s.FLUX" % args.test[0]):
            print("ERROR: FLUX file from DUMPFLUX run not created")
            sys.exit(1)

        # Needs the coordinates from the
        print("Generating new FLUX file...")

        grid_coarse = EclGrid("%s.EGRID" % args.test[0])
        grid_fine = EclGrid("%s.EGRID" % args.test[0])

#        flux_coarse = EclFile("%s.FLUX" % args.test[0])
        flux_fine = EclFile("%s.FLUX" % args.test[0])

    else:
        print("Executing DUMPFLUX NOSIM run ...")
        if args.version:
            new_data_file.run_DUMPFLUX_NOSIM(args.version)
        else:
            new_data_file.run_DUMPFLUX_NOSIM()

        if not os.path.isfile("DUMPFLUX_%s.FLUX" % ECLIPSE_CASE_ROOT):
            print("ERROR: FLUX file from DUMPFLUX run not created")
            sys.exit(1)

        # Needs the coordinates from the
        print("Generating new FLUX file...")

        grid_coarse = EclGrid("DUMPFLUX_%s.EGRID" % ECLIPSE_CASE_ROOT)
        grid_fine = EclGrid("DUMPFLUX_%s.EGRID" % ECLIPSE_CASE_ROOT)

#        flux_coarse = EclFile("DUMPFLUX_%s.FLUX" % ECLIPSE_CASE_ROOT)
        flux_fine = EclFile("DUMPFLUX_%s.FLUX" % ECLIPSE_CASE_ROOT)

    # Reads restart file
    if args.restart:
        rst_coarse = EclFile("%s.UNRST" % args.restart[0])
    else:
        rst_coarse = EclFile("%s.UNRST" % args.ECLIPSE_CASE[0])

    fluxObj_fine = ffo.Fluxfile(grid_fine, flux_fine)
#    fluxObj_coarse = ffo.Fluxfile(grid_coarse, flux_coarse)

    # ######################################################
    # Creating map
    # ######################################################
    f_c_map = ffo.create_map_rst(
        fluxObj_fine, grid_coarse, scale_i=1, scale_j=1, scale_k=1
    )

    # ######################################################
    # Importing elements
    # ######################################################

    # Open FortIO stream
    fortio = FortIO("%s.FLUX" % args.OUTPUT_CASE[0], mode=FortIO.WRITE_MODE)

    ffo.write_new_fluxfile_from_rst(
        fluxObj_fine, grid_coarse, rst_coarse, f_c_map, fortio
    )

    # Close FortIO stream
    fortio.close()

    # ######################################################
    # Writing USEFLUX suggestion
    # ######################################################

    print("Writing suggestion for USEFLUX DATA-file ...")
    new_data_file.create_USEFLUX(FLUXNUM_filename, args.OUTPUT_CASE[0])

    new_data_file.add_USEFLUX_header_coarse(args)


def main():
    """
    """

    header_print()
    parser = get_parser()
    input_args = parser.parse_args()

    sector_to_fluxnum(input_args)


if __name__ == "__main__":
    main()
