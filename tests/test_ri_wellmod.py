import os
from pathlib import Path
import subprocess
import pytest


from subscript.ri_wellmod import ri_wellmod

SCRIPTNAME = "ri_wellmod"
DATAPATH = Path(__file__).parent / "testdata_ri_wellmod"

try:
    # pylint: disable=unused-import
    import ert_shared  # noqa

    HAVE_ERT = True
except ImportError:
    HAVE_ERT = False


def drogon_runpath():
    """Return path to large test dataset"""
    drogon_on_prem_runpath = Path("/project/res/share/subscript/tests/data/drogon")
    drogon_alternative_path = Path(__file__).parent / "data" / "drogon"
    if drogon_on_prem_runpath.exists():
        return drogon_on_prem_runpath
    if drogon_alternative_path.exists():
        return drogon_alternative_path
    return None


def has_display():
    """
    Check if an X display is available
    """
    return "DISPLAY" in os.environ and os.environ["DISPLAY"]


def file_contains(filename, string_to_find):
    """
    Utility function to check if a file contains a given string.
    """
    if not Path(filename).exists():
        return False

    with open(filename) as fhandle:
        filetext = fhandle.read()
        return filetext.find(string_to_find) >= 0


@pytest.mark.integration
def test_integration():
    """Test that endpoint is installed"""
    assert subprocess.check_output([SCRIPTNAME, "-h"])


@pytest.mark.skipif(
    not ri_wellmod.get_resinsight_exe(), reason="Could not find a ResInsight executable"
)
@pytest.mark.skipif(drogon_runpath() is None, reason="Could not find Drogon data")
def test_main_initcase(tmpdir, mocker):
    """Test well data generation from init case"""
    tmpdir.chdir()

    proj_name = str(DATAPATH / "drogon_wells_noicd.rsp")
    init_case_name = str(drogon_runpath() / "eclipse/model/DROGON-0_NOSIM")
    outfile = "welldefs_initcase.sch"

    mocker.patch("sys.argv", [SCRIPTNAME, proj_name, init_case_name, "-o", outfile])
    ri_wellmod.main()
    assert Path(outfile).exists() and file_contains(outfile, "A4")


@pytest.mark.skipif(
    not ri_wellmod.get_resinsight_exe(),
    reason="Could not find a ResInsight executable",
)
def test_main_inputcase(tmpdir, mocker):
    """Test well data generation from input case"""
    tmpdir.chdir()

    proj_name = str(DATAPATH / "drogon_wells_noicd.rsp")
    grid_name = str(DATAPATH / "drogon_include/grid/drogon.grid.grdecl")
    perm_name = str(DATAPATH / "drogon_include/grid/drogon.perm.grdecl")
    ntg_name = str(DATAPATH / "drogon_include/grid/drogon.ntg.grdecl")
    outfile = "welldefs_inputcase.sch"

    mocker.patch(
        "sys.argv",
        [
            SCRIPTNAME,
            proj_name,
            grid_name,
            "--property_files",
            perm_name,
            ntg_name,
            "-o",
            outfile,
        ],
    )
    ri_wellmod.main()
    assert Path(outfile).exists() and file_contains(outfile, "A4")


@pytest.mark.skipif(
    not ri_wellmod.get_resinsight_exe(), reason="Could not find a ResInsight executable"
)
@pytest.mark.skipif(drogon_runpath() is None, reason="Could not find Drogon data")
def test_drogon_mswdef(tmpdir, mocker):
    """Test multi-segment well data generation"""
    tmpdir.chdir()

    proj_name = str(DATAPATH / "drogon_wells_noicd.rsp")
    init_case_name = str(drogon_runpath() / "eclipse/model/DROGON-0_NOSIM")
    outfile = "welldefs_msw.sch"

    mocker.patch(
        "sys.argv",
        [SCRIPTNAME, proj_name, init_case_name, "-o", outfile, "--msw", "A4,A2,R*"],
    )
    ri_wellmod.main()

    assert Path(outfile).exists() and file_contains(outfile, "A4")


@pytest.mark.skipif(
    not ri_wellmod.get_resinsight_exe(), reason="Could not find a ResInsight executable"
)
@pytest.mark.skipif(drogon_runpath() is None, reason="Could not find Drogon data")
def test_drogon_lgr(tmpdir, mocker):
    """Test creation of LGR"""
    tmpdir.chdir()

    proj_name = str(DATAPATH / "drogon_wells_noicd.rsp")
    init_case_name = str(drogon_runpath() / "eclipse/model/DROGON-0_NOSIM_LGR")
    outfile = "welldefs_lgr.sch"

    mocker.patch(
        "sys.argv",
        [SCRIPTNAME, proj_name, init_case_name, "-o", outfile, "--msw", "A4"],
    )
    ri_wellmod.main()

    assert Path(outfile).exists() and file_contains(outfile, "A4")


@pytest.mark.skipif(
    not ri_wellmod.get_resinsight_exe(), reason="Could not find a ResInsight executable"
)
@pytest.mark.skipif(drogon_runpath() is None, reason="Could not find Drogon data")
@pytest.mark.skipif(not has_display(), reason="Requires X display")
def test_main_lgr_cmdline(tmpdir, mocker):
    """Test creation of LGR"""
    tmpdir.chdir()

    proj_name = str(DATAPATH / "drogon_wells_noicd.rsp")
    init_case_name = str(drogon_runpath() / "eclipse/model/DROGON-0_NOSIM")
    outfile = "welldefs_lgr.sch"
    lgr_outfile = "lgr_defs.inc"

    mocker.patch(
        "sys.argv",
        [
            SCRIPTNAME,
            proj_name,
            init_case_name,
            "-o",
            outfile,
            "--msw",
            "A4,A2",
            "--lgr_output_file",
            lgr_outfile,
            "--lgr",
            "A4:3,3,1",
        ],
    )
    ri_wellmod.main()

    assert Path(outfile).exists() and file_contains(outfile, "A4")
    assert Path(lgr_outfile).exists() and file_contains(lgr_outfile, "CARFIN")


@pytest.mark.integration
@pytest.mark.skipif(
    not ri_wellmod.get_resinsight_exe(), reason="Could not find a ResInsight executable"
)
@pytest.mark.skipif(drogon_runpath() is None, reason="Could not find Drogon data")
@pytest.mark.skipif(not HAVE_ERT, reason="Requires ERT")
def test_ert_forward_model(tmpdir):
    """Test that the ERT hook can run on a mocked case"""
    # pylint: disable=redefined-outer-name
    # pylint: disable=unused-argument
    tmpdir.chdir()

    proj_name = str(DATAPATH / "drogon_wells_noicd.rsp")
    init_case_name = str(drogon_runpath() / "eclipse/model/DROGON-0_NOSIM")
    outfile = "welldefs_lgr.sch"

    with open("FOO.DATA", "w") as file_h:
        file_h.write("--Empty")
    ert_config = [
        "ECLBASE FOO.DATA",
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH .",
        "FORWARD_MODEL RI_WELLMOD("
        + "<RI_PROJECT>={},".format(proj_name)
        + "<ECLBASE>={},".format(init_case_name)
        + "<OUTPUTFILE>={},".format(outfile)
        + "<MSW>='A4'"
        + ")",
    ]

    ert_config_fname = "riwmtest.ert"
    with open(ert_config_fname, "w") as file_h:
        file_h.write("\n".join(ert_config))

    subprocess.run(["ert", "test_run", ert_config_fname], check=True)

    assert Path(outfile).exists()


# REEK TESTS
@pytest.mark.skipif(
    not ri_wellmod.get_resinsight_exe(), reason="Could not find a ResInsight executable"
)
def test_main_initcase_reek(tmpdir, mocker):
    """Test well data generation from init case on Reek"""
    tmpdir.chdir()

    proj_name = str(DATAPATH / "ri_reek_wells.rsp")
    init_case_name = str(DATAPATH / "../data/reek/eclipse/model/2_R001_REEK-0")
    outfile = "welldefs_initcase_reek.sch"

    mocker.patch("sys.argv", [SCRIPTNAME, proj_name, init_case_name, "-o", outfile])
    ri_wellmod.main()
    assert Path(outfile).exists() and file_contains(outfile, "OP_1")


# This one requires a GUI (for now)
@pytest.mark.skipif(
    not ri_wellmod.get_resinsight_exe(), reason="Could not find a ResInsight executable"
)
@pytest.mark.skipif(not has_display(), reason="Requires X display")
def test_main_lgr_reek(tmpdir, mocker):
    """Test creation of LGR on Reek"""
    tmpdir.chdir()

    proj_name = str(DATAPATH / "ri_reek_wells.rsp")
    init_case_name = str(DATAPATH / "../data/reek/eclipse/model/2_R001_REEK-0")
    outfile = "welldefs_lgr_reek.sch"

    mocker.patch(
        "sys.argv",
        [SCRIPTNAME, proj_name, init_case_name, "-o", outfile, "--lgr", "OP_1:5,5,1"],
    )
    ri_wellmod.main()

    assert Path(outfile).exists() and file_contains(outfile, "OP_1")
