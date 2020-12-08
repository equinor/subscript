import re
import argparse
import logging
from pathlib import Path

import yaml
import pandas as pd

import ecl2df

from subscript import getLogger

DESCRIPTION = """
Extract reservoir volumes from Eclipse PRT files, dump to CSV.

The data from the ascii table "FIELD TOTALS" will be parsed at
initial time step (day 0), and if found, the table called
"RESERVOIR VOLUMES". The latter table will only be written
by Eclipse if you have::

  RPTSOL
    FIP=2 'FIPRESV' /

You can supply a region2fipnum data structure in a YAML-file
which will cause a secondary CSV file to be generated, where
fipnum data are summed up to user specified regions.
"""

CATEGORY = "utility.eclipse"

EXAMPLES = """
.. code-block:: console

  FORWARD_MODEL PRTVOL2CSV(<DATAFILE>=<ECLBASE>)

where ``ECLBASE`` is already defined in your ERT config, pointing to the Eclipse
basename relative to ``RUNPATH``.
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

    pass


def get_parser():
    """A parser for command line argument parsing and for documentation."""
    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter, description=DESCRIPTION
    )
    parser.add_argument("DATAfile", type=str, help="Name of Eclipse DATA file")
    parser.add_argument(
        "--suffix", type=str, help="Resultdirectory suffix.", default=""
    )
    parser.add_argument(
        "--dir",
        type=str,
        help=(
            "Output directory. Default is FMU standard, "
            "share/results/volumes. "
            "Will be created if necessary."
        ),
        default=None,
    )
    parser.add_argument(
        "--outputfilename",
        type=str,
        help="Output filename in result directory",
        default="simulator_volume_fipnum.csv",  # FMU standard
    )
    parser.add_argument(
        "--regionoutputfilename",
        type=str,
        help="Filename for regrouped region volume output",
        default="simulator_volume_region.csv",
    )
    parser.add_argument(
        "--regions", type=str, help="YAML file containing a fipnum2region dictionary"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Be verbose, print the tables"
    )
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    return parser


def prep_output_dir(tablesdir=None, suffix=None):
    """Ensures an output directory exists, and returns
    the name of the directory."""
    if not tablesdir:
        if not suffix or suffix == "":
            tablesdir = "share/results/volumes/"  # FMU standard
        else:
            tablesdir = "share/results-" + suffix + "/volumes"
    if not Path(tablesdir).is_dir():
        Path(tablesdir).mkdir(parents=True)
    return tablesdir


def find_prtfile(basefile):
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


def currently_in_place_from_prt(prt_file, fipname="FIPNUM", date=None):
    """Extracts currently-in-place volumes from a PRT file

    This function uses ecl2df.fipreports, and slices its
    output for the purpose here.

    Args:
        prt_file (str): Path to a PRT to parse
        fipname (str): FIPNUM, FIPZON or similar.
        date (str): If None, first date will be used. If not None,
            it should be an ISO-formatted date string to extract

    Returns:
        pd.DataFrame
    """
    inplace_df = ecl2df.fipreports.df(prt_file, fipname=fipname)

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


def reservoir_volumes_from_prt(prt_file):
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
    with Path(prt_file).open() as f_handle:
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
                        "WATER_PORV": float(line_split[3]),
                        "HCPV_GAS": float(line_split[4]),
                        "HCPV_TOTAL": float(line_split[5]),
                    }
                )
    if not records:
        logger.warning("No RESERVOIR VOLUMES table found in PRT file %s", prt_file)
        logger.warning("Include RPTSOL <newline> FIP=2 'FIPRESV' in Eclipse DATA file")
        return pd.DataFrame()

    return pd.DataFrame(records).set_index("FIPNUM")


def main():
    """Function for command line invocation"""
    args = get_parser().parse_args()

    tablesdir = prep_output_dir(args.dir, args.suffix)

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

    ######################################################################
    # Merge output
    volumes = pd.concat([simvolumes_df, resvolumes_df], axis=1).fillna(value=0.0)

    ######################################################################
    #
    # Look for a REGION definition in some yaml-file
    # FIPNUM is always at a finer or equal scale as REGION
    # FIPNUM to REGION can be a many-to-many mapping
    # (sums over all REGIONs are thus not always meaningful)
    # The map is specified with REGION as the index, containing a list over FIPNUMs
    #
    # Yaml-file:
    # region2fipnum:
    #    'RegionA' : [1,4,6]
    #    'RegionB' : [2,5]
    #    'FormationA' : [1,2]
    #    'Totals' : [1,2,3,4,5,6]
    #
    # The FIPNUM-indexed table is augmented with a REGION-column,
    # containing space-separated list of referenced REGIONs
    # The REGION-indexed table is augmented with a FIPNUM-column,
    # containing space-separated list of referenced FIPNUMs

    volumesbyregions = None
    if args.regions:
        reg2fip = None
        with open(args.regions, "r") as yamlfile:
            reg2fip = yaml.safe_load(yamlfile)
        if reg2fip and "region2fipnum" in reg2fip:
            reg2fipmap = reg2fip["region2fipnum"]
            # Ensure all dictonary keys (region names) are strings:
            reg2fipmap = {str(key): value for key, value in reg2fipmap.items()}
            # Invert the dictionary of lists, as we alse need to map
            # from fipnum to region:
            fip2regmap = {}
            for reg in reg2fipmap:
                for fip in reg2fipmap[reg]:
                    if fip not in fip2regmap:
                        fip2regmap[fip] = []
                    fip2regmap[fip].append(reg)

            # Now make a REGION-indexed dataframe, with summed volumes
            # from the involved FIPNUMs
            volumesbyregions = {}
            for reg in reg2fipmap:
                volumesbyregions[reg] = pd.DataFrame(
                    volumes.loc[reg2fipmap[reg]].sum()
                ).transpose()
                # Space separated list of fipnums involved in this region
                volumesbyregions[reg]["FIPNUM"] = " ".join(map(str, reg2fipmap[reg]))
            volumesbyregions = (
                pd.concat(volumesbyregions)
                .reset_index()
                .drop("level_1", axis=1)
                .set_index("level_0")
            )
            volumesbyregions.index.name = "REGION"

            # Also tag the FIPNUM-indexed dataframe with the regions
            # that are involved in a FIPNUM, space-separated
            for fip in fip2regmap:
                volumes.loc[fip, "REGION"] = " ".join(map(str, fip2regmap[fip]))

        else:
            print("Warning: Could not parse yaml file. No region index can be made")

    if args.verbose:
        print(volumes)
    volumes.to_csv(Path(tablesdir) / args.outputfilename)
    print("Written CSV file " + str(Path(tablesdir) / args.outputfilename))

    if volumesbyregions is not None:
        if args.verbose:
            print(volumesbyregions)
        volumesbyregions.to_csv(Path(tablesdir) / args.regionoutputfilename)
        print("Written CSV file " + str(Path(tablesdir) / args.regionoutputfilename))


if __name__ == "__main__":
    main()
