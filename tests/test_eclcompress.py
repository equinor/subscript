"""Test eclcompress with  pytest"""

import sys
import os
import subprocess
from pathlib import Path

import pytest

import numpy as np

import opm.io

from subscript.eclcompress.eclcompress import (
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
    "0 0 1 1 1 1 1 1 1 1 1 1 2 0 4 1 /",
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
    "-- A comment with slashes /which/must/be/preserved as comment",
    "PORO",
    "0 0 0 / ",
    "PERMY",
    "0 0 0 / -- more comments after ending slash",
    "",
    "EQUALS",
    "MULTZ 0.017101  1 40  1 64  5  5 / nasty comment without comment characters",
    "/",
    "--fo",
]


def test_find_keyword_sets():
    """Check the indexing of list of strings into Eclipse keywords"""
    assert find_keyword_sets(["PORO", "0 1 2 3", "4 5 6", "/"]) == [(0, 3)]

    # Missing slash, then nothing found:
    assert find_keyword_sets(["PORO", "0 1 2 3", "4 5 6"]) == []

    # MORE!!

    # Keyword with no data, will be found, but untouched by compression
    kw_nodata = ["PORO", "/"]
    kw_sets = find_keyword_sets(kw_nodata)
    assert kw_sets == [(0, 1)]
    assert compress_multiple_keywordsets(kw_sets, kw_nodata) == kw_nodata


def test_empty_file(tmpdir):
    """Check that compression of empty files is a noop"""
    tmpdir.chdir()
    emptyfilename = "emptyfile.grdecl"
    with open(emptyfilename, "w"):
        pass
    assert os.stat(emptyfilename).st_size == 0
    main_eclcompress(emptyfilename, None)
    assert os.stat(emptyfilename).st_size == 0


def test_no_touch_non_eclipse(tmpdir):
    """Check that we do not change a file that does not contain
    any Eclipse data"""
    tmpdir.chdir()
    filename = "foo.txt"
    with open(filename, "w") as file_h:
        file_h.write("Some random text\nAnother line\nbut no Eclipse keywords")
    origsize = os.stat(filename).st_size
    main_eclcompress(filename, None)
    assert origsize == os.stat(filename).st_size


def test_compress_multiple_keywordsets():
    """Test compression of sample lines"""
    filelines = ["PORO", "0 0 0 3", "4 5 6", "/ postslashcomment"]
    kwsets = find_keyword_sets(filelines)
    assert compress_multiple_keywordsets(kwsets, filelines) == [
        "PORO",
        "  3*0 3 4 5 6",
        "/ postslashcomment",
    ]

    filelines = ["PORO", "0 0 0 3", "4 5 6", "/"]
    kwsets = find_keyword_sets(filelines)
    assert compress_multiple_keywordsets(kwsets, filelines) == [
        "PORO",
        "  3*0 3 4 5 6",
        "/",
    ]

    filelines = ["PORO", "0 0 0 3", "4 5 6 /"]
    kwsets = find_keyword_sets(filelines)
    assert compress_multiple_keywordsets(kwsets, filelines) == [
        "PORO",
        "  3*0 3 4 5 6 /",
    ]

    filelines = ["PORO", "0 0 0 3", "4 5 6 / postslashcomment"]
    kwsets = find_keyword_sets(filelines)
    assert compress_multiple_keywordsets(kwsets, filelines) == [
        "PORO",
        "  3*0 3 4 5 6 / postslashcomment",
    ]

    filelines = ["PORO", "0 0 0 3 4 5 6 / postslashcomment"]
    kwsets = find_keyword_sets(filelines)
    assert compress_multiple_keywordsets(kwsets, filelines) == [
        "PORO",
        "  3*0 3 4 5 6 / postslashcomment",
    ]

    filelines = ["PORO", "0 0 /", "PERMX", "1 1 /"]
    kwsets = find_keyword_sets(filelines)
    assert compress_multiple_keywordsets(kwsets, filelines) == [
        "PORO",
        "  2*0 /",
        "PERMX",
        "  2*1 /",
    ]

    filelines = ["PORO", "0 0 /", "", "PERMX", "1 1 /"]
    kwsets = find_keyword_sets(filelines)
    assert compress_multiple_keywordsets(kwsets, filelines) == [
        "PORO",
        "  2*0 /",
        "",
        "PERMX",
        "  2*1 /",
    ]

    filelines = ["-- comment", "PORO", "0 0", "/"]
    kwsets = find_keyword_sets(filelines)
    assert compress_multiple_keywordsets(kwsets, filelines) == [
        "-- comment",
        "PORO",
        "  2*0",
        "/",
    ]

    filelines = ["-- nastycomment with / slashes", "PORO", "0 0", "/"]
    kwsets = find_keyword_sets(filelines)
    assert compress_multiple_keywordsets(kwsets, filelines) == [
        "-- nastycomment with / slashes",
        "PORO",
        "  2*0",
        "/",
    ]


def test_multiplerecords():
    """Test compression on keywords with multiple records,
    for which eclcompress only supports compressing the first records

    Conservation of the remainder of the keyword is critical to test.
    """
    filelines = [
        "EQUALS",
        "  MULTZ 0.017101  1 40  1 64  5  5 / nasty comment without comment characters",
        "/",
    ]

    kwsets = find_keyword_sets(filelines)
    assert compress_multiple_keywordsets(kwsets, filelines) == [
        "EQUALS",
        "  MULTZ 0.017101 1 40 1 64 2*5 / nasty comment without comment characters",
        "/",
    ]

    filelines = [
        "EQUALS",
        "1 1 / nasty comment/",
        "2 2 / foo",
        "3 3 /",
        "/",
        "PERMX",
        "1 1 /",
    ]
    kwsets = find_keyword_sets(filelines)
    assert compress_multiple_keywordsets(kwsets, filelines) == [
        "EQUALS",
        "  2*1 / nasty comment/",  # (only compressing first record)
        "2 2 / foo",
        "3 3 /",
        "/",
        "PERMX",
        "  2*1 /",
    ]

    filelines = ["EQUALS", "1 1//", "2 2 / foo", "/"]
    kwsets = find_keyword_sets(filelines)
    assert compress_multiple_keywordsets(kwsets, filelines) == [
        "EQUALS",
        "  2*1 //",
        "2 2 / foo",
        "/",
    ]


def test_formatting():
    """Test that compressed output is only 79 characters wide"""
    numbers = " ".join([str(number) for number in np.random.rand(1, 100)[0]])
    filelines = ["PORO", numbers, "/"]
    formatted = compress_multiple_keywordsets(find_keyword_sets(filelines), filelines)
    assert max([len(line) for line in formatted]) <= 79

    # But, some keywords will not tolerate random
    # newlines in their data-section, at least the multi-record keywords.
    # So we should never wrap a line with a slash in it:
    filelines = ["VFPPROD", " FOO" * 30 + " /"]
    # If this is fed through eclcompress, it will be wrapped due to its
    # length:
    formatted = compress_multiple_keywordsets(find_keyword_sets(filelines), filelines)
    assert len(formatted) > 2
    # But then, this example is not valid Eclipse, so leave for now.


def test_grid_grdecl():
    """A typical grid.grdecl file must be able to do compression on the
    COORDS/ZCORN keywords, while conserving the other two"""
    filelines = """
SPECGRID
214  669  49   1  F  /

GDORIENT
INC INC INC DOWN RIGHT /

ZCORN
  1 1 1 1 1 1 /
""".split(
        "\n"
    )
    kwsets = find_keyword_sets(filelines)
    assert (
        compress_multiple_keywordsets(kwsets, filelines)
        == """
SPECGRID
  214 669 49 1 F /

GDORIENT
  INC INC INC DOWN RIGHT /

ZCORN
  6*1 /
""".split(
            "\n"
        )
    )


def test_include_statement():
    """A file with an INCLUDE statement has been tricky
    not to destroy while compressing"""
    filelines = ["INCLUDE", "  '../include/grid/grid.grdecl'  /"]
    kwsets = find_keyword_sets(filelines)
    assert compress_multiple_keywordsets(kwsets, filelines) == filelines


def test_eclcompress():
    """Test a given set of lines, and ensure that the output
    can be parsed by opm.io"""
    kwsets = find_keyword_sets(FILELINES)
    compressed = compress_multiple_keywordsets(kwsets, FILELINES)
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
    # Confirm that OPM can parse the starting point:
    assert opm.io.Parser().parse_string(vfpstr, parsecontext)

    # Call eclcompress as script on vfpstr:
    with open("vfpfile.inc", "w") as testdeck:
        testdeck.write(vfpstr)
    sys.argv = ["eclcompress", "--keeporiginal", "vfpfile.inc"]
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

    sys.argv = ["eclcompress", "--keeporiginal", "testdeck.inc"]
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


@pytest.mark.skipif(sys.version_info < (3, 7), reason="Requires Python 3.7 or higher")
def test_binary_file():
    """Test that a random binary file is untouched by eclcompress"""
    binfile = "wrong.grdecl"
    Path(binfile).write_bytes(os.urandom(100))
    bytes_before = Path(binfile).read_bytes()
    proc_result = subprocess.run(
        "eclcompress --verbose  " + binfile, check=True, shell=True, capture_output=True
    )
    proc_output = proc_result.stdout.decode() + proc_result.stderr.decode()
    bytes_after = Path(binfile).read_bytes()
    assert bytes_before == bytes_after
    assert (
        "No Eclipse keywords found to compress in wrong.grdecl, skipping" in proc_output
    )


def test_iso8859(tmpdir):
    """Test that a text file with ISO-8859 encoding does
    not trigger bugs (and is written back as utf-8)"""
    tmpdir.chdir()
    nastyfile = "nastyfile.inc"
    Path(nastyfile).write_text(
        "-- Gullfaks Sør\nPORO\n 1 1 1 1/\n", encoding="ISO-8859-1"
    )
    main_eclcompress(nastyfile, None)
    assert "4*1" in open(nastyfile).read()  # Outputted file is always UTF-8


def test_utf8(tmpdir):
    """Test that we can parse and write a file with utf-8 chars"""
    tmpdir.chdir()
    nastyfile = "nastyfile.inc"
    Path(nastyfile).write_text("-- Gullfaks Sør\nPORO\n 1 1 1 1/\n")
    main_eclcompress(nastyfile, None)
    assert "4*1" in open(nastyfile).read()


@pytest.fixture(name="eclincludes")
def fixture_eclincludes(tmpdir):
    """Provide a directory structure with grdecl files in it"""
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


@pytest.mark.usefixtures("eclincludes")
def test_default_pattern():
    """Check how eclcompress behaves as a command line
    tool in a standardized directory structure"""
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


@pytest.mark.usefixtures("eclincludes", "twofiles")
def test_files_override_default_wildcards():
    """Default wildcardlist will not be used if explicit files are provided"""
    assert "0 0 0 0" in open("perm.grdecl").read()
    assert "0 0 0 0" in open("eclipse/include/props/perm.grdecl").read()
    main_eclcompress("perm.grdecl", None)
    assert "13*0" in open("perm.grdecl").read()
    assert "13*0" not in open("eclipse/include/props/perm.grdecl").read()


@pytest.fixture
def twofiles(tmpdir):
    """Provide a tmpdir with two sample grdecl files and a filepattern file"""
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
@pytest.mark.usefixtures("twofiles")
def test_compress_files_filelist(args):
    """Test the command line options for giving in both excplicit files and
    a list of file(pattern)s"""

    main_eclcompress(args[0], args[1])

    assert "File compressed with eclcompress" in open("perm.grdecl").read()
    assert "File compressed with eclcompress" in open("poro.grdecl").read()
    assert "13*0" in open("perm.grdecl").read()
    assert "7*1" in open("poro.grdecl").read()


@pytest.mark.usefixtures("twofiles")
def text_compress_argparse_1():
    """Test also the command line interface with --files"""
    sys.argv = ["eclcompress", "--files", "files"]
    main()
    assert "File compressed with eclcompress" in open("perm.grdecl").read()
    assert "File compressed with eclcompress" in open("poro.grdecl").read()
    assert "13*0" in open("perm.grdecl").read()
    assert "7*1" in open("poro.grdecl").read()


@pytest.mark.usefixtures("twofiles")
def text_compress_argparse_2():
    """Command line options, explicit files vs. --files"""
    sys.argv = ["eclcompress", "perm.grdecl", "--files", "files"]
    main()
    assert "File compressed with eclcompress" in open("perm.grdecl").read()
    assert "File compressed with eclcompress" in open("poro.grdecl").read()
    assert "13*0" in open("perm.grdecl").read()
    assert "7*1" in open("poro.grdecl").read()


@pytest.mark.usefixtures("twofiles")
def text_compress_argparse_3():
    """Command line options, explicit files vs. --files"""
    sys.argv = ["eclcompress", "perm.grdecl"]
    main()
    assert "File compressed with eclcompress" in open("perm.grdecl").read()
    assert "File compressed with eclcompress" not in open("poro.grdecl").read()
    assert "13*0" in open("perm.grdecl").read()
    assert "7*1" not in open("poro.grdecl").read()


def test_glob_patterns(tmpdir):
    """Test globbing filepatterns from a file with patterns"""
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


def test_eclkw_regexp(tmpdir):
    tmpdir.chdir()

    uncompressed_str = "G1\n0 0 0 0 0 0 0 0 0 0 0 0 0\n/"

    # Nothing is found by default here.
    assert not find_keyword_sets(uncompressed_str.split())

    # Only if we specify a regexp catching this odd keyword name:

    kw_sets = find_keyword_sets(uncompressed_str.split(), eclkw_regexp="G1")
    kwend_idx = len(uncompressed_str.split()) - 1
    assert kw_sets == [(0, kwend_idx)]
    assert compress_multiple_keywordsets(kw_sets, uncompressed_str.split()) == [
        "G1",
        "  13*0",
        "/",
    ]

    with open("g1.grdecl", "w") as f_handle:
        f_handle.write(uncompressed_str)

    # Alternative regexpes that should also work with this G1:
    kw_sets = find_keyword_sets(
        uncompressed_str.split(), eclkw_regexp="[A-Z]{1-8}$"
    ) == [(0, kwend_idx)]

    kw_sets = find_keyword_sets(
        uncompressed_str.split(), eclkw_regexp="[A-Z0-9]{2-8}$"
    ) == [(0, kwend_idx)]

    sys.argv = ["eclcompress", "g1.grdecl", "--eclkw_regexp", "G1"]
    main()
    compressed = open("g1.grdecl").read()
    assert "File compressed with eclcompress" in compressed
    assert "13*0" in compressed
