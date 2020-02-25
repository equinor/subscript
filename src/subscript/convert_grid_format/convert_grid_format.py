# -*- coding: utf-8 -*-
"""Conversion between grid corner point formats"""

from __future__ import division, print_function, absolute_import

import argparse
import os
import sys

import xtgeo
from xtgeo.common import XTGeoDialog

APPNAME = "convert_grid_format (subscript)"

# allowed CONVERSIONS and MODES:
CONVERSIONS = ["ecl2roff"]
MODES = ["grid", "init", "restart"]

xtg = XTGeoDialog()
logger = xtg.functionlogger(__name__)

try:
    from ..version import version

    __version__ = version
except ImportError:
    __version__ = "0.0.0"


def get_parser():
    """Setup an argparse argument parser for parsing arguments
    and making documentation"""

    usetxt = "convert_grid_format ... "

    parser = argparse.ArgumentParser(
        description="Convert between various 3D grid cornerpoint formats", usage=usetxt
    )

    parser.add_argument(
        "--conversion",
        dest="conversion",
        type=str,
        default="ecl2roff",
        help="Conversion method, select from {} "
        "(default ecl2roff)".format(CONVERSIONS),
    )

    parser.add_argument(
        "--mode",
        dest="mode",
        type=str,
        default="grid",
        help="Mode: {} (default grid)".format(MODES),
    )

    parser.add_argument(
        "--file", dest="infile", type=str, help="Input file name (full name or root)"
    )

    parser.add_argument(
        "--output", dest="outfile", type=str, help="Output file name (full name)"
    )

    parser.add_argument(
        "--propnames",
        dest="propnames",
        type=str,
        help="List of propnames, separate either with \
                        spaces or colon",
    )
    parser.add_argument(
        "--dates",
        dest="dates",
        type=str,
        help="List of dates, separate either with \
                        spaces or colon",
    )

    parser.add_argument(
        "--standardfmu",
        dest="stdfmu",
        action="store_true",
        default=False,
        help="Use standard fmu name setting of file (no args)",
    )
    return parser


def _do_parse_args(args):
    """Parse command line arguments"""

    if args is None:
        args = sys.argv[1:]
    else:
        args = args

    parser = get_parser()

    if len(args) < 2:
        parser.print_help()
        print("QUIT")
        sys.exit(0)

    args = parser.parse_args(args)
    return args


def _convert_ecl2roff(filename, mode, outfile, option, props, dates):
    """Conversion..."""

    # pylint: disable=too-many-branches

    xtg.say("ecl2roff...")

    fname, fext = os.path.splitext(filename)
    oname, _oext = os.path.splitext(outfile)

    filesep = "_"
    if option:  # standardfmu separator
        filesep = "--"

    if mode in ["grid", "init", "restart"]:
        logger.info("Running GRID conversion...")

        logger.info("Convert from EGRID to ROFF...")
        mygrid = xtgeo.grid3d.Grid(fname + ".EGRID", fformat="egrid")

        if mode == "grid":
            xtg.say("Mode is grid")
            outputfile = oname + ".roff"
            xtg.say("Output grid to <{}>".format(oname + ".roff"))
            mygrid.to_file(outputfile, fformat="roff")
    else:
        raise SystemExit("STOP! Invalid mode: <{}>".format(mode))

    if mode in ("restart", "init"):
        xtg.say("Mode is {}".format(mode))
        logger.info("Running %s conversion...", mode.upper())
        fname, fext = os.path.splitext(filename)

        if not props:
            raise SystemExit("STOP. No properties given")

        if ":" in props:
            props = props.split(":")
        else:
            props = props.split()

        fformat = mode
        fformat = fformat.replace("restart", "unrst")
        if mode == "restart":
            if dates is None:
                raise SystemExit("STOP. No dates given")

            if ":" in dates:
                dates = dates.split(":")
            else:
                dates = dates.split()
        else:
            dates = None

        if fext in (".UNRST", ".INIT", ""):

            myprops = xtgeo.grid3d.GridProperties()

            usext = ".{}".format(fformat).upper()

            myprops.from_file(
                fname + usext, names=props, dates=dates, fformat=fformat, grid=mygrid
            )

            for prop in myprops.props:
                pname = prop.name.lower().replace("_", filesep)
                outputfile = oname + filesep + pname + ".roff"
                xtg.say("Output grid property to <{}>".format(outputfile))
                prop.to_file(outputfile, fformat="roff")
        else:
            raise SystemExit("Invalid grid extions")


def main(args=None):
    """Entry-point"""

    XTGeoDialog.print_xtgeo_header(APPNAME, __version__)

    args = _do_parse_args(args)

    logger.info(args)

    if args.conversion not in set(CONVERSIONS):
        logger.critical("ERROR")
        SystemExit(
            "Illegal conversion <{}>. Allowed are: {}".format(
                args.conversion, CONVERSIONS
            )
        )

    xtg.say("Running conversion...")
    _convert_ecl2roff(
        args.infile, args.mode, args.outfile, args.stdfmu, args.propnames, args.dates
    )


if __name__ == "__main__":
    main()
