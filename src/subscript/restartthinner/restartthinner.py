"""Restart file (UNRST) thinner, command line application"""

import argparse
import datetime
import glob
import os
import shutil
import sys
import tempfile
from pathlib import Path

import numpy
import pandas
from resdata.resfile import ResdataFile

from subscript import __version__

DESCRIPTION = """
Slice a subset of restart-dates from an E100 Restart file (UNRST)

Example::

    $ restartthinner --restarts 4 ECLIPSE.UNRST

where four restarts evenly spread out in relevant dates will be picked and
written to the same filename (keeping the original is optional)
"""


def find_resdata_app(toolname: str) -> str:
    """Locate path of apps in resdata.

    These have varying suffixes due through the history of libecl Makefiles.

    Depending on libecl-version, it has the .x or the .c.x suffix
    We prefer .x.

    Returns:
        String with path if found.

    Raises:
        IOError: if tool can't be found
    """
    extensions = [".x", ".c.x", ".cpp.x", ""]  # Order matters.
    candidates = [toolname + extension for extension in extensions]
    for candidate in candidates:
        for path in os.environ["PATH"].split(os.pathsep):
            candidatepath = Path(path) / candidate
            if candidatepath.exists():
                return str(candidatepath)
    raise IOError(toolname + " not found in path, PATH=" + str(os.environ["PATH"]))


def date_slicer(slicedates: list, restartdates: list, restartindices: list) -> dict:
    """Make a dict that maps a chosen restart date to a report index"""
    slicedatemap = {}
    for slicedate in slicedates:
        daydistances = [
            abs((pandas.Timestamp(slicedate) - x).days) for x in restartdates
        ]
        slicedatemap[slicedate] = restartindices[daydistances.index(min(daydistances))]
    return slicedatemap


def rd_repacker(rstfilename: str, slicerstindices: list, quiet: bool) -> None:
    """
    Wrapper for ecl_unpack.x and ecl_pack.x utilities. These
    utilities are from resdata.

    First unpacking a UNRST file, then deleting dates the dont't want, then
    pack the remainding files into a new UNRST file

    This function will change working directory to the
    location of the UNRST file, dump temporary files in there, and
    modify the original filename.
    """
    out = " >/dev/null" if quiet else ""
    # Error early if libecl tools are not available
    try:
        find_resdata_app("rd_unpack")
        find_resdata_app("rd_pack")
    except IOError:
        sys.exit(
            "ERROR: rd_unpack.x and/or rd_pack.x not found.\n"
            "These tools are required and must be installed separately"
        )

    # Take special care if the UNRST file we get in is not in current directory
    cwd = os.getcwd()
    rstfilepath = Path(rstfilename).parent
    try:
        os.chdir(Path(rstfilename).parent)
        tempdir = tempfile.mkdtemp(dir=".")
        os.rename(
            os.path.basename(rstfilename),
            os.path.join(tempdir, os.path.basename(rstfilename)),
        )
        os.chdir(tempdir)
        os.system(
            find_resdata_app("rd_unpack") + " " + os.path.basename(rstfilename) + out
        )
        unpackedfiles = glob.glob("*.X*")
        for file in unpackedfiles:
            if int(file.split(".X")[1]) not in slicerstindices:
                os.remove(file)
        os.system(find_resdata_app("rd_pack") + " *.X*" + out)
        # We are inside the tmp directory, move file one step up:
        os.rename(
            os.path.join(os.getcwd(), os.path.basename(rstfilename)),
            os.path.join(os.getcwd(), "../", os.path.basename(rstfilename)),
        )
    finally:
        os.chdir(cwd)
        shutil.rmtree(rstfilepath / tempdir)


def get_restart_indices(rstfilename: str) -> list:
    """Extract a list of RST indices for a filename"""
    if Path(rstfilename).exists():
        # This function segfaults if file does not exist
        return ResdataFile.file_report_list(str(rstfilename))
    raise FileNotFoundError(f"{rstfilename} not found")


def restartthinner(
    filename: str,
    numberofslices: int,
    quiet: bool = False,
    dryrun: bool = True,
    keep: bool = False,
) -> None:
    """
    Thin an existing UNRST file to selected number of restarts.
    """
    rst = ResdataFile(filename)
    restart_indices = get_restart_indices(filename)
    restart_dates = [
        rst.iget_restart_sim_time(index) for index in range(len(restart_indices))
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
            slicepresent = "X" if restart_indices[idx] in slicerstindices else ""
            print(
                f"{rstidx:4d}  "
                f"{datetime.date.strftime(restart_dates[idx], '%Y-%m-%d')}  "
                f"{slicepresent}"
            )
        print("-----------------------")
    if not dryrun:
        if keep:
            backupname = filename + ".orig"
            if not quiet:
                print(f"Info: Backing up {filename} to {backupname}")
            shutil.copyfile(filename, backupname)
        rd_repacker(filename, slicerstindices, quiet)
    print(f"Written to {filename}")


def get_parser() -> argparse.ArgumentParser:
    """Setup parser"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter, description=DESCRIPTION
    )
    parser.add_argument("UNRST", help="Name of UNRST file")
    parser.add_argument(
        "-n", "--restarts", type=int, help="Number of restart dates wanted", default=0
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
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + __version__ + ")",
    )
    return parser


def main():
    """Endpoint for command line script"""
    parser = get_parser()
    args = parser.parse_args()
    if args.restarts <= 0:
        print("ERROR: Number of restarts must be a positive number")
        sys.exit(1)
    if args.UNRST.endswith("DATA"):
        print("ERROR: Provide the UNRST file, not the DATA file")
        sys.exit(1)
    restartthinner(args.UNRST, args.restarts, args.quiet, args.dryrun, args.keep)
