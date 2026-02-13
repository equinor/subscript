"""Extract volumes from Eclipse PRT files, augmenting with region and zone
metadata"""

import argparse
import logging
import re
import warnings
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import res2df
from fmu.tools.fipmapper.fipmapper import FipMapper

from subscript import __version__, getLogger

DESCRIPTION = """
Extract in-place volumes per FIPNUM, or any FIP vector specified, from an
Eclipse PRT file and dump to CSV file. By default the first available BALANCE report
in the PRT file will be used, but any valid date for existing BALANCE report can be
specified. Dates must be in ISO-8601 format (yyyy-mm-dd), or as one of the strings
"first" and "last".

If a yaml file is specified through options, it is possible to add columns
with region and zone information to each FIPNUM. The YAML file must contain
the keys "region2fipnum" and/or "zone2fipnum". A YAML file can only be used together
with FIPNUM, - not with any additional FIP vector.
"""


logger = getLogger(__name__)


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """
    Multiple inheritance used for argparse to get both
    defaults and raw description formatter
    """


def get_parser() -> argparse.ArgumentParser:
    """A parser for command line argument parsing and for documentation."""
    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter, description=DESCRIPTION
    )
    parser.add_argument(
        "DATAfile",
        type=str,
        help="Name of Eclipse or OPM Flow DATA file, PRT file or fileroot",
    )
    parser.add_argument(
        "--outputfilename",
        type=str,
        help="CSV filename to write, including path. Directory must exist.",
        default="simulator_volume_fipnum.csv",  # FMU standard
    )
    parser.add_argument(
        "--fipname",
        type=str,
        help="Specify FIP-name, for an additional FIP vector.",
        default="FIPNUM",
    )
    parser.add_argument(
        "--rename2fipnum",
        action="store_true",
        help="Rename the additional FIP vector to FIPNUM.",
        required=False,
    )
    parser.add_argument(
        "--date",
        # type=lambda d: datetime.strptime(d, "%Y-%m-%d").date(),
        help=(
            "Specify a valid date for existing BALANCE report in the PRT file."
            "The date must be in ISO-8601 format (YYYY-MM-DD) (e.g. 2018-07-01)"
        ),
        required=False,
    )
    parser.add_argument(
        "--yaml",
        "--regions",  # Deprecated option name
        type=str,
        help=(
            "YAML file containing a fipnum2region and/or fipnum2zone dictionary "
            "(or the reverse maps region2fipnum/zone2fipnum)."
        ),
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Be verbose, print the tables"
    )
    parser.add_argument(
        "--dir",
        type=str,
        help=(
            'This option is deprecated and MUST be set to "." for future compatibility.'
        ),
        default=None,
    )
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + __version__ + ")",
    )
    return parser


def prep_output_dir(tablesdir: str | None) -> Path:
    """Ensures an output directory exists, and returns
    the name of the directory.

    This behaviour is deprecated, the user should prepare the directories
    explicitly. If directories are not in place, a FutureWarning is emitted.

    Args:
        tablesdir (str): Directory to create. Default is share/results/volumes.

    Returns:
        str: The directory that was ensured existed.
    """
    if not tablesdir:
        tablesdir = "share/results/volumes/"  # FMU standard
    if not Path(tablesdir).is_dir():
        warnings.warn(
            (
                "Output directories for prtvol2csv should be created upfront. "
                "Later versions will not create directories for you"
            ),
            FutureWarning,
            stacklevel=2,
        )
        Path(tablesdir).mkdir(parents=True)
    return Path(tablesdir)


def find_prtfile(basefile: str) -> str:
    """Convenience for command line execution for locating PRT files.

    Given FOO.DATA and FOO.PRT exists in the current directory, these

        FOO.DATA
        FOO.
        FOO
        FOO.PRT

    will all work to locate FOO.PRT. If no PRT files exists, it will
    not be located and the input is returned.

    Args:
        basefile (str): Filename, or "search string"

    Returns:
        str: A possibly existing file that ends in PRT
    """

    if basefile.endswith(".DATA") and Path(basefile.replace("DATA", "PRT")).is_file():
        prt_file = basefile.replace("DATA", "PRT")
    elif basefile.endswith(".") and Path(basefile + "PRT").is_file():
        prt_file = basefile + "PRT"
    elif (not Path(basefile).is_file()) and Path(basefile + ".PRT").is_file():
        prt_file = basefile + ".PRT"
    else:
        prt_file = basefile

    return prt_file


def find_report_date_in_prt(line: str, find_initial: bool = False) -> date | None:
    """For a line in PRT file, search for a pattern to find a report date.
    Return the corresponding date.

    Args:
        line (str): Line from the PRT file
    Returns:
        datetime.date
    """

    # To find a report in PRT file:
    # Eclipse, Flow: Look for "  REPORT " at start of line (Eclipse: up to REPORT 999)
    date_matcher = re.compile(r"^\s{2}REPORT\s{1}")

    # To find the initial date in PRT file, use different pattern for Eclipse and Flow
    # Eclipse: Look for "  REPORT   0" at start of line
    date_matcher_ecl = re.compile(r"^\s{2}REPORT\s{3}0")
    # Flow: Look for "Report step  0" at start of line
    date_matcher_flow = re.compile(r"^Report step\s{2}0")

    if find_initial:
        # Different pattern for Eclipse and Flow, try Eclipse syntax first
        date_matcher = date_matcher_ecl

    date_object = None
    if date_matcher.search(line) is not None:
        line_split = line.split("*")
        date_string = line_split[0].rstrip().split("  ")[-1]
        # Handle Eclipse dumping out July as JLY instead of JUL
        date_string = date_string.replace("JLY", "JUL")
        date_object = datetime.strptime(date_string, "%d %b %Y").date()

    if find_initial and date_object is None:
        # Try Flow syntax
        date_matcher = date_matcher_flow
        if date_matcher.search(line) is not None:
            line_split = line.split("=")
            date_string = line_split[-1].strip()
            date_object = datetime.strptime(date_string, "%d-%b-%Y").date()
            logger.debug("This is an OPM Flow PRT file\n")
    elif find_initial and date_object is not None:
        logger.debug("This is an Eclipse PRT file\n")

    return date_object


def currently_in_place_from_prt(
    prt_file: str, fipname: str = "FIPNUM", date_str: str | None = None
) -> tuple[pd.DataFrame, np.array, str]:
    """Extracts currently-in-place volumes from a PRT file

    This function uses res2df.fipreports, and slices its
    output for the purpose here.

    Args:
        prt_file (str): Path to a PRT to parse
        fipname (str): FIPNUM, FIPZON or similar.
        date (str): If None or "first", the first date will be used. If not None,
                    "first" or "last", it should be an ISO-formatted date string
                    to extract (YYYY-MM-DD).

    Returns:
        pd.DataFrame, np.array, str
    """
    inplace_df = res2df.fipreports.df(prt_file, fipname=fipname)

    if inplace_df.empty:
        logger.warning("The PRT file %s has no volume report for %s", prt_file, fipname)
        # Then there will be no RESERVOIR VOLUME report either
        return inplace_df, np.array([]), date_str

    available_dates = inplace_df.sort_values("DATE")["DATE"].unique()

    # Available dates as list of strings:
    available_dates_str = [
        date_obj.strftime("%Y-%m-%d") for date_obj in available_dates
    ]
    logger.info(f" Available dates with BALANCE report are:\n{available_dates_str}")

    if date_str is None or date_str == "first":
        date = available_dates[0]
    elif date_str == "last":
        date = available_dates[-1]
    else:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()

        if date not in available_dates:
            logger.error(
                f" The user specified date {date_str} is not available "
                f"with BALANCE report in the PRT file.\n"
                f"Available dates with BALANCE report are:\n{available_dates_str}"
            )
            return inplace_df, np.array([]), date_str

    # Avoid date_str as None
    date_str = str(date)

    # Filter to requested date:
    inplace_df = inplace_df[inplace_df["DATE"] == date]

    # Filter dataframe to only volumes pr. region, not inter-region flows:
    inplace_df = inplace_df[inplace_df["DATATYPE"] == "CURRENTLY IN PLACE"]

    # Cleanup dataframe:
    inplace_df = inplace_df.drop(
        ["DATATYPE", "TO_REGION", "FIPNAME", "DATE"], axis="columns"
    ).set_index("REGION")
    inplace_df.index.name = fipname  # Use "FIPNUM" if not handled by Webviz

    logger.info("Extracted CURRENTLY IN PLACE from %s at date %s", prt_file, date_str)

    # Find the initial date from the PRT file, to compare with date for report extracted
    initial_date_object = None
    find_initial = True
    with Path(prt_file).open(encoding="utf8") as f_handle:
        for line in f_handle:
            initial_date_object = find_report_date_in_prt(line, find_initial)

            if initial_date_object is not None:
                logger.info(
                    f"Initial date is {initial_date_object}, report date is {date_str}"
                )
                break

    if initial_date_object is not None and (date > initial_date_object):
        warnings.warn(
            (
                "The volume report extracted is not at initial time. \n The volume "
                f"report is from {date_str}, which is later than start of simulation "
                f"({initial_date_object})."
            ),
            UserWarning,
            stacklevel=2,
        )
    elif initial_date_object is None:
        warnings.warn(
            ("Cannot determine if volume report is at initial time."),
            UserWarning,
            stacklevel=2,
        )

    return inplace_df, available_dates, date_str


def reservoir_volumes_from_prt(
    prt_file: str,
    dates_bal_report: any,
    fipname: str = "FIPNUM",
    date_str: str | None = None,
) -> pd.DataFrame:
    """Extracts numbers from the table "RESERVOIR VOLUMES" in an Eclipse PRT
    file, example table is::

                                                          ===================================
                                                          :  RESERVOIR VOLUMES      RM3     :
      :---------:---------------:---------------:---------------:---------------:---------------:
      : REGION  :  TOTAL PORE   :  PORE VOLUME  :  PORE VOLUME  : PORE VOLUME   :  PORE VOLUME  :
      :         :   VOLUME      :  CONTAINING   :  CONTAINING   : CONTAINING    :  CONTAINING   :
      :         :               :     OIL       :    WATER      :    GAS        :  HYDRO-CARBON :
      :---------:---------------:---------------:---------------:---------------:---------------:
      :   FIELD :     399202846.:      45224669.:     353978177.:             0.:      45224669.:
      :       1 :      78802733.:      17000359.:      61802374.:             0.:      17000359.:
      :       2 :      79481140.:             0.:      79481140.:             0.:             0.:
      :       3 :      75757104.:      17096867.:      58660238.:             0.:      17096867.:
      :       4 :      74929403.:             0.:      74929403.:             0.:             0.:
      :       5 :      50120783.:      11127443.:      38993340.:             0.:      11127443.:
      :       6 :      40111683.:             0.:      40111683.:             0.:             0.:
      ===========================================================================================

    If no BALANCE report, there will be no RESERVOIR VOLUME report in the PRT file.

    Args:
        prt_file (str): PRT filename

    Returns:
        pd.DataFrame
    """  # noqa: E501

    records = []
    start_matcher = re.compile(r"^\s*:\s*RESERVOIR VOLUMES.*$")

    table_found = (
        False  # State determining if current line is in our interesting table or not.
    )
    # The Reservoir Volume table is not tagged with the "FIPNAME", but will appear
    # after the in-place volume table (see the "BALANCE" report) in the PRT file.
    fipname_found = fipname == "FIPNUM"  # found the corrent fipname, True for FIPNUM

    # Must pick the reservoir volume table corresponding to the date of interest
    date_found = False

    # Get the relevant date in ISO-format, as datetime.date object
    if date_str is None or date_str == "first":
        # Use the first date with BAL report also for res.vol
        wanted_date = dates_bal_report[0]
    elif date_str == "last":
        wanted_date = dates_bal_report[-1]
    else:
        wanted_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    # Eclipse, Flow: Look for "  REPORT " at start of line (Eclipse: up to REPORT 999)
    with Path(prt_file).open(encoding="utf8") as f_handle:
        for line in f_handle:
            # Search PRT file for the date requested:
            date_object = find_report_date_in_prt(line)

            if date_object == wanted_date:
                date_found = True
            if isinstance(date_object, date) and date_object > wanted_date:
                # Next report step (i.e. no Reservoir Volume Report) -> stop search
                date_found = False  # Not neccessary, but to speed up
                break

            # PRT file will have the BAL<nnn> report after the BALANCE report
            if date_found and line.startswith("  " + "BAL" + fipname[3:6]):
                fipname_found = True
                continue
            if date_found and fipname_found and start_matcher.search(line) is not None:
                table_found = True
                continue
            if table_found and line.strip().startswith("======================="):
                # PRT table is finished.
                break
            if table_found:
                # Extract lines with only numbers in between colons
                line_split = [part.strip() for part in line.split(":") if part.strip()]
                if len(line_split) != 6:
                    continue
                try:
                    int(line_split[0])
                except ValueError:
                    # Not the line we are looking for.
                    continue
                records.append(
                    {
                        fipname: int(line_split[0]),
                        "PORV_TOTAL": float(line_split[1]),
                        "HCPV_OIL": float(line_split[2]),
                        "WATPV_TOTAL": float(line_split[3]),
                        "HCPV_GAS": float(line_split[4]),
                        "HCPV_TOTAL": float(line_split[5]),
                    }
                )

    if not records:
        logger.warning(
            "No RESERVOIR VOLUMES table found in PRT file %s at requested date %s",
            prt_file,
            wanted_date,
        )
        logger.warning(
            "Include RPTSOL with FIP=2 (or 3) and 'FIPRESV' in Eclipse DATA file"
        )
        return pd.DataFrame()

    return pd.DataFrame(records).set_index(fipname)


def date_string_format_check(date_str: str) -> bool:
    """Check if a date string is in ISO 8601 format 'YYY-MM-DD'"""

    try:
        datetime.strptime(date_str, "%Y-%m-%d").date()
        return True
    except ValueError:
        err_message = f"'{date_str}' is not in ISO format, - use 'YYYY-MM-DD'."
        logger.error(err_message)
        return False


def main() -> None:
    """Function for command line invocation"""
    args = get_parser().parse_args()

    tablesdir = prep_output_dir(args.dir)

    if args.dir != ".":
        logger.warning(
            "You MUST set the directory option to '.' for future compatibility"
        )

    date_str = args.date
    if date_str in {"first", "last"}:
        pass
    elif date_str:
        # the function should return True if date_str is in ISO 8601 format
        iso_date = date_string_format_check(date_str)
        if not iso_date:
            return

    if args.verbose:
        logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    prt_file = find_prtfile(args.DATAfile)

    if not Path(prt_file).is_file():
        logger.error("PRT-file %s does not exist", prt_file)
        return

    simvolumes_df, available_dates, selected_date = currently_in_place_from_prt(
        prt_file, args.fipname, args.date
    )

    if simvolumes_df.empty:
        return

    simvolumes_df.to_csv(Path(tablesdir) / args.outputfilename)
    logger.info(
        "Written CURRENTLY_IN_PLACE data at %s to %s",
        selected_date,
        Path(tablesdir) / args.outputfilename,
    )

    # Provide array with available dates with BALANCE report as input, for comparison:
    resvolumes_df = reservoir_volumes_from_prt(
        prt_file, available_dates, args.fipname, selected_date
    )

    fipmapper: FipMapper | None
    if args.yaml:
        fipmapper = FipMapper(yamlfile=args.yaml, skipstring="Totals")
        if args.fipname != "FIPNUM":
            logger.error("Cannot use yaml file if fipname is different from FIPNUM")
            return
    else:
        fipmapper = None

    volumes = prtvol2df(
        simvolumes_df,
        resvolumes_df,
        rename2fipnum=args.rename2fipnum,
        fipmapper=fipmapper,
        fipname=args.fipname,
    )

    print(f"Output folder: {Path(tablesdir)}")  # test (lilbe)
    volumes.to_csv(Path(tablesdir) / args.outputfilename)
    logger.info("Written CSV file %s", Path(tablesdir) / args.outputfilename)


def prtvol2df(
    simvolumes_df: pd.DataFrame,
    resvolumes_df: pd.DataFrame,
    fipmapper: FipMapper | None = None,
    fipname: str = "FIPNUM",
    rename2fipnum: bool = False,
) -> pd.DataFrame:
    """
    Concatenate two dataframes (with common index) horizontally,
    and if fipname="FIPNUM", add REGION and ZONE parameter.

    Args:
        simvolumes_df (pd.DataFrame): In-place volumes from PRT (BALANCE report)
        resvolumes_df (pd.DataFrame): Reservoir volumes from PRT (report)

    Returns:
        pd.DataFrame

    """

    # Remove extra empty 'regions' (from the reservoir volume table in .PRT)
    # Concatenate dataframes horizontally. Both are/must be indexed by value
    # of fipname (FIPNUM):

    # Get maximum FIPNUM
    sim_max_fipnum = simvolumes_df.index.max()

    if not resvolumes_df.empty:
        res_max_fipnum = resvolumes_df.loc[(resvolumes_df != 0).any(axis=1)].index.max()
        max_fipnum = max(sim_max_fipnum, res_max_fipnum)
        resvolumes_df = resvolumes_df[:max_fipnum]

    volumes = (
        pd.concat([simvolumes_df, resvolumes_df], axis=1)
        .apply(pd.to_numeric)
        .fillna(value=0.0)
        .sort_index()
    )

    # Rename the index to "FIPNUM", as required by webviz-subsurface, if requested
    if rename2fipnum:
        volumes.index = volumes.index.rename("FIPNUM")
    else:
        volumes.index = volumes.index.rename(fipname)

    # Add new column with the actual FIPNAME, for info and traceability
    volumes["FIPNAME"] = fipname

    if fipmapper is not None:
        if fipmapper.has_fip2region:
            volumes["REGION"] = [
                ",".join(map(str, fipmapper.fip2region(fipnum)))
                for fipnum in volumes.index
            ]
        if fipmapper.has_fip2zone:
            volumes["ZONE"] = [
                ",".join(map(str, fipmapper.fip2zone(fipnum)))
                for fipnum in volumes.index
            ]
    if any(volumes.index < 1):
        logger.warning("%s values should be 1 or larger", fipname)
    return volumes


if __name__ == "__main__":
    main()
