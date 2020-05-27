# -*- coding: utf-8 -*-
from __future__ import absolute_import

import sys
import os
import codecs
import subprocess

import pytest

import opm.io

from subscript.eclcompress.eclcompress import (
    cleanlines,
    compress_multiple_keywordsets,
    find_keyword_sets,
    glob_patterns,
    main,
    main_eclcompress,
    parse_wildcardfile,
)


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
    "-- utf-8 comment: æøå",
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

    # Missing slash, then nothing found:
    assert find_keyword_sets(["PORO", "0 1 2 3", "4 5 6"]) == []

    # Keyword with no data, will be found, but untouched by compression
    kw_nodata = ["PORO", "/"]
    kw_sets = find_keyword_sets(kw_nodata)
    assert kw_sets == [(0, 1)]
    assert compress_multiple_keywordsets(kw_sets, kw_nodata) == kw_nodata


def test_empty_file(tmpdir):
    emptyfilename = "emptyfile.grdecl"
    with open(emptyfilename, "w"):
        pass
    assert os.stat(emptyfilename).st_size == 0
    main_eclcompress(emptyfilename, None)
    assert os.stat(emptyfilename).st_size == 0


def test_no_touch_non_eclipse(tmpdir):
    """Check that we do not change a file that does not contain
    any Eclipse data"""
    filename = "foo.txt"
    with open(filename, "w") as file_h:
        file_h.write("Some random text\nAnother line\nbut no Eclipse keywords")
    origsize = os.stat(filename).st_size
    main_eclcompress(filename, None)
    assert origsize == os.stat(filename).st_size


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

    # Feed the compressed string into opm.io. OPM hopefully chokes on whatever
    # Eclipse would choke on (and hopefully not on more..)
    parsecontext = opm.io.ParseContext(
        [("PARSE_MISSING_DIMS_KEYWORD", opm.io.action.ignore)]
    )
    assert opm.io.Parser().parse_string(compressedstr, parsecontext)


@pytest.mark.integration
def test_integration():
    """Test endpoint is installed"""
    assert subprocess.check_output(["eclcompress", "-h"])


def test_vfpprod(tmpdir):
    """VFPPROD contains multiple record data, for which E100
    fails if the record-ending slash is not on the same line as the data
    """
    tmpdir.chdir()
    vfpstr = """
VFPPROD
  10 2021.3 LIQ WCT GOR THP GRAT METRIC BHP /
  50 150 300 500 1000 1500 2000 3000 4000 5000 6500 8000 10000 /
  50 100 150 200 250 300 400 500 /
  0 0.1 0.2 0.3 0.4 0.5 0.65 0.8 0.95 /
  300 332 350 400 500 1000 2000 5000 10000 30000 /
  0 /
  1 1 1 1
  50.35 50.32 50.34 50.36 50.8 52.03 53.91 58.73 64.01 69.69 78.1 86.34 97.46 /
  1 1 2 1
  50.34 50.31 50.34 50.36 50.85 52.38 54.45 59.58 65.46 71.53 80.43 89.28 101.43 /
  1 1 3 1
"""
    parsecontext = opm.io.ParseContext(
        [("PARSE_MISSING_DIMS_KEYWORD", opm.io.action.ignore)]
    )
    # Confirm that OPM can parse the startiing point:
    assert opm.io.Parser().parse_string(vfpstr, parsecontext)

    # Call eclcompress as script on vfpstr:
    with open("vfpfile.inc", "w") as testdeck:
        testdeck.write(vfpstr)
    print("foo")
    sys.argv = ["eclcompress", "--keeporiginal", "vfpfile.inc"]  # noqa
    main()

    # Check that OPM can parse the output (but in this case, OPM allows
    # having the slashes on the next line, so it is not a good test)
    assert opm.io.Parser().parse_string(open("vfpfile.inc").read(), parsecontext)

    # Verify that a slash at record-end is still there. This test will pass
    # whether eclcompress is just skipping the file, or of it is able to
    # compress it correctly.
    assert "8000 10000 /" in open("vfpfile.inc").read()


def test_main(tmpdir):
    """Test installed endpoint"""

    tmpdir.chdir()

    with open("testdeck.inc", "w") as testdeck:
        for line in FILELINES:
            testdeck.write(line + "\n")

    if os.path.exists("testdeck.inc.orig"):
        os.unlink("testdeck.inc.orig")

    sys.argv = ["eclcompress", "--keeporiginal", "testdeck.inc"]  # noqa
    main()

    assert os.path.exists("testdeck.inc.orig")
    assert os.path.exists("testdeck.inc")
    compressedlines = open("testdeck.inc").readlines()
    compressedbytes = sum([len(x) for x in compressedlines if not x.startswith("--")])
    origbytes = sum([len(x) for x in FILELINES])

    assert compressedbytes < origbytes

    compressedstr = "\n".join(compressedlines)
    parsecontext = opm.io.ParseContext(
        [("PARSE_MISSING_DIMS_KEYWORD", opm.io.action.ignore)]
    )
    assert opm.io.Parser().parse_string(compressedstr, parsecontext)


def test_binary_file(tmpdir):
    tmpdir.chdir()
    binfile = "binfile.bin"
    with open(binfile, "wb") as file_h:
        # Random byte sequence that is not valid as UTF-8:
        file_h.write(bytearray([10, 0, 1, 2, 4, 5, 250, 255, 155]))
    main_eclcompress(binfile, None)


def test_iso8859(tmpdir):
    tmpdir.chdir()
    nastyfile = "nastyfile.inc"
    with codecs.open(nastyfile, "w", "ISO-8859-1") as file_h:
        file_h.write(u"-- Gullfaks Sør\nPORO 1 1 1 1/\n")
    main_eclcompress(nastyfile, None)
    assert "4*1" in open(nastyfile).read()  # Outputted file is always UTF-8


def test_utf8(tmpdir):
    tmpdir.chdir()
    nastyfile = "nastyfile.inc"
    with open(nastyfile, "w") as file_h:
        file_h.write("-- Gullfaks Sør\nPORO 1 1 1 1/\n")
    main_eclcompress(nastyfile, None)
    assert "4*1" in open(nastyfile).read()


@pytest.fixture
def eclincludes(tmpdir):
    tmpdir.chdir()
    os.makedirs("eclipse/include/props")
    os.makedirs("eclipse/include/regions")
    open("eclipse/include/props/perm.grdecl", "w").write(
        "PERMX\n0 0 0 0 0 0 0 0 0 0 0 0 0\n/"
    )
    open("eclipse/include/regions/fipnum.grdecl", "w").write(
        "FIPNUM\n0 0 0 0 0 0 0 0 0 0 0 0 0\n/"
    )
    yield


def test_default_pattern(eclincludes):
    main_eclcompress(None, None)
    assert (
        "File compressed with eclcompress"
        in open("eclipse/include/props/perm.grdecl").read()
    )
    assert (
        "File compressed with eclcompress"
        in open("eclipse/include/regions/fipnum.grdecl").read()
    )
    assert "13*0" in open("eclipse/include/props/perm.grdecl").read()


def test_files_override_default_wildcards(eclincludes, twofiles):
    """Default wildcardlist will not be used if explicit files are provided"""
    assert "0 0 0 0" in open("perm.grdecl").read()
    assert "0 0 0 0" in open("eclipse/include/props/perm.grdecl").read()
    main_eclcompress("perm.grdecl", None)
    assert "13*0" in open("perm.grdecl").read()
    assert "13*0" not in open("eclipse/include/props/perm.grdecl").read()


@pytest.fixture
def twofiles(tmpdir):
    tmpdir.chdir()

    open("perm.grdecl", "w").write("PERMX\n0 0 0 0 0 0 0 0 0 0 0 0 0\n/")
    open("poro.grdecl", "w").write("PORO\n1 1 1 1 1 1 1\n/")

    open("filelist", "w").write("*.grdecl")
    yield


@pytest.mark.parametrize(
    "args",
    [
        ("*.grdecl", None),
        ("", "filelist"),
        (None, "filelist"),
        ("*.grdecl", "filelist"),
        (["perm.grdecl", "poro.grdecl"], "filelist"),
        (["perm.grdecl", "poro.grdecl"], None),
        (["perm.grdecl", "poro.grdecl"], ""),
    ],
)
def test_compress_files_filelist(args, twofiles):
    """Test the command line options for giving in both excplicit files and
    a list of file(pattern)s"""

    main_eclcompress(args[0], args[1])

    assert "File compressed with eclcompress" in open("perm.grdecl").read()
    assert "File compressed with eclcompress" in open("poro.grdecl").read()
    assert "13*0" in open("perm.grdecl").read()
    assert "7*1" in open("poro.grdecl").read()


def text_compress_argparse_1(twofiles):
    """Test also the command line interface with --files"""
    sys.argv = ["eclcompress", "--files", "files"]
    main()
    assert "File compressed with eclcompress" in open("perm.grdecl").read()
    assert "File compressed with eclcompress" in open("poro.grdecl").read()
    assert "13*0" in open("perm.grdecl").read()
    assert "7*1" in open("poro.grdecl").read()


def text_compress_argparse_2(twofiles):
    """Command line options, explicit files vs. --files"""
    sys.argv = ["eclcompress", "perm.grdecl", "--files", "files"]
    main()
    assert "File compressed with eclcompress" in open("perm.grdecl").read()
    assert "File compressed with eclcompress" in open("poro.grdecl").read()
    assert "13*0" in open("perm.grdecl").read()
    assert "7*1" in open("poro.grdecl").read()


def text_compress_argparse_3(twofiles):
    """Command line options, explicit files vs. --files"""
    sys.argv = ["eclcompress", "perm.grdecl"]
    main()
    assert "File compressed with eclcompress" in open("perm.grdecl").read()
    assert "File compressed with eclcompress" not in open("poro.grdecl").read()
    assert "13*0" in open("perm.grdecl").read()
    assert "7*1" not in open("poro.grdecl").read()


def test_glob_patterns(tmpdir):
    tmpdir.chdir()

    dummyfiles = ["perm.grdecl", "poro.grdecl"]

    for dummyfile in dummyfiles:
        open(dummyfile, "w").write("")
    open("filelist", "w").write("*.grdecl")

    assert set(glob_patterns(parse_wildcardfile("filelist"))) == set(dummyfiles)

    open("filelist_dups", "w").write(
        """
*.grdecl
poro.grdecl
p*ecl
perm.grdecl"""
    )
    assert set(glob_patterns(parse_wildcardfile("filelist_dups"))) == set(dummyfiles)

    open("filelist_comments", "w").write(
        "-- this is a comment\n*.grdecl\n# some  comment"
    )
    assert set(glob_patterns(parse_wildcardfile("filelist_dups"))) == set(dummyfiles)

    open("filelist_comments", "w").write(
        "# this is a comment\n*.grdecl\n# some  comment"
    )
    assert set(glob_patterns(parse_wildcardfile("filelist_dups"))) == set(dummyfiles)
    open("filelist_comments", "w").write(
        "  # this is a comment\n*.grdecl # comment along pattern"
    )
    assert set(glob_patterns(parse_wildcardfile("filelist_dups"))) == set(dummyfiles)

    with pytest.raises(IOError):
        parse_wildcardfile("")

    with pytest.raises(IOError):
        parse_wildcardfile("notthere")
