"""
Interpolation script for relperm tables defined by ecl include files.
Candidate script to replace InterpRelperm. Script reads base/high/low
SWOF and SGOF from ecl include files and interpolates inbetween,
using interpolation parameter(s) in range [-1,1], so that 0 returns
base, -1 returns low, and 1 returns high. If either base, low or high
is missing, one can set two of the inputs (low/base/high) to read the
same file and interpolate in half the range.

Created:  2019.03.21
Modified: 2019.10.23

Autors:
- Eivind Smoergrav, eism
- Havard Berland

Config file syntax (yaml):
#********************************************************************
# Example config file

base:  # Required: SWOF and SGOF in one unified file or two separate files.
  - swof_base.inc
  - sgof_base.inc

high:  # Required: the phases to be interpoalted must be present.
       # Ie can drop SWOF or SGOF if these are not to be used
  - swof_opt.inc
  - sgof_opt.inc

low:   # Required: the phases to be interpoalted must be present.
       # Ie can drop SWOF or SGOF if these are not to be used
  - swof_pes.inc
  - sgof_pes.inc

result_file  : outfilen.inc  # Required: Name of output file with interpolated tables

delta_s      : 0.02          # Optional: resolution of Sw/Sg, defaulted to 0.01

interpolations: #  Required: applied in order of appearance so that
                #  one can define something for all and overwrite later
  - tables   : []     # Optional: list of satnums to be interpolated,
                      # defaults to empty list which is interpreted
                      # to mean all entries
    param_w  : -0.23
    param_g  :  0.44

  - tables : [1]      # will only apply to satnum nr. 1, for SWOF and SGOF
    param_w  : -0.23
    param_g  :  0.44

  - tables : [2,5,75] # applies to satnum 2, 5, and 75, for SWOF
                      # (not SGOF which is defaulted to 0.44, from before)
                      # if a parameter is not set, no interpolation will
                      # be applied ie base table is returned
    param_w  :  0.5


#*************************************************************************

Issues:
- Script does not currently handle tables with different end points correctly;
  it interpolates saturation by saturation, irregardless. It will ie run, and
  preserve the extreme endpoint. This may or may not be what you want.
"""

from __future__ import print_function
import pandas as pd
import pyscal
import sys
import os
import yaml
import argparse
from ecl2df import satfunc2df

import configsuite
from configsuite import types
from configsuite import MetaKeys as MK


@configsuite.validator_msg("Is valid file name")
def _is_filename(fname):
    return os.path.isfile(fname)


@configsuite.validator_msg("Is valid interpolator")
def _is_valid_interpolator(interp):

    valid = False
    try:
        if interp["param_w"]:
            valid = True
    except:
        pass
    try:
        if interp["param_g"]:
            valid = True
    except:
        pass

    return valid


@configsuite.validator_msg("Is valid table entries")
def _is_valid_table_entries(schema):

    valid = False
    try:
        if schema["low"]:
            valid = True
    except:
        pass

    try:
        if schema["high"]:
            valid = True
    except:
        pass

    return valid


def get_cfg_schema():

    schema = {
        MK.Type: types.NamedDict,
        MK.Content: {
            "base": {
                MK.Type: types.List,
                MK.Content: {
                    MK.Item: {
                        MK.Type: types.String,
                        MK.ElementValidators: (_is_filename,),
                    }
                },
            },
            "low": {
                MK.Type: types.List,
                MK.Content: {
                    MK.Item: {
                        MK.Type: types.String,
                        MK.ElementValidators: (_is_filename,),
                    }
                },
            },
            "high": {
                MK.Type: types.List,
                MK.Content: {
                    MK.Item: {
                        MK.Type: types.String,
                        MK.ElementValidators: (_is_filename,),
                    }
                },
            },
            "result_file": {MK.Type: types.String},
            "delta_s": {MK.Type: types.Number, MK.Required: False},
            "interpolations": {
                MK.Type: types.List,
                MK.Content: {
                    MK.Item: {
                        MK.Type: types.NamedDict,
                        MK.ElementValidators: (_is_valid_interpolator,),
                        MK.Content: {
                            "tables": {
                                MK.Type: types.List,
                                MK.Required: False,
                                MK.Content: {MK.Item: {MK.Type: types.Integer}},
                            },
                            "param_w": {MK.Type: types.Number, MK.Required: False},
                            "param_g": {MK.Type: types.Number, MK.Required: False},
                        },
                    }
                },
            },
        },
    }

    return schema


def tables_to_dataframe(filenames):
    """
    Routine to gather scal tables (SWOF and SGOF) from ecl include files.

    Parameters:
        List with filenames to be parsed. Assumed to contain ecl SCAL tables

    Returns:
        dataframe with the tables
    """

    dataframes = []
    for filename in filenames:
        filecontents_df = satfunc2df.deck2df("\n".join(open(filename).readlines()))
        dataframes.append(filecontents_df)

    return pd.concat(dataframes, sort=True)


def make_interpolant(base_df, low_df, high_df, interp_param, satnum, h):
    """
    Routine to define a relperm.interpolant instance and perform interpolation.

    Parameters:
        base_df (pandas DF): containing the base tables
        low_df  (pandas DF): containing the low tables
        high_df (pandas DF): containing the high tables
        interp_param (dict('param_w', 'param_g')): the interp parameter values
        satnum (int) : the satuation number index
        h   : (float) the saturation spcaing to be used in out tables

    Returns:
        relperm.interpolant : (relperm.recommendation) tables for a satnum
    """

    # Define base tables
    swlbase = base_df.loc["SWOF", satnum]["SW"].min()
    base = pyscal.WaterOilGas(swl=float(swlbase), h=h)
    base.wateroil.add_oilwater_fromtable(
        base_df.loc["SWOF", satnum],
        swcolname="SW",
        krwcolname="KRW",
        krowcolname="KROW",
        pccolname="PCOW",
    )

    # Define low tables
    if "SWOF" in low_df.index.unique():
        swllow = low_df.loc["SWOF", satnum]["SW"].min()
        low = pyscal.WaterOilGas(swl=float(swllow), h=h)
        low.wateroil.add_oilwater_fromtable(
            low_df.loc["SWOF", satnum],
            swcolname="SW",
            krwcolname="KRW",
            krowcolname="KROW",
            pccolname="PCOW",
        )
    else:
        swllow = base_df.loc["SWOF", satnum]["SW"].min()
        low = pyscal.WaterOilGas(swl=float(swllow), h=h)
        low.wateroil.add_oilwater_fromtable(
            base_df.loc["SWOF", satnum],
            swcolname="SW",
            krwcolname="KRW",
            krowcolname="KROW",
            pccolname="PCOW",
        )

    # Define high tables
    if "SWOF" in high_df.index.unique():
        swlhigh = high_df.loc["SWOF", satnum]["SW"].min()
        high = pyscal.WaterOilGas(swl=float(swlhigh), h=h)
        high.wateroil.add_oilwater_fromtable(
            high_df.loc["SWOF", satnum],
            swcolname="SW",
            krwcolname="KRW",
            krowcolname="KROW",
            pccolname="PCOW",
        )
    else:
        swlhigh = base_df.loc["SWOF", satnum]["SW"].min()
        high = pyscal.WaterOilGas(swl=float(swlhigh), h=h)
        high.wateroil.add_oilwater_fromtable(
            base_df.loc["SWOF", satnum],
            swcolname="SW",
            krwcolname="KRW",
            krowcolname="KROW",
            pccolname="PCOW",
        )

    # Correct types for Sg (sometimes incorrecly set to str)
    base_df["SG"] = base_df["SG"].astype("float64")

    base.gasoil.add_gasoil_fromtable(
        base_df.loc["SGOF", satnum],
        sgcolname="SG",
        krgcolname="KRG",
        krogcolname="KROG",
        pccolname="PCOG",
    )

    if "SGOF" in low_df.index.unique():
        low_df["SG"] = low_df["SG"].astype("float64")
        low.gasoil.add_gasoil_fromtable(
            low_df.loc["SGOF", satnum],
            sgcolname="SG",
            krgcolname="KRG",
            krogcolname="KROG",
            pccolname="PCOG",
        )
    else:
        low.gasoil.add_gasoil_fromtable(
            base_df.loc["SGOF", satnum],
            sgcolname="SG",
            krgcolname="KRG",
            krogcolname="KROG",
            pccolname="PCOG",
        )

    if "SGOF" in high_df.index.unique():
        high_df["SG"] = high_df["SG"].astype("float64")
        high.gasoil.add_gasoil_fromtable(
            high_df.loc["SGOF", satnum],
            sgcolname="SG",
            krgcolname="KRG",
            krogcolname="KROG",
            pccolname="PCOG",
        )
    else:
        high.gasoil.add_gasoil_fromtable(
            base_df.loc["SGOF", satnum],
            sgcolname="SG",
            krgcolname="KRG",
            krogcolname="KROG",
            pccolname="PCOG",
        )

    rec = pyscal.SCALrecommendation(low, base, high, "SATNUM " + str(satnum), h=h)

    if not "SWOF" in low_df.index.unique() and interp_param["param_w"] < 0:
        sys.exit(
            "Error: interpolation parameter for SWOF, satnum:"
            + str(satnum)
            + " set to "
            + str(interp_param["param_w"])
            + " but no low table is provided. Values cannot be negative"
        )

    if not "SWOF" in high_df.index.unique() and interp_param["param_w"] > 0:
        sys.exit(
            "Error: interpolation parameter for SWOF, satnum:"
            + str(satnum)
            + " set to "
            + str(interp_param["param_w"])
            + " but no high table is provided. Values cannot be positive"
        )

    if not "SGOF" in low_df.index.unique() and interp_param["param_g"] < 0:
        sys.exit(
            "Error: interpolation parameter for SGOF, satnum:"
            + str(satnum)
            + " set to "
            + str(interp_param["param_g"])
            + " but no low table is provided. Values cannot be negative"
        )

    if not "SGOF" in high_df.index.unique() and interp_param["param_g"] > 0:
        sys.exit(
            "Error: interpolation parameter for SGOF, satnum:"
            + str(satnum)
            + " set to "
            + str(interp_param["param_g"])
            + " but no high table is provided. Values cannot be positive"
        )

    return rec.interpolate(interp_param["param_w"], interp_param["param_g"])


def main():
    parser = argparse.ArgumentParser(
        epilog=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "-c",
        "-C",
        "--configfile",
        type=str,
        help="Name of YAML config file",
        required=True,
    )
    args = parser.parse_args()

    # parse the config file
    if not os.path.isfile(args.configfile):
        sys.exit("No such file:" + args.configfile)
    else:
        with open(args.configfile, "r") as ymlfile:
            cfg = yaml.safe_load(ymlfile)

    # validate cfg according to schema
    cfg_schema = get_cfg_schema()
    cfg_suite = configsuite.ConfigSuite(cfg, cfg_schema)

    if not cfg_suite.valid:
        print("Sorry, the configuration is invalid.")
        sys.exit(cfg_suite.errors)

    # set default values
    relperm_delta_s = 0.01
    if cfg_suite.snapshot.delta_s:
        relperm_delta_s = cfg_suite.snapshot.delta_s

    # Parse tables from files
    base_df = tables_to_dataframe(cfg_suite.snapshot.base)
    low_df = tables_to_dataframe(cfg_suite.snapshot.low)
    high_df = tables_to_dataframe(cfg_suite.snapshot.high)

    # Check what we have been provided; SWOF/SGOF/HIGH/LOW/BASE
    # base must contain SWOF and SGOF, high and low can be missing
    if "SWOF" not in base_df["KEYWORD"].unique():
        sys.exit("ERROR: No SWOF table provided for base")
    if "SGOF" not in base_df["KEYWORD"].unique():
        sys.exit("ERROR: No SGOF table provided for base")

    # low
    if (not "SWOF" in low_df["KEYWORD"].unique()) and (
        not "SGOF" in low_df["KEYWORD"].unique()
    ):
        sys.exit("ERROR: No tables provided for low; provide SWOF and/or SGOF")

    # high
    if (not "SWOF" in high_df["KEYWORD"].unique()) and (
        not "SGOF" in high_df["KEYWORD"].unique()
    ):
        sys.exit("ERROR: No tables provided for high; provide SWOF and/or SGOF")

    # This is how we want to navigate the dataframes:
    base_df.set_index(["KEYWORD", "SATNUM"], inplace=True)
    low_df.set_index(["KEYWORD", "SATNUM"], inplace=True)
    high_df.set_index(["KEYWORD", "SATNUM"], inplace=True)

    # Sort for performance
    base_df.sort_index(inplace=True)
    low_df.sort_index(inplace=True)
    high_df.sort_index(inplace=True)

    # Loop over satnum and interpolate according to default and cfg values
    interpolants = []
    satnums = range(1, base_df.reset_index("SATNUM")["SATNUM"].unique().max() + 1)

    for satnum in satnums:
        interp_values = {"param_w": 0, "param_g": 0}
        for interp in cfg_suite.snapshot.interpolations:
            if not interp.tables or satnum in interp.tables or "all" in interp.tables:
                if interp.param_w:
                    interp_values["param_w"] = interp.param_w
                if interp.param_g:
                    interp_values["param_g"] = interp.param_g

        interpolants.append(
            make_interpolant(
                base_df, low_df, high_df, interp_values, satnum, relperm_delta_s
            )
        )

    # Dump to Eclipse include file:
    with open(cfg["result_file"], "w") as f:
        f.write("SWOF\n")
        for interpolant in interpolants:
            f.write(interpolant.wateroil.SWOF(header=False))
        f.write("\nSGOF\n")
        for interpolant in interpolants:
            f.write(interpolant.gasoil.SGOF(header=False))


if __name__ == "__main__":
    main()
