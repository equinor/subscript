"""Test eclcompress with  pytest"""

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import opm.io
import pytest
from subscript.eclcompress.eclcompress import (
    compress_multiple_keywordsets,
    eclcompress,
    file_is_binary,
    find_keyword_sets,
    glob_patterns,
    main,
    main_eclcompress,
    parse_wildcardfile,
)

TESTDATADIR = Path(__file__).absolute().parent / "testdata_eclcompress"

# A permissive parser variant from OPM is used to verify some tests:
OPMIO_PARSECONTEXT = opm.io.ParseContext(
    [
        ("PARSE_INVALID_KEYWORD_COMBINATION", opm.io.action.ignore),
        ("PARSE_MISSING_DIMS_KEYWORD", opm.io.action.ignore),
    ]
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


def test_empty_file(tmp_path):
    """Check that compression of empty files is a noop"""
    os.chdir(tmp_path)
    emptyfilename = "emptyfile.grdecl"
    Path(emptyfilename).write_text("", encoding="utf8")
    assert os.stat(emptyfilename).st_size == 0
    main_eclcompress(emptyfilename, None)
    assert os.stat(emptyfilename).st_size == 0


def test_no_touch_non_eclipse(tmp_path):
    """Check that we do not change a file that does not contain
    any Eclipse data"""
    os.chdir(tmp_path)
    filename = "foo.txt"
    Path(filename).write_text(
        "Some random text\nAnother line\nbut no Eclipse keywords", encoding="utf8"
    )
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
        "1 1 / nasty comment/",
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
        "1 1//",
        "2 2 / foo",
        "/",
    ]


def test_only_allowlist_compressed(tmp_path):
    """Ensure that only keywords in the allowlist are compressed
    when no regex is supplied."""
    given = """
ZCORN
  3 3 3 3 /
PVTO
  0.000       1.0    1.0              0.645
             25.0    1.06657          0.668
/
FIPNUM
  2 4 4 5 5 6
/
"""
    filelines = given.splitlines()
    kw_sets = find_keyword_sets(filelines)
    expected = [
        "",
        "ZCORN",
        "  4*3 /",
        "PVTO",
        "  0.000       1.0    1.0              0.645",
        "             25.0    1.06657          0.668",
        "/",
        "FIPNUM",
        "  2 2*4 2*5 6",
        "/",
    ]

    assert compress_multiple_keywordsets(kw_sets, filelines) == expected


def test_whitespace(tmp_path):
    """Ensure excessive whitespace is not added"""
    kw_string = """
MULTIPLY
  'PORO' 2 /
/"""
    filelines = kw_string.splitlines()
    kw_sets = find_keyword_sets(filelines)
    assert compress_multiple_keywordsets(kw_sets, filelines) == filelines

    # Test the same when the string is read from a file:
    os.chdir(tmp_path)
    Path("test.inc").write_text(kw_string, encoding="utf8")
    eclcompress("test.inc")
    compressed_lines = Path("test.inc").read_text(encoding="utf8").splitlines()

    # The compressed output should have only two header lines added and one
    # empty lines after the header added:
    assert len(compressed_lines) == len(filelines) + 3


def test_formatting():
    """Test that compressed output is only 79 characters wide"""
    numbers = " ".join([str(number) for number in np.random.rand(1, 100)[0]])
    filelines = ["PORO", numbers, "/"]
    formatted = compress_multiple_keywordsets(find_keyword_sets(filelines), filelines)
    assert max([len(line) for line in formatted]) <= 79

    # But, some keywords will not tolerate random
    # newlines in their data-section, at least the multi-record keywords.
    # So we should never wrap a line with a slash in it:
    filelines = ["MULTZ-", " FOO" * 30 + " /"]
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
""".splitlines()
    kwsets = find_keyword_sets(filelines)
    assert (
        compress_multiple_keywordsets(kwsets, filelines)
        == """
SPECGRID
214  669  49   1  F  /

GDORIENT
INC INC INC DOWN RIGHT /

ZCORN
  6*1 /
""".splitlines()
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
    assert opm.io.Parser().parse_string(compressedstr, OPMIO_PARSECONTEXT)


@pytest.mark.integration
def test_integration():
    """Test endpoint is installed"""
    assert subprocess.check_output(["eclcompress", "-h"])


def test_vfpprod(tmp_path, mocker):
    """VFPPROD contains multiple record data, for which E100
    fails if the record-ending slash is not on the same line as the data
    """
    os.chdir(tmp_path)
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
    assert opm.io.Parser().parse_string(vfpstr, OPMIO_PARSECONTEXT)

    # Call eclcompress as script on vfpstr:
    Path("vfpfile.inc").write_text(vfpstr, encoding="utf8")
    mocker.patch("sys.argv", ["eclcompress", "--keeporiginal", "vfpfile.inc"])
    main()

    # Check that OPM can parse the output (but in this case, OPM allows
    # having the slashes on the next line, so it is not a good test)
    assert opm.io.Parser().parse_string(
        Path("vfpfile.inc").read_text(encoding="utf8"), OPMIO_PARSECONTEXT
    )

    # Verify that a slash at record-end is still there. This test will pass
    # whether eclcompress is just skipping the file, or of it is able to
    # compress it correctly.
    assert "8000 10000 /" in Path("vfpfile.inc").read_text(encoding="utf8")


def test_main(tmp_path, mocker):
    """Test installed endpoint"""

    os.chdir(tmp_path)

    Path("testdeck.inc").write_text("\n".join(FILELINES), encoding="utf8")

    mocker.patch("sys.argv", ["eclcompress", "--keeporiginal", "testdeck.inc"])
    main()

    assert os.path.exists("testdeck.inc.orig")
    assert os.path.exists("testdeck.inc")
    compressedlines = Path("testdeck.inc").read_text(encoding="utf8").splitlines()
    compressedbytes = sum([len(x) for x in compressedlines if not x.startswith("--")])
    origbytes = sum([len(x) for x in FILELINES])

    assert compressedbytes < origbytes

    compressedstr = "\n".join(compressedlines)
    assert opm.io.Parser().parse_string(compressedstr, OPMIO_PARSECONTEXT)


def test_binary_file(tmp_path):
    """Test that a random binary file is untouched by eclcompress"""
    os.chdir(tmp_path)
    binfile = "wrong.grdecl"
    Path(binfile).write_bytes(os.urandom(100))
    bytes_before = Path(binfile).read_bytes()
    proc_result = subprocess.run(
        "eclcompress --verbose  " + binfile, check=True, shell=True, capture_output=True
    )
    proc_output = proc_result.stdout.decode() + proc_result.stderr.decode()
    bytes_after = Path(binfile).read_bytes()
    assert bytes_before == bytes_after
    assert "Skipped wrong.grdecl, not text file" in proc_output


def test_iso8859(tmp_path):
    """Test that a text file with ISO-8859 encoding does
    not trigger bugs (and is written back as utf-8)"""
    os.chdir(tmp_path)
    nastyfile = "nastyfile.inc"
    Path(nastyfile).write_text(
        "-- Gullfaks Sør\nPORO\n 1 1 1 1/\n", encoding="ISO-8859-1"
    )
    main_eclcompress(nastyfile, None)
    assert "4*1" in Path(nastyfile).read_text(encoding="utf8")


def test_utf8(tmp_path):
    """Test that we can parse and write a file with utf-8 chars"""
    os.chdir(tmp_path)
    nastyfile = "nastyfile.inc"
    Path(nastyfile).write_text("-- Gullfaks Sør\nPORO\n 1 1 1 1/\n", encoding="utf8")
    main_eclcompress(nastyfile, None)
    assert "4*1" in Path(nastyfile).read_text(encoding="utf8")


@pytest.fixture(name="eclincludes")
def fixture_eclincludes(tmp_path):
    """Provide a directory structure with grdecl files in it"""
    os.chdir(tmp_path)
    os.makedirs("eclipse/include/props")
    os.makedirs("eclipse/include/regions")
    Path("eclipse/include/props/perm.grdecl").write_text(
        "PERMX\n0 0 0 0 0 0 0 0 0 0 0 0 0\n/", encoding="utf8"
    )
    Path("eclipse/include/regions/fipnum.grdecl").write_text(
        "FIPNUM\n0 0 0 0 0 0 0 0 0 0 0 0 0\n/", encoding="utf8"
    )
    yield


@pytest.mark.usefixtures("eclincludes")
def test_default_pattern():
    """Check how eclcompress behaves as a command line
    tool in a standardized directory structure"""
    main_eclcompress(None, None)
    assert "File compressed with eclcompress" in Path(
        "eclipse/include/props/perm.grdecl"
    ).read_text(encoding="utf8")
    assert "File compressed with eclcompress" in Path(
        "eclipse/include/regions/fipnum.grdecl"
    ).read_text(encoding="utf8")
    assert "13*0" in Path("eclipse/include/props/perm.grdecl").read_text(
        encoding="utf8"
    )


@pytest.mark.usefixtures("eclincludes", "twofiles")
def test_files_override_default_wildcards():
    """Default wildcardlist will not be used if explicit files are provided"""
    assert "0 0 0 0" in Path("perm.grdecl").read_text(encoding="utf8")
    assert "0 0 0 0" in Path("eclipse/include/props/perm.grdecl").read_text(
        encoding="utf8"
    )
    main_eclcompress("perm.grdecl", None)
    assert "13*0" in Path("perm.grdecl").read_text(encoding="utf8")
    assert "13*0" not in Path("eclipse/include/props/perm.grdecl").read_text(
        encoding="utf8"
    )


@pytest.fixture
def twofiles(tmp_path):
    """Provide a tmp_path with two sample grdecl files and a filepattern file"""
    os.chdir(tmp_path)

    Path("perm.grdecl").write_text(
        "PERMX\n0 0 0 0 0 0 0 0 0 0 0 0 0\n/", encoding="utf8"
    )
    Path("poro.grdecl").write_text("PORO\n1 1 1 1 1 1 1\n/", encoding="utf8")

    Path("filelist").write_text("*.grdecl", encoding="utf8")
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

    assert "File compressed with eclcompress" in Path("perm.grdecl").read_text(
        encoding="utf8"
    )
    assert "File compressed with eclcompress" in Path("poro.grdecl").read_text(
        encoding="utf8"
    )
    assert "13*0" in Path("perm.grdecl").read_text(encoding="utf8")
    assert "7*1" in Path("poro.grdecl").read_text(encoding="utf8")


@pytest.mark.usefixtures("twofiles")
def text_compress_argparse_1(mocker):
    """Test also the command line interface with --files"""
    mocker.patch("sys.argv", ["eclcompress", "--files", "files"])
    main()
    assert "File compressed with eclcompress" in Path("perm.grdecl").read_text(
        encoding="utf8"
    )
    assert "File compressed with eclcompress" in Path("poro.grdecl").read_text(
        encoding="utf8"
    )
    assert "13*0" in Path("perm.grdecl").read_text(encoding="utf8")
    assert "7*1" in Path("poro.grdecl").read_text(encoding="utf8")


@pytest.mark.usefixtures("twofiles")
def text_compress_argparse_2(mocker):
    """Command line options, explicit files vs. --files"""
    mocker.patch("sys.argv", ["eclcompress", "perm.grdecl", "--files", "files"])
    main()
    assert "File compressed with eclcompress" in Path("perm.grdecl").read_text(
        encoding="utf8"
    )
    assert "File compressed with eclcompress" in Path("poro.grdecl").read_text(
        encoding="utf8"
    )
    assert "13*0" in Path("perm.grdecl").read_text(encoding="utf8")
    assert "7*1" in Path("poro.grdecl").read_text(encoding="utf8")


@pytest.mark.usefixtures("twofiles")
def text_compress_argparse_3(mocker):
    """Command line options, explicit files vs. --files"""
    mocker.patch("sys.argv", ["eclcompress", "perm.grdecl"])
    main()
    assert "File compressed with eclcompress" in Path("perm.grdecl").read_text(
        encoding="utf8"
    )
    assert "File compressed with eclcompress" not in Path("poro.grdecl").read_text(
        encoding="utf8"
    )
    assert "13*0" in Path("perm.grdecl").read_text(encoding="utf8")
    assert "7*1" not in Path("poro.grdecl").read_text(encoding="utf8")


def test_glob_patterns(tmp_path):
    """Test globbing filepatterns from a file with patterns"""
    os.chdir(tmp_path)

    dummyfiles = ["perm.grdecl", "poro.grdecl"]

    for dummyfile in dummyfiles:
        Path(dummyfile).write_text("", encoding="utf8")
    Path("filelist").write_text("*.grdecl", encoding="utf8")

    assert set(glob_patterns(parse_wildcardfile("filelist"))) == set(dummyfiles)

    Path("filelist_dups").write_text(
        """
*.grdecl
poro.grdecl
p*ecl
perm.grdecl""",
        encoding="utf8",
    )
    assert set(glob_patterns(parse_wildcardfile("filelist_dups"))) == set(dummyfiles)

    Path("filelist_comments").write_text(
        "-- this is a comment\n*.grdecl\n# some  comment", encoding="utf8"
    )
    assert set(glob_patterns(parse_wildcardfile("filelist_dups"))) == set(dummyfiles)

    Path("filelist_comments").write_text(
        "# this is a comment\n*.grdecl\n# some  comment", encoding="utf8"
    )
    assert set(glob_patterns(parse_wildcardfile("filelist_dups"))) == set(dummyfiles)
    Path("filelist_comments").write_text(
        "  # this is a comment\n*.grdecl # comment along pattern", encoding="utf8"
    )
    assert set(glob_patterns(parse_wildcardfile("filelist_dups"))) == set(dummyfiles)

    with pytest.raises(IOError):
        parse_wildcardfile("")

    with pytest.raises(IOError):
        parse_wildcardfile("notthere")


def test_binary_example_file(tmp_path, mocker):
    """Test that a particular binary file is not touched by eclcompress

    (historical bug)
    """
    os.chdir(tmp_path)
    filename = "permxyz.grdecl"
    shutil.copy(TESTDATADIR / filename, filename)
    origfilehash = hashlib.sha256(Path(filename).read_bytes()).hexdigest()
    mocker.patch("sys.argv", ["eclcompress", "--verbose", filename])
    main()
    afterfilehash = hashlib.sha256(Path(filename).read_bytes()).hexdigest()
    assert origfilehash == afterfilehash


@pytest.mark.parametrize(
    "byte_sequence, expected",
    [
        ("foo", False),
        ("foo æøå", False),
        (bytearray([0, 30, 50, 100, 129]), True),  # "random" bytes
        (bytearray([7, 8, 9, 10, 12, 13, 27]), False),  # allow-listed bytes.
        (bytearray("foo".encode()), False),
        # Null-terminated string makes it binary:
        (bytearray("foo".encode()) + bytearray([0]), True),
        # Only first 1024 characters are checked, so we can fool it:
        (bytearray([7] * 1024), False),
        (bytearray([7] * 1023 + [0]), True),
        (bytearray([7] * 1024 + [0]), False),
    ],
)
def test_file_is_binary(byte_sequence, expected, tmp_path):
    """Test binary file detection"""
    os.chdir(tmp_path)
    if isinstance(byte_sequence, str):
        Path("foo-utf8.txt").write_text(byte_sequence, encoding="utf-8")
        assert file_is_binary("foo-utf8.txt") == expected

        Path("foo-iso8859.txt").write_text(byte_sequence, encoding="iso-8859-1")
        assert file_is_binary("foo-iso8859.txt") == expected
    else:
        Path("foo.txt").write_bytes(byte_sequence)
        assert file_is_binary("foo.txt") == expected
