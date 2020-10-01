import os
import datetime
import argparse
import logging

import dateutil.parser
import yaml

import subscript
from subscript.sunsch import sunsch

logger = subscript.getLogger(__name__)

DESCRIPTION = """Merges several ECLIPSE schedule files into one single file.
This is done by sorting on the DATES keyword in the different input files.
If a given date exists in more than one input file, the order of keywords
under that date follows the input order of the files.

Anything before the first DATES keyword in all files will be merged to
one block occuring before the first DATES in all files."""


def get_parser():
    """Make a parser for command line arguments and for documentation"""
    parser = argparse.ArgumentParser(description=DESCRIPTION)

    parser.add_argument("inputfiles", type=str, nargs="+", help="Path to input files.")
    parser.add_argument("outputfile", type=str, help="Path to output file.")
    parser.add_argument(
        "-f",
        "--force",
        dest="force",
        action="store_true",
        help="Do not prompt before overwriting",
        default=False,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    parser.add_argument(
        "-e",
        "--clip_end",
        dest="end_date",
        help="Ignore keywords in the input files after this date (YYYY-MM-DD)",
        default=None,
    )
    return parser


def main():
    """Entry point from command line"""
    parser = get_parser()
    args = parser.parse_args()

    sunsch_config = {"startdate": datetime.date(1900, 1, 1), "files": args.inputfiles}

    if args.verbose:
        # Set the root logger to INFO, will be inherited by sunsch
        logging.getLogger().setLevel(logging.INFO)

    logger.info("# Sending the following YAML configuration to sunsch:")
    logger.info(yaml.dump(sunsch_config))

    if args.end_date:
        sunsch_config["enddate"] = dateutil.parser.parse(args.end_date).date()

    sch = sunsch.process_sch_config(sunsch_config)

    if os.path.exists(args.outputfile) and not args.force:
        print("ERROR: Not overwriting existing file {}".format(args.outputfile))
    else:
        with open(args.outputfile, "w") as outfile:
            outfile.write(str(sch))
        print("Wrote {} dates to {}".format(len(sch), args.outputfile))
        # len(sch) includes the sometimes empty content before the first DATES..


if __name__ == "__main__":
    main()
