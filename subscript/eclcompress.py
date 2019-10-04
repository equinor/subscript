#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Compress Eclipse grid files by using the Eclipse
syntax <number>*<value> so that the data set

  0  0  0  1  2  3  2  2  2  2

becomes
  3*0 1 2 3 4*2

See https://en.wikipedia.org/wiki/Run-length_encoding

The script processes one file at a time, replacing the files with
compressed versions, leaving behind the original *only* if
requested by a command line option.

Compression statistics is computed

The workhorse of this script is itertools.groupby(). All other lines
are just input and output handling.

Author: Håvard Berland, havb@statoil.com, September 2017

"""

from __future__ import print_function

import sys
import os
import glob
import shutil
import datetime
import itertools
import argparse
import re


def main(files, keeporiginal=False, dryrun=False):
    """Process one or many files"""
    if not isinstance(files, list):
        files = [files]  # List with one element

    for filename in files:
        print("Compressing " + filename)
        sys.stdout.flush()
        with open(filename, 'r') as fileh:
            filelines = fileh.readlines()

        # Check if we can find the keyword INCLUDE in the file
        # If so, there is probably a path nearby that includes slashes /
        # that will most likely be broken by cleanlines.
        # We skip such files!
        if any([x.find('INCLUDE') > -1 for x in filelines]):
            print("!! skipped, contains INCLUDE statement, not supported !!")
            continue  # to next file

        # Skip if it seems we have already compressed this file
        if any([x.find('eclcompress') > -1 for x in filelines]):
            print("!! skipped, seems to be compressed already !!")
            continue  # to next file

        # Ensure ECL keywords at start of line,
        # newline before data, and put /'s as single character-lines
        filelines = cleanlines(filelines)

        origbytes = sum([len(x) for x in filelines])

        # Support multiple ECL keywords pr. file, so we first find the
        # file lines with individual keyword data to process
        keywordsets = find_keyword_sets(filelines)

        compressedlines = compress_multiple_keywordsets(keywordsets,
                                                        filelines)
        compressedbytecount = sum([len(x) for x in compressedlines])

        # 1 means no compression, the higher the better.
        # The header added below is not included in the calculated
        # compression ratio
        compressionratio = float(origbytes) \
            / float(compressedbytecount)

        savings = origbytes - compressedbytecount
        savingsKb = savings/1024.0
        print(" compression ratio: %.1f, %d Kb saved"
              % (compressionratio, savingsKb))
        if not dryrun and compressedlines:
            shutil.copy2(filename, filename + ".orig")
            with open(filename, 'w') as f:
                f.write('-- File compressed with eclcompress at '
                        + str(datetime.datetime.now()) + '\n')
                f.write('-- Compression ratio %.1f ' % compressionratio
                        + '(higher is better, 1 is no compression)\n')
                f.write('\n')

                f.write('\n'.join(compressedlines))
                f.write('\n')
                f.close()

                if not keeporiginal:
                    os.remove(filename + ".orig")


def chunks(l, n):
    """Yield successive n-sized chunks as strings from list l."""
    for i in xrange(0, len(l), n):
        yield ' '.join(l[i:i + n])


def acceptedvalue(valuestring):
    """Return true only for strings that are numbers
    we don't want to try to compress other things"""
    try:
        float(valuestring)
        return True
    except ValueError:
        return False


def compress_multiple_keywordsets(keywordsets, filelines):
    """Apply Eclipse type compression to data in filelines

    Individual ECL keyword are indicated by tuples in keywordsets
    and no compression is attempted outside the ECL keyword data"""
    compressedlines = []
    lastslashindex = 0
    for keywordtuple in keywordsets:
        if keywordtuple[0] is None:
            continue  # This happens for extra /
        startdata = keywordtuple[0] + 1
        compressedlines += filelines[lastslashindex:startdata]
        data = []  # List of strings, each string is one data element
        #            (typically integer)
        enddata = keywordtuple[1]
        lastslashindex = enddata
        for dataline in filelines[startdata:enddata]:
            data += dataline.split()
        compresseddata = []
        for _, g in itertools.groupby(data):
            equalvalues = list(g)
            # We apply compression even if there are only two consecutive
            # numbers. This reduces readability if humans ever look
            # at the output, but gives a marginal saving.
            if len(equalvalues) > 1 and acceptedvalue(equalvalues[0]):
                compresseddata += [str(len(equalvalues))
                                   + '*' + str(equalvalues[0])]
            else:
                compresseddata += [' '.join(equalvalues)]
        compressedlines += chunks(compresseddata, 5)
        # Only 5 chunks pr line, Eclipse will error if more than 132
        # charactes on a line. Reprogram to use python textwrap

    # Add whatever is present at the end after the last slash:
    compressedlines += filelines[lastslashindex:]
    return compressedlines


def find_keyword_sets(filelines):
    """Parse list of strings, looking for Eclipse data sets that we want.

    Return tuples with start and end line indices for datasets to
    compress

    """
    keywordsets = []
    kwstart = None
    for lineidx, line in enumerate(filelines):
        if re.match('[A-Z]+.*', line) is not None:
            kwstart = lineidx
        if kwstart is not None and line.strip()[0:2] == '--':
            # This means we found a comment section within a data set
            # In that case it is vital to preserve the current line
            # breaks which we don't do if we try to compress the section
            # therefore we avoid compressing this!
            # (compressing and preserving line breaks can be done later)
            kwstart = None
        if line[0] == '/':  # We can assume this because
            #                               of cleanlines()
            keywordsets.append((kwstart, lineidx))
            kwstart = None
    return keywordsets


def cleanlines(filelines):
    """Cleanup in Eclipse grid files to easen parsing

    ECL keywords always at start of a line, only uppercase letters,
    newline straight after keyword

    Any / should occur at single lines unless in comments

    Any comment start at beginning of line

    """

    # Text files are potentially big, so should we try to be a little
    # bit fast

    # Regex for capturing an Eclipse keyword at the beginning of a line
    eclkeyword = re.compile(r'^([A-Z]{2,8})\s(.*)')

    # Detect comments after a slash on a line
    slashspacecomment = re.compile(r'(.*/\s)(.*)$')
    cleaned = []
    for line in filelines:
        line = line.strip()
        # Put \n straight after any Eclipse keyword
        line = eclkeyword.sub('\\1\n\\2', line)
        if line.find('--') == -1:  # Don't touch lines with comments.
            # If we have anything after a / on a line, ensure we add '--' to it.
            # (we don't care if we add too many '--')
            line = slashspacecomment.sub('\\1 --\\2', line)
            # Split by / and ensure newlines around them
            lines = '\n/\n'.join(line.split('/')).split('\n')
        else:
            lines = [line]
        # Remove empty lines
        lines = filter(len, lines)
        cleaned += lines

    return cleaned


def test():
    """Example test for eclcompress, to be run
    and verified manually"""
    filelines = ['-- Test file for eclcompress',
                 '-- When this is compressed, it should be valid Eclipse input',  # noqa
                 'GRIDUNIT',
                 '\'METRES \' \'    \' /',
                 '',
                 ' SATNUM  ',
                 '0 0   0 1 1 1 3 1 4 3 2',
                 '0 0 1 1 1 1 1 1 1 1 1 1 2'
                 ' 0 4 1 /',
                 'IMBNUM',
                 '0 0 3 3 2 2 2 2',
                 '/ --something at the end we want to preserve',
                 'SWOF',
                 '-- A comment we dont want to mess up',
                 '-- here is some data that is commented out',
                 '0 0 1 0',
                 '0.5 0.5 0.5 0',
                 '1   1  0 0',
                 '/',
                 '-- A comment with slashes /which/must/be/preserved as comment',  # noqa
                 'PORO  0 0 0 / ',
                 'PERMY',
                 '0 0 0 / -- more comments after ending slash, destroys compression',  # noqa
                 '',
                 'EQUALS',
                 'MULTZ 0.017101  1 40  1 64  5  5 / nasty comment without comment characters'  # noqa
                 '/']

    cleaned = cleanlines(filelines)
    print(cleaned)

    kwsets = find_keyword_sets(cleaned)
    print(kwsets)

    compressed = compress_multiple_keywordsets(kwsets, cleaned)

    print('\n'.join(compressed))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("grdeclfiles", nargs="+",
                        help="List of Eclipse grdecl files to compress")
    parser.add_argument("--dryrun", action="store_true",
                        help="Dry run only")
    parser.add_argument("--keeporiginal", action="store_true",
                        help="Keep original file")
    args = parser.parse_args()

    globbedfiles = [glob.glob(gf) for gf in list(args.grdeclfiles)]
    # Flatten list of lists:
    globbedfiles = [item for sublist in globbedfiles for item in sublist]
    main(globbedfiles, args.keeporiginal, args.dryrun)
