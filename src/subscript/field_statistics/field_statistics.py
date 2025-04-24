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

# pylint: disable=missing-function-docstring, too-many-arguments
# pylint: disable=too-many-branches, too-many-statements
# pylint: disable= too-many-locals, too-many-nested-blocks
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

import subscript

logger = subscript.getLogger(__name__)
DESCRIPTION_FOR_ERT = """Calculate mean, stdev and estimated facies probabilities
from field parameters using ERTBOX grid.
"""

DESCRIPTION = """Calculate mean, stdev and estimated facies probabilities
from field parameters using ERTBOX grid.

The script reads ensembles of realizations from scratch disk  from
<RUN_PATH> directory::

  share/results/grids/geogrid--<propertyname>.roff.

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
    - Any lateral variability from realization to realization or curved shaped
      lateral grid is ignored. Only the cell indices are used to identify
      grid cell field parameters from each realization. This means that
      mean, standard deviation and estimated facies probabilities are estimated
      for each cell labeled with index (I,J,K) and not physical position (x,y,z).

The output statistical properties (mean, stdev, prob) is saved in a user
specified folder for the ERTBOX grid, but default if not specified
is 'share/grid_statistics' folder under the top level of the scratch
directory for the ERT case. The default estimate of standard deviation
is the sample standard deviation

.. math::

  \\text{variance} = \\frac{\\sum (x_i - \\bar{x})^2}{N-1}

and number of realizations must be at least 2. Optionally, the population
standard deviation

.. math::

  \\text{variance} = \\frac{\\sum (x_i - \\bar{x})^2}{N}

can be specified.

For grid cells where number of realizations are less than 2,
the standard deviation parameter calculated will be set to 0.

The script will read info about ERTBOX grid size from the FMU project
specified (The <CONFIG_PATH>) from the location::

  rms/output/aps/ERTBOX.roff

The script assumes that the keyword FACIES_ZONE keyword is defined
in the global_variables.yml file specified in the FMU project
(The <CONFIG_PATH>) from the location::

  fmuconfig/output/global_variables.yml

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

If this does not exist, it must be added.

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

    # Specify which geogrid fields to use
    # Geogrid fields are typically found in:
    # <RUN_PATH>/share/results/grids/geogrid--<property-name>.roff
    # Optional keyword
    geogrid_fields:
        # Selected set of zone names to use in calculations of statistics.
        # Must be one or more of the defined zones.
        # Require at least one zone to be selected.
        use_zones: ["Valysar", "Therys", "Volon"]

        # Zone numbers with zone name dictionary
        zone_code_names:
            1: "Valysar"
            2: "Therys"
            3: "Volon"

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
        # share/results/grids/geogrid--<name>.roff
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
        #  share/results/grids/geogrid--<name>.roff
        # files that are of continuous type
        # This key can be omitted or some of the lines specifying
        # parameters for a zone if you don't want to use it.
        continuous_property_param_per_zone:
            "Valysar": ["phit", "klogh"]
            "Therys":  ["phit", "klogh"]
            "Volon":   ["phit", "klogh"]

        # Size of ertbox grid for (nx, ny, nz)
        # Optional, but required if the ERTBOX.EGRID is not found under
        # ERT model under <CONFIG_PATH>/../../rms/output/aps
        ertbox_size: [92, 146, 66]

    # Specify which temporary field parameters (in ertbox) to use
    # to calculate mean and stdev
    # Optional keyword
    temporary_ertbox_fields:
        # Relative path relative to ERT <RUN_PATH> for localisation of
        # initial ensemble of field parameters
        initial_relative_path: "rms/output/aps"

        # Field parameter names as specified in ERT FIELD keywords
        parameter_names: [
            Volon_Channel_KLOGH,
            Volon_Channel_PHIT,
            Therys_Uppershoreface_KLOGH,
            Therys_Lowershoreface_KLOGH,
            Therys_Offshore_KLOGH,
            Therys_Uppershoreface_PHIT,
            Therys_Lowershoreface_PHIT,
            Therys_Offshore_PHIT,
            Valysar_Crevasse_KLOGH,
            Valysar_Channel_KLOGH,
            Valysar_Floodplain_KLOGH,
            Valysar_Crevasse_PHIT,
            Valysar_Channel_PHIT,
            Valysar_Floodplain_PHIT,
            aps_Volon_GRF3,
            aps_Volon_GRF2,
            aps_Volon_GRF1,
            aps_Therys_GRF3,
            aps_Therys_GRF2,
            aps_Therys_GRF1,
            aps_Valysar_GRF3,
            aps_Valysar_GRF2,
            aps_Valysar_GRF1,
        ]

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
ERTBOX_GRID_PATH = "../../rms/output/aps/ERTBOX.EGRID"


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
    field_stat = config_dict["field_stat"]

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
    if not check_if_iterations_exist(ens_path, field_stat):
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
        raise IOError(f"Result directory:  {result_path} does not exist.")

    rms_load_script = None
    if args.generate_rms_load_script:
        rms_load_script = args.generate_rms_load_script

    copy_to_geogrid_realization = args.copy_result_to_geogrid

    glob_var_config_path = ert_config_path / Path(GLOBAL_VARIABLES_FILE)
    cfg_global = utils.yaml_load(glob_var_config_path)["global"]
    keyword = "FACIES_ZONE"
    if keyword in cfg_global:
        facies_per_zone = cfg_global[keyword]
    else:
        raise KeyError(f"Missing keyword: {keyword} in {glob_var_config_path}")

    # The ERTBOX grid file location in FMU
    ertbox_path = ert_config_path / ERTBOX_GRID_PATH
    ertbox_size = get_ertbox_size(ertbox_path)
    logger.info(f"Config path to FMU project: {ert_config_path}")
    logger.info(f"Ensemble path on scratch disk: {ens_path}")
    logger.info(f"Result path on scratch disk: {result_path}")
    logger.info(f"ERTBOX size:  {ertbox_size}")

    calc_stats(
        field_stat,
        ens_path,
        facies_per_zone,
        result_path,
        ert_config_path,
        ertbox_size,
        copy_to_geogrid_realization=copy_to_geogrid_realization,
    )

    calc_temporary_field_stats(
        field_stat,
        ens_path,
        result_path,
        ert_config_path,
        ertbox_size,
    )

    ertbox_path = ert_config_path / ERTBOX_GRID_PATH
    copy_ertbox_grid_to_result_path(ertbox_path, result_path)

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


def read_ensemble_realization(
    ensemble_path,
    realization_number,
    iter_number,
    property_param_name,
    zone_code_names,
):
    realization_path = Path(f"realization-{realization_number}/iter-{iter_number}")
    grid_path = Path("share/results/grids/geogrid.roff")
    file_path_grid = Path(ensemble_path) / realization_path / grid_path
    if file_path_grid.exists():
        grid = xtgeo.grid_from_file(file_path_grid, fformat="roff")
        subgrids = grid.subgrids if grid.subgrids else None
    else:
        return None, None, None

    property_path = Path(f"share/results/grids/geogrid--{property_param_name}.roff")
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
):
    realization_path = Path(f"realization-{realization_number}/iter-{iter_number}")
    grid_path = Path("share/results/grids/geogrid.roff")
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

    assert geogrid_dimensions[0] == ertbox_size[0]
    assert geogrid_dimensions[1] == ertbox_size[1]
    assert ertbox_size[2] >= nz_zone
    prop_values = geogrid_property_param.values
    if is_continuous:
        ertbox_prop_values = np.ma.masked_all(
            (ertbox_size[0], ertbox_size[1], ertbox_size[2]), dtype=np.float32
        )
    else:
        ertbox_prop_values = np.ma.masked_all(
            (ertbox_size[0], ertbox_size[1], ertbox_size[2]), dtype=np.int32
        )
    if conformity.upper() in ["PROPORTIONAL", "TOP_CONFORM"]:
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
    if conformity.upper() in ["PROPORTIONAL", "TOP_CONFORM"]:
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
            ens_path, real_number, iter_number, zone_code_names
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
    param_name=None,
    facies_name=None,
):
    if param_name:
        geogrid_stat_name = f"geogrid--{statistics_name}_{param_name}"
    if facies_name:
        geogrid_stat_name = f"geogrid--{statistics_name}_{facies_name}"
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
            ens_path, real_number, iter_number, zone_code_names
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
            facies_name=facies_name,
        )


def get_specifications(input_dict, ertbox_size, ert_config_path):
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

    if not ertbox_size:
        # ertbox size does not exist, read it from this scripts config file instead
        logger.info("ERTBOX size is not defined, need to get it from the config file.")
        key = "ertbox_size"
        if key in input_dict["geogrid_fields"]:
            ertbox_size = input_dict["geogrid_fields"][key]
        else:
            raise KeyError(
                f"Missing keyword '{key}'."
                "Is required if the ERTBOX.EGRID is not found in the "
                "configuration directory of the FMU project under: "
                f" {ert_config_path / Path('../../rms/output/aps/ERTBOX.EGRID')}"
            )

    # Optional keywords
    key = "use_population_stdev"
    use_population_stdev = False
    if key in input_dict:
        use_population_stdev = input_dict[key]

    use_geogrid_fields = False
    zone_names_used = None
    zone_conformity = None
    zone_code_names = None
    param_name_dict = None
    disc_param_name_dict = None
    if "geogrid_fields" in input_dict:
        use_geogrid_fields = True
        geogrid_fields_dict = input_dict["geogrid_fields"]

        key = "zone_code_names"
        if key in geogrid_fields_dict:
            zone_code_names = geogrid_fields_dict[key]
        else:
            raise KeyError(
                f"Missing keyword:  {key} specifying zone name for each zone number."
            )

        key = "use_zones"
        zone_names_used = copy.copy(list(zone_code_names.values()))
        if key in geogrid_fields_dict:
            zone_names_input = geogrid_fields_dict[key]
            if zone_names_input is not None and len(zone_names_input) > 0:
                zone_names_used = zone_names_input
        check_use_zones(zone_code_names, zone_names_used)

        key = "zone_conformity"
        if key in geogrid_fields_dict:
            zone_conformity = geogrid_fields_dict[key]
        else:
            raise KeyError(f"Missing keyword:  {key} specifying conformity per zone.")
        check_zone_conformity(zone_code_names, zone_names_used, zone_conformity)

        key = "continuous_property_param_per_zone"
        if key in geogrid_fields_dict:
            param_name_dict = geogrid_fields_dict[key]
        check_param_name_dict(zone_code_names, param_name_dict)

        key = "discrete_property_param_per_zone"
        if key in geogrid_fields_dict:
            disc_param_name_dict = geogrid_fields_dict[key]
        check_disc_param_name_dict(zone_code_names, disc_param_name_dict)

        check_used_params(zone_names_used, param_name_dict, disc_param_name_dict)

    use_temporary_fields = False
    temporary_ertbox_field = None
    init_path = None
    param_list = None
    if "temporary_ertbox_fields" in input_dict:
        use_temporary_fields = True
        temporary_ertbox_field = input_dict["temporary_ertbox_fields"]

        key = "initial_relative_path"
        if key in temporary_ertbox_field:
            init_path = temporary_ertbox_field[key]
        else:
            raise KeyError(
                f"Missing keyword:  {key} "
                "specifying relative path for initial temporary fields."
            )
        key = "parameter_names"
        if key in temporary_ertbox_field:
            param_list = temporary_ertbox_field[key]
        else:
            raise KeyError(
                f"Missing keyword:  {key} "
                "specifying list of temporary field parameter names."
            )

    if not use_geogrid_fields and not use_temporary_fields:
        raise ValueError(
            "No fields are specified as input to calculation "
            "of field parameter statistics.  Check configuration "
            "file for FIELD_STATISTICS workflow job."
        )

    return (
        use_geogrid_fields,
        use_temporary_fields,
        ertbox_size,
        nreal,
        iter_list,
        use_population_stdev,
        zone_names_used,
        zone_conformity,
        zone_code_names,
        param_name_dict,
        disc_param_name_dict,
        init_path,
        param_list,
    )


def get_ertbox_size(ertbox_path):
    if not Path(ertbox_path).exists():
        print(f"The ertbox file does not exist in:  {ertbox_path}")
        return None
    ertbox_grid = xtgeo.grid_from_file(ertbox_path, fformat="egrid")
    return ertbox_grid.dimensions


def copy_ertbox_grid_to_result_path(ertbox_path, result_path):
    if not Path(ertbox_path).exists():
        raise IOError(f"The ertbox file does not exist in:  {ertbox_path}")
    ertbox_grid = xtgeo.grid_from_file(ertbox_path, fformat="egrid")
    grid_file_name = result_path / Path("ertbox.roff")
    print(f"Copy ertbox grid file from {ertbox_path} to {grid_file_name}")
    ertbox_grid.to_file(grid_file_name, fformat="roff")


def copy_to_real0_dirs(field_stat, result_path, ens_path):
    import glob
    import shutil

    iteration_list = field_stat["iterations"]
    for iter in iteration_list:
        source_files = result_path / Path(f"ertbox--*_{iter}.roff")
        target_dir = ens_path / Path(f"realization-0/iter-{iter}/share/results/grids")
        print(f"Source_files:  {source_files}")
        print(f"Target dir: {target_dir}")
        for f in glob.glob(source_files.as_posix()):
            shutil.copy(f, target_dir.as_posix())
        source_file = result_path / Path("ertbox.roff")
        shutil.copy(source_file.as_posix(), target_dir.as_posix())


def check_zone_conformity(zone_code_names, zone_names_used, zone_conformity):
    for zone_name, conformity in zone_conformity.items():
        if zone_name not in list(zone_code_names.values()):
            raise ValueError("Unknown zone names in keyword 'zone_conformity'.")
        if conformity.upper() not in ["TOP_CONFORM", "BASE_CONFORM", "PROPORTIONAL"]:
            raise ValueError(
                "Undefined zone conformity specified "
                "(Must be Top_conform, Base_conform or Proportional)."
            )
    for zone_name in zone_names_used:
        if zone_name not in zone_conformity:
            raise ValueError(
                f"Zone with name {zone_name} is missing in keyword 'zone_conformity'."
            )


def check_param_name_dict(zone_code_names, param_name_dict):
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


def check_disc_param_name_dict(zone_code_names, disc_param_name_dict):
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


def check_use_zones(zone_code_names, zone_names):
    if not zone_names or len(zone_names) == 0:
        return
    for zone_name in zone_names:
        if zone_name not in list(zone_code_names.values()):
            raise ValueError(
                "Unknown zone name in specification of keyword 'use_zones'."
            )


def check_used_params(zone_names_used, param_name_dict, disc_param_name_dict):
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
    input_dict,
    ens_path,
    facies_per_zone,
    result_path,
    ert_config_path,
    ertbox_size,
    copy_to_geogrid_realization=False,
):
    (
        use_geogrid_fields,
        use_temporary_fields,
        ertbox_size,
        nreal,
        iter_list,
        use_population_stdev,
        zone_names,
        zone_conformity,
        zone_code_names,
        param_name_dict,
        disc_param_name_dict,
        _,
        _,
    ) = get_specifications(input_dict, ertbox_size, ert_config_path)

    # Check if any need to continue to calculation
    if not use_geogrid_fields:
        return

    ensemble_path = ens_path

    logger.info(f"Number of realizations: {nreal}")
    for iter_number in iter_list:
        logger.info(f"Ensemble iteration: {iter_number}")
        for zone_name in zone_names:
            logger.info(f"Zone name: {zone_name}")
            has_written_nactive = False
            if param_name_dict:
                if zone_name not in param_name_dict:
                    continue
                for param_name in param_name_dict[zone_name]:
                    logger.info(f" Property: {param_name}")
                    all_values = np.ma.masked_all(
                        (ertbox_size[0], ertbox_size[1], ertbox_size[2], nreal),
                        dtype=np.float32,
                    )
                    number_of_skipped = 0
                    for real_number in range(nreal):
                        grid_dimensions, subgrids, property_param = (
                            read_ensemble_realization(
                                ensemble_path,
                                real_number,
                                iter_number,
                                param_name,
                                zone_code_names,
                            )
                        )
                        if grid_dimensions is None:
                            txt = f" Skip non-existing realization: {real_number}"
                            logger.info(txt)
                            number_of_skipped += 1
                            continue
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
                    number_of_skipped = 0
                    for real_number in range(nreal):
                        grid_dimensions, subgrids, property_param = (
                            read_ensemble_realization(
                                ensemble_path,
                                real_number,
                                iter_number,
                                param_name,
                                zone_code_names,
                            )
                        )

                        if grid_dimensions is None:
                            logger.info(f" Skip realization: {real_number}")
                            number_of_skipped += 1
                            continue
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
                                    copy_to_geogrid_realization=copy_to_geogrid_realization,
                                )
                        txt4 = f"  Sum facies volume fraction: {sum_fraction}"
                        logger.info(txt4)
                    else:
                        txt = (
                            "No probability estimate calculated for "
                            f"{param_name} for zone {zone_name}"
                            f" for ensemble iteration {iter_number}"
                        )
                        logger.info(txt)


def calc_temporary_field_stats(
    input_dict,
    ens_path,
    result_path,
    ert_config_path,
    ertbox_size,
):
    (
        use_geogrid_fields,
        use_temporary_fields,
        ertbox_size,
        nreal,
        iter_list,
        use_population_stdev,
        _,
        _,
        _,
        _,
        _,
        init_path,
        param_list,
    ) = get_specifications(input_dict, ertbox_size, ert_config_path)

    # Check if any need to continue to calculation
    if not use_temporary_fields:
        return

    # Import realizations of temporary field parameters
    for param_name in param_list:
        for iteration in iter_list:
            param_filename = param_name + ".roff"
            if iteration == 0:
                full_param_filename = init_path + "/" + param_filename
            elif iteration == iter_list[-1]:
                full_param_filename = param_filename
            logger.info(f"Property: {param_name}")
            all_values = np.ma.masked_all(
                (ertbox_size[0], ertbox_size[1], ertbox_size[2], nreal),
                dtype=np.float32,
            )

            number_of_skipped = 0
            for real_number in range(nreal):
                filepath = (
                    ens_path
                    / Path(
                        "realization-" + str(real_number) + "/iter-" + str(iteration)
                    )
                    / Path(full_param_filename)
                )
                if not filepath.exists():
                    txt = f" Skip non-existing realization: {real_number}"
                    logger.info(txt)
                    number_of_skipped += 1
                    continue
                property = xtgeo.gridproperty_from_file(filepath, fformat="roff")
                values = property.values
                all_values[:, :, :, real_number] = values

            # Calculate statistics
            calc_mean = False
            calc_stdev = False
            mean_values_masked = None
            stdev_values_masked = None
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
LABEL = "drogon"

# --------   Usually no need to edit the code below to fit your case ----------

PRJ = project

GRIDNAME = "ERTBOX"

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


def get_facies_per_zone(glob_var_file):
    cfg_global = utils.yaml_load(glob_var_file)["global"]
    keyword = "FACIES_ZONE"
    if keyword in cfg_global:
        facies_per_zone = cfg_global[keyword]
    else:
        raise KeyError(f"Missing keyword: {{keyword}} in {{GLOBAL_VARIABLES_FILE}}")
    return facies_per_zone


def main():
    config_dict = read_field_stat_config(FIELD_STAT_CONFIG_FILE)
    field_stat = config_dict["field_stat"]
    key = "geogrid_fields"
    geogrid_fields_dict = None
    if key in field_stat:
        geogrid_fields_dict = field_stat[key]
        zone_code_names = geogrid_fields_dict["zone_code_names"]
        facies_per_zone = get_facies_per_zone(GLOBAL_VARIABLES_FILE)

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
                            print(f"Read: {{name}} into {{GRIDNAME}}")
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
                            prop_param.to_roxar(PRJ, GRIDNAME, new_name)
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
                                    PRJ, GRIDNAME, new_difference_name)
                    for iteration in iter_list:
                        name = "ertbox--nactive_" + zone + "_" + str(iteration)
                        print(f"Read: {{name}} into {{GRIDNAME}}")
                        filename = Path(result_path) / Path(name + ".roff")
                        prop_param = xtgeo.gridproperty_from_file(
                            filename,
                            fformat="roff")
                        new_name = name
                        if label:
                            new_name = name + "_" + label
                        prop_param.name = new_name
                        prop_param.to_roxar(PRJ, GRIDNAME, new_name)

            if discrete_prop_dict and zone in discrete_prop_dict:
                code_names_per_zone = facies_per_zone[zone]
                for _, fname in code_names_per_zone.items():
                    for iteration in iter_list:
                        name = (
                            "ertbox--prob_" + zone + "_" + fname + "_" + str(iteration)
                        )
                        difference_name = "diff_ertbox--prob_" + zone + "_" + fname
                        print(f"Read: {{name}} into {{GRIDNAME}}")
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
                        prop_param.to_roxar(PRJ, GRIDNAME, new_name)
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
                            prop_param_diff.to_roxar(PRJ, GRIDNAME, new_difference_name)
                for iteration in iter_list:
                    name = "ertbox--nactive_" + zone + "_" + str(iteration)
                    print(f"Read: {{name}} into {{GRIDNAME}}")
                    filename = Path(result_path) / Path(name + ".roff")
                    prop_param = xtgeo.gridproperty_from_file(filename, fformat="roff")
                    new_name = name
                    if label:
                        new_name = name + "_" + label
                    prop_param.to_roxar(PRJ, GRIDNAME, new_name)

    key = "temporary_ertbox_fields"
    if key in field_stat:
        init_path = None
        param_names = None
        temporary_ertbox_fields = field_stat[key]
        key = "initial_relative_path"
        if key in temporary_ertbox_fields:
            init_path = temporary_ertbox_fields[key]
        key = "parameter_names"
        if key in temporary_ertbox_fields:
            param_names = temporary_ertbox_fields[key]
        if init_path and param_names:
            for param_name in param_names:
                for iteration in iter_list:
                    new_name = "mean_" + param_name + "_" + str(iteration)
                    param_file_name = Path(result_path) / Path(new_name + ".roff")
                    prop_param = xtgeo.gridproperty_from_file(
                        param_file_name, fformat="roff"
                    )
                    print(f"Read: {{new_name}} into {{GRIDNAME}}")
                    if label:
                        new_name = new_name + "_" + label
                    prop_param.to_roxar(PRJ, GRIDNAME, new_name)

                    new_name = "stdev_" + param_name + "_" + str(iteration)
                    param_file_name = Path(result_path) / Path(new_name + ".roff")
                    prop_param = xtgeo.gridproperty_from_file(
                        param_file_name, fformat="roff"
                    )
                    print(f"Read: {{new_name}} into {{GRIDNAME}}")
                    if label:
                        new_name = new_name + "_" + label
                    prop_param.to_roxar(PRJ, GRIDNAME, new_name)

if __name__ == "__main__":
    main()

"""
    print(f"Write file: {rms_load_script}")
    with open(rms_load_script, "w") as file:
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

    # pylint: disable=too-few-public-methods
    def run(self, *args):
        # pylint: disable=no-self-use
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
