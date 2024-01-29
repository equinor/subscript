import argparse
import datetime
import logging
import sys
from typing import List, Union

import pandas as pd
from dateutil.relativedelta import relativedelta

from subscript import __version__, getLogger as subscriptlogger
from subscript.eclcompress.eclcompress import glob_patterns

logger = subscriptlogger(__name__)

DESCRIPTION = "Convert CSV files with production data to OFM vol-format"

CATEGORY = "modelling.production"

EPILOG = """The indented usage is to process CSV files outputted from the pyPDM
library (possibly from the script 'export_production_data') and then
convert this back to OFM (OilField Manager) "vol"-format, which gives
the easiest route into Roxar's RMS, through a Production Profile
Import job.

Example input CSV data::

    DATE,       WELL, WOPR
    2010-01-01, A-3,  1000
    2011-01-01, A-3,  2000
    2012-01-01, A-3,  3000

which will produce the following vol-file output::

  *METRIC
  *DAILY
  *DATE   *OIL
  *NAME A-3
  2010-01-01  1000
  2011-01-01  2000
  2012-01-01  3000

In order to import such a file into RMS, select "OilField Manager text", and ensure
you set the date format to yyyy-MM-dd (ISO-8601).

See also the ofmvol2csv utility.
"""

# Translation table from what vectors are called in PDM to
# what the OFM vol-fileformat expects.
PDMCOLS2VOL = {
    "WOPR": "OIL",
    "WGPR": "GAS",
    "WWPR": "WATER",
    "WGIR": "GINJ",
    "WWIR": "WINJ",
    "WBHP": "BHP",
    "WTHP": "THP",
    "WEFF": "WEFF",
    "WOPT": "WOPT",
    "WGPT": "WGPT",
    "WWPT": "WWPT",
    "WGIT": "WGIT",
    "WWIT": "WWIT",
}

# But we only output these columns in vol-files:
SUPPORTED_VOLCOLS = ["OIL", "GAS", "WATER", "GINJ", "WINJ", "BHP", "THP"]
SUPPORTED_DAYCOLS = ["DAYS", "GIDAY", "WIDAY"]
SUPPORTED_COLS = SUPPORTED_VOLCOLS + SUPPORTED_DAYCOLS


def read_pdm_csv_files(
    csvfiles: Union[pd.DataFrame, str, List[str], List[pd.DataFrame]],
) -> pd.DataFrame:
    """Read a list of CSV files and return a dataframe

    If the CSV files does not look like data from PDM,
    a ValueError will be thrown.

    If multiple files, all will be loaded and merged into
    the same dataframe. If index duplicates, the last is kept
    and a warning is printed.

    Args:
        csvfiles: list of strings of filepaths to CSV files,
            or list of DataFrames for which read_csv() has
            been done.

    Returns:
        pd.DataFrame: Multiindex over (DATE, WELL), and data
        vectors, WOPR, WWCT, etc.
    """

    if isinstance(csvfiles, str):
        csvfiles = [csvfiles]

    if isinstance(csvfiles, pd.DataFrame):
        csvfiles = [csvfiles]

    dataframes = []
    for item in csvfiles:
        if isinstance(item, pd.DataFrame):
            dataframes.append(item)
        elif isinstance(item, str):
            dataframes.append(pd.read_csv(item))
        else:
            raise ValueError("Only list of str or dataframes supported")
    data = pd.concat(dataframes, ignore_index=True, sort=False)

    if "WELL" not in data:
        raise ValueError("WELL not found in dataset")
    if "DATE" not in data:
        raise ValueError("DATE not found in dataset")

    # Use datetime object for DATE column
    data["DATE"] = pd.to_datetime(data["DATE"])

    # Reindex:
    data = data.set_index(["WELL", "DATE"])

    if not [data.columns.values]:
        raise ValueError("No data columns found")

    # Drop duplicate multiindices (WELL, DATE)
    origlen = len(data)
    data = data[~data.index.duplicated(keep="first")]
    if origlen != len(data):
        logger.warning("Duplicate data detected. Ignoring duplicates")
    return data.sort_index()


def check_consecutive_dates(data: pd.DataFrame) -> None:
    """Analyse consecutiveness in dates pr. well.

    Determines the  most common timedelta pr. datapoint, and warns
    if there are exceptions and production/injection is nonzero.

    Output is written using logger.warning().

    Args:
        data (pd.DataFrame): Data with production, multiindex where
            WELL is first index, and DATE is second. The DATE index
            can be either a DateTimeIndex, or it will be converted to such.

    Returns:
        None
    """
    for well in data.index.levels[0]:
        welldata = data.loc[well].reset_index()
        welldata["DATE"] = pd.to_datetime(welldata["DATE"])
        welldata["datediff"] = welldata["DATE"].diff()
        if len(welldata) < 2:
            continue

        # Determine most common date diff (typically one day)
        # which will be like this in Python: Timedelta('1 days 00:00:00')
        dominantdelta = (
            welldata.groupby("datediff").count().sort_values("DATE").index[-1]
        )

        # List the dates where dates are missing prior to these:
        checkrows = welldata.dropna(axis="rows", subset=["datediff"]).loc[
            welldata["datediff"] != dominantdelta
        ]

        datedeltas = (
            pd.to_datetime(data.loc[well].reset_index()["DATE"])
            .diff()
            .dt.days.dropna()
            .unique()
        )
        datedeltas.sort()
        # Do we have nonzero production/injections in the rows with non-uniform dates?
        ratecols = [
            x for x in checkrows.columns if x.endswith("R") and x.startswith("W")
        ]
        checkprod = (
            checkrows[ratecols].dropna(axis="columns").astype("float").abs().sum().sum()
        )
        if len(datedeltas) > 1 and checkprod > 0.1:
            logger.warning(
                "Warning: Uneven date intervals for well %s, check these rows:\n%s",
                str(well),
                str(checkrows),
            )
        if int(datedeltas[0]) != 1:
            logger.warning("Dates are not daily-consecutive for well %s", str(well))
            logger.warning("Most common timedelta is: %s", str(dominantdelta))


def df2vol(data: pd.DataFrame) -> str:
    """Convert a DataFrame to a multiline string in vol-format.

    The 'tab' character is used as a field separator in this format

    Args:
        data (pd.DataFrame): Production data, indexed by [WELL, DATE].
            Unsupported columns will be ignored.

    Returns:
        str: multiline, in "OFM vol"-format.
    """

    # Apply column name translation for a subset of the incoming column names
    columns_trans = [PDMCOLS2VOL.get(colname, colname) for colname in data.columns]

    # Filter to only the supported columns:
    columns = [colname for colname in columns_trans if colname in SUPPORTED_COLS]

    if not columns:
        raise ValueError("No supported data columns provided")

    unsupported = set(columns_trans) - set(columns)
    if unsupported:
        logger.warning("Unsupported column(s) %s", str(unsupported))

    # Translate column names:
    voldata = data.rename(columns=PDMCOLS2VOL, inplace=False)

    # Drop non-supported columns:
    voldata = voldata[columns]

    # Fill empty cells with zeros, empty cells can stem from concatenation
    # of dataframes with gas and water injectors.
    voldata.fillna(value=0.0, inplace=True)

    volstr = ""
    volstr += "*METRIC\n"
    volstr += "*DAILY\n"
    if any(colname in SUPPORTED_DAYCOLS for colname in voldata.columns):
        volstr += "*HRS_IN_DAYS\n"
    volstr += "*DATE *" + " *".join(voldata.columns)
    if not voldata.empty:
        for well in voldata.index.levels[0]:
            volstr += f"\n\n*NAME {well}\n"
            volstr += voldata.loc[well].to_string(header=False, index_names=False)
    else:
        logger.warning("No data, only header written")
    return volstr


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """
    Multiple inheritance used for argparse to get both
    defaults and raw description formatter
    """

    # pylint: disable=unnecessary-pass


def get_parser() -> argparse.ArgumentParser:
    """Parse command line arguments, return a Namespace with arguments"""
    parser = argparse.ArgumentParser(
        description=DESCRIPTION, epilog=EPILOG, formatter_class=CustomFormatter
    )
    parser.add_argument("csvfiles", nargs="+", help="CSV files with data")
    parser.add_argument("-o", "--output", type=str, default="pdm_data.vol")
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + __version__ + ")",
    )
    return parser


def csv2ofmvol_main(csvfilepatterns: List[str], output: str) -> bool:
    """Convert a list of CSV files into one OFM vol-file.

    Arguments:
        csvfilepatterns (list):  strings of filenames or filename wildcards. Can also
            be a single string.
        output (str): Filename to write to.

    Returns:
        bool: True if successful
    """

    if isinstance(csvfilepatterns, str):
        csvfilepatterns = [csvfilepatterns]

    csvfiles = glob_patterns(csvfilepatterns)
    if set(csvfiles) != set(csvfilepatterns):
        logger.info("Wildcards used: %s", str(csvfilepatterns))
    if not csvfiles:
        logger.error("No filenames found")
        return False

    logger.info("Input files: %s", " ".join(csvfiles))

    data = read_pdm_csv_files(csvfiles)

    # Print warnings for suspicious data. Perhaps we should fail but difficult
    # to ascertain how downstream tools will react.
    check_consecutive_dates(data)

    # Convert dataframes to a multiline string:
    volstr = df2vol(data)

    with open(output, "w", encoding="utf8") as outfile:
        outfile.write(f"-- Data printed by csv2ofmvol at {datetime.datetime.now()}\n")
        outfile.write(f"-- Input files: {csvfiles}\n\n")
        outfile.write(volstr)
    logger.info("Well count: %s", str(len(data.index.levels[0])))
    logger.info("Date count: %s", str(len(data.index.levels[1])))

    if len(data) > 1:
        startdate = data.index.levels[1].min()
        enddate = data.index.levels[1].max()
        delta = relativedelta(enddate, startdate)
        logger.info("Date range: %s --> %s", str(startdate.date()), str(enddate.date()))
        logger.info(
            "            %s years, %s months, %s days.",
            str(delta.years),
            str(delta.months),
            str(delta.days),
        )
    logger.info("Written %s lines to %s.", str(len(volstr) + 3), output)
    return True


def main():
    """Entry point if called from command line"""
    args = get_parser().parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)

    returncode = csv2ofmvol_main(args.csvfiles, args.output)

    if not returncode:
        sys.exit(1)


if __name__ == "__main__":
    main()
