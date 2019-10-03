#!/bin/env python
#
# Usage:
#        csvMergeEnsembles.py ensemble1.csv ensemble2.csv [ensemble3.csv [...]]
#
# Given csv files (typically ensembles produced by ERT), it will 
# append all the data rows of the second ensemble to the first ensemble.
# The data will be exported to the file "merged.csv" - rename it afterwards
#
# A new column is added called 'ensemble', which will contain the name of the 
# ensemble (taken from the filename you provide).
#
# The columns in the ensembles need not be the same. Similar column names 
# will be merged, differing column names will be padded (with NaN) in the 
# ensemble where they don't exist.
#
# Note that the ordering of all columns becomes alphabetical after this merging.
#
# Author: Haavard Berland, OSE PTC RP, Sept/Oct 2015, havb@statoil.com

import sys
import pandas
import argparse
import re
import resscript.header as header

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("csvfiles", nargs="+", help="input csv files")
parser.add_argument("-o", "--output", type=str, 
                    help="name of output csv file. Use - or stdout to dump output to stdout.", default="merged.csv")
parser.add_argument("--keepconstantcolumns", action='store_true', help="Keep constant columns", default=False)
parser.add_argument("--filecolumn", type=str, help="Name of column containing original filename", default="ensemble")
parser.add_argument("-q", "--quiet", action='store_true', help="Suppress non-critical output", default=False)

args = parser.parse_args()

if args.output == "-" or args.output == "stdout":
    quiet = True
else:
    quiet = False

if args.quiet:
    quiet = True


if not quiet:
    header.compose("csvMergeEnsembles.py", 
                   "01.04.2015", 
                   ["Haavard Berland"], 
                   ["havb@statoil.com"], 
                   ["-h for help, or check wiki"], 
                   "Merge multiple CSV exports from ERT into one CSV file")


ens = pandas.DataFrame()
for csvfile in args.csvfiles:
    if not quiet:
        print " ** Loading "+  csvfile + "..."
    try:
        ensnew = pandas.read_csv(csvfile)
        if not quiet:
            print ensnew.info()

        ensnew[args.filecolumn] = pandas.Series(csvfile.replace(".csv",""), index=ensnew.index)
        realregex = ".*realization-(\d*)/"
        iterregex = ".*iter-(\d*)/"

        if re.match(realregex, csvfile):
            # We don't use the column name "Realization" yet, because it might exist in some of the 
            # input files, but later on, we will copy it to "Realization" if it doesn't exist in the end
            ensnew[args.filecolumn + "-realization"] = re.match(realregex, csvfile).group(1)
        if re.match(iterregex, csvfile):
            ensnew[args.filecolumn + "-iter"] = re.match(iterregex, csvfile).group(1)

        ens = pandas.concat([ens, ensnew], ignore_index=True, sort=True)
        # (the indices in these csv files are just the row number, which doesn't mean anything 
        #  in our data, therefore we should "ignore_index".)
        if not quiet:
            print "         ------------------  "
    except IOError:
        if not quiet:
            print "WARNING: " + csvfile + " not found."
    except pandas.errors.EmptyDataError:
        if not quiet:
            print "WARNING: " + csvfile + " seems empty, no data found."

if not args.keepconstantcolumns:
    columnstodelete = []
    for col in ens.columns:
        if len(ens[col].unique()) == 1:
            columnstodelete.append(col)
    if not quiet: 
        print "  Dropping constant columns " + str(columnstodelete) 
    ens.drop(columnstodelete, inplace=True, axis=1)

# Copy realization column if its only source is the filename.
if not "Realization" in ens.columns and args.filecolumn+"-realization" in ens.columns:
    ens["Realization"] = ens[args.filecolumn + "-realization"]
# Ditto for iteration
if not "Iter" in ens.columns and args.filecolumn+"-iter" in ens.columns:
    ens["Iter"] = ens[args.filecolumn + "-iter"]


if len(ens.index) == 0:
    print "ERROR: No data to output."
    sys.exit(1)

if not quiet:
    print " ** Merged ensemble data:"
    print ens.info()
    
    print " ** Exporting csv data to " + args.output    

if args.output == "-" or args.output == "stdout":
    ens.to_csv(sys.stdout, index=False)
else:
    ens.to_csv(path_or_buf=args.output, index=False)

if not quiet:
    print " - Finished writing to " + args.output
