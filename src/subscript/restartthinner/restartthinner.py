#!/usr/bin/env python
# encoding: utf-8
#
# Slice a subset of restart-dates from a E100 Restart file.
#
# Example
#  $ restartslicer --restarts 4 ECLIPSE.UNRST
#
# The four restarts will be evenly spread in the relevant dates.
#
# Author: Håvard Berland, OTE PTC MOD MW
# Based on idea from Merouane Hamdani

import sys
import os
import glob
import datetime
import tempfile
import shutil
import pandas
import numpy
import argparse
import ecl.ecl as ecl

import resscript.header

def date_slicer(slicedates, restartdates, restartindices):
    """Make a dict that maps a chosen restart date to a report index"""
    slicedatemap = {}
    for slicedate in slicedates:
        daydistances = [abs((pandas.Timestamp(slicedate) - x).days) for x in restartdates]
        slicedatemap[slicedate] = restartindices[daydistances.index(min(daydistances))]
    return slicedatemap

def ecl_repacker(rstfilename, slicerstindices, quiet):
    """
    Wrapper for ecl_unpack.x and ecl_pack.x utilities.

    First unpacking a UNRST file, then deleting dates the dont't want, then
    pack the remainding files into a new UNRST file
    """
    if quiet:
        out=" >/dev/null"
    else:
        out = ""
    # Take special care if the UNRST file we get in is not in current directory
    if os.path.dirname(rstfilename) != "":
        os.chdir(os.path.dirname(rstfilename))
    tempdir = tempfile.mkdtemp(dir='.')
    os.rename(os.path.basename(rstfilename), os.path.join(tempdir,
            os.path.basename(rstfilename)))
    os.chdir(tempdir)
    os.system('ecl_unpack.x ' + os.path.basename(rstfilename) + out)
    unpackedfiles = glob.glob("*.X*")
    for file in unpackedfiles:
        if int(file.split('.X')[1]) not in slicerstindices:
            os.remove(file)
    os.system('ecl_pack.x *.X*' + out)
    # We are inside the tmp directory, move file one step up:
    os.rename(os.path.join(os.getcwd(), os.path.basename(rstfilename)),
              os.path.join(os.getcwd(), "../", os.path.basename(rstfilename)))
    os.chdir(os.path.join(os.getcwd(), '../'))
    shutil.rmtree(tempdir)

def main(filename, numberofslices, quiet=False, dryrun=True, keep=False):
    rst = ecl.EclFile(filename)
    restart_indices = ecl.EclFile.file_report_list(filename)
    restart_dates = [rst.iget_restart_sim_time(index) for index in range(0, len(restart_indices))]

    if numberofslices > 1:
        slicedates = pandas.DatetimeIndex(numpy.linspace(pandas.Timestamp(restart_dates[0]).value,
                                          pandas.Timestamp(restart_dates[-1]).value,
                                          int(numberofslices))).values
    else:
        slicedates = [restart_dates[-1]] # Only return last date if only one is wanted

    slicerstindices = date_slicer(slicedates, restart_dates, restart_indices).values()
    slicerstindices.sort()
    slicerstindices = list(set(slicerstindices)) # uniquify

    if not quiet:
        print "Selected restarts:"
        print "-----------------------"
        for idx in range(0, len(restart_indices)):
            if restart_indices[idx] in slicerstindices:
                slicepresent = "X"
            else:
                slicepresent = ""
            print "%4d:  %s  %s" % (restart_indices[idx],
                    datetime.date.strftime(restart_dates[idx], "%Y-%m-%d"), slicepresent)
        print "-----------------------"
    if not dryrun:
        if keep:
            if not quiet:
                print "Info: Backing up %s to %s" % (filename, filename + ".orig")
            shutil.copyfile(filename, filename + ".orig")
        ecl_repacker(filename, slicerstindices, quiet)


if __name__ == "__main__":
    resscript.header.compose("restartthinner", "", ["H. Berland"], ["havb@equinor.com"], ["wiki"], "Thin E100 UNRST files to fewer date points")

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("UNRST",
                                help="Name of UNRST file")
    parser.add_argument("-n", "--restarts", type=int, help="Number of restart dates wanted")
    parser.add_argument("-d", "--dryrun", action='store_true', default=False,
                help="Dry-run only, do not touch files")
    parser.add_argument("-q", "--quiet", action='store_true', default=False,
                help="Mute output from script")
    parser.add_argument("-k", "--keep", action='store_true', default=False,
            help="Keep original UNRST file")

    args = parser.parse_args()
    if args.restarts <= 0:
        raise argparse.ArgumentTypeError("Number of restarts must be a positive number")
    main(args.UNRST, args.restarts, args.quiet, args.dryrun, args.keep)

