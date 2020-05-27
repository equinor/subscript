#!/usr/bin/env python

import os
import glob
import shutil
import logging
import datetime
import itertools
import argparse
import re

logger = logging.getLogger(__name__)
logging.basicConfig()

DESCRIPTION = """Compress Eclipse input files by using the Eclipse
syntax <number>*<value> so that the data set

  0  0  0  1  2  3  2  2  2  2

becomes
  3*0 1 2 3 4*2

The script processes one file at a time, replacing the files with
compressed versions, leaving behind the original *only* if
requested by a command line option.

On the command line, may either provide a list of files to compress,
or point to a text file with a filename (wildcards supported) pr. line,
"""

DEFAULT_FILES_TO_COMPRESS = [
    "eclipse/include/grid/*",
    "eclipse/include/regions/*",
    "eclipse/include/props/*",
]

EPILOG = """
Compression statistics is computed and included in an Eclipse comment in
the output.

See https://en.wikipedia.org/wiki/Run-length_encoding for the compression
algorithm used.

Default list of files to compress is """ + " ".join(
    DEFAULT_FILES_TO_COMPRESS
)

# The string used here must match what is used as the DEFAULT
# parameter in the ert joob config. It is not used elsewhere.
MAGIC_DEFAULT_FILELIST = "__NONE__"


def eclcompress(files, keeporiginal=False, dryrun=False):
    """Run-length encode a set of grdecl files.

    Files will be modified in-place, backup is optional.

    Args:
        files (list of strings): Filenames to be compressed
        keeporiginal (bool): Whether to copy the original to a backup file
        dryrun (bool): If true, only print compression efficiency
    Returns:
        int: Number of bytes saved by compression.
    """

    if not isinstance(files, list):
        files = [files]  # List with one element

    totalsavings = 0

    for filename in files:
        logger.info("Compressing %s...", filename)
        try:
            with open(filename, "r") as fileh:
                filelines = fileh.readlines()
        except UnicodeDecodeError:
            # Try ISO-8859:
            try:
                with open(filename, "r", encoding="ISO-8859-1") as fileh:
                    filelines = fileh.readlines()
            except (TypeError, UnicodeDecodeError):
                # ISO-8859 under py2 is not intentionally supported
                logger.warning("Skipped %s, not text file.", filename)
                continue

        # Check if we can find the keyword INCLUDE in the file
        # If so, there is probably a path nearby that includes slashes /
        # that will most likely be broken by cleanlines.
        # We skip such files!
        if any([x.find("INCLUDE") > -1 for x in filelines]):
            logger.warning("Skipped %s, contains INCLUDE statement.", filename)
            continue  # to next file

        # VFP data records need to have trailing slashes pr. record
        # on the same line. Not yet supported, so give up.
        # (this might apply to all multi-record keywords?)
        if any([x.find("VFP") > -1 for x in filelines]):
            logger.warning("Skipped %s, contains VFPxxxx statement", filename)
            continue  # to next file

        # Skip if it seems we have already compressed this file
        if any([x.find("eclcompress") > -1 for x in filelines]):
            logger.warning("Skipped %s, compressed already", filename)
            continue  # to next file

        # Ensure ECL keywords at start of line,
        # newline before data, and put /'s as single character-lines
        filelines = cleanlines(filelines)

        origbytes = sum([len(x) for x in filelines])

        if not origbytes:
            logger.info("File %s is empty, skipping", filename)
            continue

        # Support multiple ECL keywords pr. file, so we first find the
        # file lines with individual keyword data to process
        keywordsets = find_keyword_sets(filelines)

        if not keywordsets:
            logger.info(
                "No Eclipse keywords found to compress in %s, skipping", filename
            )
            continue

        compressedlines = compress_multiple_keywordsets(keywordsets, filelines)
        compressedbytecount = sum([len(x) for x in compressedlines])

        # 1 means no compression, the higher the better.
        # The header added below is not included in the calculated
        # compression ratio
        compressionratio = float(origbytes) / float(compressedbytecount)

        savings = origbytes - compressedbytecount
        totalsavings += savings
        savingsKb = savings / 1024.0
        logger.info(
            "Compression ratio on %s: %.1f, %d Kb saved",
            filename,
            compressionratio,
            savingsKb,
        )
        if not dryrun and compressedlines:
            shutil.copy2(filename, filename + ".orig")
            with open(filename, "w") as file_h:
                file_h.write(
                    "-- File compressed with eclcompress at "
                    + str(datetime.datetime.now())
                    + "\n"
                )
                file_h.write(
                    "-- Compression ratio %.1f " % compressionratio
                    + "(higher is better, 1 is no compression)\n"
                )
                file_h.write("\n")

                file_h.write("\n".join(compressedlines))
                file_h.write("\n")

                if not keeporiginal:
                    os.remove(filename + ".orig")

    return totalsavings


def chunks(ll, nn):
    """Yield successive n-sized chunks as strings from list l."""
    for ii in range(0, len(ll), nn):
        yield " ".join(ll[ii : ii + nn])


def acceptedvalue(valuestring):
    """Return true only for strings that are numbers
    we don't want to try to compress other things

    Args:
        valuestring (str)

    Returns:
        bool
    """

    try:
        float(valuestring)
        return True
    except ValueError:
        return False


def compress_multiple_keywordsets(keywordsets, filelines):
    """Apply Eclipse type compression to data in filelines

    Individual ECL keyword are indicated by tuples in keywordsets
    and no compression is attempted outside the ECL keyword data

    Args:
        keywordsets (list of 2-tuples): (start, end) indices in
            line number in the deck, referring to individual sections
            of distinct keywords.
        filelines (list of str): lines from Eclipse deck, cleaned.

    Returns:
        list of str, to be used as a replacement Eclipse deck
    """

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
                compresseddata += [str(len(equalvalues)) + "*" + str(equalvalues[0])]
            else:
                compresseddata += [" ".join(equalvalues)]
        compressedlines += chunks(compresseddata, 5)
        # Only 5 chunks pr line, Eclipse will error if more than 132
        # characters on a line. TODO: Reprogram to use python textwrap

    # Add whatever is present at the end after the last slash:
    compressedlines += filelines[lastslashindex:]
    return compressedlines


def find_keyword_sets(filelines):
    """Parse list of strings, looking for Eclipse data sets that we want.

    Example:

    If the deck consists of six lines like this:

        -- now comes porosity
        PORO
        0.1 0.3 0.3
        0.1 0.2
        /
        -- poro done

    this will return [(1,4)] since 1 refers to the line with PORO and 4 refers
    to the line with the trailing slash.

    Args:
        filelines (list of str): Eclipse deck (partial)

    Return:
        list of 2-tuples,  with start and end line indices for datasets to
            compress

    """
    keywordsets = []
    kwstart = None
    for lineidx, line in enumerate(filelines):
        if re.match("[A-Z]+.*", line) is not None:
            kwstart = lineidx
        if kwstart is not None and line.strip()[0:2] == "--":
            # This means we found a comment section within a data set
            # In that case it is vital to preserve the current line
            # breaks which we don't do if we try to compress the section
            # therefore we avoid compressing this!
            # (compressing and preserving line breaks can be done later)
            kwstart = None
        if line[0] == "/":  # We can assume this because
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

    Args:
        filelines (list of str): Partial Eclipse deck.

    Returns:
        list of str, incoming deck, cleaned to what eclcompress supports.
    """

    # Text files are potentially big, so should we try to be a little
    # bit fast

    # Regex for capturing an Eclipse keyword at the beginning of a line
    eclkeyword = re.compile(r"^([A-Z]{2,8})\s(.*)")

    # Detect comments after a slash on a line
    slashspacecomment = re.compile(r"(.*/\s)(.*)$")
    cleaned = []
    for line in filelines:
        line = line.strip()
        # Put \n straight after any Eclipse keyword
        line = eclkeyword.sub("\\1\n\\2", line)
        if line.find("--") == -1:  # Don't touch lines with comments.
            # If we have anything after a / on a line, ensure we add '--' to it.
            # (we don't care if we add too many '--')
            line = slashspacecomment.sub("\\1 --\\2", line)
            # Split by / and ensure newlines around them
            lines = "\n/\n".join(line.split("/")).split("\n")
        else:
            lines = [line]
        # Remove empty lines
        lines = list(filter(len, lines))
        cleaned += lines

    return cleaned


def glob_patterns(patterns):
    """
    Args:
        patterns (list of str): filename patterns

    Returns:
        list of str, globbed files.
    """
    # Remove duplicates:
    patterns = list(set(patterns))

    # Do globbing on the filesystem:
    globbedfiles = [glob.glob(globpattern.strip()) for globpattern in patterns]

    # Return flattened and with duplicates deleted
    return list(
        {
            globbed
            for sublist in globbedfiles
            for globbed in sublist
            if os.path.isfile(globbed)
        }
    )


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """
    Multiple inheritance used for argparse to get both
    defaults and raw description formatter
    """

    pass


def get_parser():
    """Setup parser"""
    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter, description=DESCRIPTION, epilog=EPILOG
    )
    parser.add_argument(
        "grdeclfiles",
        nargs="*",
        help=(
            "List of Eclipse grdecl files to compress, supporting wildcards. "
            "If no files are given, a default wildcard list will be used."
        ),
    )
    parser.add_argument("--dryrun", action="store_true", help="Dry run only")
    parser.add_argument(
        "--keeporiginal", action="store_true", help="Copy original to filename.orig"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    parser.add_argument(
        "--files",
        help=(
            "Text file with one wildcard pr. line, "
            "specifying which files to apply compression to. "
            "Defaults to everything below eclipse/include, but only if "
            "no files are specified on the command line."
        ),
    )
    return parser


def parse_wildcardfile(filename):
    """Parse a file with one filename wildcard pr. line

    If a magic filename is supplied, default list of
    wildcards is returned. Magic filename is __NONE__

    Wildcard file supports comments, starting by # or --

    Args:
        filename (str)

    Returns:
        list of str
    """
    if filename == MAGIC_DEFAULT_FILELIST:
        return DEFAULT_FILES_TO_COMPRESS
    if not os.path.exists(filename):
        raise IOError("File {} not found".format(filename))

    lines = open(filename).readlines()
    lines = [line.strip() for line in lines]
    lines = [line.split("#")[0] for line in lines]
    lines = [line.split("--")[0] for line in lines]
    lines = filter(len, lines)
    return lines


def main():
    """Wrapper for the function main_eclcompress, parsing command line arguments"""
    parser = get_parser()
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)

    main_eclcompress(args.grdeclfiles, args.files, args.keeporiginal, args.dryrun)


def main_eclcompress(grdeclfiles, wildcardfile, keeporiginal=False, dryrun=False):
    """Implements the command line functionality

    Args:
        grdeclfiles (list of str or str): Filenames to compress
        wildcardfile (str): Filename containing wildcards
        keeporiginal (bool): Whether a backup file should be left behind
        dryrun (bool): Nothing written to disk, only statistics for
            compression printed to terminal.
    """
    # A list of wildcards on the command line should always be compressed:
    if grdeclfiles:
        patterns = grdeclfiles
        if not isinstance(patterns, list):
            patterns = [patterns]
    else:
        patterns = []

    # Default handling of the wildcardfile depend on whether grdeclfiles
    # is empty or not:
    if grdeclfiles:
        if wildcardfile and wildcardfile != MAGIC_DEFAULT_FILELIST:
            patterns += parse_wildcardfile(wildcardfile)
    else:
        # If no explicit wildcards on the command line, default filelist will be
        # processed:
        if wildcardfile is not None:
            patterns += parse_wildcardfile(wildcardfile)
        else:
            logger.info("Defaulted wildcards")
            patterns += parse_wildcardfile(MAGIC_DEFAULT_FILELIST)

    globbedfiles = glob_patterns(patterns)

    if not globbedfiles:
        logger.warning("No files to compress")
        return

    if globbedfiles:
        logger.info("Will try to compress the files: " + " ".join(globbedfiles))
        savings = eclcompress(globbedfiles, keeporiginal, dryrun)
        logger.info("Finished. Saved %d Mb from compression", savings / 1024.0 / 1024.0)
    else:
        logger.warning("No files found to compress")


if __name__ == "__main__":
    main()
