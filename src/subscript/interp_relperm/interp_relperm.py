import sys
import os
import logging
import argparse

import yaml
import pandas as pd

import pyscal

from ecl2df import satfunc
import subscript

import configsuite
from configsuite import types
from configsuite import MetaKeys as MK

logger = subscript.getLogger(__name__)

DESCRIPTION = """Interpolation script for relperm tables.
Script reads base/high/low SWOF and SGOF tables from files and
interpolates in between, using interpolation parameter(s) in range
[-1,1], so that -1, 0, and 1 corresponds to low, base, and high tables
respectively.

The base tables must contain both SWOF and SGOF to ensure consistent
endpoints. Files for base, low and high must be declared, however
they may be identical. Consequently, if either base, low or high
is missing in the scal recommendation, two of the inputs can be
set to point to the same file and by adjusting the interpolation
range accordingly interpolation between base and high, or low and
high may be achieved.

Krw, Krow, Pcow interpolated using parameter param_w

Krg, Krog, Pcog interpolated using parameter param_g

"""

EPILOGUE = """
.. code-block:: yaml

  # Example config file

  base:
    # Required: SWOF and SGOF in one unified or two separate files.
    # Absolute or relative paths are accepted. Relative paths are
    # interpreted with respect to command line option --root-path
    - swof_base.inc
    - /project/snakeoil/r017f/ert/input/relperm/sgof_base.inc

  high:
    # Required: the phase(s) to be interpolated must be present,
    # ie can drop either SWOF or SGOF if not relevant.
    - swof_opt.inc
    - ../include/sgof_opt.inc

  low:
    # Required: see high
    - swof_pes.inc
    - /project/snakeoil/user/best/r001/ert/input/relperm/sgof_low.inc

  result_file  : outfilen.inc  # Required: Name of output file with interpolated tables

  delta_s      : 0.02          # Optional: resolution of Sw/Sg, defaulted to 0.01

  # Required: applied in order of appearance so that
  # a default value for all tables can set and overrided
  # for individual satnums later.
  interpolations:
    - tables   : []
      # Required: list of satnums to be interpolated
      # empty list interpreted as all entries
      # for individual satnums later.
      param_w  : -0.23
      param_g  :  0.44

  # Required: list of satnums to be interpolated
  # empty list interpreted as all entries

    - tables : [1]
      # will only apply to satnum nr. 1, for SWOF and SGOF
      param_w  : -0.23
      param_g  :  0.24

    - tables : [2,5,75]
      # applies to satnum 2, 5, and 75, for SWOF
      # (not SGOF since param_g not declared) SGOF
      # will be interpolated using 0.44, from above.
      # If a parameter not set, no interpolation will
      # be applied ie base table is returned
      param_w  :  0.5

"""

CATEGORY = "modeling.reservoir"

EXAMPLES = """
.. code-block:: console

 FORWARD_MODEL INTERP_RELPERM(<INTERP_CONFIG>=interp_relperm.yml, <ROOT_PATH>=<CONFIG_PATH>)

"""  # noqa


@configsuite.validator_msg("Valid file name")
def _is_filename(fname):
    return os.path.isfile(fname)


@configsuite.validator_msg("Valid interpolator list")
def _is_valid_interpolator_list(interpolators):
    if len(interpolators) > 0:
        return True
    return False


@configsuite.validator_msg("Valid interpolator")
def _is_valid_interpolator(interp):
    valid = False

    try:
        if interp["param_w"]:
            valid = True
        elif interp["param_w"] == 0:
            valid = True

    except (KeyError, ValueError, TypeError):
        pass

    try:
        if interp["param_w"] > 1.0 or interp["param_w"] < -1.0:
            valid = False
    except (KeyError, ValueError, TypeError):
        pass

    try:
        if interp["param_g"]:
            valid = True
        elif interp["param_g"] == 0:
            valid = True
    except (KeyError, ValueError, TypeError):
        pass

    try:
        if interp["param_g"] > 1.0 or interp["param_g"] < -1.0:
            valid = False
    except (KeyError, ValueError, TypeError):
        pass

    return valid


@configsuite.validator_msg("Valid table entries")
def _is_valid_table_entries(schema):

    valid = False
    try:
        if schema["low"]:
            valid = True
    except (KeyError, ValueError, TypeError):
        pass

    try:
        if schema["high"]:
            valid = True
    except (KeyError, ValueError, TypeError):
        pass

    return valid


def get_cfg_schema():
    """
    Defines the yml config schema
    """
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
            "delta_s": {MK.Type: types.Number, MK.Default: 0.01},
            "interpolations": {
                MK.Type: types.List,
                MK.ElementValidators: (_is_valid_interpolator_list,),
                MK.Content: {
                    MK.Item: {
                        MK.Type: types.NamedDict,
                        MK.ElementValidators: (_is_valid_interpolator,),
                        MK.Content: {
                            "tables": {
                                MK.Type: types.List,
                                MK.Content: {MK.Item: {MK.Type: types.Integer}},
                            },
                            "param_w": {MK.Type: types.Number, MK.AllowNone: True},
                            "param_g": {MK.Type: types.Number, MK.AllowNone: True},
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
        filenames (list): List with filenames (str) to be parsed.
            Assumed to contain ecl SCAL tables

    Returns:
        dataframe with the tables
    """

    return pd.concat(
        [satfunc.df(open(filename).read()) for filename in filenames], sort=False
    )


def make_interpolant(base_df, low_df, high_df, interp_param, satnum, delta_s):
    """
    Routine to define a pyscal.interpolant instance and perform interpolation.

    Parameters:
        base_df (pd.DataFrame): containing the base tables
        low_df (pd.DataFrame): containing the low tables
        high_df (pd.DataFrame): containing the high tables
        interp_param (dict): With keys ('param_w', 'param_g'),
            the interp parameter values
        satnum (int): the satuation number index
        delta_s (float): the saturation spacing to be used in out tables

    Returns:
        pyscal.WaterOilGas: Object holding tables for one satnum
    """

    # Define base tables
    swlbase = base_df.loc["SWOF", satnum]["SW"].min()
    base = pyscal.WaterOilGas(swl=float(swlbase), h=delta_s)
    base.wateroil.add_fromtable(
        base_df.loc["SWOF", satnum].reset_index(),
        swcolname="SW",
        krwcolname="KRW",
        krowcolname="KROW",
        pccolname="PCOW",
    )

    # Define low tables
    if "SWOF" in low_df.index.unique():
        swllow = low_df.loc["SWOF", satnum]["SW"].min()
        low = pyscal.WaterOilGas(swl=float(swllow), h=delta_s)
        low.wateroil.add_fromtable(
            low_df.loc["SWOF", satnum].reset_index(),
            swcolname="SW",
            krwcolname="KRW",
            krowcolname="KROW",
            pccolname="PCOW",
        )
    else:
        swllow = base_df.loc["SWOF", satnum]["SW"].min()
        low = pyscal.WaterOilGas(swl=float(swllow), h=delta_s)
        low.wateroil.add_fromtable(
            base_df.loc["SWOF", satnum].reset_index(),
            swcolname="SW",
            krwcolname="KRW",
            krowcolname="KROW",
            pccolname="PCOW",
        )

    # Define high tables
    if "SWOF" in high_df.index.unique():
        swlhigh = high_df.loc["SWOF", satnum]["SW"].min()
        high = pyscal.WaterOilGas(swl=float(swlhigh), h=delta_s)
        high.wateroil.add_fromtable(
            high_df.loc["SWOF", satnum].reset_index(),
            swcolname="SW",
            krwcolname="KRW",
            krowcolname="KROW",
            pccolname="PCOW",
        )
    else:
        swlhigh = base_df.loc["SWOF", satnum]["SW"].min()
        high = pyscal.WaterOilGas(swl=float(swlhigh), h=delta_s)
        high.wateroil.add_fromtable(
            base_df.loc["SWOF", satnum].reset_index(),
            swcolname="SW",
            krwcolname="KRW",
            krowcolname="KROW",
            pccolname="PCOW",
        )

    # Correct types for Sg (sometimes incorrecly set to str)
    base_df["SG"] = base_df["SG"].astype("float64")

    base.gasoil.add_fromtable(
        base_df.loc["SGOF", satnum].reset_index(),
        sgcolname="SG",
        krgcolname="KRG",
        krogcolname="KROG",
        pccolname="PCOG",
    )

    if "SGOF" in low_df.index.unique():
        low_df["SG"] = low_df["SG"].astype("float64")
        low.gasoil.add_fromtable(
            low_df.loc["SGOF", satnum].reset_index(),
            sgcolname="SG",
            krgcolname="KRG",
            krogcolname="KROG",
            pccolname="PCOG",
        )
    else:
        low.gasoil.add_fromtable(
            base_df.loc["SGOF", satnum].reset_index(),
            sgcolname="SG",
            krgcolname="KRG",
            krogcolname="KROG",
            pccolname="PCOG",
        )

    if "SGOF" in high_df.index.unique():
        high_df["SG"] = high_df["SG"].astype("float64")
        high.gasoil.add_fromtable(
            high_df.loc["SGOF", satnum].reset_index(),
            sgcolname="SG",
            krgcolname="KRG",
            krogcolname="KROG",
            pccolname="PCOG",
        )
    else:
        high.gasoil.add_fromtable(
            base_df.loc["SGOF", satnum].reset_index(),
            sgcolname="SG",
            krgcolname="KRG",
            krogcolname="KROG",
            pccolname="PCOG",
        )

    rec = pyscal.SCALrecommendation(low, base, high, "SATNUM " + str(satnum), h=delta_s)

    if "SWOF" not in low_df.index.unique() and interp_param["param_w"] < 0:
        sys.exit(
            "Error: interpolation parameter for SWOF, satnum:"
            + str(satnum)
            + " set to "
            + str(interp_param["param_w"])
            + " but no low table is provided. Values cannot be negative"
        )

    if "SWOF" not in high_df.index.unique() and interp_param["param_w"] > 0:
        sys.exit(
            "Error: interpolation parameter for SWOF, satnum:"
            + str(satnum)
            + " set to "
            + str(interp_param["param_w"])
            + " but no high table is provided. Values cannot be positive"
        )

    if "SGOF" not in low_df.index.unique() and interp_param["param_g"] < 0:
        sys.exit(
            "Error: interpolation parameter for SGOF, satnum:"
            + str(satnum)
            + " set to "
            + str(interp_param["param_g"])
            + " but no low table is provided. Values cannot be negative"
        )

    if "SGOF" not in high_df.index.unique() and interp_param["param_g"] > 0:
        sys.exit(
            "Error: interpolation parameter for SGOF, satnum:"
            + str(satnum)
            + " set to "
            + str(interp_param["param_g"])
            + " but no high table is provided. Values cannot be positive"
        )

    return rec.interpolate(interp_param["param_w"], interp_param["param_g"], h=delta_s)


def get_parser():
    """
    Define the argparse parser
    """
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        epilog=EPILOGUE,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "-c",
        "-C",
        "--configfile",
        type=str,
        help="Name of YAML config file",
        required=True,
    )
    parser.add_argument(
        "-r",
        "--root-path",
        type=str,
        default="./",
        help=(
            "Root path assumed for relative paths"
            " in config file, except for the output file."
        ),
    )
    return parser


def main():
    """
    Main function; this is what is executed
    """
    parser = get_parser()
    args = parser.parse_args()

    logger.setLevel(logging.INFO)

    # Mute expected warnings from ecl2df.inferdims, we get these
    # because we don't tell the module how many SATNUMs there are in
    # input files, which is slightly fragile for opm to parse.
    logging.getLogger("ecl2df.inferdims").setLevel(logging.ERROR)

    # parse the config file
    if not os.path.isfile(args.configfile):
        sys.exit("No such file:" + args.configfile)
    else:
        with open(args.configfile, "r") as ymlfile:
            cfg = yaml.safe_load(ymlfile)
    process_config(cfg, args.root_path)


def process_config(cfg, root_path=""):
    """
    Process a configuration and dumps produced Eclipse include file to disk.

    Args:
        cfg (dict): Configuration for files to parse and interpolate in
        root_path (str): Preprended to the file paths. Defaults to empty string
    """
    # add root-path to all include files
    if "base" in cfg.keys():
        for idx in range(len(cfg["base"])):
            if not os.path.isabs(cfg["base"][idx]):
                cfg["base"][idx] = os.path.join(root_path, cfg["base"][idx])
    if "high" in cfg.keys():
        for idx in range(len(cfg["high"])):
            if not os.path.isabs(cfg["high"][idx]):
                cfg["high"][idx] = os.path.join(root_path, cfg["high"][idx])
    if "low" in cfg.keys():
        for idx in range(len(cfg["low"])):
            if not os.path.isabs(cfg["low"][idx]):
                cfg["low"][idx] = os.path.join(root_path, cfg["low"][idx])

    # validate cfg according to schema
    cfg_schema = get_cfg_schema()
    cfg_suite = configsuite.ConfigSuite(cfg, cfg_schema, deduce_required=True)

    if not cfg_suite.valid:
        logger.error("Sorry, the configuration is invalid.")
        sys.exit(cfg_suite.errors)

    # set default values
    relperm_delta_s = False
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
    if ("SWOF" not in low_df["KEYWORD"].unique()) and (
        "SGOF" not in low_df["KEYWORD"].unique()
    ):
        sys.exit("ERROR: No tables provided for low; provide SWOF and/or SGOF")

    # high
    if ("SWOF" not in high_df["KEYWORD"].unique()) and (
        "SGOF" not in high_df["KEYWORD"].unique()
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
            if not interp.tables or satnum in interp.tables:
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
    with open(cfg_suite.snapshot.result_file, "w") as fileh:
        fileh.write("SWOF\n")
        for interpolant in interpolants:
            fileh.write(interpolant.wateroil.SWOF(header=False))
        fileh.write("\nSGOF\n")
        for interpolant in interpolants:
            fileh.write(interpolant.gasoil.SGOF(header=False))

    logger.info(
        "Done; interpolated relperm curves written to file: %s",
        str(cfg_suite.snapshot.result_file),
    )


if __name__ == "__main__":
    main()
