"""
Interpolation script for relperm tables defined by ecl include files.
Candidate script to replace InterpRelperm. Script reads base/high/low
SWOF and SGOF from ecl include files and interpolates inbetween,
using interpolation parameter(s) in range [-1,1], so that 0 returns
base, -1 returns low, and 1 returns high.

Created:  2019.03.21
Modified: 2019.10.18

Autors:
- Eivind Smoergrav, eism
- Havard Berland

Config file syntax (yaml):
#********************************************************************
# Example config file

base:  # One unified file with SWOF and SGOF or two separate files.
       # Both SWOF and SGOF are required for base
  - swof_base.inc
  - sgof_base.inc

high:  # Nothing required; can be omitted if only to interpolate
       # between base and low.
       # Can drop SGOF if interolating SWOF only and vice verca
  - swof_opt.inc
  - sgof_opt.inc

low:   # Nothing required; can be omitted if only to interpolate
       # between base and high.
       # Can drop SGOF if interolating SWOF only and vice verca
  - swof_pes.inc
  - sgof_pes.inc

result_file  : outfilen.inc  # Name of output file with interpolated tables

delta_s      : 0.02          # optional: resolution of Sw/Sg, defaulted to 0.01

interpolations:
  - param_w  : -0.23  # not listing tables explicitly defaults to all satnums
    param_g  :  0.44

  - tables   : [all]  # exact same as above
    param_w  : -0.23
    param_g  :  0.44

  - tables : [1]      # will only apply to satnum 1, for SWOF and SGOF
    param_w  : -0.23
    param_g  :  0.44

  - tables : [2,5,75] # applies to satnum 2, 5, and 75, for SWOF (not SGOF)
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
        filecontents_df = satfunc2df.deck2df(
            "\n".join(open(filename).readlines()))
        dataframes.append(filecontents_df)

    return pd.concat(dataframes, sort=True)


def make_interpolant(
    base_df,
    low_df,
    high_df,
    interp_param,
    satnum,
    has_high_SWOF,
    has_low_SWOF,
    has_high_SGOF,
    has_low_SGOF,
    h,
):
    """
    Routine to define a relperm.interpolant instance and perform interpolation.

    Parameters:
        base_df (pandas DF): containting the base tables
        low_df  (pandas DF): containting the low tables
        high_df (pandas DF): containting the high tables
        interp_param (dict('param_w', 'param_g')): the interp parameter values
        satnum (int) : the satuation number index
        has_high_SWOF : (bool) if user has provided a high table for SWOF
        has_low_SWOF  : (bool) if user has provided a low  table for SWOF
        has_high_SGOF : (bool) if user has provided a high table for SGOF
        has_low_SWOF  : (bool) if user has provided a low  table for SGOF
        h   : (float) the saturation spcaing to be used in out tables

    Returns:
        relperm.interpolant : (relperm.recommendation) tables for a satnum
    """

    # Define base/high/low tables
    swllow = base_df.loc["SWOF", satnum]["SW"].min()
    swlbase = base_df.loc["SWOF", satnum]["SW"].min()
    swlhigh = base_df.loc["SWOF", satnum]["SW"].min()

    if has_low_SWOF:
        swllow = low_df.loc["SWOF", satnum]["SW"].min()
    if has_high_SWOF:
        swlhigh = high_df.loc["SWOF", satnum]["SW"].min()

    low = pyscal.WaterOilGas(swl=float(swllow), h=h)
    base = pyscal.WaterOilGas(swl=float(swlbase), h=h)
    high = pyscal.WaterOilGas(swl=float(swlhigh), h=h)

    print(base_df.head())
    print(base_df.loc["SWOF", satnum].head())
    # sys.exit()

    base.wateroil.add_oilwater_fromtable(
        base_df.loc["SWOF", satnum],
        swcolname="SW",
        krwcolname="KRW",
        krowcolname="KROW",
        pccolname="PCOW",
    )
    if has_low_SWOF:
        low.wateroil.add_oilwater_fromtable(
            low_df.loc["SWOF", satnum],
            swcolname="SW",
            krwcolname="KRW",
            krowcolname="KROW",
            pccolname="PCOW",
        )
    else:
        low.wateroil.add_oilwater_fromtable(
            base_df.loc["SWOF", satnum],
            swcolname="SW",
            krwcolname="KRW",
            krowcolname="KROW",
            pccolname="PCOW",
        )

    if has_high_SWOF:
        high.wateroil.add_oilwater_fromtable(
            high_df.loc["SWOF", satnum],
            swcolname="SW",
            krwcolname="KRW",
            krowcolname="KROW",
            pccolname="PCOW",
        )
    else:
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

    if has_low_SGOF:
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

    if has_high_SGOF:
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

    rec = pyscal.SCALrecommendation(
        low,
        base,
        high,
        "SATNUM " + str(satnum),
        h=h)

    # Sett interpolation parameter. Default to 0 (base) if nothing specified
    swof_param = 0
    if "param_w" in interp_param.keys():
        swof_param = interp_param["param_w"]
        if not has_low_SWOF and interp_param["param_w"] < 0:
            sys.exit(
                "Error: interpolation parameter for SWOF, satnum:"
                + str(satnum)
                + " set to "
                + str(interp_param["param_w"])
                + " but no low table is provided. Values cannot be negative"
            )

        if not has_high_SWOF and interp_param["param_w"] > 0:
            sys.exit(
                "Error: interpolation parameter for SWOF, satnum:"
                + str(satnum)
                + " set to "
                + str(interp_param["param_w"])
                + " but no high table is provided. Values cannot be positive"
            )

    sgof_param = 0
    if "param_g" in interp_param.keys():
        sgof_param = interp_param["param_g"]
        if not has_low_SGOF and interp_param["param_g"] < 0:
            sys.exit(
                "Error: interpolation parameter for SGOF, satnum:"
                + str(satnum)
                + " set to "
                + str(interp_param["param_g"])
                + " but no low table is provided. Values cannot be negative"
            )

        if not has_high_SGOF and interp_param["param_g"] > 0:
            sys.exit(
                "Error: interpolation parameter for SGOF, satnum:"
                + str(satnum)
                + " set to "
                + str(interp_param["param_g"])
                + " but no high table is provided. Values cannot be positive"
            )

    return rec.interpolate(swof_param, sgof_param)


if __name__ == "__main__":
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

    relperm_delta_s = 0.01
    if "delta_s" in cfg.keys():
        relperm_delta_s = cfg["delta_s"]

    has_low_SGOF = False
    has_low_SWOF = False
    has_high_SGOF = False
    has_high_SWOF = False

    # Parse tables from files
    base_df = tables_to_dataframe(cfg["base"])
    low_df = tables_to_dataframe(cfg["low"])
    high_df = tables_to_dataframe(cfg["high"])

    # Check what we have been provided; SWOF/SGOF/HIGH/LOW/BASE
    # base must contain SWOF and SGOF, high and low can be missing
    if "SWOF" not in base_df.KEYWORD.unique():
        sys.exit("ERROR: No SWOF table provided for base")
    if "SGOF" not in base_df.KEYWORD.unique():
        sys.exit("ERROR: No SGOF table provided for base")

    # low
    if "SWOF" in low_df.KEYWORD.unique():
        has_low_SWOF = True
    if "SGOF" in low_df.KEYWORD.unique():
        has_low_SGOF = True
    if not has_low_SWOF and not has_low_SGOF:
        sys.exit(
            "ERROR: No tables provided for low; provide SWOF and/or SGOF")

    # high
    if "SWOF" in high_df.KEYWORD.unique():
        has_high_SWOF = True
    if "SGOF" in high_df.KEYWORD.unique():
        has_high_SGOF = True
    if not has_high_SWOF and not has_high_SGOF:
        sys.exit(
            "ERROR: No tables provided for high; provide SWOF and/or SGOF")

    # This is how we want to navigate the dataframes:
    base_df.set_index(["KEYWORD", "SATNUM"], inplace=True)
    low_df.set_index(["KEYWORD", "SATNUM"], inplace=True)
    high_df.set_index(["KEYWORD", "SATNUM"], inplace=True)

    # Sort for performance
    base_df.sort_index(inplace=True)
    low_df.sort_index(inplace=True)
    high_df.sort_index(inplace=True)

    # Loop over satnum and interpolate according to defaul and cfg values
    interpolants = []
    satnums = range(
        1, base_df.reset_index("SATNUM")["SATNUM"].unique().max()+1
        )

    for satnum in satnums:
        interp_values = {"param_w": 0, "param_g": 0}

        for interp in cfg["interpolations"]:
            for key in ["param_w", "param_g"]:
                if "tables" not in interp.keys():
                    if key in interp.keys():
                        interp_values[key] = interp[key]
                elif satnum in interp["tables"] and key in interp.keys():
                    interp_values[key] = interp[key]
                elif "all" in interp["tables"] and key in interp.keys():
                    interp_values[key] = interp[key]

        interpolants.append(
            make_interpolant(
                base_df,
                low_df,
                high_df,
                interp_values,
                satnum,
                has_high_SWOF,
                has_low_SWOF,
                has_high_SGOF,
                has_low_SGOF,
                relperm_delta_s,
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
