import os
import subprocess
from pathlib import Path

import pandas as pd
import pytest
import yaml
from pydantic import ValidationError
from pyscal import PyscalFactory
from pyscal.utils.testing import sat_table_str_ok
from res2df import satfunc
from subscript.interp_relperm import interp_relperm
from subscript.interp_relperm.interp_relperm import InterpRelpermConfig

TESTDATA = Path(__file__).absolute().parent / "testdata_interp_relperm"

TWO_SATNUM_PYSCAL_MOCK = pd.DataFrame(
    columns=[
        "CASE",
        "SATNUM",
        "Nw",
        "Now",
        "Ng",
        "Nog",
        "swl",
        "a",
        "b",
        "poro_ref",
        "perm_ref",
        "drho",
    ],
    data=[
        ["low", 1, 1.1, 1, 1, 1, 0.1, 2, -2, 0.25, 100, 150],
        ["low", 2, 1.1, 1, 1, 1, 0.1, 2, -2, 0.25, 100, 150],
        ["base", 1, 2, 2, 2, 2, 0.1, 2, -2, 0.25, 200, 150],
        ["base", 2, 2, 2, 2, 2, 0.1, 2, -2, 0.25, 200, 150],
        ["high", 1, 3, 3, 3, 3, 0.1, 2, -2, 0.25, 300, 150],
        ["high", 2, 3, 3, 3, 3, 0.1, 2, -2, 0.25, 300, 150],
    ],
).set_index("CASE")


def test_prepend_root_path():
    """Test that we need to prepend with root-path"""
    cfg_filen = TESTDATA / "cfg.yml"

    cfg = yaml.safe_load(cfg_filen.read_text(encoding="utf8"))

    with pytest.raises(ValidationError):
        InterpRelpermConfig(**cfg)

    cfg_with_rootpath = interp_relperm.prepend_root_path_to_relative_files(
        cfg, TESTDATA
    )
    InterpRelpermConfig(**cfg_with_rootpath)

    # When root-path is prepended (with an absolute part) it should not
    # matter if we reapply:
    cfg_with_double_rootpath = interp_relperm.prepend_root_path_to_relative_files(
        cfg_with_rootpath, TESTDATA
    )
    InterpRelpermConfig(**cfg_with_double_rootpath)


@pytest.mark.parametrize(
    "dictupdates, expected_error",
    [
        ({"base": ["foo.inc"]}, "Path does not point to a file"),
        ({}, "Field required"),
        ({"interpolations": [{"tables": []}]}, "Provide either param_w or param_g"),
        ({"interpolations": [{"param_w": 1.5}]}, "Input should be less than"),
        ({"interpolations": [{"param_w": -1.1}]}, "Input should be greater than"),
        ({"interpolations": [{"param_w": 0}]}, None),
        ({"interpolations": [{"param_g": 0}]}, None),
        ({"interpolations": [{"param_w": 0, "param_g": 0}]}, None),
        ({"interpolations": [{"param_w": 0.1, "param_g": -0.1}]}, None),
        ({"interpolations": [{"param_g": -1.5}]}, "Input should be greater than"),
        ({"interpolations": [{"param_g": 1.5}]}, "Input should be less than"),
        ({"interpolations": [{"param_w": "weird"}]}, "Input should be a valid number"),
        ({"interpolations": [{"param_g": "Null"}]}, "Input should be a valid number"),
    ],
)
def test_config_errors(dictupdates, expected_error):
    """Test that the pydantic model errors correctly with some hint to the
    resolution"""
    os.chdir(TESTDATA)
    cfg = {
        "base": ["swof_base.inc", "sgof_base.inc"],
        "high": ["swof_opt.inc", "sgof_opt.inc"],
        "low": ["swof_pes.inc", "sgof_pes.inc"],
        "result_file": "foo.inc",
    }
    cfg.update(dictupdates)

    if expected_error is not None:
        with pytest.raises(ValidationError) as validation_error:
            InterpRelpermConfig(**cfg)
        assert expected_error in str(validation_error)
    else:
        InterpRelpermConfig(**cfg)


def test_schema_errors_low_base_high():
    """Test for detection of config errors related to low/base/high"""
    os.chdir(TESTDATA)
    cfg = {
        "base": ["swof_base.inc", "sgof_base.inc"],
        "high": ["swof_opt.inc", "sgof_opt.inc"],
        "low": ["swof_pes.inc", "sgof_pes.inc"],
        "result_file": "foo.inc",
        "interpolations": [{"param_w": 0.1, "param_g": -0.1}],
    }
    InterpRelpermConfig(**cfg)

    cfg_no_low = cfg.copy()
    del cfg_no_low["low"]
    with pytest.raises(ValidationError) as validation_error:
        InterpRelpermConfig(**cfg_no_low)
    assert "low is not provided" in str(validation_error)

    cfg_no_high = cfg.copy()
    del cfg_no_high["high"]
    with pytest.raises(ValidationError) as validation_error:
        InterpRelpermConfig(**cfg_no_high)
    assert "high is not provided" in str(validation_error)

    cfg_no_base = cfg.copy()
    del cfg_no_base["base"]
    with pytest.raises(ValidationError) as validation_error:
        InterpRelpermConfig(**cfg_no_base)
    assert "base is not provided" in str(validation_error)

    cfg_string_for_high = cfg.copy()
    cfg_string_for_high["high"] = "sgof_opt.inc"
    with pytest.raises(ValidationError) as validation_error:
        InterpRelpermConfig(**cfg_string_for_high)
    assert "Input should be a valid list" in str(validation_error)
    assert "sgof_opt.inc" in str(validation_error)


def test_garbled_base_input(tmp_path):
    """Perturb the swof_base.inc so that it does not include the SWOF keyword"""
    os.chdir(TESTDATA)
    Path(tmp_path / "swof_base_invalid.inc").write_text(
        "xx" + Path("swof_base.inc").read_text(encoding="utf8"), encoding="utf8"
    )
    cfg = {
        "base": [str(tmp_path / "swof_base_invalid.inc"), "sgof_base.inc"],
        "high": ["swof_opt.inc", "sgof_opt.inc"],
        "low": ["swof_pes.inc", "sgof_pes.inc"],
        "result_file": str(tmp_path / "foo.inc"),
        "interpolations": [{"param_w": 0.1, "param_g": -0.1}],
    }
    with pytest.raises(SystemExit):
        interp_relperm.process_config(cfg)


def test_parse_satfunc_files():
    """Test that tables in Eclipse format can be converted
    into dataframes (using res2df)"""
    swoffn = TESTDATA / "swof_base.inc"
    sgoffn = TESTDATA / "sgof_base.inc"

    tables_df = interp_relperm.parse_satfunc_files([swoffn, sgoffn])

    assert isinstance(tables_df, pd.DataFrame)

    assert "SWOF" in tables_df.KEYWORD.unique()
    assert "SGOF" in tables_df.KEYWORD.unique()

    assert "SW" in tables_df.columns
    assert "SG" in tables_df.columns
    assert "KRW" in tables_df.columns
    assert "KRG" in tables_df.columns
    assert "KROW" in tables_df.columns
    assert "KROG" in tables_df.columns
    assert "PCOW" in tables_df.columns
    assert "PCOG" in tables_df.columns
    assert not tables_df.empty


def test_make_interpolant():
    """Test that we are able to make an interpolant from inc files"""
    swoffn = TESTDATA / "swof_base.inc"
    sgoffn = TESTDATA / "sgof_base.inc"

    base_df = interp_relperm.parse_satfunc_files([swoffn, sgoffn])

    swoffn = TESTDATA / "swof_pes.inc"
    sgoffn = TESTDATA / "sgof_pes.inc"

    low_df = interp_relperm.parse_satfunc_files([swoffn, sgoffn])

    swoffn = TESTDATA / "swof_opt.inc"
    sgoffn = TESTDATA / "sgof_opt.inc"

    high_df = interp_relperm.parse_satfunc_files([swoffn, sgoffn])

    interpolant = interp_relperm.make_interpolant(
        base_df, low_df, high_df, {"param_w": 0.1, "param_g": -0.5}, 1, 0.1
    )

    assert "SWOF" in interpolant.wateroil.SWOF()
    assert "SGOF" in interpolant.gasoil.SGOF()


def test_args(tmp_path, mocker):
    """Test that we can parse args on the command line"""
    os.chdir(tmp_path)

    test_cfg = TESTDATA / "cfg.yml"

    mocker.patch(
        "sys.argv",
        [__file__, "--configfile", str(test_cfg), "--root-path", str(TESTDATA)],
    )

    interp_relperm.main()

    assert Path("outfile.inc").exists()


def mock_family_1():
    """Mock a family 1 dataset (three files)"""
    columns = [
        "SATNUM",
        "Nw",
        "Now",
        "Ng",
        "Nog",
        "swl",
        "a",
        "b",
        "poro_ref",
        "perm_ref",
        "drho",
    ]
    dframe_pess = pd.DataFrame(
        columns=columns,
        data=[[1, 1, 1, 1, 1, 0.1, 2, -2, 0.25, 100, 150]],
    )
    dframe_base = pd.DataFrame(
        columns=columns,
        data=[[1, 2, 2, 2, 2, 0.1, 2, -2, 0.25, 200, 150]],
    )
    dframe_opt = pd.DataFrame(
        columns=columns,
        data=[[1, 3, 3, 3, 3, 0.1, 2, -2, 0.25, 300, 150]],
    )
    Path("pess.inc").write_text(
        PyscalFactory.create_pyscal_list(dframe_pess).build_eclipse_data(family=1),
        encoding="utf-8",
    )

    Path("base.inc").write_text(
        PyscalFactory.create_pyscal_list(dframe_base).build_eclipse_data(family=1),
        encoding="utf-8",
    )

    Path("opt.inc").write_text(
        PyscalFactory.create_pyscal_list(dframe_opt).build_eclipse_data(family=1),
        encoding="utf-8",
    )


def test_mock(tmp_path):
    """Mocked pyscal-generated input files.

    Note that this is using pyscal both for dumping to disk and
    parsing from disk, and is thus not representative for how flexible
    the code is for reading from include files not originating in pyscal.
    """
    os.chdir(tmp_path)
    mock_family_1()

    config = {
        "base": ["base.inc"],
        "low": ["pess.inc"],
        "high": ["opt.inc"],
        "result_file": "outfile.inc",
        "interpolations": [{"param_w": -0.5, "param_g": 0.5}],
        "delta_s": 0.1,
    }

    interp_relperm.process_config(config)

    outfile_df = satfunc.df(Path("outfile.inc").read_text(encoding="utf8"), ntsfun=1)
    assert set(outfile_df["KEYWORD"].unique()) == {"SWOF", "SGOF"}
    assert outfile_df["SW"].sum() > 0
    assert outfile_df["SG"].sum() > 0
    assert outfile_df["KRW"].sum() > 0
    assert outfile_df["KROW"].sum() > 0
    assert outfile_df["KRG"].sum() > 0
    assert outfile_df["KROG"].sum() > 0
    assert outfile_df["PCOW"].sum() > 0


def test_family_2_output(tmp_path):
    """Test that we gan get family 2 ouput (from family 1 input)"""
    os.chdir(tmp_path)
    mock_family_1()

    config = {
        "base": ["base.inc"],
        "low": ["pess.inc"],
        "high": ["opt.inc"],
        "result_file": "outfile.inc",
        "interpolations": [{"param_w": -0.5, "param_g": 0.5}],
        "family": 2,
        "delta_s": 0.1,
    }
    interp_relperm.process_config(config)
    output = Path("outfile.inc").read_text(encoding="utf8")

    assert "SWFN" in output
    assert "SGFN" in output
    assert "SOF3" in output


def test_wrong_family(tmp_path):
    """Test error when wrong family type is provided"""
    os.chdir(tmp_path)
    mock_family_1()

    config = {
        "base": ["base.inc"],
        "low": ["pess.inc"],
        "high": ["opt.inc"],
        "result_file": "outfile.inc",
        "interpolations": [{"param_w": -0.5, "param_g": 0.5}],
        "family": "Rockefeller",
        "delta_s": 0.1,
    }
    with pytest.raises(ValidationError, match="Input should be 1 or 2"):
        interp_relperm.process_config(config)

    config["family"] = 3
    with pytest.raises(ValidationError):
        interp_relperm.process_config(config)


def test_mock_two_satnums_via_xlsx(tmp_path):
    """Test initializing interp_relperm from a pyscal xlsx file"""
    os.chdir(tmp_path)
    TWO_SATNUM_PYSCAL_MOCK.reset_index().to_excel("scal_input.xlsx")
    config = {
        "pyscalfile": "scal_input.xlsx",
        "result_file": "outfile.inc",
        "interpolations": [{"param_w": -0.5, "param_g": 0.5}],
        "delta_s": 0.1,
    }
    interp_relperm.process_config(config)
    outfile_str = Path("outfile.inc").read_text(encoding="utf8")
    assert outfile_str.find("SCAL recommendation interpolation to 0.5")


def test_mock_two_satnums_via_files(tmp_path):
    """Mocked pyscal-generated input files.

    Note that this is using pyscal both for dumping to disk and
    parsing from disk, and is thus not representative for how flexible
    the code is for reading from include files not originating in pyscal.
    """
    # pylint: disable=no-value-for-parameter
    os.chdir(tmp_path)
    Path("pess.inc").write_text(
        PyscalFactory.create_pyscal_list(
            TWO_SATNUM_PYSCAL_MOCK.loc["low"]
        ).build_eclipse_data(family=1),
        encoding="utf-8",
    )
    Path("base.inc").write_text(
        PyscalFactory.create_pyscal_list(
            TWO_SATNUM_PYSCAL_MOCK.loc["base"]
        ).build_eclipse_data(family=1),
        encoding="utf-8",
    )
    Path("opt.inc").write_text(
        PyscalFactory.create_pyscal_list(
            TWO_SATNUM_PYSCAL_MOCK.loc["high"]
        ).build_eclipse_data(family=1),
        encoding="utf-8",
    )

    config = {
        "base": ["base.inc"],
        "low": ["pess.inc"],
        "high": ["opt.inc"],
        "result_file": "outfile.inc",
        "interpolations": [{"param_w": -0.5, "param_g": 0.5}],
        "delta_s": 0.1,
    }

    interp_relperm.process_config(config)
    outfile_str = Path("outfile.inc").read_text(encoding="utf8")

    # Assert things about the comments emitted by pyscal when interpolating:
    # This is used as a proxy for asserting that interpolation parameters
    # are used for the correct satnums
    assert outfile_str.find("SCAL recommendation interpolation to 0.5")
    assert outfile_str.find("SCAL recommendation interpolation to -0.5")
    # SWOF comes before SGOF:
    assert outfile_str.find("to -0.5") < outfile_str.find("to 0.5")
    outfile_df = satfunc.df(outfile_str, ntsfun=2)
    assert set(outfile_df["KEYWORD"].unique()) == {"SWOF", "SGOF"}
    assert set(outfile_df["SATNUM"].unique()) == {1, 2}

    config = {
        "base": ["base.inc"],
        "low": ["pess.inc"],
        "high": ["opt.inc"],
        "result_file": "outfile.inc",
        "interpolations": [
            {"tables": [1], "param_w": -0.9, "param_g": -0.5},
            {"tables": [2], "param_w": 0.5, "param_g": 0.8},
        ],
        "delta_s": 0.1,
    }
    interp_relperm.process_config(config)
    outfile_str = Path("outfile.inc").read_text(encoding="utf8")
    assert outfile_str.find("to -0.9") < outfile_str.find("to 0.5")
    assert outfile_str.find("to 0.5") < outfile_str.find("to -0.5")
    assert outfile_str.find("to 0.5") < outfile_str.find("to 0.8")

    config = {
        "base": ["base.inc"],
        "low": ["pess.inc"],
        "high": ["opt.inc"],
        "result_file": "outfile.inc",
        "interpolations": [
            # This is a user error, the latter will override the first
            {"param_w": -0.9, "param_g": -0.5},
            {"param_w": 0.5, "param_g": 0.8},
        ],
        "delta_s": 0.1,
    }
    interp_relperm.process_config(config)
    outfile_str = Path("outfile.inc").read_text(encoding="utf8")
    assert "interpolation to -0.9" not in outfile_str
    assert "interpolation to 0.8" in outfile_str

    config = {
        "base": ["base.inc"],
        "low": ["pess.inc"],
        "high": ["opt.inc"],
        "result_file": "outfile.inc",
        "interpolations": [
            # Here the user intentionally overwrites the first:
            {"param_w": -0.9, "param_g": -0.5},
            {"tables": [], "param_w": 0.5, "param_g": 0.8},
        ],
        "delta_s": 0.1,
    }
    interp_relperm.process_config(config)
    outfile_str = Path("outfile.inc").read_text(encoding="utf8")
    assert "interpolation to -0.9" not in outfile_str
    assert "interpolation to 0.8" in outfile_str


@pytest.mark.parametrize(
    "int_param, expected_file",
    [(-1, "pess.inc"), (0, "base.inc"), (1, "opt.inc"), (-0.5, None), (0.5, None)],
)
def test_mock_two_satnums_via_fam2_files(tmp_path, int_param, expected_file):
    """Test that we can interpolate via family 2 input files"""
    os.chdir(tmp_path)
    Path("pess.inc").write_text(
        PyscalFactory.create_pyscal_list(
            TWO_SATNUM_PYSCAL_MOCK.loc["low"], h=0.1
        ).build_eclipse_data(family=2),
        encoding="utf-8",
    )
    Path("base.inc").write_text(
        PyscalFactory.create_pyscal_list(
            TWO_SATNUM_PYSCAL_MOCK.loc["base"], h=0.1
        ).build_eclipse_data(family=2),
        encoding="utf-8",
    )
    Path("opt.inc").write_text(
        PyscalFactory.create_pyscal_list(
            TWO_SATNUM_PYSCAL_MOCK.loc["high"], h=0.1
        ).build_eclipse_data(family=2),
        encoding="utf-8",
    )
    config = {
        "base": ["base.inc"],
        "low": ["pess.inc"],
        "high": ["opt.inc"],
        "result_file": "outfile.inc",
        "interpolations": [{"param_w": int_param, "param_g": int_param}],
        "family": 2,
        "delta_s": 0.1,
    }

    interp_relperm.process_config(config)
    outfile_str = Path("outfile.inc").read_text(encoding="utf8")
    outfile_df = satfunc.df(outfile_str)
    if expected_file is not None:
        expected_df = satfunc.df(Path(expected_file).read_text(encoding="utf8"))
        pd.testing.assert_frame_equal(outfile_df, expected_df)
    else:
        # Use test function from pyscal to assert that the produced file is
        # valid for Eclipse (not testing numerically that the interpolation
        # is correct)
        sat_table_str_ok(outfile_str)


@pytest.mark.integration
def test_integration():
    """Test that endpoint is installed"""
    assert subprocess.check_output(["interp_relperm", "-h"])


def test_main(tmp_path, mocker):
    """Test invocation from command line"""
    os.chdir(tmp_path)

    assert subprocess.check_output(["interp_relperm", "-h"])

    test_cfg = TESTDATA / "cfg.yml"

    mocker.patch("sys.argv", [__file__, "-c", str(test_cfg), "-r", str(TESTDATA)])
    interp_relperm.main()

    assert Path("outfile.inc").exists()
