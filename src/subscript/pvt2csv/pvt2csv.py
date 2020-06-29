"""
Parses Eclipse 100 PVT input files into CSV files suitable
for analysis in Pandas and/or Spotfire

This script is doing Python-only text parsing of the Eclipse 100 file
and is very UNLIKELY to support all PVT files that E100 actually would
accept.
"""
from __future__ import print_function

import re
import argparse

import pandas

COLUMNNAMES = {
    "DENSITY": ["PVTNUM", "OILDENSITY", "WATERDENSITY", "GASDENSITY"],
    "PVTW": [
        "PVTNUM",
        "PRESSURE",
        "VOLUMEFACTOR",
        "COMPRESSIBILITY",
        "VISCOSITY",
        "VISCOSIBILITY",
    ],
    "PVTO": ["PVTNUM", "GOR", "PRESSURE", "VOLUMEFACTOR", "VISCOSITY"],
    "PVTG": ["PVTNUM", "PRESSURE", "RV", "VOLUMEFACTOR", "VISCOSITY"],
    "PVDG": ["PVTNUM", "PRESSURE", "VOLUMEFACTOR", "VISCOSITY"],
    "ROCK": ["PVTNUM", "PRESSURE", "COMPRESSIBILITY"],
}


def get_parser():
    """Set up parser for command line utility"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("PVTFILES", nargs="+", help="PVT files containing PVT keywords")
    parser.add_argument(
        "-o", "--output", type=str, help="name of output csv file", default="pvt.csv"
    )
    return parser


# Used for parsing, to check if a string can be parsed as a floating point number
def is_number(numberstring):
    """Determine if a string can be parsed as a floating point number

    Returns:
       bool - true if float(numberstring) would not throw an exception
    """
    try:
        float(numberstring)
        return True
    except ValueError:
        return False


def main():
    """Process command line arguments"""
    parser = get_parser()
    args = parser.parse_args()

    print("WARNING: This tool is deprecated. Use 'ecl2csv pvt' instead")

    tables_each_file = []
    for filename in args.PVTFILES:
        print(" ** Parsing {}".format(filename))
        tables_each_file.append(pvtfile2df(filename))
    allfiles_df = pandas.concat(tables_each_file)
    allfiles_df.to_csv(args.output, index=False)


def pvtfile2df(filename):
    """Convert a text file into a dataframe with PVT information

    Multiple PVT keywords are merged into one dataframe, with padding for
    not-applicable cells.

    Args:
        filename (str) - filename to be opened and parsed.

    Returns:
        pd.DataFrame
    """
    lines = open(filename).readlines()

    # Strip newlines, comments and empty lines:
    lines = [x.strip() for x in lines]
    lines = [x.split("--")[0] for x in lines]
    lines = [x for x in lines if x != ""]

    # Now we go through the file with a state machine holding which keyword is active

    active_ecl_keyword = ""
    current_gor = 0
    current_pg = 0

    density_df = pandas.DataFrame(columns=COLUMNNAMES["DENSITY"])
    pvtw_df = pandas.DataFrame(columns=COLUMNNAMES["PVTW"])
    pvto_df = pandas.DataFrame(columns=COLUMNNAMES["PVTO"])
    pvtg_df = pandas.DataFrame(columns=COLUMNNAMES["PVTG"])
    pvdg_df = pandas.DataFrame(columns=COLUMNNAMES["PVDG"])
    rock_df = pandas.DataFrame(columns=COLUMNNAMES["ROCK"])

    ecl_keyword_re = re.compile(r"^[A-Z]+\s*.*")
    for line in lines:

        # Changing to next keyword?
        if ecl_keyword_re.match(line):
            active_ecl_keyword = line.split(" ")[0]
            current_pvtnum = 1
            continue  # Hope user has not written more data on the keyword line.

        if active_ecl_keyword == "DENSITY":
            # Check if we have a record with three numbers:
            if (
                list(map(is_number, line.split()[0:3])) == [True, True, True]
                and line.split()[3] == "/"
            ):
                density_df.loc[len(density_df) + 1] = [current_pvtnum] + list(
                    map(float, line.split()[0:3])
                )
                current_pvtnum += 1
                # If we forget this continue, the script will think we
                # did not understand the keyword
                continue

        if active_ecl_keyword == "PVTW":
            if (
                list(map(is_number, line.split()[0:5]))
                == [True, True, True, True, True]
                and line.split()[5] == "/"
            ):
                pvtw_df.loc[len(pvtw_df) + 1] = [current_pvtnum] + list(
                    map(float, line.split()[0:5])
                )
                current_pvtnum += 1
                continue

            # Item 5 (dCw - viscosibility) is sometimes skipped, then
            # it is defaulted to zero.
            if (
                list(map(is_number, line.split()[0:4])) == [True, True, True, True]
                and line.split()[4] == "/"
            ):
                pvtw_df.loc[len(pvtw_df) + 1] = (
                    [current_pvtnum] + list(map(float, line.split()[0:4])) + [0.0]
                )
                current_pvtnum += 1
                continue

        if active_ecl_keyword == "PVTO":
            # Special consideration for undersaturated oil must be done.

            # 4 numbers on a line is a new GOR.
            if list(map(is_number, line.split()[0:4])) == [True, True, True, True]:
                current_gor = float(line.split()[0])
                pvto_df.loc[len(pvto_df) + 1] = [current_pvtnum] + list(
                    map(float, line.split()[0:4])
                )
                continue

            # 3 numbers and trailing slash or not means to use the
            # current_gor (undersaturated line)
            if list(map(is_number, line.split()[0:3])) == [True, True, True]:
                pvto_df.loc[len(pvto_df) + 1] = [current_pvtnum, current_gor] + list(
                    map(float, line.split()[0:3])
                )
                continue

        # Single slash means go to the next PVTNUM
        if line.split()[0] == "/":
            current_pvtnum += 1
            continue

        if active_ecl_keyword == "PVTG":
            # Special consideration for undersaturated oil must be done.

            # 4 numbers is a new GOR
            if list(map(is_number, line.split()[0:4])) == [True, True, True, True]:
                current_pg = float(line.split()[0])
                pvtg_df.loc[len(pvtg_df) + 1] = [current_pvtnum] + list(
                    map(float, line.split()[0:4])
                )
                continue

            # 3 numbers and trailing slash or not means to use the
            # current_gor (undersaturated line)
            if list(map(is_number, line.split()[0:3])) == [True, True, True]:
                pvtg_df.loc[len(pvtg_df) + 1] = [current_pvtnum, current_pg] + list(
                    map(float, line.split()[0:3])
                )
                continue

        if active_ecl_keyword == "PVDG":
            # 3 numbers and no trailing slash
            if list(map(is_number, line.split()[0:3])) == [True, True, True]:
                pvdg_df.loc[len(pvdg_df) + 1] = [current_pvtnum] + list(
                    map(float, line.split()[0:3])
                )
                continue

        if active_ecl_keyword == "ROCK":
            # 2 numbers and trailing slash
            if (
                list(map(is_number, line.split()[0:2])) == [True, True]
                and line.split()[2] == "/"
            ):
                rock_df.loc[len(rock_df) + 1] = [current_pvtnum] + list(
                    map(float, line.split()[0:2])
                )
                current_pvtnum += 1
                continue

        print(
            "Info: Keyword "
            + active_ecl_keyword
            + " ignored. Unknown or unsupported syntax."
        )

    density_df["KEYWORD"] = "DENSITY"
    pvto_df["KEYWORD"] = "PVTO"
    pvtg_df["KEYWORD"] = "PVTG"
    pvtw_df["KEYWORD"] = "PVTW"
    pvdg_df["KEYWORD"] = "PVDG"
    rock_df["KEYWORD"] = "ROCK"

    file_df = pandas.concat(
        [density_df, pvto_df, pvtg_df, pvtw_df, pvdg_df, rock_df], sort=False
    )

    file_df["FILENAME"] = filename
    return file_df
