"""Merge multiple CSV files."""

import argparse
import logging
import os
import re
import sys
from typing import Dict, List, Optional

import pandas as pd
from ert.config import ErtScript
from ert.shared.plugins.plugin_manager import hook_implementation  # type: ignore

from subscript import __version__, getLogger
from subscript.eclcompress.eclcompress import glob_patterns

logger = getLogger(__name__)

REAL_REGEXP = r".*realization-(\d+)/.*"
ITER_REGEXP = r".*/iter-(\d+).*"
ENSEMBLE_REGEXP = r".*realization-\d+/(.*?)/.*"
ENSEMBLESET_REGEXP = r".*/(.*?)/realization.*"

# This documentation is for csv_merge as an ERT workflow
DESCRIPTION = """
CSV_MERGE will merge a selection of CSV files, typically across
an ensemble, and write merged CSV to an output file, with the
additional columns REAL and ENSEMBLE.
"""

EXAMPLES = """
Add a file named e.g. ``ert/bin/workflows/MERGE_SATFUNC`` with the contents::

  MAKE_DIRECTORY <CASEDIR>/share/results/tables/
  CSV_MERGE "<CASEDIR>/realization-*/iter-*/share/results/tables/satfunc.csv" "<CASEDIR>/share/results/tables/satfunc.csv"

(where ``<CASEDIR>`` typically points to ``/scratch/..``).

Add to your ERT config to have the workflow automatically executed on successful
runs::

  LOAD_WORKFLOW ../bin/workflows/MERGE_SATFUNC
  HOOK_WORKFLOW MERGE_SATFUNC POST_SIMULATION

"""  # noqa


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """
    Multiple inheritance used for argparse to get both
    defaults and raw description formatter
    """

    # pylint: disable=unnecessary-pass


class CsvMerge(ErtScript):
    """A class with a run() function that can be registered as an ERT plugin"""

    # pylint: disable=too-few-public-methods
    def run(self, *args):
        # pylint: disable=no-self-use
        """Parse with a simplified command line parser, for ERT only,
        call csv_merge_main()"""
        parser = get_ertwf_parser()
        args = parser.parse_args(args)
        logger.setLevel(logging.INFO)
        globbedfiles = glob_patterns(args.csvfiles)
        csv_merge_main(csvfiles=globbedfiles, output=args.output)


def get_parser() -> argparse.ArgumentParser:
    """Construct parser object for csv_merge"""
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
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--debug", action="store_true", help="Debug output, more verbose than --verbose"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + __version__ + ")",
    )
    return parser


def get_ertwf_parser() -> argparse.ArgumentParser:
    """Alternative parser used for CSV_MERGE ERT workflow job"""
    parser = argparse.ArgumentParser(formatter_class=CustomFormatter, description="")

    parser.add_argument(
        "csvfiles", nargs="+", help="input csv files, wildcards supported"
    )
    parser.add_argument(
        "output",
        type=str,
        help="Name of output csv file.",
    )
    return parser


def merge_csvfiles(
    csvfiles: list, tags: Optional[Dict[str, List]], memoryconservative: bool = False
) -> pd.DataFrame:
    """
    Load CSV files from disk. Tag each row with filename origin.

    Args:
        csvfiles (list): List of strings with pathnames to CSV files
        tags (dict): Dict of lists. Each key will become a column name
            in the returned dataframe, with values from the list
            corresponding to the csvfiles.
        memoryconservative (bool): If true, one dataframe will
            be read from disk and merged at a time. Slower, but
            requires less memory than loading every dataframe up front.

    Returns:
        pd.Dataframe
    """
    if not tags:
        tags = {}
    if memoryconservative:
        logger.info("Memory-conservative mode, one merge for every loaded CSV")
        merged_df = pd.DataFrame()
        for idx, csvfname in enumerate(csvfiles):
            logger.info(" - Loading %s", csvfname)
            try:
                dframe = pd.read_csv(csvfname)
            except pd.errors.EmptyDataError:
                logger.warning("Empty file %s, ignored", csvfname)
                dframe = pd.DataFrame()
            except FileNotFoundError:
                logger.warning("File %s not found, ignored", csvfname)
                dframe = pd.DataFrame()
            for tag in tags:
                if len(tags[tag]) == len(csvfiles):
                    if tag not in dframe:
                        # pylint: disable=E1137
                        # (false positive)
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
        loaded_files = 0
        for csvfile in csvfiles:
            logger.debug(" - Loading %s", csvfile)
            try:
                dfs.append(pd.read_csv(csvfile))
                loaded_files += 1
            except pd.errors.EmptyDataError:
                logger.warning("Empty file %s, ignored", csvfile)
                dfs.append(pd.DataFrame())
            except FileNotFoundError:
                logger.warning("File %s not found, ignored", csvfile)
                dfs.append(pd.DataFrame())
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
        logger.info("Merging %d files..", loaded_files)
        merged_df = pd.concat(dfs, axis=0, ignore_index=True, sort=False)
    return merged_df


def taglist(strings: List[str], regexp_str: str) -> list:
    """Apply a regexp string to a list of strings
    and return a list of the matches.

    The list may contain None for strings where there are no matches.
    If there are no matches for any of the strings, an empty
    list is returned.
    """
    regexp = re.compile(regexp_str)
    matches = (re.match(regexp, x) for x in strings)
    values = [x and x.group(1) for x in matches]
    if any(values):
        return values
    return []


def main() -> None:
    """Entry point from command line"""
    parser = get_parser()
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    csv_merge_main(
        csvfiles=args.csvfiles,
        output=args.output,
        filecolumn=args.filecolumn,
        memoryconservative=args.memoryconservative,
        dropconstantcolumns=args.dropconstantcolumns,
    )


def csv_merge_main(
    csvfiles: list,
    output: str,
    filecolumn: str = "",
    memoryconservative: bool = False,
    dropconstantcolumns: bool = False,
) -> None:
    """A "main" function that can be used both from the command line,
    and from an ERT workflow"""
    csvfiles = list(filter(os.path.exists, csvfiles))

    tags = {}
    tags["REAL"] = taglist(csvfiles, REAL_REGEXP)
    tags["ITER"] = taglist(csvfiles, ITER_REGEXP)
    tags["ENSEMBLE"] = taglist(csvfiles, ENSEMBLE_REGEXP)
    tags["ENSEMBLESET"] = taglist(csvfiles, ENSEMBLESET_REGEXP)
    if filecolumn:
        tags[filecolumn] = csvfiles
    tags = {key: value for key, value in tags.items() if len(value)}

    logger.info("Found tags: %s", str(tags.keys()))
    logger.debug("Tags: %s", str(tags))

    merged_df = merge_csvfiles(csvfiles, tags, memoryconservative=memoryconservative)

    if dropconstantcolumns:
        columnstodelete = []
        for col in merged_df.columns:
            if len(merged_df[col].unique()) == 1:
                columnstodelete.append(col)
        logger.info("Dropping constant columns %s", str(columnstodelete))
        merged_df.drop(columnstodelete, inplace=True, axis=1)

    if merged_df.empty:
        logger.error("No data to output.")
        sys.exit(1)

    logger.info("Final column list: %s", str(merged_df.columns))

    logger.info("Exporting CSV data to %s", output)

    if output in ["-", "stdout"]:
        merged_df.to_csv(sys.stdout, index=False)
    else:
        merged_df.to_csv(path_or_buf=output, index=False)

    logger.info(" - Finished writing to %s", output)


@hook_implementation
def legacy_ertscript_workflow(config):
    """Hook the CsvMerge class into ERT with the name CSV_MERGE,
    and inject documentation"""
    workflow = config.add_workflow(CsvMerge, "CSV_MERGE")
    workflow.parser = get_ertwf_parser
    workflow.description = DESCRIPTION
    workflow.examples = EXAMPLES
    workflow.category = "export"


if __name__ == "__main__":
    main()
