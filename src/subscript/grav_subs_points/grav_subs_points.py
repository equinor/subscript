import argparse
import logging
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import yaml
from pydantic import BaseModel, Field, FilePath, field_validator
from resdata.gravimetry import ResdataGrav, ResdataSubsidence
from resdata.grid import Grid
from resdata.resfile import ResdataFile
from typing_extensions import Annotated

import subscript

logger = subscript.getLogger(__name__)

# Constant for subsidence modelling, not influencing results
# since subsidence is calculated from porevolume change RPORV
# therefore defaulted
DUMMY_YOUNGS = 10

PREFIX_POINTS = "all"  # calculation is cumulative over all zones
EXTENSION_POINTS = ".txt"  # extension for points in roxar points format
PREFIX_GENDATA = ""
EXTENSION_GENDATA = "_1.txt"  # extension for points to Ert GENDATA

DESCRIPTION = """
Modelling gravity change and subsidence based on flow simulation
output (EGRID, INIT and UNRST files) for a list of locations (
bencmark stations) at seabed.

The script reads flow simulation results and a yaml configuration file
specifying input and calculation parameters.
For configuration of the yaml config file, see:
https://fmu-docs.equinor.com/docs/subscript/scripts/grav_subs_points.html

"""

EPILOGUE = """
.. code-block:: yaml

  # Example config file for grav_subs_points

  input:
        - [2020-07-01, 2018-01-01] # Difference date to model. Must exist in UNRST file.

  stations: # Path to files with station coordinates to model for each difference years
    grav:
      "2020_2018": station_coordinates.csv
    subs:
      "2020_2018": station_coordinates.csv

  calculations:
    poisson_ratio: 0.45 # For subsidence calulcations, used in Geertsma model
    phases: ["gas", "oil","water", "total"] # One pointset for each phase specified

.. code-block:: plaintext

  The file with station coordinates should be on .csv format and contain headers
  as specified in this example:

  bm_id;utmx;utmy;depth;area
  1;462632.692871;5930050.419434;200.000000;WL
  2;464438.063965;5932652.277710;200.000000;CH
  3;462924.737793;5933448.764526;200.000000;CH
  4;459977.734863;5935121.387695;200.000000;NH
  5;462247.045000;5934298.281000;200.000000;CH
  6;461517.610352;5933448.764526;200.000000;CN
  7;463933.621582;5931643.393677;200.000000;CS
  8a;463429.180176;5935068.288086;200.000000;EL
  9b;460561.825684;5936608.163086;200.000000;CH
  10;460482.177246;5931723.042358;200.000000;WL

  bm_id: Name of the bencmark location.
  utmx: UTM X for the bencmark location [m]
  utmy: UTM Y for the bencmark location [m]
  depth: Seabed depth for benchmark location [m TVD MSL]
  area: An area identifier that can be used for grouping in visualisations

"""


CATEGORY = "modelling.reservoir"


EXAMPLES = """
.. code-block:: console

  FORWARD_MODEL GRAV_SUBS_POINTS(<UNRST_FILE=<ECLBASE>.UNRST, <GRAV_CONFIG>=grav_subs_points.yml, <ROOT_PATH>=<CONFIG_PATH>, <OUTPUTDIR>=share/results/points)

where ``ECLBASE`` is already defined in your ERT config, pointing to the flowsimulator
basename relative to ``RUNPATH``, grav_subs_points.yml is a YAML file defining
the inputs and modelling parameters and ``OUTPUTDIR`` is the path to the output folder.
``ROOT_PATH`` is optinal and defaulted to "./". This is the rooth path assumed for
relative paths in the yml config.

The directory to export point files to must exist.
"""  # noqa


class GravPointsInput(BaseModel):
    diffdates: List[Tuple[date, date]]


class GravPointsStations(BaseModel):
    grav: Dict[str, FilePath]
    subs: Dict[str, FilePath]


class GravPointsCalc(BaseModel):
    poisson_ratio: Annotated[float, Field(strict=True, ge=0, le=0.5)]
    phases: List[str]

    @field_validator("phases")
    @classmethod
    def check_phases(cls, phases: List[str]) -> List[str]:
        allowed_phases = ["oil", "gas", "water", "total"]
        for item in phases:
            assert item in allowed_phases, f"allowed phases are {str(allowed_phases)}"
        return phases


class GravPointsConfig(BaseModel):
    input: GravPointsInput
    stations: GravPointsStations
    calculations: GravPointsCalc


def get_parser() -> argparse.ArgumentParser:
    """Function to create the argument parser that is going to be served to the user.

    Returns:
        argparse.ArgumentParser: The argument parser to be served

    """
    parser = argparse.ArgumentParser(
        prog="grav_subs_points.py",
        description=DESCRIPTION,
        epilog=EPILOGUE,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("UNRSTfile", type=str, help="Path to flowsimulator UNRST file")
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
        help=("Root path assumed for relative paths" " in config file."),
    )
    parser.add_argument(
        "-o",
        "--outputdir",
        type=str,
        help="Path to directory for output maps. Directory must exist.",
        default="./",
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

    # parse the config file
    if not Path(args.configfile).exists():
        sys.exit("No such file:" + args.configfile)
    config = yaml.safe_load(Path(args.configfile).read_text(encoding="utf8"))

    if not Path(args.outputdir).exists():
        sys.exit("Output folder does not exist:" + args.outputdir)
    if not Path(args.UNRSTfile).exists():
        sys.exit("UNRST file does not exist:" + args.UNRSTfile)

    main_gravpoints(args.UNRSTfile, config, Path(args.root_path), Path(args.outputdir))


def prepend_root_path_to_relative_files(
    cfg: Dict[str, Any], root_path: Path
) -> Dict[str, Any]:
    """Prepend root_path to relative files found paths in a configuration
    dictionary.

    Note: This function is before prior to validation of the configuration!

    Will look for filename in the keys "grav" and "subs"

    Args:
        cfg: grav_subs_points configuration dictionary
        root_path: A relative or absolute path to be prepended

    Returns:
        Modified configuration for grav_subs_points
    """

    stations = cfg.get("stations")

    if stations is None:
        return cfg

    for key in ["grav", "subs"]:
        if key in stations and isinstance(stations[key], dict):
            for item in stations[key]:
                if os.path.isabs(stations[key][item]):
                    continue

                stations[key][item] = str(root_path / Path(stations[key][item]))

    return cfg


def export_grav_points_xyz(act_stations, phase, diff_date, out_folder) -> None:
    """Write points in xyz format, roxar.FileFormat.RMS_POINTS"""
    logger.info(f"Exporting simulated gravity values to {out_folder} as xyz points")
    outfile = (
        PREFIX_POINTS
        + "--"
        + "delta_gravity_"
        + phase
        + "--"
        + diff_date[0]
        + "_"
        + diff_date[1]
        + EXTENSION_POINTS
    )

    with open(os.path.join(out_folder, outfile), "w") as file:
        for index, row in act_stations.iterrows():
            file.write(
                f"{row['utmx']:.3f} {row['utmy']:.3f} "
                f"{row['dgsim_'+phase+'_'+diff_date[0]+'_'+diff_date[1]]:.3f} \n"
            )


def export_grav_points_ert(act_stations, diff_date, out_folder) -> None:
    """Export for ert for each diffdate, only total, not per phase"""
    logger.info(f"Exporting simulated gravity values to {out_folder} for use by ert")
    part = act_stations["dgsim_total_" + diff_date[0] + "_" + diff_date[1]]
    outfile = (
        PREFIX_GENDATA
        + "gravity_"
        + diff_date[0]
        + "_"
        + diff_date[1]
        + EXTENSION_GENDATA
    )

    output_path = Path(out_folder) / outfile
    part.to_csv(output_path, header=None, index=None)


def export_subs_points_xyz(act_stations, diff_date, out_folder) -> None:
    """Write points in xyz format, roxar.FileFormat.RMS_POINTS"""
    logger.info(f"Exporting simulated subsidence values to {out_folder} as xyz points")
    outfile = (
        PREFIX_POINTS
        + "--"
        + "subsidence"
        + "--"
        + diff_date[0]
        + "_"
        + diff_date[1]
        + EXTENSION_POINTS
    )

    with open(os.path.join(out_folder, outfile), "w") as file:
        for index, row in act_stations.iterrows():
            file.write(
                f"{row['utmx']:.3f} {row['utmy']:.3f} "
                f"{row['subsidence_'+diff_date[0]+'_'+diff_date[1]]:.3f}\n"
            )


def export_subs_points_ert(act_stations, diff_date, out_folder) -> None:
    """Export for ert for each diffdate"""
    logger.info(f"Exporting simulated subsidence values to {out_folder} for use by ert")
    part = act_stations["subsidence_" + diff_date[0] + "_" + diff_date[1]]
    outfile = (
        PREFIX_GENDATA
        + "subsidence_"
        + diff_date[0]
        + "_"
        + diff_date[1]
        + EXTENSION_GENDATA
    )

    output_path = Path(out_folder) / outfile
    part.to_csv(output_path, header=None, index=None)


def main_gravpoints(
    unrst_file: str,
    config: Dict[str, Any],
    root_path: Optional[Path],
    output_folder: Path,
) -> None:
    """
    Process a configuration, model gravity and subsidence points and write to disk.

    Args:
        resdata: Path to flow simulation UNRST file
        config: Configuration for modelling
    """

    if root_path is not None:
        config = prepend_root_path_to_relative_files(config, root_path)

    cfg = GravPointsConfig.model_validate(config).model_dump()

    # Read inputs and calculation parameters
    input_diffdates = cfg["input"]["diffdates"]
    station_files = cfg["stations"]
    phases = cfg["calculations"]["phases"]
    poisson_ratio = cfg["calculations"]["poisson_ratio"]

    if isinstance(unrst_file, str):
        restart_file = unrst_file[:-6] + ".UNRST"
        egrid_file = unrst_file[:-6] + ".EGRID"
        init_file = unrst_file[:-6] + ".INIT"
        grid = Grid(egrid_file)
        init = ResdataFile(init_file)
        rest = ResdataFile(restart_file)

    restart_index = {}

    # From restart datetime format to YYYYMMDD as key
    for i, restart_date in enumerate(rest.dates):
        restart_index[restart_date.strftime("%Y%m%d")] = i

    diffdates = []
    # Convert dates from datetime format to strings
    logger.info("Starting modelling for diffdates: ")
    for diffdate in input_diffdates:
        diff = [diffdate[0].strftime("%Y%m%d"), diffdate[1].strftime("%Y%m%d")]
        diffdates.append(diff)
        logger.info(f"{diffdate[0]}_{diffdate[1]}")

    grav = ResdataGrav(grid, init)
    subsidence = ResdataSubsidence(grid, init)

    added_dates = []

    for diffdate in diffdates:
        for singledate in diffdate:  # base and monitor
            rsb = rest.restartView(0)
            if singledate not in added_dates:
                if singledate in restart_index:
                    rsb = rest.restartView(restart_index[singledate])
                    grav.add_survey_RFIP(singledate, rsb)
                    subsidence.add_survey_PRESSURE(singledate, rsb)
                    added_dates.append(singledate)
                else:
                    logger.error(
                        f"Date {singledate} specified but not found in UNRST file."
                    )
                    sys.exit(1)

    phase_code = {"oil": 1, "gas": 2, "water": 4, "total": 7}

    # Gravity
    for diffdate in diffdates:
        diff_year = str(diffdate[0][0:4]) + "_" + str(diffdate[1][0:4])
        active_stations = pd.read_csv(station_files["grav"][diff_year], sep=";")

        for phase in phases:
            logger.info(
                f"Calculating delta gravity at bencmark stations "
                f"from {phase} for {diffdate[0]}_{diffdate[1]}"
            )

            gravity_values = [
                grav.eval(
                    diffdate[1], diffdate[0], (x, y, z), phase_mask=phase_code[phase]
                )
                for x, y, z in zip(
                    active_stations["utmx"],
                    active_stations["utmy"],
                    active_stations["depth"],
                )
            ]
            active_stations[
                "dgsim_" + phase + "_" + diffdate[0] + "_" + diffdate[1]
            ] = gravity_values

            # Export for each diffdate, all phases specified in config
            export_grav_points_xyz(active_stations, phase, diffdate, output_folder)

        # Export to ert for each diffdate, only total, not per phase
        export_grav_points_ert(active_stations, diffdate, output_folder)

    # Subsidence

    for diffdate in diffdates:
        diff_year = str(diffdate[0][0:4]) + "_" + str(diffdate[1][0:4])
        active_stations = pd.read_csv(station_files["subs"][diff_year], sep=";")

        subs_values = [
            subsidence.eval_geertsma_rporv(
                diffdate[1], diffdate[0], (x, y, z), DUMMY_YOUNGS, poisson_ratio, z
            )
            for x, y, z in zip(
                active_stations["utmx"],
                active_stations["utmy"],
                active_stations["depth"],
            )
        ]

        active_stations["subsidence" + "_" + diffdate[0] + "_" + diffdate[1]] = [
            i * 100 for i in subs_values
        ]  # from m to cm

        export_subs_points_xyz(active_stations, diffdate, output_folder)

        export_subs_points_ert(active_stations, diffdate, output_folder)

    logger.info(
        f"Done; All gravity and subsidence points written to folder: "
        f"{str(output_folder)}",
    )


if __name__ == "__main__":
    main()
