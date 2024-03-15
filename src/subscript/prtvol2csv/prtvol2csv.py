"""Extract volumes from Eclipse PRT files, augmenting with region and zone
metadata"""

import argparse
import logging
import re
import warnings
from pathlib import Path
from typing import Optional

import pandas as pd
import res2df
from fmu.tools.fipmapper.fipmapper import FipMapper

from subscript import __version__, getLogger

DESCRIPTION = """
Extract reservoir volumes pr FIPNUM from Eclipse PRT files and dump to CSV.

If a yaml file is specified through options, it is possible to add columns
with region and zone information to each FIPNUM. The YAML file must contain
the keys "region2fipnum" and/or "zone2fipnum".
"""

CATEGORY = "utility.eclipse"

EXAMPLES = """
.. code-block:: console

  FORWARD_MODEL PRTVOL2CSV(<DATAFILE>=<ECLBASE>, <REGIONS>=regions.yml, <DIR>=., <OUTPUTFILENAME>=simulator_volume_fipnum.csv)

where ``ECLBASE`` is already defined in your ERT config, pointing to the Eclipse
basename relative to ``RUNPATH`` and ``regions.yml`` is a YAML file defining
the map from regions and/or zones to FIPNUM.

Using anything else than "." in the ``DIR`` argument is deprecated. To write to a CSV
file in a specific directory, add the path in the ``OUTPUTFILENAME`` argument.
The directory to export to must exist.
"""  # noqa

logger = getLogger(__name__)


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """
    Multiple inheritance used for argparse to get both
    defaults and raw description formatter
    """

    # pylint: disable=unnecessary-pass


def get_parser() -> argparse.ArgumentParser:
    """A parser for command line argument parsing and for documentation."""
    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter, description=DESCRIPTION
    )
    parser.add_argument("DATAfile", type=str, help="Name of Eclipse DATA file")
    parser.add_argument(
        "--outputfilename",
        type=str,
        help="CSV filename to write, including path. Directory must exist.",
        default="simulator_volume_fipnum.csv",  # FMU standard
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
            'This option is deprecated and MUST be set to "." for future '
            "compatibility."
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


def prep_output_dir(tablesdir: Optional[str], suffix: Optional[str]) -> Path:
    """Ensures an output directory exists, and returns
    the name of the directory.

    This behaviour is deprecated, the user should prepare the directories
    explicitly. If directories are not in place, a FutureWarning is emitted.

    Args:
        tablesdir (str): Directory to create. Default is share/results/volumes.
        suffix (str): If nonempty, added to the results-part in tablesdir.

    Returns:
        str: The directory that was ensured existed.
    """
    if not tablesdir:
        if not suffix or suffix == "":
            tablesdir = "share/results/volumes/"  # FMU standard
        else:
            tablesdir = "share/results-" + suffix + "/volumes"
    if not Path(tablesdir).is_dir():
        warnings.warn(
            (
                "Output directories for prtvol2csv should be created upfront. "
                "Later versions will not create directories for you"
            ),
            FutureWarning,
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


def currently_in_place_from_prt(
    prt_file: str, fipname: str = "FIPNUM", date: Optional[str] = None
) -> pd.DataFrame:
    """Extracts currently-in-place volumes from a PRT file

    This function uses res2df.fipreports, and slices its
    output for the purpose here.

    Args:
        prt_file (str): Path to a PRT to parse
        fipname (str): FIPNUM, FIPZON or similar.
        date (str): If None, first date will be used. If not None,
            it should be an ISO-formatted date string to extract

    Returns:
        pd.DataFrame
    """
    inplace_df = res2df.fipreports.df(prt_file, fipname=fipname)

    available_dates = inplace_df.sort_values("DATE")["DATE"].unique()
    if date is None or date == "first":
        date_str = available_dates[0]
    elif date == "last":
        date_str = available_dates[-1]
    else:
        date_str = str(date)

    # Filter to requested date:
    inplace_df = inplace_df[inplace_df["DATE"] == date_str]

    # Filter dataframe to only volumes pr. region, not inter-region flows:
    inplace_df = inplace_df[inplace_df["DATATYPE"] == "CURRENTLY IN PLACE"]

    # Cleanup dataframe:
    inplace_df.drop(
        ["DATATYPE", "TO_REGION", "FIPNAME", "DATE"], axis="columns", inplace=True
    )
    inplace_df.set_index("REGION", inplace=True)
    inplace_df.index.name = "FIPNUM"

    logger.info("Extracted CURRENTLY IN PLACE from %s at date %s", prt_file, date_str)
    return inplace_df


def reservoir_volumes_from_prt(prt_file: str) -> pd.DataFrame:
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


    Args:
        prt_file (str): PRT filename

    Returns:
        pd.DataFrame
    """  # noqa
    records = []
    start_matcher = re.compile(r"^\s*:\s*RESERVOIR VOLUMES.*$")

    table_found = (
        False  # State determining if current line is in our interesting table or not.
    )
    with Path(prt_file).open(encoding="utf8") as f_handle:
        for line in f_handle:
            if start_matcher.search(line) is not None:
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
                        "FIPNUM": int(line_split[0]),
                        "PORV_TOTAL": float(line_split[1]),
                        "HCPV_OIL": float(line_split[2]),
                        "WATPV_TOTAL": float(line_split[3]),
                        "HCPV_GAS": float(line_split[4]),
                        "HCPV_TOTAL": float(line_split[5]),
                    }
                )

    if not records:
        logger.warning("No RESERVOIR VOLUMES table found in PRT file %s", prt_file)
        logger.warning("Include RPTSOL <newline> FIP=2 'FIPRESV' in Eclipse DATA file")
        return pd.DataFrame()

    return pd.DataFrame(records).set_index("FIPNUM")


def main() -> None:
    """Function for command line invocation"""
    args = get_parser().parse_args()

    tablesdir = prep_output_dir(args.dir, "")

    if args.dir != ".":
        logger.warning(
            "You MUST set the directory option to '.' for future compatibility"
        )

    if args.verbose:
        logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    prt_file = find_prtfile(args.DATAfile)

    if not Path(prt_file).is_file():
        logger.error("PRT-file %s does not exist", prt_file)
        return

    simvolumes_df = currently_in_place_from_prt(prt_file, "FIPNUM")
    simvolumes_df.to_csv(Path(tablesdir) / args.outputfilename)
    logger.info(
        "Written CURRENTLY_IN_PLACE data to %s",
        str(Path(tablesdir) / args.outputfilename),
    )

    resvolumes_df = reservoir_volumes_from_prt(prt_file)

    fipmapper: Optional[FipMapper]
    if args.yaml:
        fipmapper = FipMapper(yamlfile=args.yaml, skipstring="Totals")
    else:
        fipmapper = None

    volumes = prtvol2df(simvolumes_df, resvolumes_df, fipmapper=fipmapper)

    volumes.to_csv(Path(tablesdir) / args.outputfilename)
    logger.info("Written CSV file %s", str(Path(tablesdir) / args.outputfilename))


def prtvol2df(
    simvolumes_df: pd.DataFrame,
    resvolumes_df: pd.DataFrame,
    fipmapper: Optional[FipMapper] = None,
) -> pd.DataFrame:
    """
    Concatenate two dataframes (with common index) horizontally,
    and add REGION and ZONE parameter.
    """
    # Concatenate dataframes horizontally. Both are/must be indexed by FIPNUM:
    volumes = (
        pd.concat([simvolumes_df, resvolumes_df], axis=1)
        .apply(pd.to_numeric)
        .fillna(value=0.0)
    )

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
        logger.warning("FIPNUM values should be 1 or larger")
    return volumes


if __name__ == "__main__":
    main()
