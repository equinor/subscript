"""Restart file (UNRST) thinner, command line application"""

import argparse
import datetime
import logging
import shutil
import subprocess
import tempfile
from contextlib import chdir
from pathlib import Path

import numpy as np
import pandas as pd
from resdata.resfile import ResdataFile

from subscript import __version__, getLogger

logger = getLogger(__name__)

DESCRIPTION = """
Slice a subset of restart-dates from an E100 Restart file (UNRST)

Example::

    $ restartthinner --restarts 4 ECLIPSE.UNRST

where four restarts evenly spread out in relevant dates will be picked and
written to the same filename (keeping the original is optional)
"""


def find_resdata_app(toolname: str) -> str:
    """Locate path of resdata apps, trying common suffixes (.x, .c.x, .cpp.x).

    Args:
        toolname: Base name of the tool (e.g., 'rd_unpack')

    Returns:
        Full path to the executable.

    Raises:
        OSError: If tool cannot be found in PATH.
    """
    for ext in [".x", ".c.x", ".cpp.x", ""]:  # Order matters.
        if path := shutil.which(toolname + ext):
            return path
    raise OSError(f"{toolname} not found in PATH")


def date_slicer(
    slicedates: list[pd.Timestamp],
    restartdates: list[datetime.datetime],
    restartindices: list[int],
) -> list[int]:
    """Make a list of report indices that match the input slicedates."""
    slicedatelist = []
    for slicedate in slicedates:
        daydistances = [abs((pd.Timestamp(slicedate) - x).days) for x in restartdates]
        slicedatelist.append(restartindices[daydistances.index(min(daydistances))])
    return slicedatelist


def rd_repacker(rstfilename: str, slicerstindices: list[int], quiet: bool) -> None:
    """Repack a UNRST file keeping only selected restart indices.

    Uses rd_unpack and rd_pack utilities from resdata to unpack the UNRST file,
    remove unwanted dates, and repack into a new UNRST file.

    Args:
        rstfilename: Path to the UNRST file.
        slicerstindices: List of restart indices to keep.
        quiet: If True, suppress subprocess output.

    Raises:
        OSError: If rd_unpack or rd_pack tools are not found.
    """
    rd_unpack = find_resdata_app("rd_unpack")
    rd_pack = find_resdata_app("rd_pack")

    rstpath = Path(rstfilename)
    rstdir = rstpath.parent or Path(".")
    rstname = rstpath.name

    with chdir(rstdir):
        tempdir = Path(tempfile.mkdtemp(dir="."))
        try:
            # Move UNRST into temp directory and work there
            shutil.move(rstname, tempdir / rstname)

            with chdir(tempdir):
                subprocess.run(
                    [rd_unpack, rstname],
                    stdout=subprocess.DEVNULL if quiet else None,
                    check=True,
                )

                for file in Path(".").glob("*.X*"):
                    index = int(file.suffix.lstrip(".X"))
                    if index not in slicerstindices:
                        file.unlink()

                remaining_files = sorted(Path(".").glob("*.X*"))
                subprocess.run(
                    [rd_pack, *[str(f) for f in remaining_files]],
                    stdout=subprocess.DEVNULL if quiet else None,
                    check=True,
                )

                # Move result back up
                shutil.move(rstname, Path("..") / rstname)
        finally:
            shutil.rmtree(tempdir)


def get_restart_indices(rstfilename: str) -> list[int]:
    """Extract a list of restart indices for a filename.

    Args:
        rstfilename: Path to the UNRST file.

    Returns:
        List of restart report indices.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
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
    """Thin an existing UNRST file to selected number of restarts.

    Args:
        filename: Path to the UNRST file.
        numberofslices: Number of restart dates to keep.
        quiet: If True, suppress informational output.
        dryrun: If True, only show what would be done without modifying files.
        keep: If True, keep original file with .orig suffix.
    """
    rst = ResdataFile(filename)
    restart_indices = get_restart_indices(filename)
    restart_dates = [
        rst.iget_restart_sim_time(index) for index in range(len(restart_indices))
    ]

    if numberofslices > 1:
        slicedates = pd.DatetimeIndex(
            np.linspace(
                pd.Timestamp(restart_dates[0]).value,
                pd.Timestamp(restart_dates[-1]).value,
                int(numberofslices),
            )
        ).to_list()
    else:
        slicedates = [restart_dates[-1]]  # Only return last date if only one is wanted

    slicerstindices = date_slicer(slicedates, restart_dates, restart_indices)
    slicerstindices = sorted(set(slicerstindices))  # uniquify

    if not quiet:
        logger.info("Selected restarts:")
        logger.info("-----------------------")
        for idx, rstidx in enumerate(restart_indices):
            slicepresent = "X" if rstidx in slicerstindices else ""
            logger.info(
                "%4d  %s  %s",
                rstidx,
                datetime.date.strftime(restart_dates[idx], "%Y-%m-%d"),
                slicepresent,
            )
        logger.info("-----------------------")

    if not dryrun:
        if keep:
            backupname = filename + ".orig"
            logger.info("Backing up %s to %s", filename, backupname)
            shutil.copyfile(filename, backupname)
        rd_repacker(filename, slicerstindices, quiet)
        logger.info("Written to %s", filename)


def get_parser() -> argparse.ArgumentParser:
    """Setup parser"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter, description=DESCRIPTION
    )
    parser.add_argument("UNRST", help="Name of UNRST file")
    parser.add_argument(
        "-n",
        "--restarts",
        type=int,
        help="Number of restart dates wanted",
        required=True,
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


def main() -> None:
    """Endpoint for command line script."""
    parser = get_parser()
    args = parser.parse_args()

    if args.restarts <= 0:
        parser.error("Number of restarts must be a positive number")
    if args.UNRST.endswith(".DATA"):
        parser.error("Provide the UNRST file, not the DATA file")
    if args.quiet:
        logger.setLevel(logging.WARNING)

    restartthinner(args.UNRST, args.restarts, args.quiet, args.dryrun, args.keep)


if __name__ == "__main__":
    main()
