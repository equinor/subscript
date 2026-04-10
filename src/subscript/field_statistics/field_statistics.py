#!/usr/bin/env python3
"""Purpose:
  Calculate mean and stdev of continuous field parameters
  Estimate volume fraction of facies (facies probabilities)
  Works for non-shared grids where nx, ny is fixed,
  but nz per zone may vary from realization to realization.
Result:
  Output mean and stdev for continuous field parameter
  Output estimate of facies probabilities for facies parameters
"""

import argparse
import copy
import logging
import sys
from pathlib import Path

import ert
import fmu.config.utilities as utils
import numpy as np
import xtgeo
import yaml
from numpy.ma import MaskedArray

import subscript

logger = subscript.getLogger(__name__)
DESCRIPTION_FOR_ERT = """Calculate mean, stdev and estimated facies probabilities
from field parameters using ERTBOX grid.
"""

DESCRIPTION = """Calculate mean, stdev and estimated facies probabilities
from field parameters using ERTBOX grid.

The script reads ensembles of realizations from scratch disk  from
<RUN_PATH> directory::

  share/results/grids/<geogridname>--<propertyname>.roff.

Optionally also temporary field parameters coming from APS or petrophysical
field parameters can be used to calculate mean and standard deviations.
The ensemble of realizations are usually located under <RUN_PATH> directory::

  rms/output/aps

Since the realizations may have a grid geometry that is realization dependent
and may have multiple zones, the values are first copied over to a static grid
called ERTBOX grid. Depending on the grid conformity of the geogrid zones,
the values are filled up from top or bottom of the ERTBOX grid. This is to
ensure that zones with varying number of layers for each realization can
be handled when calculating mean, standard deviation or estimated facies
probabilities.

The grid cell indices in the ERTBOX grid is a label of the parameter value,
and mean, standard deviation and facies fractions are calculated for
each specified property for each individual grid cell (I,J,K) in the ERTBOX grid.
Number of realizations of property values may vary from grid cell to grid cell
due to varying number of layers per realization and due to stair case faults.
Therefore also a parameter counting the number of realizations present for each
individual grid cell is also calculated and used in the estimates of mean,
standard deviation and facies probabilities.

The assumption behind this method (using ERTBOX grid as a fixed common grid for
all realizations) is:

    - The lateral extension of the geogrid is close to a regular grid with same
      orientation and grid resolution as the ERTBOX grid.
    - The ERTBOX grid should be the same as used in ERT when field parameters
      are updated using the ERT keyword FIELD in the ERT configuration file.
    - Any lateral variability of the geometry of the geogrid from realization
      to realization or curved shaped lateral grid is ignored.
      Only the cell indices are used to identify grid cell field parameters
      from each realization. This means that mean, standard deviation
      and estimated facies probabilities are estimated
      for each cell labeled with index (I,J,K) and not physical position (x,y,z).

The output statistical properties (mean, stdev, prob) is saved in a user
specified folder for the ERTBOX grid, but default if not specified
is 'share/grid_statistics' folder under the top level of the scratch
directory for the ERT case. The default estimate of standard deviation
is the sample standard deviation.




.. math::

  \\text{variance} = \\frac{\\sum (x_i - \\bar{x})^2}{N-1}

and number of realizations must be at least 2. Optionally, the population
standard deviation

.. math::

  \\text{variance} = \\frac{\\sum (x_i - \\bar{x})^2}{N}

can be specified.

For grid cells where number of realizations are less than 2,
the standard deviation parameter calculated will be set to 0.

The ERTBOX grid can now also be individual per geological zone. This means that
the user can define one ERTBOX grid per zone having the same lateral number of
grid cells as for the geomodel grid and number of layers that are at least as
large as the number of layers in the zone (for all realizations).

The advantage of using individual ERTBOX grid per geomodel grid zone is to
reduce unwanted disk space, memory and runtime when running on a case with
multiple zones in the geomodel where the size of the different zones in
number of grid cells is varying a lot. Another possibility is that it
is now possible to split a geogrid with multiple zones into single zone grids
and define different grid resolutions not only vertically but also laterally
if that is needed to represent the geology with different resolutions for
different zones in the geomodel workflow. The upscaling can then be applied
to get the properties into a simulation grid from each of the single zone
geomodel grids.

The script will read info about ERTBOX grid size for each individual grid
from the FMU project specified (The <CONFIG_PATH>) from the location::

  rms/output/aps

The script assumes that the keyword FACIES_ZONE keyword is defined
in the global_variables.yml file specified in the FMU project
(The <CONFIG_PATH>) from the location::

  fmuconfig/output/global_variables.yml

If it is not defined, the keyword 'facies_per_zone' must be specified
in the config file instead.

Example of format for FACIES_ZONE keyword in global_variables.yml file
from the Drogon case:

.. code-block:: yaml

  FACIES_ZONE:
    Valysar:
      0: Floodplain
      1: Channel
      2: Crevasse
      5: Coal
    Therys:
      6: Calcite
      10: Offshore
      11: Lowershoreface
      12: Uppershoreface
    Volon:
      0: Floodplain
      1: Channel
      6: Calcite

If this does not exist, add the keyword 'facies_per_zone' to the config file
within the section under the keyword 'geogrid_fields'. The 'facies_per_zone'
keyword for the config file is defined in same way as 'FACIES_ZONE'
keyword is defined in the global variables file.

There is an option to copy the resulting statistical estimates into the geogrid
for a single realization of the grid. This makes it possible to visualize
the results together with well paths. But be aware that the statistical
estimates  does not in general match 100% a single realization of the grid.
So, comparing estimated facies probability with a facies log for a particular
realization of the grid, will only give you an approximate impression
of the well conditioning since the blocked wells grid cells may vary
from realization to realization due to the variability of the grid which is
due to structural uncertainty.

If this ERT workflow is run before the realizations are generated
for all specified iterations, the script will not start calculating statistics,
but return without doing anything.

"""


EPILOGUE = """
.. code-block:: yaml

  # Configuration file for script wf_field_param_statistics.py
  field_stat:
    # Number of realizations for specified ensemble
    # Required.
    nreal: 100

    # Iteration numbers from ES-MDA in ERT (iteration = 0 is initial ensemble,
    # usually iteration=3 is final updated ensemble)
    # Required.
    iterations: [0, 3]

    # Standard deviation estimator.
    # Optional. Default is False which means that
    # sample standard deviation ( normalize by (N-1)) is used
    # where N is number of realizations.
    # The alternative is True which means that
    # population standard deviation ( normalize by N) is used.
    use_population_stdev: False

    # Specify path to directory where the ertbox grids are stored
    # relative to config path (ert/model)
    relative_path_ertbox_grids: "../../rms/output/aps"

    # Specify ertbox grids per zone and/or a default global ertbox grid.
    # The ertbox names are the same as the filenames except for the suffix.
    # The specified default ertbox grid is only used for zones where
    # individual ertbox grid is not specified. The default ertbox grid name
    # must be the same as the ertbox grid specified in the global GRID keyword
    # in ERT.
    # Note that specification of 'ertbox_per_zone' must be consistent with
    # the specification of the FIELD keyword in ERT.
    # If the FIELD keyword in ERT config file does not use the
    # sub-keyword GRID for any zone, skip the keyword 'ertbox_per_zone'
    # and use only ertbox_default keyword.This means that all zones use the
    # same ertbox grid size.
    # If some or all FIELD kewywords in ERT use the sub-keyword GRID,
    # then specify 'ertbox_per_zone' keyword for all zones and use the
    # same ertbox grid for each zone as specified in ERT keyword FIELD.
    # If some of the FIELD keywords don't use sub-keyword GRID, it means
    # that the ertbox grid specified by the global GRID keyword in ERT
    # is used. In this case, specify the name of the default ertbox grid
    # for those zones. In this way it is possible to define the ertbox grid
    # in the same ways here for field_statistics as was done in ERT config file.
    ertbox_per_zone:
        "Valysar": "ertbox_Valysar"
        "Therys":  "ertbox_Therys"
        "Volon":   "ertbox_Volon"
    ertbox_default: "ERTBOX"

    # Zone numbers with zone name dictionary
    zone_code_names:
        1: "Valysar"
        2: "Therys"
        3: "Volon"

    # Specify which geogrid fields to use
    # Geogrid fields are typically found in:
    # <RUN_PATH>/share/results/grids/<geogridname>--<property-name>.roff
    # Optional keyword
    geogrid_fields:
        # Prefix (name of geogrid) to be used for field parameters related to the
        # geogrid.
        geogrid_name: "geogrid"

        # Selected set of zone names to use in calculations of statistics.
        # Must be one or more of the defined zones.
        # Require at least one zone to be selected.
        use_zones: ["Valysar", "Therys", "Volon"]


        # Specify facies per zone either here or in global variables file.
        facies_per_zone:
            Valysar:
                0: Floodplain
                1: Channel
                2: Crevasse
                5: Coal
            Therys:
                6: Calcite
                10: Offshore
                11: Lowershoreface
                12: Uppershoreface
            Volon:
                0: Floodplain
                1: Channel
                6: Calcite

        # For each zone specify either Proportional, Top_conform or Base_conform
        # as grid conformity.
        # Conformity can be checked by opening the RMS job that has created
        # the geogrid and check the grid settings for grid layers.
        # Proportional means that number of layers is specified.
        # Top or base conform means that grid cell thickness is specified.
        # Required (but only for zones you want to use)
        zone_conformity:
            "Valysar": "Proportional"
            "Therys": "Top_conform"
            "Volon": "Proportional"

        # For each zone specify which discrete parameter to use to calculate
        # facies probability estimates.
        # Possible names are those found in the
        # share/results/grids/<geogridname>--<name>.roff
        # files that are of discrete type.
        # This key can be omitted or some of the lines specifying parameters
        # for a zone if you don't want to use it.
        discrete_property_param_per_zone:
            "Valysar": ["facies"]
            "Therys": ["facies"]
            "Volon": ["facies"]

        # For each zone specify which continuous parameter to use to
        # calculate estimate of mean and stdev over ensemble.
        # Possible names are those found in the
        #  share/results/grids/<geogridname>--<name>.roff
        # files that are of continuous type
        # This key can be omitted or some of the lines specifying
        # parameters for a zone if you don't want to use it.
        continuous_property_param_per_zone:
            "Valysar": ["phit", "klogh"]
            "Therys":  ["phit", "klogh"]
            "Volon":   ["phit", "klogh"]


    # Specify which temporary field parameters (in ertbox) to use
    # to calculate mean and stdev
    # Optional keyword
    temporary_ertbox_fields:
        # Relative path relative to ERT <RUN_PATH> for localisation of
        # initial ensemble of field parameters
        initial_field_relative_path: "rms/output/aps"

        # Field parameter names as specified in ERT FIELD keywords
        # grouped by zone
        parameter_name_per_zone:
            Volon:   [ aps_Volon_GRF1,   aps_Volon_GRF2,   aps_Volon_GRF3]
            Therys:  [ aps_Therys_GRF1,  aps_Therys_GRF2,  aps_Therys_GRF3]
            Valysar: [ aps_Valysar_GRF1, aps_Valysar_GRF2, aps_Valysar_GRF3]

"""

CATEGORY = "analysis"

EXAMPLES = """Add a file named e.g. ``ert/bin/workflows/wf_field_statistics`` with the contents::

  DEFINE <FIELD_STAT_CONFIG_FILE>  ../input/config/field_param_stat.yml
  DEFINE <ENSEMBLE_PATH>           <SCRATCH>/<USER>/<CASE_DIR>
  DEFINE <RESULT_FIELD_STAT_PATH>  <ENSEMBLE_PATH>/share/grid_statistics
  DEFINE <LOAD_TO_RMS_SCRIPT>      <RESULT_FIELD_STAT_PATH>/tmp_import_field_stat_into_rms.py
  MAKE_DIRECTORY                   <RESULT_FIELD_STAT_PATH>
  FIELD_STATISTICS  -c  <FIELD_STAT_CONFIG_FILE>
                    -p  <CONFIG_PATH>
                    -e  <ENSEMBLE_PATH> 
                    -z  <LOAD_TO_RMS_SCRIPT>
                    -g

where the config file for FIELD_STATISTICS in this example is located under::

  ert/input/config/field_param_stat.yml

and <SCRATCH>, <CONFIG_PATH>, <CASE_DIR>, <USER> are defined in the ERT config file.
The specification of options ``-c  -e`` are required. The options ``-p`` is optional and
specifies configuration path for ERT model (<CONFIG_PATH>) and option ``-r`` is optional
with default relative path relative to <ENSEMBLE_PATH> and equal to::

  share/grid_statistics

The option ``-g`` is optional and when specified,
the result is also copied to parameters for the geomodel grid under the directories::

  realization-0/iter-0/share/results/grids
  realization-0/iter-3/share/results/grids

for the initial and final ensemble results if iteration 3 is the final update.

The option ``-z`` is optional and used to specify name of a script to be generated
by this workflow job and is meant to be used as a RMS python job to load the results
into RMS for visualization.

Add the installation of the ERT workflow to your ERT config to have the
workflow executed after all forward models and all updates are completed::

  -- Installation of the ERT workflow:
  LOAD_WORKFLOW   ../../bin/workflows/wf_field_statistics
  HOOK_WORKFLOW  wf_field_statistics POST_SIMULATION

Note that the HOOK_WORKFLOW using POST_SIMULATION will run the workflow after each
iteration in ERT when using ES-MDA. The FIELD_STATISTICS workflow job will check
if the final iteration exists in the ensemble directory before calculating field statistics.

"""  # noqa
DEFAULT_RELATIVE_RESULT_PATH = "share/grid_statistics"
GLOBAL_VARIABLES_FILE = "../../fmuconfig/output/global_variables.yml"
# ERTBOX_GRID_PATH = "../../rms/output/aps"


class ArgumentFileNotFound(Exception):
    pass


def main():
    """Invocated from the command line, parsing command line arguments"""
    parser = get_parser()
    args = parser.parse_args()
    logger.setLevel(logging.INFO)
    try:
        field_stat(args)
    except ArgumentFileNotFound:
        sys.exit(1)


def field_stat(args):
    # parse the config file for this script
    if not Path(args.configfile).exists():
        logger.error(f"No such file: {args.configfile}")
        raise ArgumentFileNotFound(f"No such file: {args.configfile}")

    config_file = args.configfile
    config_dict = read_field_stat_config(config_file)
    field_stat_dict = config_dict["field_stat"]

    # Path to FMU project models ert/model directory (ordinary CONFIG PATH in ERT)
    if not Path(args.ertconfigpath).exists():
        logger.error(f"No such file: {args.ertconfigpath}")
        raise ArgumentFileNotFound(f"No such file: {args.ertconfigpath}")
    ert_config_path = Path(args.ertconfigpath)

    # Path to ensemble on SCRATCH disk
    if not Path(args.ensemblepath).exists():
        logger.error(f"No such file: {args.ensemblepath}")
        raise ArgumentFileNotFound(f"No such file: {args.ensemblepath}")
    ens_path = Path(args.ensemblepath)
    if not check_if_iterations_exist(ens_path, field_stat_dict):
        # The ensemble realization does not exist for all specified iterations
        # Probably this workflow is called before the ensemble is completed for
        # all iterations specified.
        # Do nothing
        return

    # Path for result of ensemble statistics calculations
    # Default path is defined.
    relative_result_path = DEFAULT_RELATIVE_RESULT_PATH
    if args.resultpath:
        relative_result_path = Path(args.resultpath)
    result_path = ens_path / relative_result_path
    if not result_path.exists():
        result_path.mkdir()
        logger.info(
            f"Result directory:  {result_path} does not exist. Will be created."
        )

    rms_load_script = None
    if args.generate_rms_load_script:
        rms_load_script = args.generate_rms_load_script

    copy_to_geogrid_realization = args.copy_result_to_geogrid

    glob_var_config_path = ert_config_path / Path(GLOBAL_VARIABLES_FILE)
    cfg_global = utils.yaml_load(glob_var_config_path)["global"]
    keyword = "FACIES_ZONE"
    facies_per_zone = cfg_global.get(keyword, None)

    logger.info(f"Config path to FMU project: {ert_config_path}")
    logger.info(f"Ensemble path on scratch disk: {ens_path}")
    logger.info(f"Result path on scratch disk: {result_path}")

    key1 = "geogrid_fields"
    key2 = "temporary_ertbox_fields"
    if key1 not in field_stat_dict and key2 not in field_stat_dict:
        raise KeyError(
            f"Missing keywords. At least one of '{key1}' and '{key2}' must be specified"
        )

    calc_stats(
        field_stat_dict,
        ens_path,
        facies_per_zone,
        result_path,
        ert_config_path,
        copy_to_geogrid_realization=copy_to_geogrid_realization,
    )

    calc_temporary_field_stats(field_stat_dict, ens_path, result_path, ert_config_path)

    relative_path_ertbox_grids = field_stat_dict["relative_path_ertbox_grids"]
    ertbox_path = ert_config_path / Path(relative_path_ertbox_grids)
    copy_ertbox_grid_to_result_path(ertbox_path, field_stat_dict, result_path)

    if rms_load_script:
        generate_script(rms_load_script, ert_config_path, result_path, config_file)

    logger.info(
        "Finished running workflow to calculate statistics "
        "for ensemble of field parameters"
    )


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
        "--configfile",
        type=str,
        help="Name of YAML config file",
        required=True,
    )
    parser.add_argument(
        "-p",
        "--ertconfigpath",
        type=str,
        default="./",
        help="Path to the configuration of ERT (<CONFIG_PATH>).",
    )
    parser.add_argument(
        "-e",
        "--ensemblepath",
        type=str,
        help="File path to ensemble directory on scratch disk",
        required=True,
    )
    parser.add_argument(
        "-r",
        "--resultpath",
        type=str,
        default="share/grid_statistics",
        help=(
            "Relative file path to result files relative to "
            "ensemble directory on scratch disk"
        ),
    )
    parser.add_argument(
        "-z",
        "--generate_rms_load_script",
        type=str,
        default="tmp_import_ensemble_field_statistics.py",
        help=(
            "Output script to be used in RMS to load results"
            " into RMS for visualization. "
        ),
    )
    parser.add_argument(
        "-g",
        "--copy_result_to_geogrid",
        action="store_true",
        help=(
            "Option to copy results into realization-0 for the geogrid "
            "under realization-0/iter-<iter>/share/results/grids/"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + subscript.__version__ + ")",
    )
    return parser


def get_parser_ert() -> argparse.ArgumentParser:
    """
    Define the argparse parser
    """
    parser = argparse.ArgumentParser(
        description=DESCRIPTION_FOR_ERT,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-c",
        "--configfile",
        type=str,
        help="Name of YAML config file",
        required=True,
    )
    parser.add_argument(
        "-p",
        "--ertconfigpath",
        type=str,
        default="./",
        help="Path to the configuration of ERT (<CONFIG_PATH>).",
    )
    parser.add_argument(
        "-e",
        "--ensemblepath",
        type=str,
        help="File path to ensemble directory on scratch disk",
        required=True,
    )
    parser.add_argument(
        "-r",
        "--resultpath",
        type=str,
        default="share/grid_statistics",
        help=(
            "Relative file path to result files relative to "
            "ensemble directory on scratch disk"
        ),
    )
    parser.add_argument(
        "-z",
        "--generate_rms_load_script",
        type=str,
        default="tmp_import_ensemble_field_statistics.py",
        help=(
            "Output script to be used in RMS to load results"
            " into RMS for visualization. "
        ),
    )
    parser.add_argument(
        "-g",
        "--copy_result_to_geogrid",
        action="store_true",
        help=(
            "Option to copy results into realization-0 for the geogrid "
            "under realization-0/iter-<iter>/share/results/grids/"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + subscript.__version__ + ")",
    )
    return parser


def check_if_iterations_exist(ens_path, input_dict):
    """
    Get specified interations from specifications
    and check that the iteration exist in the ensemble.
    """
    key = "nreal"
    if key in input_dict:
        nreal = input_dict["nreal"]
    else:
        raise KeyError(
            f"Missing keyword:  {key} specifying number of realizations "
            " for ensembles from ERT ES-MDA"
        )
    key = "iterations"
    if key in input_dict:
        iter_list = input_dict[key]
    else:
        raise KeyError(
            f"Missing keyword:  {key} specifying a list of iteration numbers "
            " for ensembles from ERT ES-MDA"
        )

    found_for_iter = [False for i in range(iter_list[-1] + 1)]
    for iter_number in iter_list:
        for real_number in range(nreal):
            real_path = Path(f"realization-{real_number}/iter-{iter_number}")
            full_path_for_iter = ens_path / real_path
            if full_path_for_iter.exists():
                found_for_iter[iter_number] = True
                continue

    complete = True
    for iter_number in iter_list:
        if not found_for_iter[iter_number]:
            complete = False
    return complete


def read_field_stat_config(config_file_name):
    txt = f"Settings for field statistics using config file: {config_file_name}"
    logging.info(txt)

    with open(config_file_name, encoding="utf-8") as yml_file:
        return yaml.safe_load(yml_file)


def get_ertbox_size_per_zone(
    field_stat_dict: dict,
    ert_config_path: str | Path,
):
    """Read the size of the ertbox grids for each zone if specified. Use a default
    ertbox grid if ertbox grid for some or all specified zones are not defined.
    ertbox grid size define the size of the field parameters for the zones.
    Returns a dictionary with zone name as key and a tuple with the grid size
    for the ertbox grid for the zone.
    """
    main_key = "field_stat"
    key = "zone_code_names"
    if key not in field_stat_dict:
        raise KeyError(f"Missing keyword '{key}' under main keyword '{main_key}'")
    zone_code_names = field_stat_dict["zone_code_names"]
    zone_names = list(zone_code_names.values())

    ertbox_per_zone_dict = None
    ertbox_default = None
    key1 = "ertbox_per_zone"
    if key1 in field_stat_dict:
        ertbox_per_zone_dict = field_stat_dict[key1]
    key2 = "ertbox_default"
    if key2 in field_stat_dict:
        ertbox_default = field_stat_dict[key2]
    if ertbox_per_zone_dict is None and ertbox_default is None:
        raise ValueError(
            f"The keyword '{key1}' and/or '{key2}' "
            f"must be specified under main keyword '{main_key}'."
        )
    relative_path_ertbox_dir = field_stat_dict["relative_path_ertbox_grids"]
    ertbox_path = Path(ert_config_path) / Path(relative_path_ertbox_dir)

    # If a zone does not have any specified ertbox grid
    # check that the default ertbox grid is defined and
    # use the size of that. If the default ertbox is not defined,
    # the ertbox for the zone is not specified and error is reported.
    ertbox_size_dict = {}
    zones_with_individual_ertbox = []
    if ertbox_per_zone_dict:
        for zone_name, grid_name in ertbox_per_zone_dict.items():
            name = zone_name.strip()
            ertbox_file_path = Path(ertbox_path) / Path(grid_name + ".EGRID")
            ertbox_size_dict[name] = get_ertbox_size(ertbox_file_path)
            zones_with_individual_ertbox.append(name)

    if ertbox_default is not None:
        ertbox_file_path = Path(ertbox_path) / Path(ertbox_default + ".EGRID")
        ertbox_size_default = get_ertbox_size(ertbox_file_path)
    err = 0
    for zone_name in zone_names:
        if zone_name not in zones_with_individual_ertbox:
            if ertbox_default:
                ertbox_size_dict[zone_name] = ertbox_size_default
            else:
                err += 1
                logger.warning(f"No ertbox grid is defined for zone {zone_name}")
    if err > 0:
        raise ValueError("Missing specification of ERTBOX for some zones")

    return ertbox_size_dict


def read_ensemble_realization(
    ensemble_path,
    realization_number,
    iter_number,
    property_param_name,
    zone_code_names,
    geogrid_name,
):
    realization_path = Path(f"realization-{realization_number}/iter-{iter_number}")
    grid_path = Path("share/results/grids/" + geogrid_name + ".roff")
    file_path_grid = Path(ensemble_path) / realization_path / grid_path
    if file_path_grid.exists():
        grid = xtgeo.grid_from_file(file_path_grid, fformat="roff")
        subgrids = grid.subgrids if grid.subgrids else None
    else:
        return None, None, None

    property_path = Path(
        "share/results/grids/" + geogrid_name + f"--{property_param_name}.roff"
    )
    file_path_property = Path(ensemble_path) / realization_path / property_path
    property_param = xtgeo.gridproperty_from_file(file_path_property, fformat="roff")

    # Update subgrid names if default names are used and multi-zone grid
    if zone_code_names and len(zone_code_names) > 1:
        set_subgrid_names(grid, zone_code_names)
        subgrids = grid.subgrids

    return grid.dimensions, subgrids, property_param


def read_geogrid_realization(
    ensemble_path,
    realization_number,
    iter_number,
    zone_code_names,
    geogrid_name,
):
    realization_path = Path(f"realization-{realization_number}/iter-{iter_number}")
    grid_path = Path("share/results/grids/" + geogrid_name + ".roff")
    file_path_grid = Path(ensemble_path) / realization_path / grid_path
    if file_path_grid.exists():
        grid = xtgeo.grid_from_file(file_path_grid, fformat="roff")
        subgrids = grid.subgrids if grid.subgrids else None
    else:
        return None, None

    # Update subgrid names if default names are used and multi-zone grid
    if zone_code_names and len(zone_code_names) > 1:
        set_subgrid_names(grid, zone_code_names)
        subgrids = grid.subgrids

    return grid.dimensions, subgrids


def get_values_in_ertbox(
    geogrid_dimensions,
    geogrid_subgrids,
    geogrid_property_param,
    zone_name,
    ertbox_size,
    conformity,
    is_continuous=True,
):
    if geogrid_subgrids:
        # Multi-zone grid
        assert zone_name in geogrid_subgrids
        # layers count from 1, change to count from 0
        layers = geogrid_subgrids[zone_name]
        start_layer = layers[0] - 1
        end_layer = layers[-1]
        nz_zone = end_layer - start_layer
    else:
        # Single zone grid
        nz_zone = geogrid_dimensions[2]
        start_layer = 0
        end_layer = nz_zone
    if (
        (ertbox_size[0] != geogrid_dimensions[0])
        or (ertbox_size[1] != geogrid_dimensions[1])
        or (ertbox_size[2] < nz_zone)
    ):
        raise ValueError(
            "The dimension of ertbox grid: "
            f"({ertbox_size[0]}, {ertbox_size[1]}, {ertbox_size[2]}) "
            f"does not match the geogrid zone {zone_name}. "
            "The geogrid dimension for this zone is: "
            f"({geogrid_dimensions[0]}, {geogrid_dimensions[1]}, {nz_zone}). "
            f"The ertbox grid must have number of layers >= {nz_zone}"
        )
    prop_values = geogrid_property_param.values
    if is_continuous:
        ertbox_prop_values = np.ma.masked_all(
            (ertbox_size[0], ertbox_size[1], ertbox_size[2]), dtype=np.float32
        )
    else:
        ertbox_prop_values = np.ma.masked_all(
            (ertbox_size[0], ertbox_size[1], ertbox_size[2]), dtype=np.int32
        )
    if conformity.upper() in {"PROPORTIONAL", "TOP_CONFORM"}:
        ertbox_prop_values[:, :, :nz_zone] = prop_values[:, :, start_layer:end_layer]
    elif conformity.upper() == "BASE_CONFORM":
        start_layer_ertbox = ertbox_size[2] - nz_zone
        ertbox_prop_values[:, :, start_layer_ertbox:] = prop_values[
            :, :, start_layer:end_layer
        ]
    return ertbox_prop_values


def set_values_in_geogrid(
    geogrid_dimensions,
    geogrid_subgrids,
    geogrid_property_param,
    ertbox_property_param,
    zone_name,
    ertbox_size,
    conformity,
    initialize_geogrid_property_param_values=False,
):
    if geogrid_subgrids:
        # Multi-zone grid
        assert zone_name in geogrid_subgrids
        # layers count from 1, change to count from 0
        layers = geogrid_subgrids[zone_name]
        start_layer = layers[0] - 1
        end_layer = layers[-1]
        nz_zone = end_layer - start_layer
    else:
        # Single zone grid
        nz_zone = geogrid_dimensions[2]
        start_layer = 0
        end_layer = nz_zone

    assert geogrid_dimensions[0] == ertbox_size[0]
    assert geogrid_dimensions[1] == ertbox_size[1]
    assert ertbox_size[2] >= nz_zone

    # Get the values from ertbox grid
    ertbox_values = ertbox_property_param.values

    # Get or initialize values from geogrid
    if initialize_geogrid_property_param_values:
        # If not already existing, set all values to 0
        prop_values = np.ma.zeros(geogrid_dimensions, dtype=np.float32)
    else:
        prop_values = geogrid_property_param.values

    # Update only the property of the geogrid for the given zone
    if conformity.upper() in {"PROPORTIONAL", "TOP_CONFORM"}:
        prop_values[:, :, start_layer:end_layer] = ertbox_values[:, :, :nz_zone]
    elif conformity.upper() == "BASE_CONFORM":
        start_layer_ertbox = ertbox_size[2] - nz_zone
        prop_values[:, :, start_layer:end_layer] = ertbox_values[
            :, :, start_layer_ertbox:
        ]

    return prop_values


def set_subgrid_names(grid, zone_code_names=None, new_subgrids=None):
    if new_subgrids:
        # Use specified new subgrids when it is defined
        grid.set_subgrids(new_subgrids)
        return

    # Modify zone names of existing subgrids if not consistent with zone_code_names
    assert zone_code_names
    subgrids = grid.get_subgrids()
    new_subgrids = {}
    for zone_number, zone_name in zone_code_names.items():
        # Replace subgrid_0 with first zone name and subgrid_1
        # with second zone name and so on
        for name, val in subgrids.items():
            if name == f"subgrid_{zone_number - 1}":
                new_subgrids[zone_name] = copy.copy(val)
    grid.set_subgrids(new_subgrids)


def write_mean_stdev_nactive(
    iter_number,
    zone_name,
    param_name,
    ertbox_mean_values_masked,
    ertbox_stdev_values_masked,
    ertbox_ncount_active_values,
    conformity,
    result_path,
    ens_path,
    zone_code_names,
    geogrid_name,
    copy_to_geogrid_realization=False,
):
    output_path = result_path
    if not output_path.exists():
        # Create the directory
        output_path.mkdir()
    ertbox_dims = ertbox_mean_values_masked.shape
    name_mean = "ertbox--mean_" + zone_name + "_" + param_name + "_" + str(iter_number)
    name_stdev = (
        "ertbox--stdev_" + zone_name + "_" + param_name + "_" + str(iter_number)
    )
    name_nactive = "ertbox--nactive_" + zone_name + "_" + str(iter_number)
    result_mean_file_path = output_path / Path(name_mean + ".roff")
    result_stdev_file_path = output_path / Path(name_stdev + ".roff")
    result_nactive_file_path = output_path / Path(name_nactive + ".roff")

    # Fill masked values with 0
    ertbox_mean_values = ertbox_mean_values_masked.filled(fill_value=0.0)
    ertbox_stdev_values = ertbox_stdev_values_masked.filled(fill_value=0.0)

    xtgeo_ertbox_mean = xtgeo.GridProperty(
        ncol=ertbox_dims[0],
        nrow=ertbox_dims[1],
        nlay=ertbox_dims[2],
        name=name_mean,
        values=ertbox_mean_values,
    )
    xtgeo_ertbox_stdev = xtgeo.GridProperty(
        ncol=ertbox_dims[0],
        nrow=ertbox_dims[1],
        nlay=ertbox_dims[2],
        name=name_stdev,
        values=ertbox_stdev_values,
    )

    xtgeo_ertbox_ncount_active = xtgeo.GridProperty(
        ncol=ertbox_dims[0],
        nrow=ertbox_dims[1],
        nlay=ertbox_dims[2],
        name=name_nactive,
        values=ertbox_ncount_active_values,
    )

    if copy_to_geogrid_realization:
        # Get geogrid in order to get dimension and subgrid info.
        # Use realization number 0
        real_number = 0
        geogrid_dimensions, geogrid_subgrids = read_geogrid_realization(
            ens_path,
            real_number,
            iter_number,
            zone_code_names,
            geogrid_name,
        )

        ertbox_to_geogrid_statistics(
            "mean",
            zone_name,
            iter_number,
            geogrid_dimensions,
            geogrid_subgrids,
            xtgeo_ertbox_mean,
            ertbox_dims,
            conformity,
            ens_path,
            geogrid_name,
            param_name=param_name,
        )

        ertbox_to_geogrid_statistics(
            "stdev",
            zone_name,
            iter_number,
            geogrid_dimensions,
            geogrid_subgrids,
            xtgeo_ertbox_stdev,
            ertbox_dims,
            conformity,
            ens_path,
            geogrid_name,
            param_name=param_name,
        )

    logger.info(f"  Write parameter: {name_mean}")
    xtgeo_ertbox_mean.to_file(result_mean_file_path, fformat="roff")

    logger.info(f"  Write parameter: {name_stdev}")
    xtgeo_ertbox_stdev.to_file(result_stdev_file_path, fformat="roff")

    logger.info(f"  Write parameter: {name_nactive}")
    xtgeo_ertbox_ncount_active.to_file(result_nactive_file_path, fformat="roff")


def ertbox_to_geogrid_statistics(
    statistics_name,
    zone_name,
    iter_number,
    geogrid_dimensions,
    geogrid_subgrids,
    xtgeo_ertbox_param,
    ertbox_dimensions,
    zone_conformity,
    ens_path,
    geogrid_name,
    param_name=None,
    facies_name=None,
):
    if param_name:
        geogrid_stat_name = f"{geogrid_name}--{statistics_name}_{param_name}"
    if facies_name:
        geogrid_stat_name = f"{geogrid_name}--{statistics_name}_{facies_name}"
    assert (param_name is not None) or (facies_name is not None)
    geogrid_stat_file_name = (
        ens_path
        / Path(f"realization-0/iter-{iter_number}/share/results/grids")
        / Path(geogrid_stat_name + ".roff")
    )

    # If the grid parameter file already exists, get the parameter values,
    # update the current zone with the new values and write the new version
    # of the file to same file name
    init_geogrid_param = not Path(geogrid_stat_file_name).exists()
    if not init_geogrid_param:
        xtgeo_prop_geogrid_stat = xtgeo.gridproperty_from_file(
            geogrid_stat_file_name, fformat="roff"
        )
    else:
        logger.info(f"  Create geogrid parameter: {geogrid_stat_name}")
        (nx, ny, nz) = geogrid_dimensions
        xtgeo_prop_geogrid_stat = xtgeo.GridProperty(
            ncol=nx,
            nrow=ny,
            nlay=nz,
            name=geogrid_stat_name,
        )

    xtgeo_prop_geogrid_stat.values = set_values_in_geogrid(
        geogrid_dimensions,
        geogrid_subgrids,
        xtgeo_prop_geogrid_stat,
        xtgeo_ertbox_param,
        zone_name,
        ertbox_dimensions,
        zone_conformity,
        initialize_geogrid_property_param_values=init_geogrid_param,
    )
    logger.info(f"  Update geogrid parameter: {xtgeo_prop_geogrid_stat.name}")
    xtgeo_prop_geogrid_stat.to_file(geogrid_stat_file_name, fformat="roff")


def write_fraction_nactive(
    iter_number,
    zone_name,
    facies_name,
    ertbox_fraction_masked,
    conformity,
    result_path,
    ens_path,
    zone_code_names,
    geogrid_name,
    ncount_active_values=None,
    copy_to_geogrid_realization=False,
):
    output_path = result_path
    if not output_path.exists():
        # Create the directory
        output_path.mkdir()
    ertbox_dimensions = ertbox_fraction_masked.shape
    name_fraction = (
        "ertbox--prob_" + zone_name + "_" + facies_name + "_" + str(iter_number)
    )
    name_nactive = "ertbox--nactive_" + zone_name + "_" + str(iter_number)

    ertbox_result_fraction_file_path = output_path / Path(name_fraction + ".roff")
    ertbox_result_nactive_file_path = output_path / Path(name_nactive + ".roff")

    # Fill masked values with 0
    ertbox_fraction = ertbox_fraction_masked.filled(fill_value=0.0)

    xtgeo_ertbox_fraction = xtgeo.GridProperty(
        ncol=ertbox_dimensions[0],
        nrow=ertbox_dimensions[1],
        nlay=ertbox_dimensions[2],
        name=name_fraction,
        values=ertbox_fraction,
    )

    logger.info(f"  Write parameter: {name_fraction}")
    xtgeo_ertbox_fraction.to_file(ertbox_result_fraction_file_path, fformat="roff")

    if ncount_active_values is not None:
        xtgeo_ertbox_ncount_active = xtgeo.GridProperty(
            ncol=ertbox_dimensions[0],
            nrow=ertbox_dimensions[1],
            nlay=ertbox_dimensions[2],
            name=name_nactive,
            values=ncount_active_values,
        )

        logger.info(f"  Write parameter: {name_nactive}")
        xtgeo_ertbox_ncount_active.to_file(
            ertbox_result_nactive_file_path, fformat="roff"
        )

    if copy_to_geogrid_realization:
        # Get geogrid in order to get dimension and subgrid info.
        # Use realization number 0
        real_number = 0
        geogrid_dimensions, geogrid_subgrids = read_geogrid_realization(
            ens_path,
            real_number,
            iter_number,
            zone_code_names,
            geogrid_name,
        )
        ertbox_to_geogrid_statistics(
            "prob",
            zone_name,
            iter_number,
            geogrid_dimensions,
            geogrid_subgrids,
            xtgeo_ertbox_fraction,
            ertbox_dimensions,
            conformity,
            ens_path,
            geogrid_name,
            facies_name=facies_name,
        )


def get_geogrid_field_specifications(
    input_dict,
    use_facies_per_zone=True,
    facies_per_zone=None,
):
    (
        _use_geogrid_fields,
        _use_temporary_fields,
        _nreal,
        _iter_list,
        _use_population_stdev,
        _relative_path_ertbox_grids,
        _ertbox_per_zone,
        _ertbox_default,
        _zone_code_names,
        geo_zone_names_used,
        geo_zone_conformity,
        geo_facies_per_zone,
        geo_geogrid_name,
        geo_param_name_dict,
        geo_disc_param_name_dict,
        _field_init_path,
        _field_param_per_zone_dict,
    ) = get_specifications(
        input_dict,
        use_facies_per_zone=use_facies_per_zone,
        geo_facies_per_zone=facies_per_zone,
    )
    return (
        geo_zone_names_used,
        geo_zone_conformity,
        geo_facies_per_zone,
        geo_geogrid_name,
        geo_param_name_dict,
        geo_disc_param_name_dict,
    )


def get_temporary_field_specifications(input_dict: dict):
    (
        _use_geogrid_fields,
        _use_temporary_fields,
        _nreal,
        _iter_list,
        _use_population_stdev,
        _relative_path_ertbox_grids,
        _ertbox_per_zone,
        _ertbox_default,
        _zone_code_names,
        _geo_zone_names_used,
        _geo_zone_conformity,
        _geo_facies_per_zone,
        _geo_geogrid_name,
        _geo_param_name_dict,
        _geo_disc_param_name_dict,
        field_init_path,
        field_param_per_zone_dict,
    ) = get_specifications(
        input_dict, use_facies_per_zone=True, geo_facies_per_zone=None
    )
    key_temporary_fields = "temporary_ertbox_fields"
    if field_init_path is None:
        key = "initial_field_relative_path"
        raise KeyError(
            f"Missing keyword '{key}' under keyword '{key_temporary_fields}'"
        )
    if field_param_per_zone_dict is None:
        key = "parameter_name_per_zone"
        raise KeyError(
            f"Missing keyword '{key}' under keyword '{key_temporary_fields}'"
        )

    return (
        field_init_path,
        field_param_per_zone_dict,
    )


def get_specifications(
    input_dict,
    use_facies_per_zone=True,
    geo_facies_per_zone=None,
):
    # Required keywords
    key = "nreal"
    if key in input_dict:
        nreal = input_dict[key]
    else:
        raise KeyError(f"Missing keyword:  {key} specifying number of realizations")

    key = "iterations"
    if key in input_dict:
        iter_list = input_dict[key]
    else:
        raise KeyError(
            f"Missing keyword:  {key} specifying a list of iteration numbers "
            " for ensembles from ERT ES-MDA"
        )

    key = "relative_path_ertbox_grids"
    if key in input_dict:
        relative_path_ertbox_grids = input_dict[key]
    else:
        raise KeyError(
            f"Missing keyword:  {key} specifying path to "
            "directory where ertbox grids are stored relative to ert config path}"
        )

    key = "ertbox_default"
    ertbox_default = None
    if key in input_dict:
        ertbox_default = input_dict[key]

    key = "ertbox_per_zone"
    ertbox_per_zone = None
    if key in input_dict:
        ertbox_per_zone = input_dict[key]

    if not ertbox_default and not ertbox_per_zone:
        raise KeyError(
            "Ertbox grid must be specified either as a common "
            "grid for all zones or individual one per zone"
        )

    key = "zone_code_names"
    if key in input_dict:
        zone_code_names = input_dict[key]
    else:
        raise KeyError(f"Missing keyword:  {key} specifying zone codes and zone names.")

    # Optional keywords
    key = "use_population_stdev"
    use_population_stdev = False
    if key in input_dict:
        use_population_stdev = input_dict[key]

    use_geogrid_fields = False
    geo_geogrid_name = None
    geo_zone_names_used = None
    geo_zone_conformity = None
    geo_param_name_dict = None
    geo_disc_param_name_dict = None
    if "geogrid_fields" in input_dict:
        use_geogrid_fields = True
        geogrid_fields_dict = input_dict["geogrid_fields"]

        key = "geogrid_name"
        if key in geogrid_fields_dict:
            geo_geogrid_name = geogrid_fields_dict[key]
            geo_geogrid_name = geo_geogrid_name.strip()
        else:
            raise KeyError(f"Missing keyword {key} in keyword 'geogrid_fields'")

        # Default is to use all zones
        key = "use_zones"
        geo_zone_names_used = copy.copy(list(zone_code_names.values()))
        if key in geogrid_fields_dict:
            zone_names_input = geogrid_fields_dict[key]
            if zone_names_input is not None and len(zone_names_input) > 0:
                geo_zone_names_used = zone_names_input
        check_use_zones(zone_code_names, geo_zone_names_used)

        if use_facies_per_zone and (geo_facies_per_zone is None):
            # Not defined in global variables file.
            # Look for specification of it in config file instead.
            key = "facies_per_zone"
            if key in geogrid_fields_dict:
                facies_per_zone_input = geogrid_fields_dict["facies_per_zone"]
                if (facies_per_zone_input is not None) and len(
                    facies_per_zone_input
                ) > 0:
                    geo_facies_per_zone = facies_per_zone_input
            else:
                raise KeyError(
                    f"Keyword '{key}' is required in config file for this script "
                    "if global_variables.yml file has not defined the "
                    "keyword 'FACIES_ZONE'"
                )

        key = "zone_conformity"
        if key in geogrid_fields_dict:
            geo_zone_conformity = geogrid_fields_dict[key]
        else:
            raise KeyError(f"Missing keyword:  {key} specifying conformity per zone.")
        check_zone_conformity(zone_code_names, geo_zone_names_used, geo_zone_conformity)

        key = "continuous_property_param_per_zone"
        if key in geogrid_fields_dict:
            geo_param_name_dict = geogrid_fields_dict[key]
        check_param_name_dict(zone_code_names, geo_param_name_dict)

        key = "discrete_property_param_per_zone"
        if key in geogrid_fields_dict:
            geo_disc_param_name_dict = geogrid_fields_dict[key]
        check_disc_param_name_dict(zone_code_names, geo_disc_param_name_dict)

        check_used_params(
            geo_zone_names_used, geo_param_name_dict, geo_disc_param_name_dict
        )

    use_temporary_fields = False
    temporary_ertbox_field = None
    field_init_path = None
    field_param_per_zone_dict = None
    if "temporary_ertbox_fields" in input_dict:
        use_temporary_fields = True
        temporary_ertbox_field = input_dict["temporary_ertbox_fields"]

        key = "initial_field_relative_path"
        if key in temporary_ertbox_field:
            field_init_path = temporary_ertbox_field[key]
        else:
            raise KeyError(
                f"Missing keyword:  {key} "
                "specifying relative path for initial temporary fields "
                "in keyword 'temporary_ertbox_fields."
            )

        key2 = "parameter_name_per_zone"
        if key2 in temporary_ertbox_field:
            field_param_per_zone_dict = temporary_ertbox_field[key2]
        else:
            field_param_per_zone_dict = None

    if not use_geogrid_fields and not use_temporary_fields:
        raise ValueError(
            "No fields are specified as input to calculation "
            "of field parameter statistics.  Check configuration "
            "file for FIELD_STATISTICS workflow job."
        )

    return (
        use_geogrid_fields,
        use_temporary_fields,
        nreal,
        iter_list,
        use_population_stdev,
        relative_path_ertbox_grids,
        ertbox_per_zone,
        ertbox_default,
        zone_code_names,
        geo_zone_names_used,
        geo_zone_conformity,
        geo_facies_per_zone,
        geo_geogrid_name,
        geo_param_name_dict,
        geo_disc_param_name_dict,
        field_init_path,
        field_param_per_zone_dict,
    )


def get_ertbox_size(ertbox_path: str | Path) -> tuple:
    if not Path(ertbox_path).exists():
        raise OSError(f"The ertbox file does not exist in:  {ertbox_path}")
    ertbox_grid = xtgeo.grid_from_file(ertbox_path, fformat="egrid")
    return ertbox_grid.dimensions


def copy_ertbox_grid_to_result_path(
    ertbox_config_path: Path | str, config_dict: dict, result_path: Path | str
) -> None:

    key1 = "ertbox_default"
    ertbox_default = None
    if key1 in config_dict:
        ertbox_default = config_dict[key1]

    key2 = "ertbox_per_zone"
    ertbox_per_zone = None
    if key2 in config_dict:
        ertbox_per_zone = config_dict[key2]

    if not ertbox_default and not ertbox_per_zone:
        raise ValueError(f"Missing both keywords {key1} and {key2}")

    if ertbox_default:
        ertbox_file = Path(ertbox_config_path) / Path(ertbox_default.upper() + ".EGRID")
        if Path(ertbox_file).exists():
            ertbox_grid = xtgeo.grid_from_file(ertbox_file, fformat="egrid")
            grid_file_name = result_path / Path(ertbox_default + ".roff")
            ertbox_grid.to_file(grid_file_name, fformat="roff")
        else:
            raise OSError(f"Can not find ertbox grid file {ertbox_file}")

    if ertbox_per_zone:
        for _zone_name, ertbox_name in ertbox_per_zone.items():
            ertbox_file = Path(ertbox_config_path) / Path(ertbox_name + ".EGRID")
            if Path(ertbox_file).exists():
                ertbox_grid = xtgeo.grid_from_file(ertbox_file, fformat="egrid")
                grid_file_name = result_path / Path(ertbox_name + ".roff")
                logger.info(f"Copy ertbox grid from {ertbox_file} to {grid_file_name}")
                ertbox_grid.to_file(grid_file_name, fformat="roff")
            else:
                raise OSError(f"Can not find ertbox grid file {ertbox_file}")


# def copy_to_real0_dirs(
#     field_stat: dict, result_path: Path | str, ens_path: Path | str
# ) -> None:
#     iteration_list = field_stat["iterations"]
#     for iter in iteration_list:
#         source_files = result_path / Path(f"ertbox--*_{iter}.roff")
#         target_dir = ens_path / Path(f"realization-0/iter-{iter}/share/results/grids")
#         print(f"Source_files:  {source_files}")
#         print(f"Target dir: {target_dir}")
#         for f in glob.glob(source_files.as_posix()):
#             shutil.copy(f, target_dir.as_posix())
#         source_file = result_path / Path("ertbox.roff")
#         shutil.copy(source_file.as_posix(), target_dir.as_posix())


def check_zone_conformity(
    zone_code_names: dict, zone_names_used: list[str], zone_conformity: dict
) -> None:
    for zone_name, conformity in zone_conformity.items():
        if zone_name not in list(zone_code_names.values()):
            raise ValueError("Unknown zone names in keyword 'zone_conformity'.")
        if conformity.upper() not in {"TOP_CONFORM", "BASE_CONFORM", "PROPORTIONAL"}:
            raise ValueError(
                "Undefined zone conformity specified "
                "(Must be Top_conform, Base_conform or Proportional)."
            )
    for zone_name in zone_names_used:
        if zone_name not in zone_conformity:
            raise ValueError(
                f"Zone with name {zone_name} is missing in keyword 'zone_conformity'."
            )


def check_param_name_dict(zone_code_names: dict, param_name_dict: dict) -> None:
    if not param_name_dict:
        return
    for zone_name, prop_list in param_name_dict.items():
        if zone_name not in list(zone_code_names.values()):
            raise ValueError(
                "Unknown zone name in specification of keyword "
                "'continuous_property_param_per_zone'."
            )
        if prop_list is None or len(prop_list) == 0:
            raise ValueError(
                "Missing list of property names for a specified zone in "
                "keyword 'continuous_property_param_per_zone'."
            )


def check_disc_param_name_dict(
    zone_code_names: dict, disc_param_name_dict: dict
) -> None:
    if not disc_param_name_dict:
        return
    for zone_name, prop_list in disc_param_name_dict.items():
        if zone_name not in list(zone_code_names.values()):
            raise ValueError(
                "Unknown zone name in specification of keyword "
                "'discrete_property_param_per_zone'."
            )
        if prop_list is None or len(prop_list) == 0:
            raise ValueError(
                "Missing list of property names for a specified zone in keyword "
                "'discrete_property_param_per_zone'."
            )


def check_use_zones(zone_code_names: dict, zone_names: list[str]) -> None:
    if not zone_names or len(zone_names) == 0:
        return
    for zone_name in zone_names:
        if zone_name not in list(zone_code_names.values()):
            raise ValueError(
                "Unknown zone name in specification of keyword 'use_zones'."
            )


def check_used_params(
    zone_names_used: list[str], param_name_dict: dict, disc_param_name_dict: dict
) -> None:
    for zone_name in zone_names_used:
        found = False
        if param_name_dict and zone_name in param_name_dict:
            found = True
        if disc_param_name_dict and zone_name in disc_param_name_dict:
            found = True
        if not found:
            raise ValueError(
                f"Zone with name {zone_name} is specified to be used, "
                "but not specified in keywords 'continuous_property_param_per_zone' "
                "or 'discrete_property_param_per_zone'."
                "If keyword 'use_zones' is not specified, "
                "it is assumed that all defined zones in keyword 'zone_code_names' "
                "are used."
            )


def calc_stats(
    input_dict: dict,
    ens_path: Path | str,
    facies_per_zone: dict,
    result_path: Path | str,
    ert_config_path: Path | str,
    copy_to_geogrid_realization: bool = False,
) -> None:

    # Check if any need to continue to calculation
    if "geogrid_fields" not in input_dict:
        return

    ertbox_size_dict = get_ertbox_size_per_zone(input_dict, ert_config_path)

    nreal = input_dict["nreal"]
    iter_list = input_dict["iterations"]
    use_population_stdev = input_dict["use_population_stdev"]
    zone_code_names = input_dict["zone_code_names"]
    ertbox_per_zone_dict = None
    ertbox_default = None
    key = "ertbox_per_zone"
    if key in input_dict:
        ertbox_per_zone_dict = input_dict[key]
    key = "ertbox_default"
    if key in input_dict:
        ertbox_default = input_dict[key]

    (
        zone_names_used,
        zone_conformity,
        facies_per_zone,
        geogrid_name,
        param_name_dict,
        disc_param_name_dict,
    ) = get_geogrid_field_specifications(
        input_dict, use_facies_per_zone=True, facies_per_zone=None
    )

    # Get list of active realization (Must be active for all iterations in iter_list)
    active_real, number_of_skipped = get_active_real(
        iter_list, ens_path, nreal, geogrid_name
    )
    if number_of_skipped == nreal:
        raise ValueError(
            f"No active realizations. Maybe grid name '{geogrid_name}' is wrong?"
        )

    ensemble_path = ens_path

    logger.info(f"Number of realizations: {nreal}")
    logger.info(f"Number of active realizations: {nreal - number_of_skipped}")

    for iter_number in iter_list:
        logger.info(f"Ensemble iteration: {iter_number}")
        for zone_name in zone_names_used:
            logger.info(f"Zone name: {zone_name}")
            if ertbox_per_zone_dict and zone_name in ertbox_per_zone_dict:
                logger.info(f" Ertbox grid: {ertbox_per_zone_dict[zone_name]}")
            else:
                logger.info(f" Ertbox grid: {ertbox_default}")
            has_written_nactive = False
            ertbox_size = ertbox_size_dict[zone_name.strip()]
            if param_name_dict:
                if zone_name not in param_name_dict:
                    continue
                for param_name in param_name_dict[zone_name]:
                    logger.info(f" Property: {param_name}")
                    all_values = np.ma.masked_all(
                        (ertbox_size[0], ertbox_size[1], ertbox_size[2], nreal),
                        dtype=np.float32,
                    )

                    for real_number in active_real:
                        grid_dimensions, subgrids, property_param = (
                            read_ensemble_realization(
                                ensemble_path,
                                real_number,
                                iter_number,
                                param_name,
                                zone_code_names,
                                geogrid_name,
                            )
                        )
                        assert grid_dimensions is not None
                        ertbox_prop_values = get_values_in_ertbox(
                            grid_dimensions,
                            subgrids,
                            property_param,
                            zone_name,
                            ertbox_size,
                            zone_conformity[zone_name],
                            is_continuous=True,
                        )

                        all_values[:, :, :, real_number] = ertbox_prop_values

                    calc_mean = False
                    calc_stdev = False
                    mean_values = None
                    stdev_values = None
                    if number_of_skipped < nreal:
                        # Mean value
                        mean_values = all_values.mean(axis=3)
                        calc_mean = True
                        if number_of_skipped < (nreal - 1):
                            # Std deviation
                            if use_population_stdev:
                                stdev_values = all_values.std(axis=3, ddof=0)
                            else:
                                stdev_values = all_values.std(axis=3, ddof=1)
                            calc_stdev = True
                    # Number of realization for each grid cell
                    ncount_active_values = nreal - np.ma.count_masked(
                        all_values, axis=3
                    )

                    # Write mean, stdev
                    if calc_mean and calc_stdev:
                        write_mean_stdev_nactive(
                            iter_number,
                            zone_name,
                            param_name,
                            mean_values,
                            stdev_values,
                            ncount_active_values,
                            zone_conformity[zone_name],
                            result_path,
                            ens_path,
                            zone_code_names,
                            geogrid_name,
                            copy_to_geogrid_realization=copy_to_geogrid_realization,
                        )
                        has_written_nactive = True
                    else:
                        info_txt = f"No mean and stdev calculated for {param_name} "
                        f"for zone {zone_name} for ensemble iteration "
                        f"{iter_number}"
                        logger.info(info_txt)

            if disc_param_name_dict:
                if zone_name not in disc_param_name_dict:
                    continue

                if zone_name not in facies_per_zone:
                    key = "facies_per_zone"
                    raise KeyError(
                        f"The keyword {key} is not defined for zone '{zone_name}'"
                    )

                for param_name in disc_param_name_dict[zone_name]:
                    logger.info(f" Property: {param_name}")
                    all_values = np.ma.masked_all(
                        (ertbox_size[0], ertbox_size[1], ertbox_size[2], nreal),
                        dtype=np.int32,
                    )
                    all_active = np.ma.masked_all(
                        (ertbox_size[0], ertbox_size[1], ertbox_size[2], nreal),
                        dtype=np.int32,
                    )
                    ones = np.ma.ones(
                        (ertbox_size[0], ertbox_size[1], ertbox_size[2], nreal),
                        dtype=np.int32,
                    )

                    for real_number in active_real:
                        grid_dimensions, subgrids, property_param = (
                            read_ensemble_realization(
                                ensemble_path,
                                real_number,
                                iter_number,
                                param_name,
                                zone_code_names,
                                geogrid_name,
                            )
                        )
                        assert grid_dimensions is not None
                        ertbox_prop_values = get_values_in_ertbox(
                            grid_dimensions,
                            subgrids,
                            property_param,
                            zone_name,
                            ertbox_size,
                            zone_conformity[zone_name],
                            is_continuous=False,
                        )

                        all_values[:, :, :, real_number] = ertbox_prop_values
                        all_active[:, :, :, real_number] = ~ertbox_prop_values.mask

                    # Count number of realizations per discrete code per grid cell
                    # Count number of realizations per grid cell
                    if number_of_skipped < nreal:
                        sum_fraction = 0
                        for code, facies_name in facies_per_zone[zone_name].items():
                            selected_cells = np.ma.masked_where(
                                all_values != code, ones
                            )
                            sum_active = np.ma.sum(all_active, axis=3)
                            number_of_cells = np.ma.sum(selected_cells, axis=3)
                            prob_with_code = np.ma.divide(number_of_cells, sum_active)
                            sum_total_active = np.ma.sum(sum_active) / nreal
                            sum_total_code = np.ma.sum(number_of_cells) / nreal
                            fraction = sum_total_code / sum_total_active
                            logger.info(
                                f"  Average number of active cells: {sum_total_active}"
                            )
                            logger.info(
                                f"  Average number of cells with facies "
                                f"{facies_name} is {sum_total_code}"
                            )
                            logger.info(
                                "  Average estimated facies probability for facies "
                                f"{facies_name}: {fraction}"
                            )

                            sum_fraction += fraction

                            # Write fraction (estimated facies probability from ensemble

                            if not has_written_nactive:
                                # The parameter for number of realization for each grid
                                # cell value is not already written
                                write_fraction_nactive(
                                    iter_number,
                                    zone_name,
                                    facies_name,
                                    prob_with_code,
                                    zone_conformity[zone_name],
                                    result_path,
                                    ens_path,
                                    zone_code_names,
                                    geogrid_name,
                                    ncount_active_values=sum_active,
                                    copy_to_geogrid_realization=copy_to_geogrid_realization,
                                )
                                has_written_nactive = True
                            else:
                                write_fraction_nactive(
                                    iter_number,
                                    zone_name,
                                    facies_name,
                                    prob_with_code,
                                    zone_conformity[zone_name],
                                    result_path,
                                    ens_path,
                                    zone_code_names,
                                    geogrid_name,
                                    copy_to_geogrid_realization=copy_to_geogrid_realization,
                                )
                        txt4 = f"  Sum facies volume fraction: {sum_fraction}"
                        logger.info(txt4)
                        if abs(sum_fraction) < 0.999:
                            txt5 = "  Sum facies volume fraction is less than 1."
                            txt5 += (
                                " Maybe some facies is not included in the calculation?"
                            )
                            logger.info(txt5)
                    else:
                        txt = (
                            "No probability estimate calculated for "
                            f"{param_name} for zone {zone_name}"
                            f" for ensemble iteration {iter_number}"
                        )
                        logger.info(txt)


def calc_temporary_field_stats(
    input_dict: dict,
    ens_path: str,
    result_path: str,
    ert_config_path: Path | str,
) -> None:

    # Check if any need to continue to calculation
    if "temporary_ertbox_fields" not in input_dict:
        return
    nreal = input_dict["nreal"]
    iter_list = input_dict["iterations"]
    use_population_stdev = input_dict["use_population_stdev"]
    ertbox_per_zone_dict: dict[str, str] | None = None
    ertbox_default: Path | str | None = None
    key = "ertbox_per_zone"
    if key in input_dict:
        ertbox_per_zone_dict = input_dict[key]
    key = "ertbox_default"
    if key in input_dict:
        ertbox_default = input_dict[key]

    ertbox_size_dict = get_ertbox_size_per_zone(input_dict, ert_config_path)
    field_init_path, field_param_per_zone_dict = get_temporary_field_specifications(
        input_dict
    )
    assert field_init_path
    assert field_param_per_zone_dict
    # Get list of active realization (Must be active for all iterations in iter_list)
    active_real, _ = get_active_real(iter_list, ens_path, nreal)
    # Import realizations of temporary field parameters

    calc_stats_for_temporary_parameters(
        field_param_per_zone_dict,
        ertbox_size_dict,
        ertbox_per_zone_dict,
        ertbox_default,
        iter_list,
        field_init_path,
        ens_path,
        nreal,
        active_real,
        use_population_stdev,
        result_path,
    )


def calc_stats_for_temporary_parameters(
    field_param_per_zone_dict: dict[str, str],
    ertbox_size_dict: dict[str, tuple],
    ertbox_per_zone_dict: dict[str, str] | None,
    ertbox_default: Path | str | None,
    iter_list: list[int],
    field_init_path: Path | str,
    ens_path: Path | str,
    nreal: int,
    active_real: list[int],
    use_population_stdev: bool,
    result_path: Path | str,
) -> None:

    for zone_name, param_names_for_zone in field_param_per_zone_dict.items():
        ertbox_size = ertbox_size_dict[zone_name]
        ertbox_name: Path | str | None
        if ertbox_per_zone_dict:
            ertbox_name = ertbox_per_zone_dict[zone_name]
        else:
            ertbox_name = ertbox_default

        for param_name in param_names_for_zone:
            calc_stat_for_one_temporary_parameter(
                param_name,
                zone_name,
                ertbox_size,
                ertbox_name,
                iter_list,
                field_init_path,
                ens_path,
                nreal,
                active_real,
                use_population_stdev,
                result_path,
            )


def calc_stat_for_one_temporary_parameter(
    param_name: str,
    zone_name: str,
    ertbox_size: tuple[int, int, int],
    ertbox_name: Path | str | None,
    iter_list: list[int],
    init_path: Path | str,
    ens_path: Path | str,
    nreal: int,
    active_real: list[int],
    use_population_stdev: bool,
    result_path: Path | str,
) -> None:
    for iteration in iter_list:
        param_filename = param_name + ".roff"
        if iteration == 0:
            full_param_filename = init_path / Path(param_filename)
        else:
            full_param_filename = Path(param_filename)
        logger.info(f"Property: {param_name}")
        logger.info(f"  Ertbox: {ertbox_name}")
        all_values = np.ma.masked_all(
            (ertbox_size[0], ertbox_size[1], ertbox_size[2], nreal),
            dtype=np.float32,
        )
        for real_number in active_real:
            filepath = (
                ens_path
                / Path("realization-" + str(real_number) + "/iter-" + str(iteration))
                / Path(full_param_filename)
            )
            if not filepath.exists():
                key = "initial_field_relative_path"
                temporary_field_key = "temporary_ertbox_fields"
                raise OSError(
                    f"The file path: {filepath} does not exists.\n"
                    f"Check specification of parameter name '{param_name}' or "
                    f"specification of keyword '{key}' "
                    f"under keyword '{temporary_field_key}'"
                )

            property = xtgeo.gridproperty_from_file(filepath, fformat="roff")
            values = property.values
            # Check that the size of the property match the grid box size
            field_dim = values.shape
            if field_dim != ertbox_size:
                raise ValueError(
                    f"Field parameter: {param_name} has dimension "
                    f"({field_dim[0]}, {field_dim[1]}, {field_dim[2]})\n"
                    f"ERTBOX grid size for this zone {zone_name} has dimension "
                    f"({ertbox_size[0]}, {ertbox_size[1]}, {ertbox_size[2]})\n"
                    "Check keyword 'ertbox_per_zone' or 'ertbox_default' to "
                    "ensure correct ertbox grid is assigned to the zone"
                )
            all_values[:, :, :, real_number] = values

        # Calculate statistics
        calc_mean = False
        calc_stdev = False
        mean_values_masked: MaskedArray
        stdev_values_masked: MaskedArray
        number_of_skipped = nreal - len(active_real)
        if number_of_skipped < nreal:
            # Mean value
            mean_values_masked = all_values.mean(axis=3)
            calc_mean = True
            if number_of_skipped < (nreal - 1):
                # Std deviation
                if use_population_stdev:
                    stdev_values_masked = all_values.std(axis=3, ddof=0)
                else:
                    stdev_values_masked = all_values.std(axis=3, ddof=1)
                calc_stdev = True

        # Write results to result directory
        # Fill masked values with 0
        if calc_mean:
            ertbox_mean_values = mean_values_masked.filled(fill_value=0.0)
            name_mean = "mean_" + param_name + "_" + str(iteration)
            result_mean_file_path = result_path / Path(name_mean + ".roff")
            xtgeo_ertbox_mean = xtgeo.GridProperty(
                ncol=ertbox_size[0],
                nrow=ertbox_size[1],
                nlay=ertbox_size[2],
                name=name_mean,
                values=ertbox_mean_values,
            )
            logger.info(f"  Write parameter: {name_mean}")
            xtgeo_ertbox_mean.to_file(result_mean_file_path, fformat="roff")

        if calc_stdev:
            ertbox_stdev_values = stdev_values_masked.filled(fill_value=0.0)
            name_stdev = "stdev_" + param_name + "_" + str(iteration)
            result_stdev_file_path = result_path / Path(name_stdev + ".roff")
            xtgeo_ertbox_stdev = xtgeo.GridProperty(
                ncol=ertbox_size[0],
                nrow=ertbox_size[1],
                nlay=ertbox_size[2],
                name=name_stdev,
                values=ertbox_stdev_values,
            )
            logger.info(f"  Write parameter: {name_stdev}")
            xtgeo_ertbox_stdev.to_file(result_stdev_file_path, fformat="roff")


def get_active_real(
    iter_list: list, ens_path: Path | str, nreal: int, geogrid_name: str = ""
) -> tuple[list, int]:
    """Get a list of active realizations"""
    active_real = []
    for real_number in range(nreal):
        real_exist = True
        for iteration in iter_list:
            ensemble_path = ens_path / Path(
                "realization-" + str(real_number) + "/iter-" + str(iteration)
            )
            if len(geogrid_name) > 0:
                grid_path = Path("share/results/grids/" + geogrid_name + ".roff")
                file_path_grid = ensemble_path / grid_path
                txt = f" Skip non-existing realization of grid: {real_number}"
            else:
                file_path_grid = ensemble_path
                txt = f" Skip non-existing realization: {real_number}"
            if not file_path_grid.exists():
                logger.info(txt)
                # No need to check other iterations since active_real should
                # only be those realizations that exists for all specified
                # iterations in iter_list
                real_exist = False
                continue
        if real_exist:
            active_real.append(real_number)

    number_of_skipped = nreal - len(active_real)
    return active_real, number_of_skipped


def generate_script(
    rms_load_script, ert_config_path, result_path, field_stat_config_file
):
    template_string = """#!/usr/bin/env python
# -*- coding: utf-8 -*-


from pathlib import Path

import fmu.config.utilities as utils
import xtgeo
import yaml

# Edit this label to fit your case
LABEL = "test"

# --------   Usually no need to edit the code below to fit your case ----------

PRJ = project
ERT_CONFIG_PATH = "{ert_config_path}"
GLOBAL_VARIABLES_FILE = Path(ERT_CONFIG_PATH) / Path(
    "../../fmuconfig/output/global_variables.yml"
)
FIELD_STAT_CONFIG_FILE = Path(ERT_CONFIG_PATH) / Path("{field_stat_config_file}")
RESULT_PATH = Path("{result_path}")


def read_field_stat_config(config_file_name):
    print(f"Read file: {{config_file_name}}")
    with open(config_file_name, encoding="utf-8") as yml_file:
        return yaml.safe_load(yml_file)


def get_facies_per_zone(glob_var_file, geogrid_fields_dict):
    cfg_global = utils.yaml_load(glob_var_file)["global"]
    keyword = "FACIES_ZONE"
    if keyword in cfg_global:
        facies_per_zone = cfg_global[keyword]
    else:
        facies_per_zone = geogrid_fields_dict.get('facies_per_zone',None)
        if facies_per_zone is None:
            raise KeyError(f"Missing keyword: {{keyword}}")
    return facies_per_zone


def main():
    config_dict = read_field_stat_config(FIELD_STAT_CONFIG_FILE)
    field_stat = config_dict["field_stat"]
    code_names_per_zone = field_stat["zone_code_names"]
    ertbox_per_zone_dict = None
    ertbox_default = code_names_per_zone
    if "ertbox_per_zone" in field_stat:
        ertbox_per_zone_dict = field_stat["ertbox_per_zone"]
    if "ertbox_default" in field_stat:
        ertbox_default = field_stat["ertbox_default"]

    key = "geogrid_fields"
    geogrid_fields_dict = None
    if key in field_stat:
        geogrid_fields_dict = field_stat[key]
        facies_per_zone = get_facies_per_zone(
            GLOBAL_VARIABLES_FILE, geogrid_fields_dict)

        key = "use_zones"
        if key in geogrid_fields_dict:
            zone_list = geogrid_fields_dict["use_zones"]
        else:
            zone_list = list(zone_code_names.values())

        key = "continuous_property_param_per_zone"
        cont_prop_dict = None
        if key in geogrid_fields_dict:
            cont_prop_dict = geogrid_fields_dict[key]

        key = "discrete_property_param_per_zone"
        discrete_prop_dict = None
        if key in geogrid_fields_dict:
            discrete_prop_dict = geogrid_fields_dict[key]

    result_path = RESULT_PATH
    stat_list = ["mean", "stdev"]
    iter_list = field_stat["iterations"]

    label = LABEL
    if geogrid_fields_dict:
        for zone in zone_list:
            if ertbox_per_zone_dict:
                if zone in ertbox_per_zone_dict:
                    ertbox_grid_name = ertbox_per_zone_dict[zone]
                else:
                    if ertbox_default:
                        ertbox_grid_name = ertbox_default
                    else:
                        raise ValueError(f"Missing ertbox grid for zone {{zone}}")
            elif ertbox_default:
                ertbox_grid_name = ertbox_default
            else:
                raise ValueError("Missing definition of ertbox grid")
            if cont_prop_dict and zone in cont_prop_dict:
                for stat in stat_list:
                    for prop_name in cont_prop_dict[zone]:
                        for iteration in iter_list:
                            name = (
                                "ertbox--"
                                + stat
                                + "_"
                                + zone
                                + "_"
                                + prop_name
                                + "_"
                                + str(iteration)
                            )
                            difference_name = (
                                "diff_ertbox--" + stat + "_" + zone + "_" + prop_name
                            )
                            print(f"Read: {{name}} into {{ertbox_grid_name}}")
                            filename = Path(result_path) / Path(name + ".roff")
                            prop_param = xtgeo.gridproperty_from_file(
                                filename, fformat="roff"
                            )
                            new_name = name
                            new_difference_name = difference_name
                            if label:
                                new_name = name + "_" + label
                                new_difference_name = difference_name + "_" + label
                            prop_param.name = new_name
                            prop_param.to_roxar(PRJ, ertbox_grid_name, new_name)
                            if iteration == iter_list[0]:
                                # Init
                                prop_param_init = prop_param
                            elif iteration == iter_list[-1]:
                                prop_param_upd = prop_param
                                prop_param_diff = prop_param_upd.copy(
                                    new_difference_name
                                )
                                # Calculate the difference
                                prop_param_diff.values = (
                                    prop_param_diff.values - prop_param_init.values
                                )
                                prop_param_diff.to_roxar(
                                    PRJ, ertbox_grid_name, new_difference_name)
                    for iteration in iter_list:
                        name = "ertbox--nactive_" + zone + "_" + str(iteration)
                        print(f"Read: {{name}} into {{ertbox_grid_name}}")
                        filename = Path(result_path) / Path(name + ".roff")
                        prop_param = xtgeo.gridproperty_from_file(
                            filename,
                            fformat="roff")
                        new_name = name
                        if label:
                            new_name = name + "_" + label
                        prop_param.name = new_name
                        prop_param.to_roxar(PRJ, ertbox_grid_name, new_name)

            if discrete_prop_dict and zone in discrete_prop_dict:
                code_names_per_zone = facies_per_zone[zone]
                for _, fname in code_names_per_zone.items():
                    for iteration in iter_list:
                        name = (
                            "ertbox--prob_" + zone + "_" + fname + "_" + str(iteration)
                        )
                        difference_name = "diff_ertbox--prob_" + zone + "_" + fname
                        print(f"Read: {{name}} into {{ertbox_grid_name}}")
                        filename = Path(result_path) / Path(name + ".roff")
                        prop_param = xtgeo.gridproperty_from_file(
                            filename,
                            fformat="roff")
                        new_name = name
                        new_difference_name = difference_name
                        if label:
                            new_name = name + "_" + label
                            new_difference_name = difference_name + "_" + label
                        prop_param.name = new_name
                        prop_param.to_roxar(PRJ, ertbox_grid_name, new_name)
                        if iteration == iter_list[0]:
                            # Init
                            prop_param_init = prop_param
                        elif iteration == iter_list[-1]:
                            prop_param_upd = prop_param
                            prop_param_diff = prop_param_upd.copy(new_difference_name)
                            # Calculate the difference
                            prop_param_diff.values = (
                                prop_param_diff.values - prop_param_init.values
                            )
                            prop_param_diff.to_roxar(
                                PRJ, ertbox_grid_name, new_difference_name
                            )
                for iteration in iter_list:
                    name = "ertbox--nactive_" + zone + "_" + str(iteration)
                    print(f"Read: {{name}} into {{ertbox_grid_name}}")
                    filename = Path(result_path) / Path(name + ".roff")
                    prop_param = xtgeo.gridproperty_from_file(filename, fformat="roff")
                    new_name = name
                    if label:
                        new_name = name + "_" + label
                    prop_param.to_roxar(PRJ, ertbox_grid_name, new_name)

    key_fields = "temporary_ertbox_fields"
    if key_fields in field_stat:
        init_path = None
        parameter_name_per_zone = None
        temporary_ertbox_fields = field_stat[key_fields]
        key = "initial_field_relative_path"
        if key in temporary_ertbox_fields:
            init_path = temporary_ertbox_fields[key]
        else:
            raise ValueError(f"Missing keyword: {{key}} in keyword {{key_fields}}")
        key = "parameter_name_per_zone"
        if key in temporary_ertbox_fields:
            parameter_name_per_zone = temporary_ertbox_fields[key]
        else:
            raise ValueError(f"Missing keyword: {{key}} in keyword {{key_fields}}")
        for zone, param_names in parameter_name_per_zone.items():
            if ertbox_per_zone_dict:
                if zone in ertbox_per_zone_dict:
                    ertbox_grid_name = ertbox_per_zone_dict[zone]
                else:
                    if ertbox_default:
                        ertbox_grid_name = ertbox_default
                    else:
                        raise ValueError(f"Missing ertbox grid for zone {{zone}}")
            elif ertbox_default:
                ertbox_grid_name = ertbox_default
            else:
                raise ValueError("Missing definition of ertbox grid")

            for param_name in param_names:
                for iteration in iter_list:
                    mean_name = "mean_" + param_name + "_" + str(iteration)
                    std_name = "stdev_" + param_name + "_" + str(iteration)

                    mean_param_file_name = Path(result_path) / Path(mean_name + ".roff")
                    mean_prop_param = xtgeo.gridproperty_from_file(
                        mean_param_file_name, fformat="roff"
                    )
                    print(f"Read: {{mean_name}} into {{ertbox_grid_name}}")

                    std_param_file_name = Path(result_path) / Path(std_name + ".roff")
                    std_prop_param = xtgeo.gridproperty_from_file(
                        std_param_file_name, fformat="roff"
                    )
                    print(f"Read: {{std_name}} into {{ertbox_grid_name}}")

                    if label:
                        new_mean_name = mean_name + "_" + label
                        new_std_name = std_name + "_" + label
                        difference_mean_name = "diff_" + new_mean_name
                        difference_std_name = "diff_" + new_std_name

                    mean_prop_param.to_roxar(PRJ, ertbox_grid_name, new_mean_name)
                    std_prop_param.to_roxar(PRJ, ertbox_grid_name, new_std_name)

                    if iteration == iter_list[0]:
                        # Init
                        mean_prop_param_init = mean_prop_param
                        std_prop_param_init = std_prop_param
                    elif iteration == iter_list[-1]:
                        mean_prop_param_upd = mean_prop_param
                        std_prop_param_upd = std_prop_param
                        diff_mean_prop_param = mean_prop_param_upd.copy()
                        diff_std_prop_param = std_prop_param_upd.copy()
                        diff_mean_prop_param.values = (
                            mean_prop_param_upd.values - mean_prop_param_init.values)
                        diff_std_prop_param.values =  (
                            std_prop_param_upd.values - std_prop_param_init.values)
                        diff_mean_prop_param.to_roxar(PRJ,
                            ertbox_grid_name, difference_mean_name)
                        diff_std_prop_param.to_roxar(PRJ,
                            ertbox_grid_name, difference_std_name)

if __name__ == "__main__":
    main()

"""  # noqa: RUF027
    print(f"Write file: {rms_load_script}")
    with open(rms_load_script, "w", encoding="utf-8") as file:
        file.write(
            template_string.format(
                ert_config_path=ert_config_path,
                field_stat_config_file=field_stat_config_file,
                result_path=result_path,
            )
        )
        file.write("\n")


class FieldStatistics(ert.ErtScript):
    """This class defines the ERT workflow hook.

    It is constructed to work identical to the command line except

      * field_statistics is upper-cased to FIELD_STATISTICS
      * All option names with double-dash must be enclosed in "" to avoid
        interference with the ERT comment characters "--".
    """

    def run(self, *args):
        """Pass the ERT workflow arguments on to the same parser as the command
        line."""
        parser = get_parser_ert()
        parsed_args = parser.parse_args(args)
        field_stat(parsed_args)


@ert.plugin(name="subscript")
def legacy_ertscript_workflow(config):
    """A hook for usage of this script in an ERT workflow,
    using the legacy hook format."""

    workflow = config.add_workflow(FieldStatistics, "FIELD_STATISTICS")
    workflow.parser = get_parser_ert
    workflow.description = DESCRIPTION_FOR_ERT
    workflow.examples = EXAMPLES
    workflow.category = CATEGORY


if __name__ == "__main__":
    main()
