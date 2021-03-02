import os
from pathlib import Path

import subprocess
import filecmp
import pytest

from subscript.pack_sim import pack_sim

ECLDIR = Path(__file__).absolute().parent / "data" / "reek" / "eclipse" / "model"
ECLCASE = "2_R001_REEK-0.DATA"

# pylint: disable=protected-access


@pytest.mark.integration
def test_integration():
    """Test that endpoint is installed"""
    assert subprocess.check_output(["pack_sim", "-h"])


@pytest.mark.integration
def test_main(tmpdir, mocker):
    """Test invocation from command line"""
    tmpdir.chdir()

    datafilepath = ECLDIR / ECLCASE
    mocker.patch("sys.argv", ["pack_sim", str(datafilepath), "."])
    pack_sim.main()

    assert Path(ECLCASE).exists()
    assert Path("include").exists()


def test_binary_file_detection(tmpdir):
    """Test that binary files are found and handled correctly"""

    tmpdir.chdir()

    packing_path = "./packed"
    tmp_data_file = "TMP.DATA"
    egrid_file = "2_R001_REEK-0.EGRID"

    Path("TMP.DATA").write_text(f"GDFILE\n'{egrid_file}' /")

    os.mkdir(packing_path)
    os.mkdir(packing_path + "/include")
    pack_sim.inspect_file(tmp_data_file, str(ECLDIR) + "/", packing_path, "", "", False)

    assert filecmp.cmp(
        "%s/%s" % (ECLDIR, egrid_file), "%s/include/%s" % (packing_path, egrid_file)
    )


def test_empty_file_inspection(tmpdir):
    """Test that an empty include file is inspected correctly"""

    tmpdir.chdir()

    empty_include_file = "empty.inc"

    packing_path = Path("packed")
    Path(empty_include_file).write_text("")

    os.mkdir(packing_path)
    os.mkdir(packing_path / "include")

    include_text = pack_sim.inspect_file(
        empty_include_file, str(ECLDIR) + "/", str(packing_path), "", "", False
    )

    assert isinstance(include_text, str)
    assert len(include_text) == 0


def test_strip_comments(tmpdir, mocker):
    """Test that we can strip comments"""
    tmpdir.chdir()

    datafilepath = ECLDIR / ECLCASE
    size_with_comments = os.stat(datafilepath).st_size
    mocker.patch("sys.argv", ["pack_sim", "-c", str(ECLDIR / ECLCASE), "."])
    pack_sim.main()
    size_no_comments = os.stat(ECLCASE).st_size
    assert size_no_comments < size_with_comments
    assert "--" not in Path(ECLCASE).read_text()
    for includefile in os.listdir("include"):
        assert "--" not in (Path("include") / includefile).read_text()


def test_replace_paths():
    """Test that we are able to replace paths for include file reorganization"""
    test_str = " $ECLINCLUDE/grid/foo.grdecl \n $ECLINCLUDE/props/satnums.inc"
    paths = {"ECLINCLUDE": "include"}
    transformed_str = pack_sim._replace_paths(test_str, paths)
    assert "ECLINCLUDE" not in transformed_str
    assert "include" in transformed_str


def test_get_paths(tmpdir):
    """Test that we can obtain the PATHS keyword from a deck"""
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
    """Test removal of Eclipse style comments from strings"""
    test_str = "faljklj a -- a comment\n--\n\n    --"
    assert "--" not in pack_sim._remove_comments(True, test_str)
    assert "--" in pack_sim._remove_comments(False, test_str)


def test_md5sum(tmpdir):
    """Check md5sum computations from files"""
    tmpdir.chdir()
    test_str = "foo bar com"
    with open("foo.txt", "w") as fhandle:
        fhandle.write(test_str)
    assert pack_sim._md5checksum("foo.txt") == pack_sim._md5checksum(data=test_str)
    with pytest.raises(ValueError):
        pack_sim._md5checksum("foo.txt", test_str)

    # Check that the result is hexadecimal using int(x, 16)
    int(pack_sim._md5checksum("foo.txt"), 16)


def test_utf8(tmpdir):
    """Test that no errors are triggered when UTF-8 input is provided"""
    tmpdir.chdir()
    datafile_str = """RUNSPEC
TITLE
Smørbukk Sør
"""
    Path("FOO.DATA").write_text(datafile_str)
    pack_sim.pack_simulation("FOO.DATA", "somedir", True, False)
    assert Path("somedir/FOO.DATA").read_text() == datafile_str
