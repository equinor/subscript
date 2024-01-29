import argparse
import io
import logging
import re
from pathlib import Path
from typing import List, Union

import pandas as pd

from subscript import __version__, getLogger as subscriptlogger
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

CATEGORY = "modelling.production"


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """
    Multiple inheritance used for argparse to get both
    defaults and raw description formatter
    """

    # pylint: disable=unnecessary-pass


def get_parser() -> argparse.ArgumentParser:
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
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + __version__ + ")",
    )
    return parser


def cleanse_ofm_lines(filelines: List[str]) -> List[str]:
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
    filelines = list(
        map(str.rstrip, filelines)
    )  # Remove Windows line endings and any whitespace at line end

    # Remove comment lines
    filelines = [line for line in filelines if not line.startswith("--")]
    # Remove empty lines:
    filelines = [line for line in filelines if line != ""]
    # Make everything upper case (not pretty, but simplifies parsing)
    filelines = [line.upper() for line in filelines]
    # OFM sometimes uses the tab character, replace by space to robustify parsing
    return [line.replace("\t", " ") for line in filelines]


def unify_dateformat(lines: List[str]) -> List[str]:
    """Some OFM files have day, month year in separate columns.

    This function catches one variant of this, with day-month-year
    in the first three columns. The column data is string-formatted into
    one column.

    Args:
        lines (list): One string pr. line

    Return:
        list: One string pr. line
    """
    if any(line.startswith("*DAY *MONTH *YEAR") for line in lines):
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


def extract_columnnames(filelines: List[str]) -> List[str]:
    """Look for lines starting with `*DATE`, these signify the columns
    available in the current file being read.

    If multiple lines with this information is found, a ValueError is raised,
    as this is not supported.

    Args:
        filelines: One string pr. line

    Return:
        The column names (strings) that is found, including the first DATE.
        The star prefix for each column is removed.
    """
    columnnamelines = [line for line in filelines if "*DATE" in line]

    if not columnnamelines:
        return []
    if len(columnnamelines) > 1:
        logger.error("Only support files with *DATE occuring once")
        raise ValueError

    return columnnamelines[0].rstrip().replace("*", "").split()


def split_list(linelist: List[str], splitidxs: List[int]) -> List[List[str]]:
    """Split a list of lines into chunks, where each chunck
    is a list of lines with each chunk only containing data for
    one well

    Example::

      split_list(['a', 'b', 'c', 'd', 'e', 'f'], [2,5])

    would return::

      [['a', 'b'], ['c', 'd', 'e'], ['f']]

    Arguments:
        linelis: List to divide into chunks.
        splitidx: Indexes (int) at which to split, the index
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


def find_wellstart_indices(filelines: List[str]) -> List[int]:
    """Locate the indices of the lines that start with the identifier
    for a new well, the string ``*NAME``.

    Args:
        filelines: One string pr. line

    Returns:
        List of integers
    """
    return [i for i in range(len(filelines)) if filelines[i].startswith("*NAME")]


def parse_well(well_lines: List[str], columnnames: List[str]) -> pd.DataFrame:
    """Parse a list of lines with OFM data for only one well
    into a DataFrame

    The list of input strings provided must have been cleaned upfront,
    and only data for a single well should be provided.

    Use extract_columnnames() to find the list of columnnames that
    can be extracted from the lines.

    Args:
        well_lines: One line pr. string
        columnnames: Strings with columnnames to extract.
            Other columns will be ignored.

    Returns:
        Dataframe indexed by WELL and DATE.

    """

    if "*NAME" not in well_lines[0]:
        logger.error("parse_well(), first string must start with *NAME, got:")
        logger.error("%s", well_lines[0])
        raise ValueError
    wellname = well_lines[0].replace("*NAME", "").strip().strip("'").strip('"')

    data = parse_ofmtable(well_lines, columnnames)

    data["WELL"] = wellname.strip("'")  # remove single quotes around wellname
    if not data.empty:
        # pylint: disable=E1101
        # (false positive)
        return data.reset_index().set_index(["WELL", "DATE"]).sort_index()
    return pd.DataFrame()


def parse_ofmtable(
    ofmstring: Union[str, List[str]], columnnames: List[str]
) -> pd.DataFrame:
    """Parse an OFM table from a list of lines, either called once
    pr. well, or all data in one go with wellname as a table column.

    Args:
        ofmstring: OFM data as multiline string or list of strings.
        columnnames: Strings with columnnames to extract.
            Other columns will be ignored.
    """
    if isinstance(ofmstring, list):
        ofmstring = "\n".join(ofmstring)

    assert "DATE" in columnnames

    data = pd.read_table(
        io.StringIO(ofmstring),
        skiprows=1,
        sep=r"\s+",
        names=columnnames,
        on_bad_lines="skip",  # pylint: disable=unexpected-keyword-arg
    )
    data["DATE"] = pd.to_datetime(data["DATE"], dayfirst=True)

    if "WELL" in data and "DATE" in data:
        data = data.set_index(["WELL", "DATE"]).sort_index()
    else:
        # pylint: disable=no-member
        # (false positive)
        data = data.set_index(["DATE"]).sort_index()
    return data


def process_volfile(filename: str) -> pd.DataFrame:
    """Parse a single OFM vol-file and return a DataFrame.

    Args:
        filename: Path to file on disk

    Returns:
        Dataframe indexed by WELL and DATE.
    """
    logger.info("Parsing file %s", filename)
    dframe = process_volstr(Path(filename).read_text(encoding="utf8"))
    if dframe.empty:
        logger.warning("No data extracted from %s", filename)
    return dframe


def process_volstr(volstr: str) -> pd.DataFrame:
    """Parse a volstring (typically a vol-file read into a string with
    newline characters)

    Two different data syntaxes are supported. Either each well
    is given in separate blocks of lines, then there is a ``*NAME`` line
    that gives the well name.

    The alternative syntax has wellname encoded in the table as any other
    parameter, in the ``*WELL`` column.

    Args:
        volstr

    Returns:
        Dataframe indexed by WELL and DATE.
    """
    filelines = unify_dateformat(cleanse_ofm_lines(volstr.split("\n")))

    columnnames = extract_columnnames(filelines)
    if not columnnames:
        raise ValueError("No columns found, one line must contain *DATE")
    logger.info("Columns found: %s", str(columnnames))

    frames = []

    if "WELL" not in columnnames:
        # For the OFM syntax with each well in a separate text block:
        for wellchunk in split_list(filelines, find_wellstart_indices(filelines))[1:]:
            # wellchunk zero does not contain data:            --------->        ^^^^
            frames.append(parse_well(wellchunk, columnnames))
    else:
        # For the OFM syntax with WELL as a table attribute:
        data_start_row = [idx for idx, line in enumerate(filelines) if "WELL" in line][
            0
        ]
        frames.append(parse_ofmtable(filelines[data_start_row:], columnnames))

    if frames:
        return pd.concat(frames, sort=False).sort_index()
    return pd.DataFrame()


def ofmvol2csv_main(
    volfiles: Union[str, List[str]], output: str, includefileorigin: bool = False
) -> None:
    """Convert a set of volfiles (or wildcard patterns) into one CSV file.

    Args:
        volfiles: A string or a list of strings, with filenames and/or
            wildcard patterns.
        output: Filename to write to, in CSV format.
        includefileorigin: Whether to add a column with the originating
            volfile filename for each row of data.
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
