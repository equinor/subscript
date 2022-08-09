import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import configsuite  # lgtm [py/import-and-import-from]
import pandas as pd
import pyscal
import yaml
from configsuite import MetaKeys as MK  # lgtm [py/import-and-import-from]
from configsuite import types  # lgtm [py/import-and-import-from]
from ecl2df import satfunc

import subscript

logger = subscript.getLogger(__name__)

DESCRIPTION = """Interpolation script for relperm tables.

The script reads files with SWOF/SGOF tables (or family 2) with base/high/low
curves in SWOF and SGOF tables from files and interpolates in between, using
interpolation parameter(s) in the range [-1,1], so that -1, 0, and 1
correspond to low, base, and high respectively.

The tables must contain both SWOF and SGOF (or SWFN and SGFN) to ensure
consistent endpoints. Files for base, low and high must be declared, however
they may be identical in the case only "low" and "high" is available, and
together with an adjusted interpolation parameter range.

The interpolation parameter ``param_w`` in the YAML configuration will be used
to interpolate KRW, KROW and PCOW. The parameter ``param_g`` is used for KRG,
KROG and PCOG. These parameters can be set individually pr. SATNUM.
"""

EPILOGUE = """
.. code-block:: yaml

  # Example config file for interp_relperm

  base:
    # SWOF and SGOF in one unified or two separate files.
    # Absolute or relative paths are accepted. Relative paths are
    # interpreted with respect to command line option --root-path
    - swof_base.inc
    - /project/snakeoil/r017f/ert/input/relperm/sgof_base.inc

  high:
    - swof_opt.inc
    - ../include/sgof_opt.inc

  low:
    - swof_pes.inc
    - /project/snakeoil/user/best/r001/ert/input/relperm/sgof_low.inc

  pyscalfile: scal_input.xlsx  # Optional, alternative to providing low/base/high

  result_file: outfile.inc  # Required: Name of output file with interpolated tables

  family: 1  # Eclipse keyword family. Optional. 1 is default, 2 is the alternative

  delta_s: 0.02  # Optional: resolution of Sw/Sg, defaulted to 0.01

  # Required: applied in order of appearance so that
  # a default value for all tables can set and overrided
  # for individual satnums later.
  interpolations:
    - tables: []
      # Required: list of satnums to be interpolated
      # empty list interpreted as all entries
      # for individual satnums later.
      param_w: -0.23
      param_g:  0.44

  # Required: list of satnums to be interpolated
  # empty list interpreted as all entries

    - tables: [1]
      # will only apply to satnum nr. 1, for SWOF and SGOF
      param_w: -0.23
      param_g:  0.24

    - tables: [2,5,75]
      # applies to satnum 2, 5, and 75, for SWOF
      # (not SGOF since param_g not declared) SGOF
      # will be interpolated using 0.44, from above.
      # If a parameter not set, no interpolation will
      # be applied ie base table is returned
      param_w:  0.5

"""

CATEGORY = "modelling.reservoir"

EXAMPLES = """
.. code-block:: console

 FORWARD_MODEL INTERP_RELPERM(<INTERP_CONFIG>=interp_relperm.yml, <ROOT_PATH>=<CONFIG_PATH>)

"""  # noqa


@configsuite.validator_msg("Valid file name")
def _is_filename(filename: str):
    return Path(filename).exists()


@configsuite.validator_msg("Valid interpolator list")
def _is_valid_interpolator_list(interpolators: list):
    if len(interpolators) > 0:
        return True
    return False


@configsuite.validator_msg("Valid interpolator")
def _is_valid_interpolator(interp: dict):
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


@configsuite.validator_msg("Low, base and high are provided")
def _is_valid_table_entries(schema: dict):
    if "base" in schema and "low" in schema and "high" in schema:
        if schema["low"] and schema["base"] and schema["high"]:
            return (
                isinstance(schema["low"], tuple)
                and isinstance(schema["base"], tuple)
                and isinstance(schema["high"], tuple)
            )
    if "pyscalfile" in schema:
        # If pyscalfile is given, we don't need low/base/high
        return True
    return False


@configsuite.validator_msg("Valid Eclipse keyword family")
def _is_valid_eclipse_keyword_family(familychoice: int):
    return familychoice in [1, 2]


def get_cfg_schema() -> dict:
    """
    Defines the yml config schema
    """
    schema = {
        MK.Type: types.NamedDict,
        MK.ElementValidators: (_is_valid_table_entries,),
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
            "pyscalfile": {
                MK.Type: types.String,
                MK.ElementValidators: (_is_filename,),
                MK.AllowNone: True,
            },
            "result_file": {MK.Type: types.String},
            "family": {
                MK.Type: types.Number,
                MK.Default: 1,
                MK.ElementValidators: (_is_valid_eclipse_keyword_family,),
            },
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


def parse_satfunc_files(filenames: List[str]) -> pd.DataFrame:
    """
    Routine to gather scal tables (SWOF and SGOF) from ecl include files.

    Parameters:
        filenames: List with filenames to be parsed. Assumed to contain Eclipse
            saturation function keywords.

    Returns:
        dataframe with the tables
    """

    return pd.concat(
        [
            satfunc.df(Path(filename).read_text(encoding="utf8"))
            for filename in filenames
        ],
        sort=False,
    ).set_index("SATNUM")


def make_wateroilgas(dframe: pd.DataFrame, delta_s: float) -> pyscal.WaterOilGas:
    """Construct a pyscal WaterOilGas object from a dataframe of tabulated
    relperm and capillary pressure values

    Arguments:
        dframe: Containing tabulated values with pyscals column naming.
            The data must be restricted to only one SATNUM.
    """
    dframe = dframe.copy()  # Copy since we will modify it.
    wog = pyscal.WaterOilGas(swl=dframe["SW"].min(), h=delta_s)
    if "PCOW" not in dframe:
        dframe = dframe.assign(PCOW=0)
    if "PCOG" not in dframe:
        dframe = dframe.assign(PCOG=0)

    # If we have parsed family 2 input, KRO and KROW are not
    # on the same row. Merge the rows into family 1 style:
    if "KEYWORD" in dframe and "SOF3" in dframe["KEYWORD"].values:
        sof3_rows = dframe["KEYWORD"] == "SOF3"
        dframe.loc[sof3_rows, "SW"] = 1 - dframe[sof3_rows]["SO"]
        swl = dframe["SW"].min()
        dframe.loc[sof3_rows, "SG"] = 1 - swl - dframe[sof3_rows]["SO"]
        wo_dframe = (
            dframe[["SW", "KRW", "KROW", "PCOW"]]
            .set_index("SW")
            .sort_index()
            .dropna(how="all")
            .interpolate(method="index")
            .fillna(method="bfill")
            .round(8)
            .drop_duplicates()
            .reset_index()
        )
        go_dframe = (
            dframe[["SG", "KRG", "KROG", "PCOG"]]
            .set_index("SG")
            .sort_index()
            .dropna(how="all")
            .interpolate(method="index")
            .fillna(method="bfill")
            .round(8)
            .drop_duplicates()
            .reset_index()
        )
    else:
        wo_dframe = dframe[["SW", "KRW", "KROW", "PCOW"]].dropna().reset_index()
        go_dframe = dframe[["SG", "KRG", "KROG", "PCOG"]].dropna().reset_index()

    wog.wateroil.add_fromtable(wo_dframe)
    wog.gasoil.add_fromtable(go_dframe)

    # socr can for floating point reasons become estimated to be larger than
    # sorw, which means we are in an oil paleo zone setting. This is not
    # supported by interp_relperm. Reset the property to ensure interpolation
    # is not affected:
    wog.wateroil.socr = wog.wateroil.sorw

    # If sgro > 0, it is a gas condensate object, which cannot be
    # mixed with non-gas condensate (during interpolation). Avoid pitfalls
    # in the estimated sgro by always setting it to zero:
    wog.gasoil.sgro = 0.0
    return wog


def make_interpolant(
    base_df: pd.DataFrame,
    low_df: pd.DataFrame,
    high_df: pd.DataFrame,
    interp_param: Dict[str, float],
    satnum: int,
    delta_s: float,
) -> pyscal.WaterOilGas:
    """
    Define a pyscal WaterOilGas interpolant

    Parameters:
        base_df: containing the base tables
        low_df: containing the low tables
        high_df: containing the high tables
        interp_param: With keys ('param_w', 'param_g'),
            the interp parameter values
        satnum: the satuation number index
        delta_s: the saturation spacing to be used in out tables
    """

    base = make_wateroilgas(base_df.loc[satnum], delta_s)
    low = make_wateroilgas(low_df.loc[satnum], delta_s)
    high = make_wateroilgas(high_df.loc[satnum], delta_s)
    rec = pyscal.SCALrecommendation(low, base, high, "SATNUM " + str(satnum), h=delta_s)

    return rec.interpolate(interp_param["param_w"], interp_param["param_g"], h=delta_s)


def get_parser() -> argparse.ArgumentParser:
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
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + subscript.__version__ + ")",
    )
    return parser


def main() -> None:
    """Invocated from the command line, parsing command line arguments"""
    parser = get_parser()
    args = parser.parse_args()

    logger.setLevel(logging.INFO)

    # Mute expected warnings from ecl2df.inferdims, we get these
    # because we don't tell the module how many SATNUMs there are in
    # input files, which is slightly fragile for opm to parse.
    logging.getLogger("ecl2df.inferdims").setLevel(logging.ERROR)

    # parse the config file
    if not Path(args.configfile).exists():
        sys.exit("No such file:" + args.configfile)
    cfg = yaml.safe_load(Path(args.configfile).read_text(encoding="utf8"))
    process_config(cfg, Path(args.root_path))


def prepend_root_path_to_relative_files(
    cfg: Dict[str, Any], root_path: Path
) -> Dict[str, Any]:
    """Prepend root_path to relative files found paths in a configuration
    dictionary.

    Note: This function is before prior to validation of the configuration!

    Will look for list of filenames in the keys "pyscalfile, base, low and high"

    Args:
        cfg: interp_relperm configuration dictionary
        root_path: An relative or absolute path to be prepended

    Returns:
        Modified configuration for interp_relperm
    """
    if "base" in cfg.keys() and isinstance(cfg["base"], list):
        for idx in range(len(cfg["base"])):
            if not os.path.isabs(cfg["base"][idx]):
                cfg["base"][idx] = str(root_path / Path(cfg["base"][idx]))
    if "high" in cfg.keys() and isinstance(cfg["high"], list):
        for idx in range(len(cfg["high"])):
            if not os.path.isabs(cfg["high"][idx]):
                cfg["high"][idx] = str(root_path / Path(cfg["high"][idx]))
    if "low" in cfg.keys() and isinstance(cfg["low"], list):
        for idx in range(len(cfg["low"])):
            if not os.path.isabs(cfg["low"][idx]):
                cfg["low"][idx] = str(root_path / Path(cfg["low"][idx]))
    if "pyscalfile" in cfg.keys():
        if not os.path.isabs(cfg["pyscalfile"]):
            cfg["pyscalfile"] = str(root_path / Path(cfg["pyscalfile"]))

    return cfg


def process_config(cfg: Dict[str, Any], root_path: Optional[Path] = None) -> None:
    """
    Process a configuration and dumps produced Eclipse include file to disk.

    Args:
        cfg: Configuration for files to parse and interpolate in
        root_path: Prepended to the file paths
    """

    if root_path is not None:
        cfg = prepend_root_path_to_relative_files(cfg, root_path)

    cfg_schema = get_cfg_schema()
    cfg_suite = configsuite.ConfigSuite(cfg, cfg_schema, deduce_required=True)

    if not cfg_suite.valid:
        logger.error("Sorry, the configuration is invalid.")
        sys.exit(cfg_suite.errors)

    # set default values
    relperm_delta_s = False
    if cfg_suite.snapshot.delta_s:
        relperm_delta_s = cfg_suite.snapshot.delta_s

    base_df: pd.DataFrame = pd.DataFrame()
    low_df: pd.DataFrame = pd.DataFrame()
    high_df: pd.DataFrame = pd.DataFrame()

    if cfg_suite.snapshot.pyscalfile is not None:
        if cfg_suite.snapshot.base or cfg_suite.snapshot.low or cfg_suite.snapshot.high:
            logger.error(
                "Inconsistent configuration. "
                "You cannot define both pyscalfile and base/low/high"
            )
            sys.exit(1)

        logger.info(
            "Loading relperm parametrization from %s", cfg_suite.snapshot.pyscalfile
        )
        param_dframe = pyscal.PyscalFactory.load_relperm_df(
            cfg_suite.snapshot.pyscalfile
        ).set_index("CASE")
        base_df = (
            pyscal.PyscalFactory.create_pyscal_list(param_dframe.loc["base"])
            .df()
            .set_index("SATNUM")
        )
        low_df = (
            pyscal.PyscalFactory.create_pyscal_list(param_dframe.loc["low"])
            .df()
            .set_index("SATNUM")
        )
        high_df = (
            pyscal.PyscalFactory.create_pyscal_list(param_dframe.loc["high"])
            .df()
            .set_index("SATNUM")
        )
    else:
        # Parse tables from files
        base_df = parse_satfunc_files(cfg_suite.snapshot.base)
        low_df = parse_satfunc_files(cfg_suite.snapshot.low)
        high_df = parse_satfunc_files(cfg_suite.snapshot.high)

    if not (
        set(base_df.columns) == set(low_df.columns)
        and set(base_df.columns) == set(high_df.columns)
    ):
        logger.error("Base input had columns: %s", str(base_df.columns.values))
        logger.error("Low input had columns: %s", str(low_df.columns.values))
        logger.error("High input had columns: %s", str(high_df.columns.values))
        logger.error("Inconsistent input data, check keywords in input files")
        sys.exit(1)

    # Loop over satnum and interpolate according to default and cfg values
    interpolants = pyscal.PyscalList()
    satnums = range(1, base_df.reset_index("SATNUM")["SATNUM"].unique().max() + 1)
    for satnum in satnums:
        interp_values = {"param_w": 0.0, "param_g": 0.0}
        for interp in cfg_suite.snapshot.interpolations:
            if not interp.tables or satnum in interp.tables:
                if interp.param_w:
                    interp_values["param_w"] = interp.param_w
                if interp.param_g:
                    interp_values["param_g"] = interp.param_g

        interpolants.append(
            make_interpolant(
                base_df.loc[satnum],
                low_df.loc[satnum],
                high_df.loc[satnum],
                interp_values,
                satnum,
                relperm_delta_s,
            )
        )

    Path(cfg_suite.snapshot.result_file).write_text(
        interpolants.build_eclipse_data(cfg_suite.snapshot.family), encoding="utf-8"
    )

    logger.info(
        "Done; interpolated relperm curves written to file: %s",
        str(cfg_suite.snapshot.result_file),
    )


if __name__ == "__main__":
    main()
