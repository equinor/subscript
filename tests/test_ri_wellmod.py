import os
import subprocess
from pathlib import Path

import pytest
from subscript.ri_wellmod import ri_wellmod

SCRIPTNAME = "ri_wellmod"
DATAPATH = Path(__file__).parent / "testdata_ri_wellmod"
RI_DEV = "/project/res/bin/resinsightdev"

try:
    # pylint: disable=unused-import
    import ert.shared  # noqa

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


def has_resinsight():
    """
    Check for a valid ResInsight install
    """
    resinsight_exe = ri_wellmod.get_resinsight_exe()

    if not resinsight_exe:
        return False

    riexe_path = Path(resinsight_exe)
    if (
        len(riexe_path.parts) >= 2
        and riexe_path.parts[0] == "/"
        and riexe_path.parts[1] == "tmp"
    ):
        riexe_path.unlink()

    return True


def file_contains(filename, string_to_find):
    """
    Utility function to check if a file contains a given string.
    """
    if not Path(filename).exists():
        return False

    filetext = Path(filename).read_text(encoding="utf8")
    return filetext.find(string_to_find) >= 0


def github_online_runner():
    gh_runner = os.getenv("GITHUB_ACTIONS") == "true"

    # we still want to run tests on github actions local (komodo) runners
    local_gh_runner = "f_scout_ci" in str(os.getenv("RUNNER_NAME"))
    return gh_runner and not local_gh_runner


@pytest.mark.integration
def test_integration():
    """Test that endpoint is installed"""
    assert subprocess.check_output([SCRIPTNAME, "-h"])


@pytest.mark.skipif(
    not has_resinsight(), reason="Could not find a ResInsight executable"
)
@pytest.mark.skipif(drogon_runpath() is None, reason="Could not find Drogon data")
def test_main_initcase(tmp_path, mocker):
    """Test well data generation from init case"""
    os.chdir(tmp_path)

    proj_name = str(DATAPATH / "drogon_wells_noicd.rsp")
    init_case_name = str(drogon_runpath() / "eclipse/model/DROGON-0_NOSIM")
    outfile = "welldefs_initcase.sch"

    mocker.patch("sys.argv", [SCRIPTNAME, proj_name, init_case_name, "-o", outfile])
    ri_wellmod.main()
    assert Path(outfile).exists() and file_contains(outfile, "A4")


@pytest.mark.skipif(
    github_online_runner(), reason="Cannot test on github online runner"
)
@pytest.mark.skipif(
    not has_resinsight(),
    reason="Could not find a ResInsight executable",
)
def test_main_inputcase(tmp_path, mocker):
    """Test well data generation from input case"""
    os.chdir(tmp_path)

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
    not has_resinsight(), reason="Could not find a ResInsight executable"
)
@pytest.mark.skipif(drogon_runpath() is None, reason="Could not find Drogon data")
def test_drogon_mswdef(tmp_path, mocker):
    """Test multi-segment well data generation"""
    os.chdir(tmp_path)

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
    not has_resinsight(), reason="Could not find a ResInsight executable"
)
@pytest.mark.skipif(drogon_runpath() is None, reason="Could not find Drogon data")
def test_drogon_lgr(tmp_path, mocker):
    """Test creation of LGR"""
    os.chdir(tmp_path)

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
    not has_resinsight(), reason="Could not find a ResInsight executable"
)
@pytest.mark.skipif(drogon_runpath() is None, reason="Could not find Drogon data")
def test_main_lgr_cmdline(tmp_path, mocker):
    """Test creation of LGR"""
    os.chdir(tmp_path)

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
    not has_resinsight(), reason="Could not find a ResInsight executable"
)
@pytest.mark.skipif(drogon_runpath() is None, reason="Could not find Drogon data")
@pytest.mark.skipif(not HAVE_ERT, reason="Requires ERT")
def test_ert_forward_model(tmp_path):
    """Test that the ERT hook can run on a mocked case"""
    # pylint: disable=redefined-outer-name
    # pylint: disable=unused-argument
    os.chdir(tmp_path)

    proj_name = str(DATAPATH / "drogon_wells_noicd.rsp")
    init_case_name = str(drogon_runpath() / "eclipse/model/DROGON-0_NOSIM")
    outfile = "welldefs_lgr.sch"

    Path("FOO.DATA").write_text("--Empty", encoding="utf8")
    ert_config = [
        "ECLBASE FOO.DATA",
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH <CONFIG_PATH>",
        "FORWARD_MODEL RI_WELLMOD("
        + f"<RI_PROJECT>={proj_name},"
        + f"<ECLBASE>={init_case_name},"
        + f"<OUTPUTFILE>={outfile},"
        + "<MSW>='A4'"
        + ")",
    ]

    ert_config_fname = "riwmtest.ert"
    Path(ert_config_fname).write_text("\n".join(ert_config), encoding="utf8")

    subprocess.run(["ert", "test_run", ert_config_fname], check=True)

    assert Path(outfile).exists()


# REEK TESTS
@pytest.mark.skipif(
    github_online_runner(), reason="Cannot test on github online runner"
)
@pytest.mark.skipif(
    not has_resinsight(), reason="Could not find a ResInsight executable"
)
def test_main_initcase_reek(tmp_path, mocker):
    """Test well data generation from init case on Reek"""
    os.chdir(tmp_path)

    proj_name = str(DATAPATH / "ri_reek_wells.rsp")
    init_case_name = str(DATAPATH / "../data/reek/eclipse/model/2_R001_REEK-0")
    outfile = "welldefs_initcase_reek.sch"

    mocker.patch("sys.argv", [SCRIPTNAME, proj_name, init_case_name, "-o", outfile])
    ri_wellmod.main()
    assert Path(outfile).exists() and file_contains(outfile, "OP_1")


@pytest.mark.skipif(
    github_online_runner(), reason="Cannot test on github online runner"
)
@pytest.mark.skipif(
    not has_resinsight(), reason="Could not find a ResInsight executable"
)
def test_main_lgr_reek(tmp_path, mocker):
    """Test creation of LGR on Reek"""
    os.chdir(tmp_path)

    proj_name = str(DATAPATH / "ri_reek_wells.rsp")
    init_case_name = str(DATAPATH / "../data/reek/eclipse/model/2_R001_REEK-0")
    outfile = "welldefs_lgr_reek.sch"

    mocker.patch(
        "sys.argv",
        [SCRIPTNAME, proj_name, init_case_name, "-o", outfile, "--lgr", "OP_1:5,5,1"],
    )
    ri_wellmod.main()

    assert Path(outfile).exists() and file_contains(outfile, "OP_1")


@pytest.mark.ri_dev  # Need --ri_dev option to pytest to run this.
@pytest.mark.skipif(
    not Path(RI_DEV).exists(), reason="No dev-version of ResInsight available"
)
@pytest.mark.skipif(drogon_runpath() is None, reason="Could not find Drogon data")
def test_main_lgr_cmdline_dev_version(tmp_path, mocker):
    """Test creation of LGR using development version"""
    os.chdir(tmp_path)

    proj_name = str(DATAPATH / "drogon_wells_noicd.rsp")
    init_case_name = str(drogon_runpath() / "eclipse/model/DROGON-0_NOSIM")
    resinsightdev = RI_DEV
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
            "--with-resinsight-dev",
            resinsightdev,
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
