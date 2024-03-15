from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import pandas as pd
import pyscal
import yaml
from pydantic import BaseModel, Field, FilePath, model_validator
from res2df import satfunc
from typing_extensions import Annotated

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


class Interpolator(BaseModel):
    tables: Optional[List[int]] = []
    param_w: Optional[Annotated[float, Field(strict=True, ge=-1, le=1)]] = None
    param_g: Optional[Annotated[float, Field(strict=True, ge=-1, le=1)]] = None

    @model_validator(mode="after")
    def check_param_w_or_param_g(self) -> Interpolator:
        assert (
            self.param_w is not None or self.param_g is not None
        ), "Provide either param_w or param_g"
        return self


class InterpRelpermConfig(BaseModel):
    low: Optional[List[FilePath]] = None
    base: Optional[List[FilePath]] = None
    high: Optional[List[FilePath]] = None
    pyscalfile: Optional[FilePath] = None
    result_file: str
    family: Literal[1, 2] = 1
    delta_s: float = 0.01
    interpolations: Annotated[List[Interpolator], Field(..., min_length=1)]

    @model_validator(mode="after")
    def check_lowbasehigh_or_pyscalfile(self) -> InterpRelpermConfig:
        if self.pyscalfile is None:
            assert self.base is not None, "base is not provided"
            assert self.high is not None, "high is not provided"
            assert self.low is not None, "low is not provided"
        else:
            assert self.base is None, "do not specify base when pyscalfile is set"
            assert self.high is None, "do not specify high when pyscalfile is set"
            assert self.low is None, "do not specify low when pyscalfile is set"
        return self


def parse_satfunc_files(filenames: List[Path]) -> pd.DataFrame:
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
            .bfill()
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
            .bfill()
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

    # Mute expected warnings from res2df.inferdims, we get these
    # because we don't tell the module how many SATNUMs there are in
    # input files, which is slightly fragile for opm to parse.
    logging.getLogger("res2df.inferdims").setLevel(logging.ERROR)

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
    if "base" in cfg and isinstance(cfg["base"], list):
        for idx in range(len(cfg["base"])):
            if not os.path.isabs(cfg["base"][idx]):
                cfg["base"][idx] = str(root_path / Path(cfg["base"][idx]))
    if "high" in cfg and isinstance(cfg["high"], list):
        for idx in range(len(cfg["high"])):
            if not os.path.isabs(cfg["high"][idx]):
                cfg["high"][idx] = str(root_path / Path(cfg["high"][idx]))
    if "low" in cfg and isinstance(cfg["low"], list):
        for idx in range(len(cfg["low"])):
            if not os.path.isabs(cfg["low"][idx]):
                cfg["low"][idx] = str(root_path / Path(cfg["low"][idx]))
    if "pyscalfile" in cfg and not os.path.isabs(cfg["pyscalfile"]):
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

    config = InterpRelpermConfig(**cfg)

    base_df: pd.DataFrame = pd.DataFrame()
    low_df: pd.DataFrame = pd.DataFrame()
    high_df: pd.DataFrame = pd.DataFrame()

    if config.pyscalfile is not None:
        if config.base or config.low or config.high:
            logger.error(
                "Inconsistent configuration. "
                "You cannot define both pyscalfile and base/low/high"
            )
            sys.exit(1)

        logger.info("Loading relperm parametrization from %s", config.pyscalfile)
        param_dframe = pyscal.PyscalFactory.load_relperm_df(
            config.pyscalfile
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
        assert config.base is not None
        base_df = parse_satfunc_files(config.base)
        assert config.low is not None
        low_df = parse_satfunc_files(config.low)
        assert config.high is not None
        high_df = parse_satfunc_files(config.high)

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
        for interp in config.interpolations:
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
                config.delta_s,
            )
        )

    Path(config.result_file).write_text(
        interpolants.build_eclipse_data(config.family), encoding="utf-8"
    )

    logger.info(
        "Done; interpolated relperm curves written to file: %s",
        str(config.result_file),
    )


if __name__ == "__main__":
    main()
