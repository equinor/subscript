import pandas as pd
import re
import os
import yaml
import sys
import configsuite
from subscript.interp_relperm import interp_relperm


TESTDATA = "data/relperm/"


def correct_relpaths(newfn, oldfn, new_path, old_path):
    newfh = open(newfn, "w")
    print("New:" + new_path)
    print("Old:" + old_path)
    for line in open(oldfn, "r"):
        newfh.write(line.replace(old_path, new_path))
    newfh.close()


def test_get_cfg_schema():

    new_path = os.path.join(os.path.dirname(__file__), TESTDATA)
    test_cfg = new_path + "/cfg.yml"

    tmpfn = "delete_me.yml"
    correct_relpaths(tmpfn, test_cfg, new_path, "data/relperm")

    with open(tmpfn, "r") as ymlfile:
        cfg = yaml.safe_load(ymlfile)

    schema = interp_relperm.get_cfg_schema()
    suite = configsuite.ConfigSuite(cfg, schema)
    os.unlink(tmpfn)

    assert suite.valid


def test_tables_to_dataframe():
    swoffn = os.path.join(os.path.dirname(__file__), TESTDATA + "swof_base.inc")
    sgoffn = os.path.join(os.path.dirname(__file__), TESTDATA + "sgof_base.inc")

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
    swoffn = os.path.join(os.path.dirname(__file__), TESTDATA + "/swof_base.inc")

    sgoffn = os.path.join(os.path.dirname(__file__), TESTDATA + "/sgof_base.inc")

    base_df = interp_relperm.tables_to_dataframe([swoffn, sgoffn])

    swoffn = os.path.join(os.path.dirname(__file__), TESTDATA + "/swof_pes.inc")
    sgoffn = os.path.join(os.path.dirname(__file__), TESTDATA + "/sgof_pes.inc")

    low_df = interp_relperm.tables_to_dataframe([swoffn, sgoffn])

    swoffn = os.path.join(os.path.dirname(__file__), TESTDATA + "/swof_opt.inc")
    sgoffn = os.path.join(os.path.dirname(__file__), TESTDATA + "/sgof_opt.inc")

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


def test_main():
    new_path = os.path.join(os.path.dirname(__file__), TESTDATA)
    test_cfg = new_path + "/cfg.yml"

    tmpfn = os.path.join(os.path.dirname(__file__), "delete_me.yml")
    correct_relpaths(tmpfn, test_cfg, new_path, "data/relperm")

    tmp2fn = os.path.join(os.path.dirname(__file__), "delete_me2.yml")
    fileh = open(tmp2fn, "w")
    for l in open(tmpfn, "r"):
        if re.search("result_file", l):
            fileh.write(
                "result_file : "
                + os.path.join(os.path.dirname(__file__), "outfilen.inc")
            )
        else:
            fileh.write(l)
    fileh.close()

    sys.argv = [__file__, "-c", tmp2fn]

    interp_relperm.main()
    result_file = os.path.join(os.path.dirname(__file__), "outfilen.inc")

    assert os.path.exists(result_file)

    os.unlink(tmpfn)
    os.unlink(tmp2fn)
    os.unlink(result_file)


if __name__ == "__main__":
    test_get_cfg_schema()
    test_main()
