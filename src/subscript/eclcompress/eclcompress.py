#!/usr/bin/env python

import os
import glob
import shutil
import logging
import datetime
import itertools
import textwrap
import argparse
import re

import subscript

logger = subscript.getLogger(__name__)

DESCRIPTION = """Apply run-length encoding to Eclipse input files, such
that consecutive numbers like "1 1 1 1" are compressed to "4*1".
The script processes one file at a time, replacing the files with
compressed versions.

If called with no arguments, a default file list is used.
"""

DEFAULT_FILES_TO_COMPRESS = [
    "eclipse/include/grid/*",
    "eclipse/include/regions/*",
    "eclipse/include/props/*",
]

EPILOG = """
Default list of files to compress is """ + " ".join(
    DEFAULT_FILES_TO_COMPRESS
)

CATEGORY = "utility.eclipse"

# The string used here must match what is used as the DEFAULT
# parameter in the ert joob config. It is not used elsewhere.
MAGIC_DEFAULT_FILELIST = "__NONE__"


def eclcompress(files, keeporiginal=False, dryrun=False):
    """Run-length encode a set of grdecl files.

    Files will be modified in-place, backup is optional.

    Args:
        files (list): List of filenames (str) to be compressed
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

        # Skip if it seems we have already compressed this file
        if any([x.find("eclcompress") > -1 for x in filelines]):
            logger.warning("Skipped %s, compressed already", filename)
            continue  # to next file

        origbytes = sum([len(x) for x in filelines])

        if not origbytes:
            logger.info("File %s is empty, skipping", filename)
            continue

        # Index the list of strings (the file contents) by the line numbers
        # where Eclipse keywords start, and where the first data record of the keyword
        # ends (compression is not attempted in record 2 and onwards for any keyword)
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
        savings_kb = savings / 1024.0
        logger.info(
            "Compression ratio on %s: %.1f, %d Kb saved",
            filename,
            compressionratio,
            savings_kb,
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

    The list of strings given as input (filelines) is indexed
    by the tuples in keywordsets.

    Args:
        keywordsets (list): List of 2-tuples, (start, end) indices in
            line number in the deck, referring to individual sections
            of distinct keywords.
        filelines (list): list of lines (strings) from Eclipse deck, cleaned.

    Returns:
        list:  List of strings to be used as a replacement Eclipse deck
    """

    # List of finished lines to build up:
    compressedlines = []

    # Line pointer to the last line with a slash in it:
    lastslash_linepointer = 0

    for keywordtuple in keywordsets:
        if keywordtuple[0] is None:
            continue  # This happens for an extra /
        start_linepointer = keywordtuple[0] + 1  # The line number where data starts.

        # Append whatever we have gathered since previous keyword
        compressedlines += filelines[lastslash_linepointer:start_linepointer]

        data = (
            []
        )  # List of strings, each string is one data element (typically integer)
        end_linepointer = keywordtuple[1]
        lastslash_linepointer = end_linepointer + 1
        for dataline in filelines[start_linepointer:end_linepointer]:
            data += dataline.split()

        # Handle the last line carefully, it might contain something after the slash,
        # and data in front of the slash:
        assert "/" in filelines[end_linepointer]
        lastline_comps = filelines[end_linepointer].split("/")
        preslashdata = lastline_comps[0]
        postslash = "/".join(filelines[end_linepointer].split("/")[1:])
        data += preslashdata.split()
        compresseddata = []
        for _, group in itertools.groupby(data):
            equalvalues = list(group)
            # We apply compression even if there are only two consecutive
            # numbers. This reduces readability if humans ever look
            # at the output, but gives a marginal saving.
            if len(equalvalues) > 1 and acceptedvalue(equalvalues[0]):
                compresseddata += [str(len(equalvalues)) + "*" + str(equalvalues[0])]
            else:
                compresseddata += [" ".join(equalvalues)]

        # Wrap the output to 79 characters pr. line. Eclipse will error if more
        # than 132 characters, if there are comments after the slash it will be
        # added to the last line emitted by the wrapping and could overshoot the
        # 132 limit (but having Eclipse ignore a comment is fine)
        compressedlines += textwrap.wrap(
            " ".join(compresseddata),
            initial_indent="  ",
            subsequent_indent="  ",
            width=79,
        )

        # Add the slash ending the record to the last line, or on a new line
        # if the slash was already on its own line.
        if preslashdata:
            compressedlines[-1] += " /" + postslash.rstrip()
        else:
            compressedlines += ["/" + postslash.rstrip()]
    # Add whatever is present at the end after the last slash
    # (more DeckRecords (not compressed), comments, whatever)
    # (avoid newlines, it will be readded later)
    compressedlines += map(str.rstrip, filelines[lastslash_linepointer:])
    return compressedlines


def find_keyword_sets(filelines):
    """Parse list of strings, looking for Eclipse data sets that we want.

    Example:

    If the deck consists of six lines like this::

        -- now comes porosity
        PORO
        0.1 0.3 0.3
        0.1 0.2
        /
        -- poro done

    this will return [(1,4)] since 1 refers to the line with PORO and 4 refers
    to the line with the trailing slash.

    More tricky keywords like (multiple records)::

        EQUALS
          'FIPNUM' 0 1 0 1 0 1 10 /
          'FIPNUM' 1 2 1 2 1 2 20 /
        /

    we are not able to detect anything but the first record (line) without
    having a full Eclipse parser (OPM). This means we we only compress the
    first line. These type of keywords are not important to compress, and we
    could just as well avoid compressing them altogether.

    Eclipse keyword strings must always be alone on a line, if not they
    are skipped (i.e. not recognized as an Eclipse keyword)

    Args:
        filelines (list): List of Eclipse deck (str) (not necessarily complete decks)

    Return:
        list: List of 2-tuples, with start and end line indices for datasets to
        compress

    """
    blacklisted_keywords = ["INCLUDE"]  # (due to slashes in filenames)
    keywordsets = []
    kwstart = None
    for lineidx, line in enumerate(filelines):
        if (
            re.match("[A-Z]{2,8}$", line) is not None
            and line.strip() not in blacklisted_keywords
        ):
            kwstart = lineidx
            continue
        if kwstart is not None and line.strip()[0:2] == "--":
            # This means we found a comment section within a data set
            # In that case it is vital to preserve the current line
            # breaks which we don't do if we try to compress the section
            # therefore we avoid compressing this!
            # (compressing and preserving line breaks can be done later)
            kwstart = None
            continue
        if "/" in line:  # First occurence of a slash ends the keyword section
            keywordsets.append((kwstart, lineidx))
            kwstart = None
    return keywordsets


def glob_patterns(patterns):
    """
    Args:
        patterns (list): List of strings with filename patterns

    Returns:
        list: List of strings with globbed files.
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

    # pylint: disable=W0107
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
            "If no files are given, a default wildcard list will be used. "
            "Wildcards should be enclosed in quotes when called on the command line."
        ),
    )
    parser.add_argument(
        "--dryrun",
        action="store_true",
        help=(
            "Dry run only. No files on disk will be modified, "
            "but compression statistics will be outputted."
        ),
    )
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
        list: List of strings
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
        grdeclfiles (list): List of strings or a string, with filename(s) to compress
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
        logger.info("Will try to compress the files: %s", " ".join(globbedfiles))
        savings = eclcompress(globbedfiles, keeporiginal, dryrun)
        print(
            "eclcompress finished. Saved %d Mb from compression"
            % (savings / 1024.0 / 1024.0)
        )
    else:
        logger.warning("No files found to compress")


if __name__ == "__main__":
    main()
