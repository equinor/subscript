"""Restart file (UNRST) thinner, command line application"""
import os
import glob
import datetime
import tempfile
import shutil
import argparse

import pandas
import numpy

from ecl.eclfile import EclFile

DESCRIPTION = """
Slice a subset of restart-dates from an E100 Restart file (UNRST)

Example:
    $ restartthinner --restarts 4 ECLIPSE.UNRST
where four restarts evenly spread out in relevant dates will be picked and
written to the same filename (keeping the original is optional)
"""
EPILOG = ""


def find_libecl_app(toolname):
    """Locate path of apps in libecl.

    These have varying suffixes due to a bug(?) in libecl Makefiles.

    Depending on libecl-version, it has the .x or the .c.x suffix
    We prefer .x

    See https://github.com/equinor/libecl/pull/685

    Returns:
        string with path if found.

    Raises:
        IOError if tool can't be found
    """
    extensions = [".x", ".c.x", ".cpp.x"]  # Order matters.
    candidates = [toolname + extension for extension in extensions]
    for candidate in candidates:
        for path in os.environ["PATH"].split(os.pathsep):
            candidatepath = os.path.join(path, candidate)
            if os.path.isfile(candidatepath):
                return candidatepath
    raise IOError(toolname + " not found in path, PATH=" + str(os.environ["PATH"]))


def date_slicer(slicedates, restartdates, restartindices):
    """Make a dict that maps a chosen restart date to a report index"""
    slicedatemap = {}
    for slicedate in slicedates:
        daydistances = [
            abs((pandas.Timestamp(slicedate) - x).days) for x in restartdates
        ]
        slicedatemap[slicedate] = restartindices[daydistances.index(min(daydistances))]
    return slicedatemap


def ecl_repacker(rstfilename, slicerstindices, quiet):
    """
    Wrapper for ecl_unpack.x and ecl_pack.x utilities. These
    utilities are from libecl.

    First unpacking a UNRST file, then deleting dates the dont't want, then
    pack the remainding files into a new UNRST file

    This function will change working directory to the
    location of the UNRST file, dump temporary files in there, and
    modify the original filename.
    """
    if quiet:
        out = " >/dev/null"
    else:
        out = ""
    # Take special care if the UNRST file we get in is not in current directory
    if os.path.dirname(rstfilename) != "":
        os.chdir(os.path.dirname(rstfilename))
    tempdir = tempfile.mkdtemp(dir=".")
    os.rename(
        os.path.basename(rstfilename),
        os.path.join(tempdir, os.path.basename(rstfilename)),
    )
    os.chdir(tempdir)
    os.system(find_libecl_app("ecl_unpack") + " " + os.path.basename(rstfilename) + out)
    unpackedfiles = glob.glob("*.X*")
    for file in unpackedfiles:
        if int(file.split(".X")[1]) not in slicerstindices:
            os.remove(file)
    os.system(find_libecl_app("ecl_pack") + " *.X*" + out)
    # We are inside the tmp directory, move file one step up:
    os.rename(
        os.path.join(os.getcwd(), os.path.basename(rstfilename)),
        os.path.join(os.getcwd(), "../", os.path.basename(rstfilename)),
    )
    os.chdir(os.path.join(os.getcwd(), "../"))
    shutil.rmtree(tempdir)


def get_restart_indices(rstfilename):
    """Extract a list of RST indices for a filename"""
    return EclFile.file_report_list(rstfilename)


def restartthinner(filename, numberofslices, quiet=False, dryrun=True, keep=False):
    """
    Thin an existing UNRST file to selected number of restarts.
    """
    rst = EclFile(filename)
    restart_indices = get_restart_indices(filename)
    restart_dates = [
        rst.iget_restart_sim_time(index) for index in range(0, len(restart_indices))
    ]

    if numberofslices > 1:
        slicedates = pandas.DatetimeIndex(
            numpy.linspace(
                pandas.Timestamp(restart_dates[0]).value,
                pandas.Timestamp(restart_dates[-1]).value,
                int(numberofslices),
            )
        ).values
    else:
        slicedates = [restart_dates[-1]]  # Only return last date if only one is wanted

    slicerstindices = list(
        date_slicer(slicedates, restart_dates, restart_indices).values()
    )
    slicerstindices.sort()
    slicerstindices = list(set(slicerstindices))  # uniquify

    if not quiet:
        print("Selected restarts:")
        print("-----------------------")
        for idx, rstidx in enumerate(restart_indices):
            if restart_indices[idx] in slicerstindices:
                slicepresent = "X"
            else:
                slicepresent = ""
            print(
                "%4d:  %s  %s"
                % (
                    rstidx,
                    datetime.date.strftime(restart_dates[idx], "%Y-%m-%d"),
                    slicepresent,
                )
            )
        print("-----------------------")
    if not dryrun:
        if keep:
            if not quiet:
                print("Info: Backing up %s to %s" % (filename, filename + ".orig"))
            shutil.copyfile(filename, filename + ".orig")
        ecl_repacker(filename, slicerstindices, quiet)


def get_parser():
    """Setup parser"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("UNRST", help="Name of UNRST file")
    parser.add_argument(
        "-n", "--restarts", type=int, help="Number of restart dates wanted"
    )
    parser.add_argument(
        "-d",
        "--dryrun",
        action="store_true",
        default=False,
        help="Dry-run only, do not touch files",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        default=False,
        help="Mute output from script",
    )
    parser.add_argument(
        "-k",
        "--keep",
        action="store_true",
        default=False,
        help="Keep original UNRST file",
    )
    return parser


def main():
    """Endpoint for command line script"""
    parser = get_parser()
    args = parser.parse_args()
    if args.restarts <= 0:
        raise argparse.ArgumentTypeError("Number of restarts must be a positive number")
    restartthinner(args.UNRST, args.restarts, args.quiet, args.dryrun, args.keep)
