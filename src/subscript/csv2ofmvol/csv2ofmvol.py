import sys
import datetime
from dateutil.relativedelta import relativedelta
import argparse
import pandas as pd

DESCRIPTION = "Convert CSV files with production data to OFM vol-format"

EPILOG = """The indented usage is to process CSV files outputted from the pyPDM
library (possibly from the script 'export_production_data') and then
convert this back to OFM (OilField Manager) "vol"-format, which gives
the easiest route into Roxar's RMS, through a Production Profile
Import job.

Example input CSV data::

    DATE,WELL,WOPR
    2010-01-01,A-3,1000
    2011-01-01,A-3,2000
    2012-01-01,A-3,3000

which will produce the following vol-file output::

  *METRIC
  *DAILY
  *DATE   *OIL
  *NAME A-3
  2010-01-01  1000
  2011-01-01  2000
  2012-01-01  3000

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
SUPPORTED_COLS = SUPPORTED_VOLCOLS + ["DAYS"]


def read_pdm_csv_files(csvfiles):
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

    if not isinstance(csvfiles, list):
        csvfiles = [csvfiles]

    # Make list of dataframes:
    dataframes = []
    for item in csvfiles:
        if isinstance(item, pd.DataFrame):
            dataframes.append(item)
        elif isinstance(item, str):
            dataframes.append(pd.read_csv(item, low_memory=False))
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

    # Should we enforce only upper case columns as well?

    # Drop duplicate multiindices (WELL, DATE)
    origlen = len(data)
    data = data[~data.index.duplicated(keep="first")]
    if origlen != len(data):
        print(" ** Warning **: Duplicate data detected. Ignoring duplicates")
    return data.sort_index()


def check_consecutive_dates(data):
    """Verify that every day is present from the first to the last for every well"""
    for well in data.index.levels[0]:
        welldata = data.loc[well].reset_index()
        welldata["DATE"] = pd.to_datetime(welldata["DATE"])
        welldata["datediff"] = welldata["DATE"].diff()

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
            print("")
            print(
                "Warning: Uneven date intervals for well "
                + well
                + ", potentially check this data:"
            )
            print(checkrows)
        if int(datedeltas[0]) != 1:
            print("Warning: Dates are not daily-consecutive for well " + well)
            print("         Most common timedelta is: " + str(dominantdelta))

    return True


def df2vol(data):
    """Convert a DataFrame to a multiline string in vol-format.

    The 'tab' character is used as a field separator in this format
    """
    volcolumns = []
    for colname in data.columns.values:
        if colname in SUPPORTED_COLS:
            volcolumns.append(colname)
        elif colname in PDMCOLS2VOL:
            volcolumns.append(PDMCOLS2VOL[colname])
        else:
            print("Warning: Unsupported column " + str(colname))
    voldata = data.copy()
    voldata.columns = volcolumns
    for col in voldata.columns:
        if col not in SUPPORTED_COLS:
            del voldata[col]
    volstr = ""
    volstr += "*METRIC\n"
    volstr += "*DAILY\n"
    if "DAYS" in voldata.columns:
        volstr += "*HRS_IN_DAYS\n"
    volstr += "*DATE\t*" + "\t*".join(voldata.columns) + "\n"
    for well in voldata.index.levels[0]:
        volstr += "*NAME " + well + "\n"
        volstr += voldata.loc[well].to_csv(sep="\t", header=None)
    return volstr


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """
    Multiple inheritance used for argparse to get both
    defaults and raw description formatter
    """

    pass


def get_parser():
    """Parse command line arguments, return a Namespace with arguments"""
    parser = argparse.ArgumentParser(
        description=DESCRIPTION, epilog=EPILOG, formatter_class=CustomFormatter
    )
    parser.add_argument("csvfiles", nargs="+", help="CSV files with data")
    parser.add_argument("-o", "--output", type=str, default="pdm_data.vol")
    return parser


def main():
    """Entry point if called from command line"""
    args = get_parser().parse_args()

    print("Input files: {}".format(" ".join(args.csvfiles)))
    data = read_pdm_csv_files(args.csvfiles)

    if not check_consecutive_dates(data):
        # The called subroutine will print relevant error messages
        sys.exit(1)

    # Convert dataframes to a multiline string:
    volstr = df2vol(data)

    with open(args.output, "w") as outfile:
        outfile.write(
            "-- Data printed by csv2ofmvol at " + str(datetime.datetime.now()) + "\n"
        )
        outfile.write("-- Input files: " + str(args.csvfiles) + "\n")
        outfile.write("\n")
        outfile.write(volstr)
    print("Well count: " + str(len(data.index.levels[0])))
    print("Date count: " + str(len(data.index.levels[1])))
    startdate = data.index.levels[1].min()
    enddate = data.index.levels[1].max()
    delta = relativedelta(enddate, startdate)
    print("Date range: " + str(startdate.date()) + " --> " + str(enddate.date()))
    print(
        "            "
        + str(delta.years)
        + " years, "
        + str(delta.months)
        + " months, "
        + str(delta.days)
        + " days."
    )
    print("Written " + str(len(volstr) + 3) + " lines to " + args.output)


if __name__ == "__main__":
    main()
