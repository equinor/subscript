"""Tool to stack/pivot CSV files, exposed as command line client,
ERT workflow and ERT forward model"""

import argparse
import logging
import re
import sys
import warnings
from typing import Pattern

import pandas as pd
from ert.config import ErtScript
from ert.shared.plugins.plugin_manager import hook_implementation  # type: ignore

from subscript import __version__, getLogger

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

# The following string is used for the ERT forward model:
EXAMPLE = """
Put this in your ERT config::

  FORWARD_MODEL CSV_STACK(<CSVFILE>=stackme.csv, <OUTPUT>=stacked.csv, <OPTION>="--keepminimal")

"""  # noqa

CATEGORY = "utility.transformation"

# The following string is used for the ERT workflow documentation, note
# the very subtle difference in variable name.
WORKFLOW_EXAMPLE = """
Add a file named e.g. ``ert/bin/workflows/CSV_STACK_WELLS`` with the contents::

  CSV_STACK "<CASEDIR>/share/results/tables/unsmry--montly.csv" "--split" well "--keepminimal"

assuming you already have a CSV file in the given path that you want to stack.

It is important to individually quote any arguments that include ``--`` or else
ERT will take the rest of the line as a comment.

Add to your ERT config to have the workflow automatically executed on
successful runs::

  LOAD_WORKFLOW ../bin/workflows/CSV_STACK_WELLS
  HOOK_WORKFLOW CSV_STACK_WELLS POST_SIMULATION

"""  # noqa

# List of columns that will always be kept, case insensitive:
ALWAYS_KEEP = [
    "REAL",
    "ITER",
    "ENSEMBLE",
    "DATE",
]

# Library of columns that we are able to split.
# Dictionary of lists. Lists contain the elements:
#  0: regexp for matching in front of the colum name separator
#  1: Separator in column names
#  2: Name of new column
STACK_LIBRARY = {
    "well": ["W[A-Z0-9]*:.*", ":", "WELL"],
    "region": ["R[A-Z_0-9]*:.*", ":", "REGION"],
    "group": ["G[A-Z0-9]*:.*", ":", "GROUP"],
    "block": ["B[A-Z0-9]*:.*", ":", "BLOCK"],
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


class CsvStack(ErtScript):
    """A class with a run() function that can be registered as an ERT plugin,
    to be used as an ERT workflow (wrapping the command line utility)"""

    # pylint: disable=too-few-public-methods
    def run(self, *args):
        # pylint: disable=no-self-use
        """Parse with a simplified command line parser, for ERT only,
        calling csv_stack_main()"""
        parser = get_parser()
        args = parser.parse_args(args)
        csv_stack_main(args, support_magics=False)


def get_parser() -> argparse.ArgumentParser:
    """Set up parser for command line utility"""
    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter,
        description=DESCRIPTION,
    )
    parser.add_argument(
        "csvfile",
        help="Input CSV file. If you use -, it will read from stdin ",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Name of output csv file. Use - to write to stdout.",
        default="stacked.csv",
    )
    parser.add_argument(
        "-s",
        "--split",
        type=str,
        help="Type of column to be split/unpivoted/stacked. Choose from the "
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
            "Keep only REAL, ENSEMBLE, ITER, DATE and unpivoted columns. "
            "Implies dropping constant columns"
        ),
        default=False,
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Be verbose", default=False
    )
    parser.add_argument(
        # Placeholders for one empty argument from ERT forward model
        # This is the way to support --keepminimal, the default
        # in the job configuration is "" and will end in this argument
        # unless the ert config sets it to f.ex. --keepminimal
        "option",
        default="",
        nargs="?",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + __version__ + ")",
    )

    return parser


def deprecated_main() -> None:
    """Function to display deprecation warning before going to main()"""
    warnings.warn("csvStack is deprecated. Use csv_stack", FutureWarning)
    main()


def main() -> None:
    """Function for command line invocation"""
    parser = get_parser()
    args = parser.parse_args()
    csv_stack_main(args, support_magics=True)


def csv_stack_main(args: argparse.Namespace, support_magics: bool = False) -> None:
    """A main function to be used both from the command line, and
    when used as an ERT plugin (ERT workflow).

    This function writes to disk or to stdout.

    Args:
        args (argparse.Namespace): Namespace with command line arguments
        support_magics (bool): If True, it is possible to read and write to
            stdin/stdout. Should not be set when used as ERT workflow.
    """
    if not support_magics and (
        args.output == __MAGIC_STDOUT__ or args.csvfile == __MAGIC_STDIN__
    ):
        logger.error("Can't use stdin/stdout")
        sys.exit(1)

    if args.verbose:
        if args.output == __MAGIC_STDOUT__:
            raise SystemExit("Don't use verbose mode when writing to stdout")
        logger.setLevel(logging.INFO)

    if args.csvfile == __MAGIC_STDIN__:
        logger.info("Loading CSV data from stdin.")
        dframe = pd.read_csv(sys.stdin)
    else:
        logger.info("Loading CSV data from %s", args.csvfile)
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


def drop_constants(
    dframe: pd.DataFrame, keepminimal: bool, stackmatcher: Pattern
) -> pd.DataFrame:
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
        # Also drop columns not involved in stacking operation
        if keepminimal and (not (stackmatcher.match(col) or col.lower() in keepthese)):
            columnstodelete.append(col)
    if keepminimal:
        logger.info("Deleting constant and unwanted columns %s", str(columnstodelete))
    else:
        logger.info("Deleting constant columns %s", str(columnstodelete))
    logger.info("Deleted %d columns", len(columnstodelete))
    return dframe.drop(columnstodelete, axis=1)


def csv_stack(
    dframe: pd.DataFrame, stackmatcher: Pattern, stackseparator: str, newcolumn: str
) -> pd.DataFrame:
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
            tuplecols.append((col, ""))
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
        dframe[nostackcolumnnames] = dframe[nostackcolumnnames].ffill()

        dframe = dframe.reset_index()

        # Now we have rows that does not belong to any well, we should
        # delete those rows
        dframe = dframe[dframe[newcolumn] != ""]

        # And delete a byproduct of our reshaping (this is the index
        # prior to stacking)
        del dframe["level_0"]

    return dframe.reset_index(drop=True)


@hook_implementation
def legacy_ertscript_workflow(config) -> None:
    """Hook the CsvStack class into ERT with the name CSV_STACK,
    and inject documentation"""
    workflow = config.add_workflow(CsvStack, "CSV_STACK")
    workflow.parser = get_parser
    workflow.description = DESCRIPTION
    workflow.examples = WORKFLOW_EXAMPLE
    workflow.category = CATEGORY


if __name__ == "__main__":
    main()
