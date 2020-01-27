"""
Merge multiple CSV files.
"""

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import os
import sys
import argparse
import re
import logging

import pandas as pd

logging.basicConfig()
logger = logging.getLogger(__name__.split(".")[-1])

REAL_REGEXP = r".*realization-(\d+)/.*"
ITER_REGEXP = r".*/iter-(\d+).*"
ENSEMBLE_REGEXP = r".*realization-\d+/(.*?)/.*"
ENSEMBLESET_REGEXP = r".*/(.*?)/realization.*"


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """
    Multiple inheritance used for argparse to get both
    defaults and raw description formatter
    """

    pass


def get_parser():
    """Construct parser object for csvMergeEnsembles"""
    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter,
        description="""
Merge multiple CSV files into one. Each row will be tagged at least with
the original filename in the FILENAME column.

Additionally, if realization, iteration and ensemble name can be inferred
from the paths, it will be added to the REAL, ITER and ENSEMBLE and ENSEMBLESET
columns.

The columns in the ensembles need not be the same. Similar column names
will be merged, differing column names will be padded (with NaN) in the
resulting dataset where they don't exist.

Do not assume anything on the ordering of columns after merging.
""",
    )
    parser.add_argument("csvfiles", nargs="+", help="input csv files")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="name of output csv file. Use - or stdout to dump output to stdout.",
        default="merged.csv",
    )
    parser.add_argument(
        "--memoryconservative",
        "-m",
        action="store_true",
        help=(
            "Conserve memory while merging at the expense of speed. "
            "Default is to use up to twice as much memory "
            "as the size of the final CSV. Do not use unless normal mode fails."
        ),
        default=False,
    )
    parser.add_argument(
        "--keepconstantcolumns",
        help=argparse.SUPPRESS,
        # Deprecated and default. Use --dropconstantcolumns to drop
    )
    parser.add_argument(
        "--dropconstantcolumns",
        action="store_true",
        help="Drop (delete) constant columns in the merged dataset",
        default=False,
    )
    parser.add_argument(
        "--filecolumn",
        type=str,
        help="Name of column containing original filename",
        default="FILENAME",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="More verbose output"
    )
    parser.add_argument(
        "-q",
        "--quiet",
        help=argparse.SUPPRESS,
        # Deprecated (and default). Use --verbose if more output is wanted.
    )
    return parser


def merge_csvfiles(csvfiles, tags=None, memoryconservative=False):
    """
    Load CSV files from disk, tag them and return DataFrame

    Args:
        csvfiles (list of str): Pathnames to CSV files
        tags (dict of lists): Each key will become a column name
            in the returned dataframe, with values from the list
            corresponding to the csvfiles.
        memoryconservative (bool): If true, one dataframe will
            be read from disk and merged at a time. Slower, but
            requires less memory than loading every dataframe up front.
    """
    if not tags:
        tags = {}
    if memoryconservative:
        logger.info("Memory-conservative mode, one merge for every loaded CSV")
        merged_df = pd.DataFrame()
        for idx, csvfname in enumerate(csvfiles):
            logger.info(" - Loading %s", csvfname)
            dframe = pd.read_csv(csvfname)
            for tag in tags:
                if len(tags[tag]) == len(csvfiles):
                    if tag not in dframe:
                        dframe[tag] = tags[tag][idx]
                    else:
                        logger.warning("Tag %s already in dataframe", str(tag))
                else:
                    logger.warning(
                        "Could not use tag %s, insufficient length", str(tag)
                    )
            logger.info(" - Merging with previously loaded CSV files")
            merged_df = pd.concat(
                [merged_df, dframe], axis=0, ignore_index=True, sort=False
            )
    else:
        logger.info("Loading all CSV files into memory before merging")
        dfs = []
        for csvfile in csvfiles:
            logger.info(" - Loading %s", csvfile)
            dfs.append(pd.read_csv(csvfile))
        for idx, dframe in enumerate(dfs):
            for tag in tags:
                if len(tags[tag]) == len(csvfiles):
                    if tag not in dframe:
                        dframe[tag] = tags[tag][idx]
                    else:
                        logger.warning("Tag %s already in dataframe", str(tag))
                else:
                    logger.warning(
                        "Could not use tag %s, insufficient length", str(tag)
                    )
        logger.info("Merging..")
        merged_df = pd.concat(dfs, axis=0, ignore_index=True, sort=False)
    return merged_df


def taglist(strings, regexp_str):
    """Apply a regexp string to a list of strings
    and return a list of the matches.

    The list may contain None for strings where there are no matches.
    If there are no matches for any of the strings, an empty
    list is returned.

    If all found tags are equal, empty list is returned.
    """
    regexp = re.compile(regexp_str)
    matches = map(lambda x: re.match(regexp, x), strings)
    values = [x and x.group(1) for x in matches]
    if any(values) and len(set(values)) > 1:
        return values
    return []


def main():
    """Entry point from command line"""
    parser = get_parser()
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)

    csvfiles = list(filter(os.path.exists, args.csvfiles))

    tags = {}
    tags["REAL"] = taglist(csvfiles, REAL_REGEXP)
    tags["ITER"] = taglist(csvfiles, ITER_REGEXP)
    tags["ENSEMBLE"] = taglist(csvfiles, ENSEMBLE_REGEXP)
    tags["ENSEMBLESET"] = taglist(csvfiles, ENSEMBLESET_REGEXP)
    tags[args.filecolumn] = csvfiles
    tags = {tag: tags[tag] for tag in tags if len(tags[tag])}

    logger.info("Tags: %s", str(tags))

    merged_df = merge_csvfiles(
        csvfiles, tags, memoryconservative=args.memoryconservative
    )

    if args.dropconstantcolumns:
        columnstodelete = []
        for col in merged_df.columns:
            if len(merged_df[col].unique()) == 1:
                columnstodelete.append(col)
        logger.info("Dropping constant columns " + str(columnstodelete))
        merged_df.drop(columnstodelete, inplace=True, axis=1)

    if merged_df.empty:
        print("ERROR: No data to output.")
        sys.exit(1)

    logger.info("Final column list: %s", str(merged_df.columns))

    logger.info("Exporting CSV data to " + args.output)

    if args.output == "-" or args.output == "stdout":
        merged_df.to_csv(sys.stdout, index=False)
    else:
        merged_df.to_csv(path_or_buf=args.output, index=False)

    if args.verbose:
        print(" - Finished writing to " + args.output)


if __name__ == "__main__":
    main()
