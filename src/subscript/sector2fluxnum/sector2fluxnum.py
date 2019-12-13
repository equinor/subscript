import argparse
import os
import datetime
from cwrap import open
from ecl.grid import EclGrid
from ecl.eclfile import EclFile, FortIO
from subscript.sector2fluxnum import flux_obj
from subscript.sector2fluxnum import fluxfile_obj
from subscript.sector2fluxnum import datafile_obj
from subscript.sector2fluxnum import completions


DESCRIPTION = """
The script sector2fluxnum will execute different steps in a workflow
for generating sector models in ECLIPSE and utilize the FLUX
functionality in ECL100. The workflow will take user defined region of interest (ROI)
and convert that into a FLUXNUM region that is possible for ECLIPSE to include.
This includes crossing well trajectories.

Futhermore, the script will generate a template FLUX file and populate this
with restart data from the RESTART file. This way it is not necessary to run
a full DUMPFLUX run if the ROI is changed.

The sector models have the same block resolution as the mother full-field model,
but opens up for including LGR functionality.

Further details about usage and howto can be found here:
https://wiki.equinor.com/wiki/index.php/Res:Workflow_for_boundary_condition_handling
"""

EOL_UNIX = r"\n"
EOL_WINDOWS = r"\r\n"
EOL_MAC = r"\r"

EPILOG = ""


def get_parser():
    """Function to create the argument parser that is going to be served to the user.

    Returns:
    parser (argparse.ArgumentParser): The argument parser to be served

    """

    parser = argparse.ArgumentParser(prog="sector2fluxnum.py", description=DESCRIPTION)
    parser.add_argument("ECLIPSE_CASE", type=str, help="Eclipse input case")
    parser.add_argument(
        "OUTPUT_CASE",
        type=str,
        help="Name of output FLUX file with file extension .FLUX",
    )
    parser.add_argument("-i", type=str, help="Sector box dimension. Example: -i 5-20")
    parser.add_argument("-j", type=str, help="Sector box dimension. Example: -j 5-20")
    parser.add_argument("-k", type=str, help="Sector box dimension. Example: -k 5-20")
    parser.add_argument(
        "-f", "--fipnum", type=str, help="Sector FIPNUM region. Example: -f 46"
    )
    parser.add_argument(
        "-r", "--restart", type=str, help="Name of restart file read separately"
    )
    parser.add_argument(
        "-e", "--egrid", type=str, help="Name of EGRID file read separately"
    )
    parser.add_argument(
        "-w", "--well", action="store_true", help="Well data read from RST file"
    )
    parser.add_argument(
        "--fipfile", type=str, help="Name of FIPNUM file read separately"
    )
    parser.add_argument(
        "--fluxfile", type=str, help="Name of FLUXNUM file read separately"
    )
    parser.add_argument(
        "--test", type=str, help="Name of predefined DUMPFLUX case for testing"
    )
    parser.add_argument("-v", "--ecl_version", type=str, help="ECL version")

    return parser


def sector_to_fluxnum(args):

    """
    Wrapper function that generates an ECL DATA file with single FLUXNUM based on
    user Region-of-Interest.

    This is the function that executes the different
    steps in the workflow for generating sector models in ECLIPSE.
    The sector models have the same resolution as the full-field model
    """

    now = datetime.datetime.now()
    args.ECLIPSE_CASE = os.path.abspath(args.ECLIPSE_CASE).split(".")[0:1]
    if not args.ECLIPSE_CASE:
        raise Exception("ERROR: Case does not exist", " ")

    # Root name for writing to target directory
    ECLIPSE_CASE_ROOT = os.path.basename(args.ECLIPSE_CASE[0])

    args.OUTPUT_CASE = args.OUTPUT_CASE.split(".")[0:1]
    if not args.OUTPUT_CASE:
        raise Exception("ERROR: Specify OUTPUT_NAME of final FLUX file", " ")

    if args.restart:
        args.restart = os.path.abspath(args.restart).split(".")[0:1]

    print("Reading grid ...")
    if args.egrid:
        args.egrid = os.path.abspath(args.egrid).split(".")[0:1]
        grid = EclGrid("%s.EGRID" % args.egrid[0])
    else:
        grid = EclGrid("%s.EGRID" % args.ECLIPSE_CASE[0])

    init = EclFile("%s.INIT" % args.ECLIPSE_CASE[0])

    # Finding well completions
    completion_list, well_list = completions.get_completion_list(
        "%s.DATA" % args.ECLIPSE_CASE[0]
    )

    # Check ROI arguments
    if (args.i is None or args.j is None or args.k is None) and args.fipnum is None:
        raise Exception("ERROR: Region of interest not set correctly!")

    if args.fipfile:
        fluxnum_new = flux_obj.FluxnumFipnum(
            grid, init, args.i, args.j, args.k, args.fipnum, args.fipfile
        )
    else:
        fluxnum_new = flux_obj.FluxnumFipnum(
            grid, init, args.i, args.j, args.k, args.fipnum
        )

    print("Generating FLUXNUM ...")
    if args.fluxfile:
        print("From input file ...")
        fluxnum_new.set_fluxnum_kw_from_file(args.fluxfile)
    else:
        fluxnum_new.set_fluxnum_kw()

    print("Checking completions ...", " ")
    # Checks for well completions in multiple FLUXNUM regions
    print("Including wells ...")
    fluxnum_new.include_well_completions(completion_list, well_list)

    # Second iteration to check for wells completed in multiple cells
    print("Including wells ...")
    fluxnum_new.include_well_completions(completion_list, well_list)

    print("Writing FLUXNUM file ...")
    fluxnum_new_kw = fluxnum_new.get_fluxnum_kw()

    FLUXNUM_filename = "FLUXNUM_FIPNUM_%s_%d.grdecl" % (args.fipnum, now.microsecond)

    with open(FLUXNUM_filename, "w") as file_handle:
        fluxnum_new_kw.write_grdecl(file_handle)

    print("Writing DUMPFLUX DATA-file ...")
    new_data_file = datafile_obj.Datafile("%s.DATA" % args.ECLIPSE_CASE[0])

    if new_data_file.has_KW("DUMPFLUX") or new_data_file.has_KW("USEFLUX"):
        raise Exception("ERROR: FLUX keywords already present in input ECL_CASE")

    new_data_file.create_DUMPFLUX_file(FLUXNUM_filename)

    if args.test:
        args.test = os.path.abspath(args.test).split(".")[0:1]

        if not os.path.isfile("%s.FLUX" % args.test[0]):
            raise Exception("ERROR: FLUX file from DUMPFLUX run not created")

        # Needs the coordinates from the
        print("Generating new FLUX file...")

        grid_coarse = EclGrid("%s.EGRID" % args.test[0])
        grid_fine = EclGrid("%s.EGRID" % args.test[0])
        flux_fine = EclFile("%s.FLUX" % args.test[0])

    else:
        print("Executing DUMPFLUX NOSIM run ...")
        if args.ecl_version:
            new_data_file.run_DUMPFLUX_nosim(args.ecl_version)
        else:
            new_data_file.run_DUMPFLUX_nosim()

        if not os.path.isfile("DUMPFLUX_%s.FLUX" % ECLIPSE_CASE_ROOT):
            raise Exception("ERROR: FLUX file from DUMPFLUX run not created")

        # Needs the coordinates from the
        print("Generating new FLUX file...")

        grid_coarse = EclGrid("DUMPFLUX_%s.EGRID" % ECLIPSE_CASE_ROOT)
        grid_fine = EclGrid("DUMPFLUX_%s.EGRID" % ECLIPSE_CASE_ROOT)
        flux_fine = EclFile("DUMPFLUX_%s.FLUX" % ECLIPSE_CASE_ROOT)

    # Reads restart file
    if args.restart:
        rst_coarse = EclFile("%s.UNRST" % args.restart[0])
    else:
        rst_coarse = EclFile("%s.UNRST" % args.ECLIPSE_CASE[0])

    flux_object_fine = fluxfile_obj.Fluxfile(grid_fine, flux_fine)

    # Creating map
    f_c_map = fluxfile_obj.create_map_rst(
        flux_object_fine, grid_coarse, scale_i=1, scale_j=1, scale_k=1
    )

    # Importing elements
    # Open FortIO stream
    fortio = FortIO("%s.FLUX" % args.OUTPUT_CASE[0], mode=FortIO.WRITE_MODE)

    fluxfile_obj.write_new_fluxfile_from_rst(
        flux_object_fine, grid_coarse, rst_coarse, f_c_map, fortio
    )

    # Close FortIO stream
    fortio.close()

    # Writing USEFLUX suggestion
    print("Writing suggestion for USEFLUX DATA-file ...")
    new_data_file.create_USEFLUX_file(FLUXNUM_filename, args.OUTPUT_CASE[0])
    new_data_file.set_USEFLUX_header(args)


def main():
    """
    main method
    """
    parser = get_parser()
    input_args = parser.parse_args()

    sector_to_fluxnum(input_args)


if __name__ == "__main__":
    main()
