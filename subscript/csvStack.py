#!/usr/bin/env python
#
# Stack wells in a CSV exported file. 
# 
# All columns in your data set with a colon ":" in it, will 
# be split such that the string after the colon will become
# a column value instead of its own column. Thus all 
# columns called WOPT:A-1, WOPT:A-2, WOPT:A-3 etc will be merged
# into one column called WOPT, and you will have a column name
# called "Well" that contains A-1, A-2, or A-3 as values.
#
# If importing the produced stackedversion.csv into Spotfire, 
# you may then view and filter WOPT and friends by wellname, instead
# of selecting individual columns.
#
# Usage:
#  stackWells.py myexportedfile.csv -o stackedversion.csv
#
# Haavard Berland, OSE PTC RP, 26 October 2015, havb@statoil.com
#

import pandas
import sys
import re
import argparse
import resscript.header as header


parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("csvfile", help="input csv file. If you type stdin or -, it will read from stdin ")
parser.add_argument("-o", "--output", type=str, 
                    help="name of output csv file. Use - or stdout to have the output dumped to stdout.", default="stacked.csv")
parser.add_argument("--split", type=str, help="type of column to be split/unpivoted/stacked. Choose from the " +
                    "the predefined set: well, region, group, block, all", default="well")
parser.add_argument("--keepconstantcolumns", action="store_true", help="Keep constant columns before stacking", default=False)
parser.add_argument("--keepminimal", action="store_true", help="Keep only Realization, Iteration, Date and unpivoted columns", default=False) 
args = parser.parse_args()

if args.output == "-" or args.output == "stdout":
    quiet = True
else:
    quiet = False

if not quiet:
    header.compose("csvStack.py", 
                   "November 2015", 
                   ["Haavard Berland"], 
                   ["havb@statoil.com"], 
                   ["-h for help, or check wiki"], 
                   "Stack related columns in CSV files by adding more rows")

# Maybe too much usage()-noise to have these as options (?)
# Case does not matter in these lists, they will be lower()ed.
realization_names = ["Realization", "Realisation", "RunName"]
iteration_names = ["Iteration", "Iter"]
date_names = ["date"]

# Library of columns that we are able to split.
unpivottypes = {
    "well"   : [ 'W[A-Z]*:.*', ':', 'Well'],
    "region" : [ 'R[A-Z_]*:.*', ':', 'Region'],
    "group"  : [ 'G[A-Z]*:.*', ':', 'Group' ],
    "block"  : [ 'B[A-Z]*:.*', ':', 'Block' ],
    "all"    : [ '.*:.*',      ':', 'Identifier' ]
    }


if args.csvfile == "stdin" or args.csvfile == "-":
    if not quiet:
        print "Loading ensemble from stdin."
    ens = pandas.read_csv(sys.stdin)
else:
    if not quiet:
        print "Loading ensemble from " + args.csvfile
    ens = pandas.read_csv(args.csvfile)

if not unpivottypes.has_key(args.split):
    print "ERROR: Don't know how to split on " + str(args.split)
    sys.exit(1)

pivottype = unpivottypes[args.split]
wellmatcher = re.compile(pivottype[0])

# Constant columns should be deleted upfront for speed reasons.
keepthese = set([x.lower() for x in realization_names + iteration_names + date_names])
if not args.keepconstantcolumns:
    columnstodelete = []
    for col in ens.columns:
        if len(ens[col].unique()) == 1:
            columnstodelete.append(col)
        if args.keepminimal:
            if not (wellmatcher.match(col) or col.lower() in keepthese):
                columnstodelete.append(col)
    if args.keepminimal:
        if not quiet:
            print "Deleting constant and unwanted columns " + str(columnstodelete) 
    else:
        if not quiet:
            print "Deleting constant columns " + str(columnstodelete) 
    ens.drop(columnstodelete, inplace=True, axis=1)
    if not quiet:
        print "Deleted " + str(len(columnstodelete)) + " columns"


tuplecols = []
dostack=False
colstostack = 0
if not quiet:
    print "Will stack columns matching '" + pivottype[0] + "' with separator '" + pivottype[1] + "'"
    print "Name of new identifying column will be '" + pivottype[2] + "'"

nostackcolumnnames = []
for col in ens.columns:
    if wellmatcher.match(col):
        tuplecols.append(tuple(col.split(pivottype[1]))) 
        colstostack = colstostack + 1
        dostack=True
    else:
        tuplecols.append(tuple([col, ""]))
        nostackcolumnnames.append(col)

if not quiet:
    print "Found " + str(colstostack) + " out of " + str(len(ens.columns)) + " columns to stack"
    
if dostack:
   
    # Convert to MultiIndex columns
    ens.columns = pandas.MultiIndex.from_tuples(tuplecols,names=["Parametername",pivottype[2]])

    # Stack the multiindex columns, this will add a lot of rows to our ensemble, and condense the number of columns
    ens = ens.stack()

    # The values from non-multiindex-columns must be propagated to the rows
    # that emerged from the stacking. If you use the 'all' pivottype, then you will get some NaN-values
    # in the MultiIndex columns that are intentional.
    ens[nostackcolumnnames] = ens[nostackcolumnnames].fillna(method='ffill')
    
    ens = ens.reset_index()

    # Now we have rows that does not belong to any well, we should delete those rows
    ens = ens[ens[pivottype[2]] != ""]

    # And delete a byproduct of our reshaping (this is the index prior to stacking)
    del ens["level_0"]
   
if args.output == "stdout" or args.output == "-":
    ens.to_csv(sys.stdout, index=False)
else:
    print "Writing csv data to " + args.output
    ens.to_csv(args.output, index=False)
