#!/usr/bin/env python

import argparse
import datetime
import glob
import itertools
import logging
import os
import shutil
import textwrap
from pathlib import Path
from typing import List, Tuple, Union

import subscript

from .allowlist import ALLOWLIST_KEYWORDS

logger = subscript.getLogger(__name__)

DESCRIPTION = """Apply run-length encoding to Eclipse input files, such
that consecutive numbers like "1 1 1 1" are compressed to "4*1".
The script processes one file at a time, replacing the files with
compressed versions.

If called with no arguments, a default file list is used.
If called with ``<FILES>``, the argument provided must be a filepath to
a text file containing a file list to compress.
"""

EXAMPLES = """
.. code-block:: console

  FORWARD_MODEL ECLCOMPRESS

You can provide your own list of files to compress with the ``<FILES>``
argument.

.. code-block:: console

  FORWARD_MODEL ECLCOMPRESS(<FILES>=paths_to_compress.txt)

where ``paths_to_compress.txt`` contains a list of files or filepaths to
compress.

.. code-block:: text
  :caption: paths_to_compress.txt

  eclipse/include/grid/*
  eclipse/include/regions/*
  eclipse/include/props/*

Note that this list of file paths is the default list used when no file is
provided.
"""

DEFAULT_FILES_TO_COMPRESS = [
    "eclipse/include/grid/*",
    "eclipse/include/regions/*",
    "eclipse/include/props/*",
]

EPILOG = """
Default list of files to compress is """ + " ".join(DEFAULT_FILES_TO_COMPRESS)

CATEGORY = "modelling.reservoir"

# The string used here must match what is used as the DEFAULT
# parameter in the ert joob config. It is not used elsewhere.
MAGIC_DEFAULT_FILELIST = "__NONE__"

DENYLIST_KEYWORDS = ["INCLUDE"]  # Due to slashes in filenames


def eclcompress(
    files: Union[str, List[str]],
    keeporiginal: bool = False,
    dryrun: bool = False,
) -> int:
    """Run-length encode a set of grdecl files.

    Files will be modified in-place, backup is optional.

    Args:
        files: Filenames to be compressed
        keeporiginal: Whether to copy the original to a backup file
        dryrun: If true, only print compression efficiency

    Returns:
        Number of bytes saved by compression.
    """

    if not isinstance(files, list):
        files = [files]  # List with one element

    totalsavings = 0

    for filename in files:
        if file_is_binary(filename):
            logger.info("Skipped %s, not text file", filename)
            continue

        logger.info("Compressing %s...", filename)

        origbytes = os.stat(filename).st_size
        if not origbytes:
            logger.info("File %s is empty, skipping", filename)
            continue

        try:
            filelines = Path(filename).read_text(encoding="utf8").splitlines()
        except UnicodeDecodeError:
            # Try ISO-8859:
            try:
                filelines = Path(filename).read_text(encoding="ISO-8859-1").splitlines()
            except (TypeError, UnicodeDecodeError):
                # ISO-8859 under py2 is not intentionally supported
                logger.warning("Skipped %s, not text file.", filename)
                continue

        # Skip if it seems we have already compressed this file
        if any(x.find("eclcompress") > -1 for x in filelines):
            logger.warning("Skipped %s, compressed already", filename)
            continue  # to next file

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
            with open(filename, "w", encoding="utf8") as file_h:
                file_h.write(
                    "-- File compressed with eclcompress "
                    f"at {datetime.datetime.now()}\n"
                )
                file_h.write(
                    f"-- Compression ratio {compressionratio:.1f} "
                    "(higher is better, 1 is no compression)\n"
                )
                file_h.write("\n")

                file_h.write("\n".join(compressedlines))
                file_h.write("\n")

                if not keeporiginal:
                    os.remove(filename + ".orig")

    return totalsavings


def file_is_binary(filename: Union[str, Path]) -> bool:
    """Determine if a file is assumed binary

    This uses the same heuristic as the Linux `file` command. Only the first
    1024 bytes are looked at.

    Args:
        filename: File to check
    """
    # pylint: disable=line-too-long
    # https://stackoverflow.com/questions/898669/how-can-i-detect-if-a-file-is-binary-non-text-in-python  # noqa
    textchars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F})
    with open(filename, "rb") as filehandle:
        return bool(filehandle.read(1024).translate(None, textchars))


def acceptedvalue(valuestring: str) -> bool:
    """Return true only for strings that are numbers.

    Used to avoid trying to compress other strings than numbers.

    Args:
        valuestring
    """

    try:
        float(valuestring)
        return True
    except ValueError:
        return False


def compress_multiple_keywordsets(
    keywordsets: List[Tuple[int, int]], filelines: List[str]
) -> List[str]:
    """Apply Eclipse type compression to data in filelines

    The list of strings given as input (filelines) is indexed
    by the tuples in keywordsets.

    Args:
        keywordsets: 2-tuples, (start, end) with indices to
            line number in the deck, referring to individual sections
            of distinct keywords.
        filelines: Lines from the Eclipse deck, cleaned.

    Returns:
        Strings to be used as a replacement Eclipse deck
    """

    compressedlines: List[str] = []

    # Line pointer to the last line with a slash in it:
    lastslash_linepointer = 0

    for keywordtuple in keywordsets:
        start_linepointer, end_linepointer = keywordtuple
        if start_linepointer is None:
            continue  # This happens for an extra /
        if start_linepointer < end_linepointer:
            start_linepointer += 1

        # Append whatever we have gathered since previous keyword
        compressedlines += filelines[lastslash_linepointer:start_linepointer]

        # List of strings, each string is one data element (typically integer):
        data: List[str] = []

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
        # than 128 characters, if there are comments after the slash it will be
        # added to the last line emitted by the wrapping and could overshoot the
        # 128 limit (but having Eclipse ignore a comment is fine)
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


def find_keyword_sets(filelines: List[str]) -> List[Tuple[int, int]]:
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
        filelines: Eclipse deck lines (not necessarily complete decks)

    Return:
        2-tuples, with start and end line indices for datasets to
        compress

    """
    keywordsets = []
    kwstart = None

    for lineidx, line in enumerate(filelines):
        line = line.strip()
        if not line:
            continue
        # Remove embracing quotes if in a multi-keyword
        keyword = line.split(" ")[0].strip("'")
        if keyword in ALLOWLIST_KEYWORDS:
            kwstart = lineidx
            if "/" in line:
                keywordsets.append((kwstart, lineidx))
                kwstart = None
            continue
        if kwstart is not None and line[0:2] == "--":
            # This means we found a comment section within a data set
            # In that case it is vital to preserve the current line
            # breaks which we don't do if we try to compress the section
            # therefore we avoid compressing this!
            # (compressing and preserving line breaks can be done later)
            kwstart = None
            continue
        if "/" in line and kwstart is not None:
            # First occurence of a slash ends the keyword section
            keywordsets.append((kwstart, lineidx))
            kwstart = None
    return keywordsets


def glob_patterns(patterns: List[str]) -> List[str]:
    """
    Args:
        patterns: List of strings with filename patterns

    Returns:
        Strings with globbed files.
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


def get_parser() -> argparse.ArgumentParser:
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
            "Path to a text file containing one wildcard filepath per line, "
            "specifying which files to apply compression to. "
            "Defaults to everything below eclipse/include, but only if "
            "no files are specified on the command line."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + subscript.__version__ + ")",
    )
    return parser


def parse_wildcardfile(filename: str) -> List[str]:
    """Parse a file with one filename wildcard pr. line

    If a magic filename is supplied, default list of
    wildcards is returned. Magic filename is __NONE__

    Wildcard file supports comments, starting by # or --

    Args:
        filename
    """
    if filename == MAGIC_DEFAULT_FILELIST:
        return DEFAULT_FILES_TO_COMPRESS
    if not os.path.exists(filename):
        raise IOError(f"File {filename} not found")

    lines = Path(filename).read_text(encoding="utf8").splitlines()
    lines = [line.strip() for line in lines]
    lines = [line.split("#")[0] for line in lines]
    lines = [line.split("--")[0] for line in lines]
    return list(filter(len, lines))


def main():
    """Wrapper for the function main_eclcompress, parsing command line arguments"""
    parser = get_parser()
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)

    main_eclcompress(
        args.grdeclfiles,
        args.files,
        keeporiginal=args.keeporiginal,
        dryrun=args.dryrun,
    )


def main_eclcompress(
    grdeclfiles: Union[List[str], str],
    wildcardfile: str,
    keeporiginal: bool = False,
    dryrun: bool = False,
) -> None:
    """Implements the command line functionality

    Args:
        grdeclfiles: Strings or a string, with filename(s) to compress
        wildcardfile: Filename containing wildcards
        keeporiginal: Whether a backup file should be left behind
        dryrun: Nothing written to disk, only statistics for
            compression printed to terminal.
    """
    # A list of wildcards on the command line should always be compressed:
    if grdeclfiles:
        patterns = grdeclfiles
        if isinstance(patterns, str):
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

    if globbedfiles:
        logger.info("Will try to compress the files: %s", " ".join(globbedfiles))
        savings = eclcompress(
            globbedfiles,
            keeporiginal=keeporiginal,
            dryrun=dryrun,
        )
        savings_mb = savings / 1024.0 / 1024.0
        print(f"eclcompress finished. Saved {savings_mb:.1f} Mb from compression")
    else:
        logger.warning("No files found to compress")


if __name__ == "__main__":
    main()
