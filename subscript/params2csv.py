#!/usr/bin/env python
#
# Takes a list of files with <key> <values> pr. line, and turns them into a csv database
# (sort of transposing and concatenation of all the data, ensuring labels for each value matches)
#
# Typical usage:
# 
#   $ params2csv realization-*/iter-0/parameters.txt > parameters.csv
#
# Limitations:
#   * If you have a datatype called "filename" in your text files, it will collide with the one used in this script.
#   * Order of data in parameters.txt is not conserved.
#
# Havard Berland, OSE PTC RP, October 2015
#
import pandas
import sys, shutil
import re
import argparse
import resscript.header as header

header.compose("params2csv.py",
               "October 2015",
               ["Havard Berland"],
               ["havb@statoil.com"],
               ["-h for help, or check wiki"],
               "Convert list of <key>-<value> files into a CSV database")
parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("parameterfile", nargs="+", help="all parameter files to be merged")
parser.add_argument("-o", "--output", type=str, help="name of output csv file", default="params.csv")
parser.add_argument("--filenamecolumnname", type=str, help="Column name that will contain the name of the parameter file", default="filename")
parser.add_argument("--keepconstantcolumns", action='store_true', help="Keep constant columns", default=False)
parser.add_argument("--clean", action='store_true', help="Write back cleaned parameters.txt", default=False)
args = parser.parse_args()
               

ens = pandas.DataFrame()

parsedfiles = 0
for parameterfilenameidx, parameterfilename in enumerate(args.parameterfile, start=0):

    try:
        paramtable = pandas.read_table(parameterfilename, delim_whitespace=True, header=None)
        parsedfiles = parsedfiles + 1
    except Exception,e:
        sys.stderr.write("WARNING: Error at " + parameterfilename + ", skipping..\n")
        sys.stderr.write("         " + str(e) + "\n")
        continue

    # Chop to only two colums, set keys, and transpose, and then merge with the previous tables
    paramtable = pandas.DataFrame(paramtable.iloc[:,0:2])
    paramtable.columns = ['key', 'value']
    paramtable.drop_duplicates('key', keep='last', inplace=True) # if key is repeated, keep the last one.
    transposed = paramtable.set_index('key').transpose()
    if args.filenamecolumnname in transposed.columns:
        print "Column name " + args.filenamecolumnname + " was already in " + parameterfilename + ", not writing"
        print "this filename into CSV output. Use --filenamecolumnname to avoid this."
    else:
        transposed.insert(0, args.filenamecolumnname,  parameterfilename)

    # Look for meta-information in filename
    realregex = ".*realization-(\d*)/"
    iterregex = ".*iter-(\d*)/"   
    if re.match(realregex, parameterfilename) and 'Realization' not in transposed.columns:
        transposed.insert(0, "Realization", re.match(realregex, parameterfilename).group(1))
    if re.match(iterregex, parameterfilename) and 'Iter' not in transposed.columns:
        transposed.insert(0, "Iter", re.match(iterregex, parameterfilename).group(1))

    ens = pandas.concat([ens, transposed], sort=True)

if args.clean:
    # Users wants the script to write back to parameters.txt a possible subset of parametervalues so
    # that the number of parameters is equal in an entire ensemble, and so that duplicate keys are removed
    # Parameters only existing in some realizations will be NaN-padded in the others.
    ensfilenames = ens.reset_index()['filename']
    ensidx = ens.reset_index().drop(['index', 'filename'],axis=1)
    for row in list(ensidx.index.values):
        paramfile = ensfilenames.loc[row] 
        shutil.copyfile(paramfile, paramfile + ".backup")
        print "Writing to " + paramfile
        ensidx.loc[row].to_csv(paramfile, sep=" ", na_rep="NaN", header=False)

# Drop constant columns:
if not args.keepconstantcolumns:
    for col in ens.columns:
        if len(ens[col].unique()) == 1:
            del ens[col]
            print "WARNING: Dropping constant column " + str(col)

ens.to_csv(args.output, index=False)
print str(parsedfiles) + " parameterfiles written to " + args.output
