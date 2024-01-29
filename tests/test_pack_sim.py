import filecmp
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from subscript.pack_sim import pack_sim

ECLDIR = Path(__file__).absolute().parent / "data" / "reek" / "eclipse" / "model"
ECLCASE = "2_R001_REEK-0.DATA"
ISO_8859_VFP = Path(__file__).absolute().parent / "data" / "vfp" / "pd2.VFP"

# pylint: disable=protected-access


@pytest.mark.integration
def test_integration():
    """Test that endpoint is installed"""
    assert subprocess.check_output(["pack_sim", "-h"])


@pytest.mark.integration
def test_main(tmp_path, mocker):
    """Test invocation from command line"""
    os.chdir(tmp_path)

    datafilepath = ECLDIR / ECLCASE
    mocker.patch("sys.argv", ["pack_sim", str(datafilepath), "."])
    pack_sim.main()

    assert Path(ECLCASE).exists()
    assert Path("include/reek.grid").exists()
    assert Path("include/reek.perm").exists()
    assert Path("include/reek.pvt").exists()
    assert Path("include/swof.inc").exists()


def test_main_fmu(tmp_path, mocker):
    """Test the --fmu option on the command line, yielding
    a different directory layout"""
    os.chdir(tmp_path)

    datafilepath = ECLDIR / ECLCASE
    mocker.patch("sys.argv", ["pack_sim", str(datafilepath), ".", "--fmu"])
    pack_sim.main()

    # Test a subset of the files that should be there, paths
    # here are different from the test above without the "--fmu" option:
    assert (Path("model") / Path(ECLCASE)).exists()
    assert Path("include/edit").exists()
    assert Path("include/grid/reek.grid").exists()
    assert Path("include/props/reek.pvt").exists()


def test_repeated_run(tmp_path, mocker):
    """Test what happens on repeated incovations"""
    os.chdir(tmp_path)

    datafilepath = ECLDIR / ECLCASE
    mocker.patch("sys.argv", ["pack_sim", str(datafilepath), ".", "--fmu"])
    pack_sim.main()

    with pytest.raises(ValueError, match="will not overwrite"):
        pack_sim.main()

    os.remove("model/" + ECLCASE)
    # Here it will reuse the packed include files:
    pack_sim.main()

    # But error if a file is not writable:
    os.remove("model/" + ECLCASE)
    os.chmod("include/grid/reek.perm", 0)
    with pytest.raises(IOError):
        pack_sim.main()


@pytest.mark.parametrize(
    "injected, expectedwarning",
    [
        ("IMPFILE", "WARNING: THE SIMULATION CONTAINS THE IMPFILE KEYWORD"),
        ("USEFLUX", "WARNING: THE SIMULATION DEPENDS ON A USEFLUX FILE"),
        ("RESTART", "WARNING: THE SIMULATION POSSIBLY DEPENDS ON A RESTART FILE"),
    ],
)
def test_restart_warning(injected, expectedwarning, tmp_path, mocker, capsys):
    """Test that warnings are emitted on various contents in the DATA file"""
    os.chdir(tmp_path)

    shutil.copytree(ECLDIR.parent / "include", "include", copy_function=os.symlink)
    shutil.copytree(ECLDIR.parent / "model", "model", copy_function=os.symlink)
    os.remove("model/" + ECLCASE)
    shutil.copy(ECLDIR.parent / "model" / ECLCASE, "model/" + ECLCASE)

    datafile = Path("model") / ECLCASE
    mocker.patch("sys.argv", ["pack_sim", str(datafile), "."])

    modifieddata = "\n".join(
        datafile.read_text(encoding="utf8").splitlines() + [injected]
    )
    datafile.write_text(modifieddata, encoding="utf8")

    pack_sim.main()

    captured = capsys.readouterr()
    assert expectedwarning in captured.out


def test_binary_file_detection(tmp_path):
    """Test that binary files are found and handled correctly"""

    os.chdir(tmp_path)

    packing_path = Path("packed")
    tmp_data_file = Path("TMP.DATA")
    egrid_file = "2_R001_REEK-0.EGRID"

    tmp_data_file.write_text(f"GDFILE\n'{egrid_file}' /", encoding="utf8")

    (packing_path / "include").mkdir(parents=True)

    pack_sim.inspect_file(tmp_data_file, ECLDIR, packing_path, "", "", False)

    assert filecmp.cmp(f"{ECLDIR}/{egrid_file}", f"{packing_path}/include/{egrid_file}")


def test_empty_file_inspection(tmp_path):
    """Test that an empty include file is inspected correctly"""

    os.chdir(tmp_path)

    empty_include_file = Path("empty.inc")

    packing_path = Path("packed")
    empty_include_file.write_text("", encoding="utf8")

    (packing_path / "include").mkdir(parents=True)

    include_text = pack_sim.inspect_file(
        empty_include_file, ECLDIR / packing_path, "", "", False
    )

    assert isinstance(include_text, str)
    assert len(include_text) == 0


def test_strip_comments(tmp_path, mocker):
    """Test that we can strip comments"""
    os.chdir(tmp_path)

    datafilepath = ECLDIR / ECLCASE
    size_with_comments = os.stat(datafilepath).st_size
    mocker.patch("sys.argv", ["pack_sim", "-c", str(ECLDIR / ECLCASE), "."])
    pack_sim.main()
    size_no_comments = os.stat(ECLCASE).st_size
    assert size_no_comments < size_with_comments
    assert "--" not in Path(ECLCASE).read_text(encoding="utf8")
    for includefile in os.listdir("include"):
        assert "--" not in (Path("include") / includefile).read_text()


def test_extra_include_due_to_comment(tmp_path, mocker):
    """Test that comment after INCLUDE/IMPORT/GDFILE is transferred correctly"""
    os.chdir(tmp_path)

    some_include = "some.inc"
    with open(some_include, "w", encoding="utf-8") as fout:
        fout.write("-- Comment")

    data_file = "TMP.DATA"
    with open(data_file, "w", encoding="utf-8") as fout:
        fout.write(f"INCLUDE\n--Comment\n  '{some_include}' /")
    mocker.patch("sys.argv", ["pack_sim", data_file, "out/"])
    pack_sim.main()

    # Test that comment is process properly after INCLUDE keyword
    assert "INCLUDE\nINCLUDE" not in Path(f"out/{data_file}").read_text(encoding="utf8")


def test_replace_paths():
    """Test that we are able to replace paths for include file reorganization"""
    test_str = " $ECLINCLUDE/grid/foo.grdecl \n $ECLINCLUDE/props/satnums.inc"
    paths = {"ECLINCLUDE": "include"}
    transformed_str = pack_sim._replace_paths(test_str, paths)
    assert "ECLINCLUDE" not in str(transformed_str)
    assert "include" in str(transformed_str)


def test_get_paths(tmp_path):
    """Test that we can obtain the PATHS keyword from a deck"""
    os.chdir(tmp_path)
    file_with_path = Path("pathfile")
    Path("somepath").mkdir()
    file_with_path.write_text("PATHS\n  'IDENTIFIER' 'somepath'/\n", encoding="utf8")
    path_dict = pack_sim._get_paths(file_with_path, Path("."))
    assert path_dict["IDENTIFIER"] == Path("somepath")


def test_normalize_line_endings():
    """Test line ending normalization"""

    # Test default ("unix")
    assert pack_sim.EOL_WINDOWS not in pack_sim._normalize_line_endings(
        "foobar" + pack_sim.EOL_WINDOWS
    )
    assert pack_sim.EOL_WINDOWS not in pack_sim._normalize_line_endings(
        "foobar" + pack_sim.EOL_WINDOWS, "unix"
    )
    assert pack_sim.EOL_MAC not in pack_sim._normalize_line_endings(
        "foobar" + pack_sim.EOL_MAC
    )

    # Test mac
    assert pack_sim.EOL_MAC in pack_sim._normalize_line_endings(
        "foobar" + pack_sim.EOL_MAC, "mac"
    )
    assert pack_sim.EOL_WINDOWS not in pack_sim._normalize_line_endings(
        "foobar" + pack_sim.EOL_UNIX, "mac"
    )
    assert pack_sim.EOL_WINDOWS not in pack_sim._normalize_line_endings(
        "foobar" + pack_sim.EOL_WINDOWS, "mac"
    )

    # Test Windows:
    assert pack_sim.EOL_WINDOWS in pack_sim._normalize_line_endings(
        "foobar" + pack_sim.EOL_WINDOWS, "windows"
    )


def test_remove_comments():
    """Test removal of Eclipse style comments from strings"""
    test_str = "faljklj a -- a comment\n--\n\n    --"
    assert "--" not in pack_sim._remove_comments(True, test_str)
    assert "--" in pack_sim._remove_comments(False, test_str)


def test_md5sum(tmp_path):
    """Check md5sum computations from files"""
    os.chdir(tmp_path)
    test_str = "foo bar com"
    Path("foo.txt").write_text(test_str, encoding="utf8")
    assert pack_sim._md5checksum("foo.txt") == pack_sim._md5checksum(data=test_str)
    with pytest.raises(ValueError):
        pack_sim._md5checksum("foo.txt", test_str)

    # Check that the result is hexadecimal using int(x, 16)
    int(pack_sim._md5checksum("foo.txt"), 16)


def test_utf8(tmp_path):
    """Test that no errors are triggered when UTF-8 input is provided"""
    os.chdir(tmp_path)
    datafile_str = """RUNSPEC
TITLE
Smørbukk Sør
"""
    Path("FOO.DATA").write_text(datafile_str, encoding="utf8")
    pack_sim.pack_simulation(Path("FOO.DATA"), Path("somedir"), True, False)
    assert Path("somedir/FOO.DATA").read_text(encoding="utf8") == datafile_str


def test_iso8859(tmp_path):
    """Test that no errors are triggered when ISO-8859-1 input is provided"""
    os.chdir(tmp_path)
    datafile_str = """RUNSPEC
TITLE
sm³
"""
    Path("FOO.DATA").write_text(datafile_str, encoding="iso-8859-1")
    iso_str = Path("FOO.DATA").read_text(encoding="iso-8859-1")

    pack_sim.pack_simulation(Path("FOO.DATA"), Path("somedir"), True, False)
    assert Path("somedir/FOO.DATA").read_text(encoding="utf8") == iso_str

    pack_sim.pack_simulation(ISO_8859_VFP, Path("somedir"), True, False)
    assert Path("somedir/pd2.VFP").exists()
