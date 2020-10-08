import logging
import argparse
import re
import io

import pandas as pd

from subscript import getLogger as subscriptlogger
from subscript.eclcompress.eclcompress import glob_patterns

logger = subscriptlogger(__name__)

DESCRIPTION = """Parse output from Oilfield Manager (OFM) (or similar)
containing production data pr. well into one CSV file. Date formats
dd.mm.yyyy and YYYY-MM-DD (recommended) are supported."""

EPILOG = """
Use this to::

  * Do QC and analysis on your historical production in Spotfire
  * Be able to utilize Pandas for production data transformation
    (scaling f.ex) ina history match setting
  * Use Python and Pandas to later generate RMS events from the data,
    after fixing whatever you need to fix

See also the utility csv2ofmvol.
"""

CATEGORY = "modeling.production"


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
    """Construct a parser for the command line utility ofmvol2csv and for
    its documentation"""
    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter, description=DESCRIPTION, epilog=EPILOG
    )
    parser.add_argument(
        "volfiles",
        nargs="+",
        help=("Filenames with volumetric data. Glob-style wildcards are supported"),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="volfiles.csv",
        help="Name of output CSV file",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    parser.add_argument(
        "--includefileorigin",
        action="store_true",
        help=(
            "If this is set, a column named OFMVOLFILE will be added "
            "to identify the source file for each row."
        ),
    )
    return parser


def cleanse_ofm_lines(filelines):
    """Cleanup a list of lines::

      * Remove comment lines
      * Remove empty lines
      * Make everything upper case
      * Replace tabs with spaces

    Args:
        filelines (list): One string pr. line.

    Return:
        list: One string pr. line
    """
    filelines = map(
        str.rstrip, filelines
    )  # Remove Windows line endings and any whitespace at line end

    # Remove comment lines
    filelines = [line for line in filelines if not line.startswith("--")]
    # Remove empty lines:
    filelines = [line for line in filelines if line != ""]
    # Make everything upper case (not pretty, but simplifies parsing)
    filelines = [line.upper() for line in filelines]
    # OFM sometimes uses the tab character, replace by space to robustify parsing
    filelines = [line.replace("\t", " ") for line in filelines]
    return filelines


def unify_dateformat(lines):
    """Some OFM files have day, month year in separate columns.

    This function catches one variant of this, with day-month-year
    in the first three columns. The column data is string-formatted into
    one column.

    Args:
        lines (list): One string pr. line

    Return:
        list: One string pr. line
    """
    if any([line.startswith("*DAY *MONTH *YEAR") for line in lines]):
        # Later: Allow any whitespace between the columns
        lines = [line.replace("*DAY *MONTH *YEAR", "*DATE") for line in lines]
        lines = [
            re.sub(
                r"^([0-9][0-9]) ([0-9][0-9]) ([0-9][0-9][0-9][0-9]) (.*)",
                r"\1.\2.\3 \4",
                line,
            )
            for line in lines
        ]
    return lines


def extract_columnnames(filelines):
    """Look for lines starting with `*DATE`, these signify the columns
    available in the current file being read.

    If multiple lines with this information is found, a ValueError is raised,
    as this is not supported.

    Args:
        filelines (list): One string pr. line

    Return:
        list: The column names (strings) that is found, including the first DATE.
        The star prefix for each column is removed.
    """
    columnnamelines = [x for x in filelines if x.startswith("*DATE")]

    if not columnnamelines:
        return []
    if len(columnnamelines) > 1:
        logger.error("Only support files with *DATE occuring once")
        raise ValueError

    columnnames = columnnamelines[0].rstrip().replace("*", "").split()
    return columnnames


def split_list(linelist, splitidxs):
    """Split a list of lines into chunks, where each chunck
    is a list of lines with each chunk only containing data for
    one well

    Example::

      split_list(['a', 'b', 'c', 'd', 'e', 'f'], [2,5])

    would return::

      [['a', 'b'], ['c', 'd', 'e'], ['f']]

    Arguments:
        linelist (list): List to divide into chunks.
        splitidx (list): Indexes (int) at which to split, the index
            points to the left edge of the resulting chunk. Repeated indices
            are ignored.

    Return:
        list of lists of strings
    """
    # Zip the split indices with a shifted version of itself:
    if not splitidxs:
        return [linelist]
    size = len(linelist)
    zipped = list(
        zip([0] + splitidxs, splitidxs + ([size] if splitidxs[-1] != size else []))
    )
    if not all(i <= j for i, j in zipped):
        raise ValueError("splitidxs must be increasing")
    return [linelist[i:j] for i, j in zipped if linelist[i:j]]


def find_wellstart_indices(filelines):
    """Locate the indices of the lines that start with the identifier
    for a new well, the string ``*NAME``.

    Args:
        filelines (list): One string pr. line

    Returns:
        list: List of integers
    """
    wellnamelinenumbers = [
        i for i in range(0, len(filelines)) if filelines[i].startswith("*NAME")
    ]
    return wellnamelinenumbers


def parse_well(well_lines, columnnames):
    """Parse a list of lines with OFM data for only one well
    into a DataFrame

    The list of input strings provided must have been cleaned upfront,
    and only data for a single well should be provided.

    Use extract_columnnames() to find the list of columnnames that
    can be extracted from the lines.

    Args:
        well_lines (list): One line pr. string
        columnnames (list): Strings with columnnames to extract.
            Other columns will be ignored.

    Returns:
        pd.DataFrame

    """

    if "*NAME" not in well_lines[0]:
        logger.error("parse_well(), first string must start with *NAME, got:")
        logger.error("%s", well_lines[0])
        raise ValueError
    wellname = well_lines[0].replace("*NAME", "").strip().strip("'").strip('"')

    stringbuf = io.StringIO()
    stringbuf.write("\n".join(well_lines))
    stringbuf.seek(0)
    data = pd.read_table(
        stringbuf,
        engine="c",
        skiprows=1,
        sep=r"\s+",
        names=columnnames,
        parse_dates=[0],
        error_bad_lines=False,
    )
    data["WELL"] = wellname.strip("'")  # remove single quotes around wellname
    data = data.set_index(["WELL", "DATE"]).sort_index()
    return data


def process_volfile(filename):
    """Parse a single OFM vol-file and return a DataFrame.

    Args:
        filename (str): Path to file on disk

    Returns:
        pd.DataFrame
    """
    logger.info("Parsing file %s", filename)
    with open(filename) as file_h:
        volstr = "\n".join(file_h.readlines())
    dframe = process_volstr(volstr)
    if dframe.empty:
        logger.warning("No data extracted from %s", filename)
    return dframe


def process_volstr(volstr):
    """Parse a volstring (typically a vol-file read into a string with
    newline characters)

    Args:
        volstr (str)

    Returns:
        pd.DataFrame
    """
    filelines = unify_dateformat(cleanse_ofm_lines(volstr.split("\n")))

    columnnames = extract_columnnames(filelines)
    logger.info("Columns found: %s", str(columnnames))

    wellframes = []
    for wellchunk in split_list(filelines, find_wellstart_indices(filelines)):
        if any([line.startswith("*NAME") for line in wellchunk]):
            wellframe = parse_well(wellchunk, columnnames)
            if not wellframe.empty:
                wellframes.append(wellframe)
        else:
            logger.info("No NAME found in chunk, probably the very first.")
    if wellframes:
        return pd.concat(wellframes, sort=False).sort_index()
    return pd.DataFrame()


def ofmvol2csv_main(volfiles, output, includefileorigin=False):
    """Convert a set of volfiles (or wildcard patterns) into one CSV file.

    Args:
        volfiles (list): A string or a list of strings, with filenames and/or
            wildcard patterns.
        output (str): Filename to write to, in CSV format.
        includefileorigin (bool): Whether to add a column with the originating
            volfile filename for each row of data.

    Returns:
        None
    """
    if isinstance(volfiles, str):
        volfiles = [volfiles]

    globbed = glob_patterns(volfiles)
    if set(globbed) != set(volfiles):
        logger.info("Wildcards expanded to: %s", str(globbed))
    dframes = []
    if not globbed:
        logger.warning("Filename(s) %s not found", str(volfiles))
        return
    for filename in globbed:
        dframe = process_volfile(filename)
        if includefileorigin:
            dframe["OFMVOLFILE"] = filename
        if not dframe.empty:
            dframes.append(dframe)
    if dframes:
        alldata = pd.concat(dframes, sort=False).sort_index()
        alldata.to_csv(output)
        logger.info("Wrote %s rows to %s", str(len(alldata)), output)
    else:
        logger.warning("No data was extracted")


def main():
    """Entry point if called from command line"""
    args = get_parser().parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)

    ofmvol2csv_main(
        args.volfiles,
        args.output,
        includefileorigin=args.includefileorigin,
    )


if __name__ == "__main__":
    main()
