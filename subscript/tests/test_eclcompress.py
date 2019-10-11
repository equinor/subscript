from __future__ import absolute_import

import sys
import os

import sunbeam.deck

from .. import eclcompress
from ..eclcompress import cleanlines, find_keyword_sets, compress_multiple_keywordsets

FILELINES = [
    "GRIDUNIT",
    "'METRES ' '    ' /",
    "",
    " SATNUM  ",
    "0 0   0 1 1 1 3 1 4 3 2",
    "0 0 1 1 1 1 1 1 1 1 1 1 2" " 0 4 1 /",
    "IMBNUM",
    "0 0 3 3 2 2 2 2",
    "/ --something at the end we want to preserve",
    "SWOF",
    "-- A comment we dont want to mess up",
    "-- here is some data that is commented out",
    "0 0 1 0",
    "0.5 0.5 0.5 0",
    "1   1  0 0",
    "/",
    "-- A comment with slashes /which/must/be/preserved as comment",  # noqa
    "PORO  0 0 0 / ",
    "PERMY",
    "0 0 0 / -- more comments after ending slash, destroys compression",  # noqa
    "",
    "EQUALS",
    "MULTZ 0.017101  1 40  1 64  5  5 / nasty comment without comment characters"  # noqa
    "/",
]


def test_cleanlines():
    assert cleanlines([" PORO"]) == ["PORO"]
    assert cleanlines(["PORO 3"]) == ["PORO", "3"]
    assert cleanlines(["PORO 1 2 3 /"]) == ["PORO", "1 2 3 ", "/"]
    assert cleanlines([" PORO/"]) == ["PORO", "/"]
    assert cleanlines([" PORO/  foo"]) == ["PORO", "/", "  -- foo"]
    assert cleanlines(["-- PORO 4"]) == ["-- PORO 4"]
    assert cleanlines(["POROFOOBARCOM  4"]) == ["POROFOOBARCOM  4"]


def test_find_keyword_sets():
    assert find_keyword_sets(["PORO", "0 1 2 3", "4 5 6", "/"]) == [(0, 3)]


def test_compress_multiple_keywordsets():
    filelines = ["PORO", "0 0 0 3", "4 5 6", "/"]
    kwsets = find_keyword_sets(filelines)
    assert compress_multiple_keywordsets(kwsets, filelines) == [
        "PORO",
        "3*0 3 4 5 6",
        "/",
    ]


def test_eclcompress():
    cleaned = cleanlines(FILELINES)
    kwsets = find_keyword_sets(cleaned)
    compressed = compress_multiple_keywordsets(kwsets, cleaned)
    compressedstr = "\n".join(compressed)

    # Feed the compressed string into sunbeam. Sunbeam hopefully chokes on whatever
    # Eclipse would choke on (and hopefully not on more..)
    recovery = [("PARSE_MISSING_DIMS_KEYWORD", sunbeam.action.ignore)]

    assert sunbeam.deck.parse_string(compressedstr, recovery=recovery)


def test_main():
    testdir = os.path.join(os.path.dirname(__file__), "testdata_eclcompress")
    if not os.path.exists(testdir):
        os.mkdir(testdir)
    os.chdir(testdir)

    with open("testdeck.inc", "w") as testdeck:
        for line in FILELINES:
            testdeck.write(line + "\n")

    if os.path.exists("testdeck.inc.orig"):
        os.unlink("testdeck.inc.orig")

    sys.argv = ["eclcompress", "--keeporiginal", "testdeck.inc"]  # noqa
    eclcompress.main()

    assert os.path.exists("testdeck.inc.orig")
    assert os.path.exists("testdeck.inc")
    compressedlines = open("testdeck.inc").readlines()
    compressedbytes = sum([len(x) for x in compressedlines if not x.startswith("--")])
    origbytes = sum([len(x) for x in FILELINES])

    assert compressedbytes < origbytes

    compressedstr = "\n".join(compressedlines)
    recovery = [("PARSE_MISSING_DIMS_KEYWORD", sunbeam.action.ignore)]
    assert sunbeam.deck.parse_string(compressedstr, recovery=recovery)
