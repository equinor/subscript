from pathlib import Path

import subprocess
import pytest

from subscript.ri_wellmod import ri_wellmod

SCRIPTNAME = "ri_wellmod"
RUNPATH = Path(__file__).parent / "data/drogon"
DATAPATH = Path(__file__).parent / "testdata_ri_wellmod"


@pytest.mark.integration
def test_integration():
    """Test that endpoint is installed"""
    assert subprocess.check_output(["ri_wellmod", "-h"])


@pytest.mark.skipif(
    not ri_wellmod.get_resinsight_exe(),
    reason="Could not find a ResInsight install",
)
def test_main_initcase(tmpdir, mocker):
    """Test well data generation from init case"""
    tmpdir.chdir()

    proj_name = str(DATAPATH / "drogon_wells_noicd.rsp")
    init_case_name = str(RUNPATH / "eclipse/model/DROGON-0_NOSIM")
    outfile = "welldefs_initcase.sch"

    mocker.patch("sys.argv", [SCRIPTNAME, proj_name, init_case_name, "-o", outfile])
    ri_wellmod.main()
    assert Path(outfile).exists()


@pytest.mark.skipif(
    not ri_wellmod.get_resinsight_exe(),
    reason="Could not find a ResInsight install",
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
    assert Path(outfile).exists()


@pytest.mark.skipif(
    not ri_wellmod.get_resinsight_exe(),
    reason="Could not find a ResInsight install",
)
def test_main_mswdef(tmpdir, mocker):
    """Test multi-segment well data generation"""
    tmpdir.chdir()

    proj_name = str(DATAPATH / "drogon_wells_noicd.rsp")
    init_case_name = str(RUNPATH / "eclipse/model/DROGON-0_NOSIM")
    outfile = "welldefs_msw.sch"

    mocker.patch(
        "sys.argv",
        [SCRIPTNAME, proj_name, init_case_name, "-o", outfile, "-msw", "A4,A2,R*"],
    )
    ri_wellmod.main()

    assert Path(outfile).exists()


@pytest.mark.skipif(
    not ri_wellmod.get_resinsight_exe(),
    reason="Could not find a ResInsight install",
)
def test_main_lgr(tmpdir, mocker):
    """Test creation of LGR"""
    tmpdir.chdir()

    proj_name = str(DATAPATH / "drogon_wells_noicd.rsp")
    init_case_name = str(RUNPATH / "eclipse/model/DROGON-0_NOSIM_LGR")
    outfile = "welldefs_lgr.sch"

    mocker.patch(
        "sys.argv", [SCRIPTNAME, proj_name, init_case_name, "-o", outfile, "-msw", "A4"]
    )
    ri_wellmod.main()

    assert Path(outfile).exists()


@pytest.mark.skipif(
    not ri_wellmod.get_resinsight_exe(),
    reason="Could not find a ResInsight install",
)
def test_main_lgr_cmdline(tmpdir, mocker):
    """Test creation of LGR"""
    tmpdir.chdir()

    proj_name = str(DATAPATH / "drogon_wells_noicd.rsp")
    init_case_name = str(RUNPATH / "eclipse/model/DROGON-0_NOSIM")
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
            "-msw",
            "A4,A2",
            "-lo",
            lgr_outfile,
            "--lgr",
            "A4:3,3,1",
        ],
    )
    ri_wellmod.main()

    assert Path(outfile).exists()
    assert Path(lgr_outfile).exists()
