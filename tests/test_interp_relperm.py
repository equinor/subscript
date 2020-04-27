# from __future__ import absolute_import

import pandas as pd
import os
import yaml
import sys
import configsuite

import subprocess
import pytest

from subscript.interp_relperm import interp_relperm
from pyscal import PyscalFactory
from ecl2df import satfunc

TESTDATA = os.path.join(os.path.dirname(__file__), "data/relperm")


def test_get_cfg_schema():

    cfg_filen = os.path.join(TESTDATA, "cfg.yml")

    with open(cfg_filen, "r") as ymlfile:
        cfg = yaml.safe_load(ymlfile)

    # add root-path to all include files
    if "base" in cfg.keys():
        for i in range(len(cfg["base"])):
            cfg["base"][i] = os.path.join(TESTDATA, cfg["base"][i])
    if "high" in cfg.keys():
        for i in range(len(cfg["high"])):
            cfg["high"][i] = os.path.join(TESTDATA, cfg["high"][i])
    if "low" in cfg.keys():
        for i in range(len(cfg["low"])):
            cfg["low"][i] = os.path.join(TESTDATA, cfg["low"][i])

    schema = interp_relperm.get_cfg_schema()
    suite = configsuite.ConfigSuite(cfg, schema)

    assert suite.valid


def test_tables_to_dataframe():
    swoffn = os.path.join(TESTDATA, "swof_base.inc")
    sgoffn = os.path.join(TESTDATA, "sgof_base.inc")

    tables_df = interp_relperm.tables_to_dataframe([swoffn, sgoffn])

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
    assert "SATNUM" in tables_df.columns
    assert not tables_df.empty


def test_make_interpolant():
    swoffn = os.path.join(TESTDATA, "swof_base.inc")
    sgoffn = os.path.join(TESTDATA, "sgof_base.inc")

    base_df = interp_relperm.tables_to_dataframe([swoffn, sgoffn])

    swoffn = os.path.join(TESTDATA, "swof_pes.inc")
    sgoffn = os.path.join(TESTDATA, "sgof_pes.inc")

    low_df = interp_relperm.tables_to_dataframe([swoffn, sgoffn])

    swoffn = os.path.join(TESTDATA, "swof_opt.inc")
    sgoffn = os.path.join(TESTDATA, "sgof_opt.inc")

    high_df = interp_relperm.tables_to_dataframe([swoffn, sgoffn])

    base_df.set_index(["KEYWORD", "SATNUM"], inplace=True)
    low_df.set_index(["KEYWORD", "SATNUM"], inplace=True)
    high_df.set_index(["KEYWORD", "SATNUM"], inplace=True)

    base_df.sort_index(inplace=True)
    low_df.sort_index(inplace=True)
    high_df.sort_index(inplace=True)

    interpolant = interp_relperm.make_interpolant(
        base_df, low_df, high_df, {"param_w": 0.1, "param_g": -0.5}, 1, 0.1
    )

    assert "SWOF" in interpolant.wateroil.SWOF()
    assert "SGOF" in interpolant.gasoil.SGOF()


def test_args(tmpdir):
    tmpdir.chdir()

    test_cfg = os.path.join(TESTDATA, "cfg.yml")

    sys.argv = [__file__, "--configfile", test_cfg, "--root-path", TESTDATA]

    interp_relperm.main()

    assert os.path.exists("outfilen.inc")


def test_mock(tmpdir):
    """Mocked pyscal-generated input files.

    Note that this is using pyscal both for dumping to disk and
    parsing from disk, and is thus not representative for how flexible
    the code is for reading from include files not originating in pyscal.
    """
    tmpdir.chdir()
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
        columns=columns, data=[[1, 1, 1, 1, 1, 0.1, 2, -2, 0.25, 100, 150]],
    )
    dframe_base = pd.DataFrame(
        columns=columns, data=[[1, 2, 2, 2, 2, 0.1, 2, -2, 0.25, 200, 150]],
    )
    dframe_opt = pd.DataFrame(
        columns=columns, data=[[1, 3, 3, 3, 3, 0.1, 2, -2, 0.25, 300, 150]],
    )
    PyscalFactory.create_pyscal_list(dframe_pess).dump_family_1("pess.inc")
    PyscalFactory.create_pyscal_list(dframe_base).dump_family_1("base.inc")
    PyscalFactory.create_pyscal_list(dframe_opt).dump_family_1("opt.inc")

    config = {
        "base": ["base.inc"],
        "low": ["pess.inc"],
        "high": ["opt.inc"],
        "result_file": "outfile.inc",
        "interpolations": [{"param_w": -0.5, "param_g": 0.5}],
        "delta_s": 0.1,
    }

    interp_relperm.process_config(config)

    outfile_df = satfunc.df(open("outfile.inc").read(), ntsfun=1)
    assert set(outfile_df["KEYWORD"].unique()) == {"SWOF", "SGOF"}
    assert outfile_df["SW"].sum() > 0
    assert outfile_df["SG"].sum() > 0
    assert outfile_df["KRW"].sum() > 0
    assert outfile_df["KROW"].sum() > 0
    assert outfile_df["KRG"].sum() > 0
    assert outfile_df["KROG"].sum() > 0
    assert outfile_df["PCOW"].sum() > 0


@pytest.mark.integration
def test_integration():
    """Test that endpoint is installed"""
    assert subprocess.check_output(["interp_relperm", "-h"])


def test_main(tmpdir):
    tmpdir.chdir()

    assert os.system("interp_relperm -h") == 0

    test_cfg = os.path.join(TESTDATA, "cfg.yml")

    sys.argv = [__file__, "-c", test_cfg, "-r", TESTDATA]

    interp_relperm.main()

    assert os.path.exists("outfilen.inc")


if __name__ == "__main__":

    test_get_cfg_schema()
    test_tables_to_dataframe()
    test_make_interpolant()
    test_args()
    test_main()
