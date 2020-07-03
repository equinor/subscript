from __future__ import absolute_import

import os
import sys

import subprocess
import filecmp
import pytest

from subscript.pack_sim import pack_sim

ECLDIR = os.path.join(os.path.dirname(__file__), "data/reek/eclipse/model")
ECLCASE = "2_R001_REEK-0.DATA"


@pytest.mark.integration
def test_integration():
    """Test that endpoint is installed"""
    assert subprocess.check_output(["pack_sim", "-h"])


def test_main(tmpdir):

    tmpdir.chdir()

    datafilepath = os.path.join(ECLDIR, ECLCASE)
    sys.argv = ["pack_sim", datafilepath, "."]
    pack_sim.main()

    assert os.path.exists(ECLCASE)
    assert os.path.exists("include")


def test_binary_file_detection(tmpdir):
    """Test that binary files are found and handled correctly"""

    tmpdir.chdir()

    packing_path = "./packed"
    tmp_data_file = "TMP.DATA"
    egrid_file = "2_R001_REEK-0.EGRID"

    test_str = "GDFILE\n" f"'{egrid_file}' /"
    with open("TMP.DATA", "w") as fhandle:
        fhandle.write(test_str)

    os.mkdir(packing_path)
    os.mkdir(packing_path + "/include")
    pack_sim.inspect_file(tmp_data_file, ECLDIR + "/", packing_path, "", "", False)

    assert filecmp.cmp(f"{ECLDIR}/{egrid_file}", f"{packing_path}/include/{egrid_file}")


def test_empty_file_inspection(tmpdir):
    """Test that an empty include file is inspected correctly"""

    tmpdir.chdir()

    empty_include_file = "empty.inc"

    packing_path = "./packed"
    os.mknod(empty_include_file)

    os.mkdir(packing_path)
    os.mkdir(packing_path + "/include")

    include_text = pack_sim.inspect_file(
        empty_include_file, ECLDIR + "/", packing_path, "", "", False
    )

    assert isinstance(include_text, str)
    assert len(include_text) == 0


def test_strip_comments(tmpdir):
    """Test that we can strip comments"""
    tmpdir.chdir()

    datafilepath = os.path.join(ECLDIR, ECLCASE)
    size_with_comments = os.stat(datafilepath).st_size
    sys.argv = ["pack_sim", "-c", os.path.join(ECLDIR, ECLCASE), "."]
    pack_sim.main()
    size_no_comments = os.stat(ECLCASE).st_size
    assert size_no_comments < size_with_comments
    assert "--" not in "".join(open(ECLCASE).readlines())
    for includefile in os.listdir("include"):
        assert "--" not in "".join(
            open(os.path.join("include", includefile)).readlines()
        )


def test_replace_paths():
    test_str = " $ECLINCLUDE/grid/foo.grdecl \n $ECLINCLUDE/props/satnums.inc"
    paths = {"ECLINCLUDE": "include"}
    transformed_str = pack_sim._replace_paths(test_str, paths)
    assert "ECLINCLUDE" not in transformed_str
    assert "include" in transformed_str


def test_get_paths(tmpdir):
    tmpdir.chdir()
    file = "pathfile"
    os.mkdir("somepath")
    with open(file, "w") as fhandle:
        fhandle.write("PATHS\n  'IDENTIFIER' 'somepath'/\n")
    path_dict = pack_sim._get_paths(file, ".")
    assert path_dict["IDENTIFIER"] == "somepath"


def test_normalize_line_endings():
    """Test line ending normalization"""

    assert pack_sim.EOL_WINDOWS not in pack_sim._normalize_line_endings(
        "foobar" + pack_sim.EOL_WINDOWS
    )
    assert pack_sim.EOL_MAC not in pack_sim._normalize_line_endings(
        "foobar" + pack_sim.EOL_MAC
    )


def test_remove_comments():
    test_str = "faljklj a -- a comment\n--\n\n    --"
    assert "--" not in pack_sim._remove_comments(True, test_str)
    assert "--" in pack_sim._remove_comments(False, test_str)


def test_md5sum(tmpdir):
    test_str = "foo bar com"
    with open("foo.txt", "w") as fhandle:
        fhandle.write(test_str)
    assert pack_sim._md5checksum("foo.txt") == pack_sim._md5checksum(data=test_str)
    with pytest.raises(ValueError):
        pack_sim._md5checksum("foo.txt", test_str)

    # Check that the result is hexadecimal using int(x, 16)
    int(pack_sim._md5checksum("foo.txt"), 16)
