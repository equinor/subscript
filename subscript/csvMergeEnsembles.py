"""
Merge multiple CSV files.
"""

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import sys
import argparse
import re

import pandas


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """
    Multiple inheritance used for argparse to get both
    defaults and raw description formatter
    """

    pass


def get_parser():
    """Construct parser object for csvMergeEnsembles"""
    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter,
        description="""
Merge multiple CSV files into one. Each row will be tagged by the filename
it came from in the column 'ensemble'.

The columns in the ensembles need not be the same. Similar column names
will be merged, differing column names will be padded (with NaN) in the
ensemble where they don't exist.

Note that the ordering of all columns becomes alphabetical after this merging.
""",
        epilog="""If realization-*/iter-* is present in the filename, that numerical information
is attempted extracted and put into the columns Realization and Iteration
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
        "--keepconstantcolumns",
        action="store_true",
        help="Keep constant columns",
        default=False,
    )
    parser.add_argument(
        "--filecolumn",
        type=str,
        help="Name of column containing original filename",
        default="ensemble",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress non-critical output",
        default=False,
    )
    return parser


def main():
    """Entry point from command line"""
    parser = get_parser()
    args = parser.parse_args()
    quiet = args.output == "-" or args.output == "stdout" or args.quiet

    ens = pandas.DataFrame()
    for csvfile in args.csvfiles:
        if not quiet:
            print(" ** Loading " + csvfile + "...")
        try:
            ensnew = pandas.read_csv(csvfile)
            if not quiet:
                print(ensnew.info())

            ensnew[args.filecolumn] = pandas.Series(
                csvfile.replace(".csv", ""), index=ensnew.index
            )
            realregex = r".*realization-(\d*)/"
            iterregex = r".*iter-(\d*)/"

            if re.match(realregex, csvfile):
                # We don't use the column name "Realization" yet,
                # because it might exist in some of the
                # input files, but later on, we will copy it to "Realization"
                # if it doesn't exist in the end
                ensnew[args.filecolumn + "-realization"] = re.match(
                    realregex, csvfile
                ).group(1)
            if re.match(iterregex, csvfile):
                ensnew[args.filecolumn + "-iter"] = re.match(iterregex, csvfile).group(
                    1
                )

            # Concatenation is done one frame at at a time.
            # This makes concatenation slower, but more memory efficient.
            ens = pandas.concat([ens, ensnew], ignore_index=True, sort=True)
            # (the indices in these csv files are just the row number,
            # which doesn't mean anything
            # in our data, therefore we should "ignore_index".)
            if not quiet:
                print("         ------------------  ")
        except IOError:
            if not quiet:
                print("WARNING: " + csvfile + " not found.")
        except pandas.errors.EmptyDataError:
            if not quiet:
                print("WARNING: " + csvfile + " seems empty, no data found.")

    if not args.keepconstantcolumns:
        columnstodelete = []
        for col in ens.columns:
            if len(ens[col].unique()) == 1:
                columnstodelete.append(col)
        if not quiet:
            print("  Dropping constant columns " + str(columnstodelete))
        ens.drop(columnstodelete, inplace=True, axis=1)

    # Copy realization column if its only source is the filename.
    if (
        "Realization" not in ens.columns
        and args.filecolumn + "-realization" in ens.columns
    ):
        ens["Realization"] = ens[args.filecolumn + "-realization"]
    # Ditto for iteration
    if "Iter" not in ens.columns and args.filecolumn + "-iter" in ens.columns:
        ens["Iter"] = ens[args.filecolumn + "-iter"]

    if ens.empty:
        print("ERROR: No data to output.")
        sys.exit(1)

    if not quiet:
        print(" ** Merged ensemble data:")
        print(ens.info())

        print(" ** Exporting csv data to " + args.output)

    if args.output == "-" or args.output == "stdout":
        ens.to_csv(sys.stdout, index=False)
    else:
        ens.to_csv(path_or_buf=args.output, index=False)

    if not quiet:
        print(" - Finished writing to " + args.output)


if __name__ == "__main__":
    main()
