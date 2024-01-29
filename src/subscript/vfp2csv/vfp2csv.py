import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from subscript import __version__

DESCRIPTION = """Process a VFP file (typically outputted from Prosper or similar)
and relayout the data into a tabular format, exported to CSV.

The table will always contain the columns FILENAME, VFPTYPE,
TABLENUMBER and DATUM. Depending on the VFPTYPE (possible values:
VFPINJ or VFPPROD) you will get different columns with data:
BHP, THP, ALQ, WGR, OGR, WCT, GOR, LIQ

Do not depend on column order. TABLENUMBER is not enforced unique, it
is taken from whatever the data indicates, which can conflict.
FILENAME is absolute or relative, depending on the input.
"""


def get_parser():
    """Set up parser for command line utility"""
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "vfpfiles", nargs="+", help="Text files containing VFPPROD/VFPINJE"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Name of output CSV file",
        default="vfptables.csv",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + __version__ + ")",
    )
    return parser


def main():
    """Process command line arguments"""
    parser = get_parser()
    args = parser.parse_args()

    # List of dataframes for each VFP table
    vfpframes = []

    for filename in args.vfpfiles:
        print(f"Processing file {filename}")
        vfpframes.append(vfpfile2df(filename))
    allvfpdata = pd.concat(vfpframes, sort=False)
    print("Exporting to " + args.output)
    allvfpdata.to_csv(args.output, index=False)


def vfpfile2df(filename: str) -> pd.DataFrame:
    """Process a VFP file (typically outputted from Prosper or similar)
    and organize the data into a dataframe

    The dataframe will always contain the columns FILENAME, VFPTYPE,
    TABLENUMBER and DATUM. Depending on the VFPTYPE (possible values:
    VFPINJ or VFPPROD) you will get different columns with data:
    BHP, THP, ALQ, WGR, OGR, WCT, GOR, LIQ

    Do not depend on column order. TABLENUMBER is not enforced unique, it
    is taken from whatever the data indicates, which can conflict.
    FILENAME is absolute or relative, depending on the input.

    Args:
        filename (str): Filename, absolute or relative path to
            an ascii file (utf-8 or iso-8859) containing VFP* data
    Returns:
        pd.DataFrame.
    """
    try:
        lines = Path(filename).read_text(encoding="utf8").splitlines()
    except UnicodeDecodeError:
        lines = Path(filename).read_text(encoding="iso-8859-1").splitlines()

    # Strip comments:
    lines = [line.split("--")[0] for line in lines]

    # BUG: Will not tolerate comments that has something else than a whitespace
    #      in front of it
    vfptabledata = [a.strip() for a in " ".join(lines).split("/")]

    # Now loop over vfptabledata. Lines starting with VFP{PROD/INJE} are the
    # interesting ones, and the consecutive lines after.
    vfpstartindices = [
        x for x in range(len(vfptabledata)) if vfptabledata[x].startswith("VFP")
    ]

    print(f" - found {len(vfpstartindices)} vfp keywords")
    for vfptableidx in vfpstartindices:
        vfptype = vfptabledata[vfptableidx].split()[0]
        tableno = vfptabledata[vfptableidx].split()[1]
        datum = vfptabledata[vfptableidx].split()[2]
        if vfptype == "VFPPROD":
            rate = vfptabledata[vfptableidx].split()[3].replace("'", "")
            wfr = vfptabledata[vfptableidx].split()[4].replace("'", "")
            gfr = vfptabledata[vfptableidx].split()[5].replace("'", "")
            if len(vfptabledata[vfptableidx].split()) > 6:
                thp = vfptabledata[vfptableidx].split()[6].replace("'", "")
            else:
                thp = "THP"  # Default in E100
            if len(vfptabledata[vfptableidx].split()) > 7:
                alq = vfptabledata[vfptableidx].split()[7].replace("'", "").strip()
            else:
                alq = ""  # E100 default
            if len(vfptabledata[vfptableidx].split()) > 8:
                units = vfptabledata[vfptableidx].split()[8].replace("'", "")
            else:
                units = "default"  # Default unit is defined in DATA file
            if len(vfptabledata[vfptableidx].split()) > 9:
                tab = vfptabledata[vfptableidx].split()[9].replace("'", "")
            else:
                tab = "BHP"
            shift = 6
        elif vfptype == "VFPINJ":
            rate = vfptabledata[vfptableidx].split()[3].replace("'", "")
            tab = "BHP"
            shift = 3

        flow_values = np.array(vfptabledata[vfptableidx + 1].split()).astype(float)
        thp_values = np.array(vfptabledata[vfptableidx + 2].split()).astype(float)

        if vfptype == "VFPPROD":
            wfr_values = np.array(vfptabledata[vfptableidx + 3].split()).astype(float)
            gfr_values = np.array(vfptabledata[vfptableidx + 4].split()).astype(float)
            alq_values = np.array(vfptabledata[vfptableidx + 5].split()).astype(float)

        if vfptype == "VFPPROD":
            rows = len(alq_values) * len(thp_values) * len(wfr_values) * len(gfr_values)
        elif vfptype == "VFPINJ":
            rows = len(thp_values)

        bhp_values = pd.DataFrame(
            [
                list(map(float, x.split()))
                for x in vfptabledata[vfptableidx + shift : vfptableidx + shift + rows]
            ]
        )

        # Replace the indices in the first four columns with
        # the actual values they represent:
        if vfptype == "VFPPROD":
            bhp_values[0] = [thp_values[int(x) - 1] for x in bhp_values[0]]
            bhp_values[1] = [wfr_values[int(x) - 1] for x in bhp_values[1]]
            bhp_values[2] = [gfr_values[int(x) - 1] for x in bhp_values[2]]
            bhp_values[3] = [alq_values[int(x) - 1] for x in bhp_values[3]]
        elif vfptype == "VFPINJ":
            bhp_values[0] = [thp_values[int(x) - 1] for x in bhp_values[0]]

        # Set up column names to allow for stacking the flow values
        # (wide data to long data)
        if vfptype == "VFPPROD":
            if alq:
                alq = "-" + alq
            indextuples = [(thp, ""), (wfr, ""), (gfr, ""), ("ALQ" + alq, "")]
        elif vfptype == "VFPINJ":
            indextuples = [("THP", "")]

        for flowvalue in flow_values:
            indextuples.append(("BHP", flowvalue))

        # Set the columns to a MultiIndex, to facilitate stacking
        bhp_values.columns = pd.MultiIndex.from_tuples(indextuples)

        # Now stack
        bhp_values_stacked = bhp_values.stack()

        # In order to propagate the gfr, thp, wct values after
        # stacking to the correct rows, we should either understand
        # how to do that properly using pandas, but for now, we try a
        # backwards fill, hopefully that is robust enough
        bhp_values_stacked.bfill(inplace=True)
        # Also reset the index:
        bhp_values_stacked.reset_index(inplace=True)
        bhp_values_stacked.drop("level_0", axis="columns", inplace=True)
        # This column is not meaningful (it is the old index)

        # Delete rows that does not belong to any flow rate (this is
        # possibly a by-product of not doing the stacking in an
        # optimal way)
        bhp_values_stacked = bhp_values_stacked[bhp_values_stacked["level_1"] != ""]

        # Add correct column name for the flow values that we have stacked
        cols = list(bhp_values_stacked.columns)
        cols[0] = rate
        bhp_values_stacked.columns = cols

        # Add meta-data
        bhp_values_stacked["VFPTYPE"] = vfptype
        bhp_values_stacked["TABLENUMBER"] = int(tableno)
        bhp_values_stacked["DATUM"] = float(datum)
        if vfptype == "VFPPROD":
            bhp_values_stacked["UNITS"] = units
            bhp_values_stacked["TABTYPE"] = tab

        bhp_values_stacked["FILENAME"] = filename
    return bhp_values_stacked
