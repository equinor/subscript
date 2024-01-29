import os
from pathlib import Path

import pytest
from subscript.sector2fluxnum import sector2fluxnum

TESTDATA = Path(__file__).absolute().parent / "testdata_sector2fluxnum"

# pylint: disable=invalid-name  # All those CAPS are due to Eclipse


def test_main_test(tmp_path, mocker):
    """Test the command line utility"""
    os.chdir(tmp_path)

    input_ECL_CASE = TESTDATA / "TEST.DATA"
    input_OUTPUT_FLUX = "OUT_COARSE.FLUX"
    input_INPUT_DUMPFLUX = TESTDATA / "DUMPFLUX_TEST.DATA"
    input_RESTART = TESTDATA / "TEST.UNRST"

    mocker.patch(
        "sys.argv",
        [
            "sector2fluxnum",
            "-i",
            "2-10",
            "-j",
            "2-9",
            "-k",
            "1-1",
            "-r",
            str(input_RESTART),
            "--test",
            str(input_INPUT_DUMPFLUX),
            str(input_ECL_CASE),
            str(input_OUTPUT_FLUX),
        ],
    )
    sector2fluxnum.main()

    assert Path("USEFLUX_TEST.DATA").exists()


def test_main_test_fipnum(tmp_path, mocker):
    """Test the --fipnum command line argument"""
    os.chdir(tmp_path)

    input_ECL_CASE = TESTDATA / "TEST.DATA"
    input_OUTPUT_FLUX = "OUT_COARSE.FLUX"
    input_INPUT_DUMPFLUX = TESTDATA / "DUMPFLUX_TEST.DATA"
    input_RESTART = TESTDATA / "TEST.UNRST"

    mocker.patch(
        "sys.argv",
        [
            "sector2fluxnum",
            "--fipnum",
            "4",
            "-r",
            str(input_RESTART),
            "--test",
            str(input_INPUT_DUMPFLUX),
            str(input_ECL_CASE),
            str(input_OUTPUT_FLUX),
        ],
    )
    sector2fluxnum.main()

    assert Path("USEFLUX_TEST.DATA").exists()


@pytest.mark.skipif(
    not Path("/prog/res/ecl/grid").exists(),
    reason="Eclipse must be installed for this test",
)
def test_main_with_ecl_run(tmp_path, mocker):
    """Test without --test on the command line, requiring
    Eclipse simulator installed in PATH"""
    os.chdir(tmp_path)

    input_ECL_CASE = TESTDATA / "TEST.DATA"
    input_OUTPUT_FLUX = "OUT_COARSE.FLUX"
    input_RESTART = TESTDATA / "TEST.UNRST"

    mocker.patch(
        "sys.argv",
        [
            "sector2fluxnum",
            "-i",
            "2-10",
            "-j",
            "2-9",
            "-k",
            "1-1",
            "-r",
            str(input_RESTART),
            str(input_ECL_CASE),
            str(input_OUTPUT_FLUX),
        ],
    )
    sector2fluxnum.main()

    assert Path("USEFLUX_TEST.DATA").exists()
