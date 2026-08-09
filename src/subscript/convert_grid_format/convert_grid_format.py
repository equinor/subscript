"""Conversion between grid corner point formats"""

import argparse
import logging
import os
import sys
from collections.abc import Sequence
from pathlib import Path

import xtgeo
from xtgeo.common import XTGeoDialog

from subscript import __version__

APPNAME = "convert_grid_format (subscript)"

# allowed CONVERSIONS and MODES:
CONVERSIONS = ["ecl2roff", "roff2ecl"]
MODES = ["grid", "init", "restart"]
ECL_FORMATS = {"grdecl", "bgrdecl", "egrid"}

xtg = XTGeoDialog()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_parser() -> argparse.ArgumentParser:
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
        help=f"Conversion method, select from {CONVERSIONS} (default ecl2roff)",
    )

    parser.add_argument(
        "--mode",
        dest="mode",
        type=str,
        default="grid",
        help=f"Mode: {MODES} (default grid). roff2ecl supports grid only.",
    )

    parser.add_argument(
        "--file",
        dest="infile",
        type=str,
        help="Input file name (full name or root)",
    )

    parser.add_argument(
        "--output", dest="outfile", type=str, help="Output file name (full name)"
    )
    parser.add_argument(
        "--outformat",
        dest="outformat",
        type=str,
        default="auto",
        help=(
            "Output Eclipse format for roff2ecl: "
            f"{sorted(ECL_FORMATS)} or auto (infer from --output extension, "
            "fallback to grdecl)"
        ),
    )

    parser.add_argument(
        "--propnames",
        dest="propnames",
        type=str,
        help="List of propnames, separate either with spaces or colon",
    )
    parser.add_argument(
        "--dates",
        dest="dates",
        type=str,
        help=(
            "List of dates, separated by spaces or colon, or filename "
            "pointing to a file with one date pr. line."
        ),
    )

    parser.add_argument(
        "--standardfmu",
        dest="stdfmu",
        action="store_true",
        default=False,
        help="Use standard fmu name setting of file (no args)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + __version__ + ")",
    )
    return parser


def _do_parse_args(args: Sequence[str] | None) -> argparse.Namespace:
    """Parse command line arguments"""

    if args is None:
        args = sys.argv[1:]

    parser = get_parser()

    if len(sys.argv[1:]) < 2:
        parser.print_help()
        print("QUIT")
        sys.exit(0)

    return parser.parse_args(args)


def _convert_ecl2roff(
    filename: str,
    mode: str,
    outfile: str,
    option: str,
    props: str,
    dates: str | None,
) -> None:
    """Conversion..."""

    xtg.say("ecl2roff...")

    fname, fext = os.path.splitext(filename)
    oname, _oext = os.path.splitext(outfile)

    filesep = "_"
    if option:  # standardfmu separator
        filesep = "--"

    if mode in {"grid", "init", "restart"}:
        logger.info("Running GRID conversion...")

        logger.info("Convert from EGRID to ROFF...")
        mygrid = xtgeo.grid_from_file(fname + ".EGRID", fformat="egrid")

        if mode == "grid":
            xtg.say("Mode is grid")
            outputfile = oname + ".roff"
            xtg.say(f"Output grid to <{oname + '.roff'}>")
            mygrid.to_file(outputfile, fformat="roff")
    else:
        raise SystemExit(f"STOP! Invalid mode: <{mode}>")

    if mode in {"restart", "init"}:
        xtg.say(f"Mode is {mode}")
        logger.info("Running %s conversion...", mode.upper())
        fname, fext = os.path.splitext(filename)

        if not props:
            raise SystemExit("STOP. No properties given")

        props_list = props.split(":") if ":" in props else props.split()

        fformat = mode
        fformat = fformat.replace("restart", "unrst")

        dates_list: list[str] | None
        if mode == "restart":
            if dates is None:
                raise SystemExit("STOP. No dates given")

            if os.path.exists(dates):
                dates = " ".join(Path(dates).read_text(encoding="utf8").splitlines())
            dates_list = dates.split(":") if ":" in dates else dates.split()
        else:
            dates_list = None

        if fext in {".UNRST", ".INIT", ""}:
            usext = f".{fformat.upper()}"
            myprops = xtgeo.gridproperties_from_file(
                fname + usext,
                names=props_list,
                dates=dates_list,
                fformat=fformat,
                grid=mygrid,
            )

            for prop in myprops.props:
                pname = prop.name.lower().replace("_", filesep)
                outputfile = oname + filesep + pname + ".roff"
                xtg.say(f"Output grid property to <{outputfile}>")
                prop.to_file(outputfile, fformat="roff")
        else:
            raise SystemExit("Invalid grid extention")


def _resolve_ecl_format(outfile: str, outformat: str) -> str:
    format_name = outformat.lower()
    if format_name != "auto":
        if format_name not in ECL_FORMATS:
            raise SystemExit(
                f"Invalid outformat <{outformat}>. Allowed: {ECL_FORMATS} or auto"
            )
        return format_name

    _name, ext = os.path.splitext(outfile)
    ext_map = {".grdecl": "grdecl", ".bgrdecl": "bgrdecl", ".egrid": "egrid"}
    inferred = ext_map.get(ext.lower())
    if inferred:
        return inferred

    logger.info(
        "outformat=auto could not infer format from extension <%s>; defaulting to "
        "grdecl",
        ext or "<none>",
    )
    return "grdecl"


def _convert_roff2ecl(
    filename: str,
    mode: str,
    outfile: str,
    outformat: str,
) -> None:
    if not filename or not outfile:
        raise SystemExit("STOP. Both --file and --output are required")
    if mode != "grid":
        raise SystemExit(f"STOP! Invalid mode for roff2ecl: <{mode}>")

    ecl_format = _resolve_ecl_format(outfile, outformat)
    grid = xtgeo.grid_from_file(filename, fformat="roff")
    grid.to_file(outfile, fformat=ecl_format)


def main(args: Sequence[str] | None = None) -> None:
    """Entry-point"""

    XTGeoDialog.print_xtgeo_header(APPNAME, __version__)

    parsed_args = _do_parse_args(args)

    logger.info(parsed_args)

    if parsed_args.conversion not in set(CONVERSIONS):
        raise ValueError(
            f"Illegal conversion <{parsed_args.conversion}>. Allowed are: {CONVERSIONS}"
        )

    xtg.say("Running conversion...")
    if parsed_args.conversion == "ecl2roff":
        _convert_ecl2roff(
            parsed_args.infile,
            parsed_args.mode,
            parsed_args.outfile,
            parsed_args.stdfmu,
            parsed_args.propnames,
            parsed_args.dates,
        )
    else:
        _convert_roff2ecl(
            parsed_args.infile,
            parsed_args.mode,
            parsed_args.outfile,
            parsed_args.outformat,
        )


if __name__ == "__main__":
    main()
