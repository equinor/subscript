"""Tool to stack/pivot CSV files, exposed as command line client,
ERT workflow and ERT forward model"""
import sys
import re
import logging
import argparse
from typing import Pattern

import pandas as pd

from subscript import getLogger

logger = getLogger(__name__)

__MAGIC_STDOUT__ = "-"
__MAGIC_STDIN__ = "-"

DESCRIPTION = """Stack columns in a CSV exported file.

All columns in your data set with a colon ":" in it, will be split such that the
string after the colon will become a column value instead of its own column.
Thus all columns called WOPT:A-1, WOPT:A-2, WOPT:A-3 etc will be merged into one
column called WOPT, and you will have a column name called "WELL" that contains
A-1, A-2, or A-3 as values.

If importing the output CSV into Spotfire, you may then view and filter WOPT and
friends by wellname, instead of selecting individual columns."""

# List of columns that will always be kept, case insensitive:
ALWAYS_KEEP = [
    "Realization",
    "Realisation",
    "RunName",
    "Real",
    "Iteration",
    "Iter",
    "Ensemble",
    "date",
]

# Library of columns that we are able to split.
# Dictionary of lists. Lists contain the elements:
#  0: regexp for matching in front of the colum name separator
#  1: Separator in column names
#  2: Name of new column
STACK_LIBRARY = {
    "well": ["W[A-Z]*:.*", ":", "WELL"],
    "region": ["R[A-Z_]*:.*", ":", "REGION"],
    "group": ["G[A-Z]*:.*", ":", "GROUP"],
    "block": ["B[A-Z]*:.*", ":", "BLOCK"],
    "all": [".*:.*", ":", "IDENTIFIER"],
}


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """
    Multiple inheritance used for argparse to get both
    defaults and raw description formatter
    """

    # pylint: disable=unnecessary-pass

    pass


def get_parser():
    """Set up parser for command line utility"""
    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter,
        description=DESCRIPTION,
    )
    parser.add_argument(
        "csvfile",
        help="input csv file. If you type stdin or -, it will read from stdin ",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help=(
            "name of output csv file. "
            "Use - or stdout to have the output dumped to stdout."
        ),
        default="stacked.csv",
    )
    parser.add_argument(
        "--split",
        type=str,
        help="type of column to be split/unpivoted/stacked. Choose from the "
        + "the predefined set: well, region, group, block, all",
        default="well",
    )
    parser.add_argument(
        "--keepconstantcolumns",
        action="store_true",
        help="Keep constant columns before stacking",
        default=False,
    )
    parser.add_argument(
        "--keepminimal",
        action="store_true",
        help=(
            "Keep only REAL, ENSEMBLE, DATE and unpivoted columns. "
            "Implies dropping constant columns"
        ),
        default=False,
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Be verbose", default=False
    )
    return parser


def main():
    """Function for command line invocation"""
    parser = get_parser()
    args = parser.parse_args()

    if args.verbose:
        if args.output == __MAGIC_STDOUT__:
            raise SystemExit("Don't use verbose mode when writing to stdout")
        logger.setLevel(logging.INFO)

    if args.csvfile == __MAGIC_STDIN__:
        logger.info("Loading ensemble from stdin.")
        dframe = pd.read_csv(sys.stdin)
    else:
        logger.info("Loading ensemble from %s", args.csvfile)
        dframe = pd.read_csv(args.csvfile)

    if args.split not in STACK_LIBRARY:
        logger.error("Don't know how to split on %s", str(args.split))
        sys.exit(1)

    stackargs = STACK_LIBRARY[args.split]

    if not args.keepconstantcolumns or args.keepminimal:
        dframe = drop_constants(dframe, args.keepminimal, re.compile(stackargs[0]))

    stacked = csv_stack(dframe, re.compile(stackargs[0]), stackargs[1], stackargs[2])

    logger.info("Writing stacked CSV to %s", args.output)
    output = args.output if args.output != __MAGIC_STDOUT__ else sys.stdout
    stacked.to_csv(output, index=False)


def drop_constants(dframe: pd.DataFrame, keepminimal: bool, stackmatcher: Pattern):
    """Drop/purge/remove columns from the dataframe that we don't want
    to include in a stacking operation (stacking can blow up the dataframe size)

    Obey a global variable with list of columns that we should always keep, you
    don't want to remove e.g. the ensemble name even if it is constant.

    Args:
        dframe (pd.DataFrame): Dataframe with data
        keepminimial (bool): If True, columns not involved in the stacking
            operation will also  be dropped.
        stackmatcher (Pattern): Regular expression that matches
            the columns to be stacked.

    Returns:
        pd.DataFrame, possibly with fewer columns.
    """
    keepthese = {x.lower() for x in ALWAYS_KEEP}
    columnstodelete = []
    for col in dframe.columns:
        if len(dframe[col].unique()) == 1:
            # col was a constant column
            columnstodelete.append(col)
        if keepminimal:
            # Also drop columns not involved in stacking operation
            if not (stackmatcher.match(col) or col.lower() in keepthese):
                columnstodelete.append(col)
    if keepminimal:
        logger.info("Deleting constant and unwanted columns %s", str(columnstodelete))
    else:
        logger.info("Deleting constant columns %s", str(columnstodelete))
    logger.info("Deleted %d columns", len(columnstodelete))
    return dframe.drop(columnstodelete, axis=1)


def csv_stack(
    dframe: pd.DataFrame, stackmatcher: Pattern, stackseparator: str, newcolumn: str
):
    """Reshape an incoming dataframe by stacking/pivoting.

    The dataframe object will be modified in-place.

    Args:
        dframe (pd.DataFrame): Data to reshape
        stackmatcher (Pattern): Regular expression that matches columns
            to be stacked.
        stackseparator (str): String to use for splitting columns names
        newcolumn (str): Name of new column containing the latter part of the
            stacked column names.

    Returns:
        pd.DataFrame
    """
    if isinstance(stackmatcher, str):
        stackmatcher = re.compile(stackmatcher)
    if newcolumn in dframe:
        raise ValueError("Column name %s already exists in the data")
    tuplecols = []
    dostack = False
    colstostack = 0
    logger.info(
        "Will stack columns matching '%s' with separator '%s'",
        stackmatcher,
        stackseparator,
    )
    logger.info("Name of new identifying column will be '%s'", newcolumn)

    nostackcolumnnames = []
    for col in dframe.columns:
        if stackmatcher.match(col):
            tuplecols.append(tuple(col.split(stackseparator)))
            colstostack = colstostack + 1
            dostack = True
        else:
            tuplecols.append(tuple([col, ""]))
            nostackcolumnnames.append(col)

    logger.info("Found %d out of %d columns to stack", colstostack, len(dframe.columns))

    if dostack:
        # Convert to MultiIndex columns
        dframe.columns = pd.MultiIndex.from_tuples(tuplecols, names=["", newcolumn])

        # Stack the multiindex columns, this will add a lot of rows to
        # our ensemble, and condense the number of columns
        dframe = dframe.stack()

        # The values from non-multiindex-columns must be propagated to
        # the rows that emerged from the stacking. If you use the
        # 'all' pivottype, then you will get some NaN-values in the
        # MultiIndex columns that are intentional.
        dframe[nostackcolumnnames] = dframe[nostackcolumnnames].fillna(method="ffill")

        dframe = dframe.reset_index()

        # Now we have rows that does not belong to any well, we should
        # delete those rows
        dframe = dframe[dframe[newcolumn] != ""]

        # And delete a byproduct of our reshaping (this is the index
        # prior to stacking)
        del dframe["level_0"]

    return dframe.reset_index(drop=True)


if __name__ == "__main__":
    main()
