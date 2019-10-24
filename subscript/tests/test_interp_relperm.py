import pandas as pd
import os
import yaml
import configsuite
from .. import interp_relperm


def test_get_cfg_schema():
    test_cfg = os.path.join(os.path.dirname(__file__), "data/relperm/cfg.yml")
    with open(test_cfg, "r") as ymlfile:
        cfg = yaml.safe_load(ymlfile)

    schema = interp_relperm.get_cfg_schema()
    suite = configsuite.ConfigSuite(cfg, schema)
    assert suite.valid


def test_tables_to_dataframe():
    swoffn = os.path.join(os.path.dirname(__file__), "data/relperm/swof_base.inc")
    sgoffn = os.path.join(os.path.dirname(__file__), "data/relperm/sgof_base.inc")

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
    swoffn = os.path.join(os.path.dirname(__file__), "data/relperm/swof_base.inc")

    sgoffn = os.path.join(os.path.dirname(__file__), "data/relperm/sgof_base.inc")

    base_df = interp_relperm.tables_to_dataframe([swoffn, sgoffn])

    swoffn = os.path.join(os.path.dirname(__file__), "data/relperm/swof_pes.inc")
    sgoffn = os.path.join(os.path.dirname(__file__), "data/relperm/sgof_pes.inc")

    low_df = interp_relperm.tables_to_dataframe([swoffn, sgoffn])

    swoffn = os.path.join(os.path.dirname(__file__), "data/relperm/swof_opt.inc")
    sgoffn = os.path.join(os.path.dirname(__file__), "data/relperm/sgof_opt.inc")

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
