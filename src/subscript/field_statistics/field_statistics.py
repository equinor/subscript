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
from ert.config import ErtScript

import subscript

logger = subscript.getLogger(__name__)
DESCRIPTION = """Calculate mean, stdev and estimated facies probabilities
from field parameters using ERTBOX grid.

The script reads ensembles of realizations from scratch disk  from
share/results/grids/geogrid--<propertyname>.roff.

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

    * The lateral extension of the geogrid is close to a regular grid with same
      orientation and grid resolution as the ERTBOX grid.
    * The ERTBOX grid should be the same as used in ERT when field parameters
      are updated using the ERT keyword FIELD in the ERT configuration file.
    * Any lateral variability from realization to realization or curved shaped
      lateral grid is ignored. Only the cell indices are used to identify
      grid cell field parameters from each realization. This means that
      mean, standard deviation and estimated facies probabilities are estimated
      for each cell labeled with index (I,J,K) and not physical position (x,y,z).

The output statistical properties (mean, stdev, prob) is saved in a user
specified folder, but default if not specified is share/grid_statistics
folder under the top level of the scratch directory for the ERT case.
The default estimate of standard deviation is the sample standard deviation
(variance = sum( (x(i)-x_mean)^2 )/(N-1) )
and number of realizations must be at least 2. Optionally, the population
standard deviation
(variance = sum( (x(i)-x_mean)^2 )/N )
can be specified.

For grid cells where number of realizations are less than 2,
the standard deviation parameter calculated will be set to 0.
"""

EPILOGUE = """
.. code-block:: yaml

  # Example config file for wf_field_param_statistics

  field_stat:
    # Number of realizations for specified ensemble
    # Required.
    nreal: 100

    # Iteration numbers from ES-MDA in ERT (iteration = 0 is initial ensemble,
    # usually iteration=3 is final updated ensemble)
    # Required.
    iterations: [0, 3]

    # Selected set of zone names to use in calculations of statistics.
    # Must be one or more of the defined zones.
    # Require at least one zone to be selected.
    use_zones: ["Valysar", "Therys", "Volon"]

    # Zone numbers with zone name dictionary ordered in increasing order of zone code
    # Required for multi-zone grids.
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
        "Valysar": ["phit"]
        "Therys":  ["phit"]
        "Volon":   ["phit"]

    # Size of ertbox grid for (nx, ny, nz)
    # Required if the ERTBOX grid is not found as a file
    # under rms/output/aps/ERTBOX.EGRID
    ertbox_size: [92, 146, 66]

    # Standard deviation estimator.
    # Optional. Default is False which means that
    # sample standard deviation ( normalize by (N-1)) is used
    # where N is number of realizations.
    # The alternative is True which means that
    # population standard deviation ( normalize by N) is used.
    use_population_stdev: False

"""

CATEGORY = "modelling.reservoir"

EXAMPLES = """
.. code-block:: console

-- Installation of the ERT workflow:
DEFINE <FIELD_STAT_CONFIG_FILE>  ../input/config/field_param_stat.yml
-- The workflow job FIELD_STATISTICS is generated automatically by ERT
-- The workflow file wf_field_param_statistics run FIELD_STATISTICS
LOAD_WORKFLOW           ../../bin/workflows/wf_field_param_statistics

-- The workflow file to be located under ert/bin/workflows run FIELD_STATISTICS:
-- Example of a workflow file can be
FIELD_STATISTICS -c <FIELD_STAT_CONFIG_FILE>
                 -p <CONFIG_PATH>
                 -e <SCRATCH>/<USER>/<CASE_DIR>
                 -r <RESULT_PATH>
-- where <FIELD_STAT_CONFIG_FILE> is the usre specification for this script,
-- and where <CONFIG_PATH> is the ERT <CONFIG_PATH> for the ERT project,
-- and where ensemble directory is specified by  the '-e' option and
-- where the result directory is specified by the <RESULT_PATH>. This is optional
-- since share/grid_statistics is used as default.
-- The results from iter-0 is also copied to 'realization-0/iter-0/share/results/grids
-- and results from iter-3 is copied to 'realization-0/iter-3/share/results/grids.
-- Workflow job for ERT to calculate field statistics is automatically
-- generated by ERT from the subscript repository, but when setting it 
-- up manually, it look like this:
INTERNAL   False
EXECUTABLE  ../scripts/field_statistics.py

MIN_ARG   6
ARG_TYPE    0   STRING
ARG_TYPE    1   STRING
ARG_TYPE    2   STRING
ARG_TYPE    3   STRING
ARG_TYPE    4   STRING
ARG_TYPE    5   STRING
ARG_TYPE    6   STRING
ARG_TYPE    7   STRING
ARG_TYPE    8   STRING


"""  # noqa
DEFAULT_RELATIVE_RESULT_PATH = "share/grid_statistics"
GLOBAL_VARIABLES_FILE = "../../fmuconfig/output/global_variables.yml"
ERTBOX_GRID_PATH = "../../rms/output/aps/ERTBOX.EGRID"


def main():
    """Invocated from the command line, parsing command line arguments"""
    parser = get_parser()
    args = parser.parse_args()
    logger.setLevel(logging.INFO)
    field_stat(args)


def field_stat(args):
    # parse the config file for this script
    if not Path(args.configfile).exists():
        sys.exit("No such file:" + args.configfile)

    config_file = args.configfile
    config_dict = read_field_stat_config(config_file)
    field_stat = config_dict["field_stat"]

    # Path to FMU project models ert/model directory (ordinary CONFIG PATH in ERT)
    if not Path(args.ertconfigpath).exists():
        sys.exit("No such file:" + args.ertconfigpath)
    ert_config_path = Path(args.ertconfigpath)

    # Path to ensemble on SCRATCH disk
    if not Path(args.ensemblepath).exists():
        sys.exit("No such file:" + args.ensemblepath)
    ens_path = Path(args.ensemblepath)

    # Path for result of ensemble statistics calculations
    # Default path is defined.
    relative_result_path = DEFAULT_RELATIVE_RESULT_PATH
    if args.resultpath:
        relative_result_path = Path(args.resultpath)
    result_path = ens_path / relative_result_path

    rms_load_script = None
    if args.generate_rms_load_script:
        rms_load_script = args.generate_rms_load_script

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
        field_stat, ens_path, facies_per_zone, result_path, ert_config_path, ertbox_size
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
        "-C",
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
        help=(
            "Root path assumed for relative paths"
            " in config file, except for the output file."
        ),
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
        "--version",
        action="version",
        version="%(prog)s (subscript version " + subscript.__version__ + ")",
    )

    parser.add_argument(
        "-z",
        "--generate_rms_load_script",
        type=str,
        default="tmp_import_ensemble_field_statistics.py",
        help=("Name of script for loading results into RMS for visualization. "),
    )
    return parser


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
    mean_values_masked,
    stdev_values_masked,
    ncount_active_values,
    result_path,
):
    output_path = result_path
    if not output_path.exists():
        # Create the directory
        output_path.mkdir()
    dims = mean_values_masked.shape
    name_mean = "ertbox--mean_" + zone_name + "_" + param_name + "_" + str(iter_number)
    name_stdev = (
        "ertbox--stdev_" + zone_name + "_" + param_name + "_" + str(iter_number)
    )
    name_nactive = "ertbox--nactive_" + zone_name + "_" + str(iter_number)
    result_mean_file_path = output_path / Path(name_mean + ".roff")
    result_stdev_file_path = output_path / Path(name_stdev + ".roff")
    result_nactive_file_path = output_path / Path(name_nactive + ".roff")

    # Fill masked values with 0
    mean_values = mean_values_masked.filled(fill_value=0.0)
    stdev_values = stdev_values_masked.filled(fill_value=0.0)

    xtgeo_mean = xtgeo.GridProperty(
        ncol=dims[0], nrow=dims[1], nlay=dims[2], name=name_mean, values=mean_values
    )
    xtgeo_stdev = xtgeo.GridProperty(
        ncol=dims[0], nrow=dims[1], nlay=dims[2], name=name_stdev, values=stdev_values
    )

    xtgeo_ncount_active = xtgeo.GridProperty(
        ncol=dims[0],
        nrow=dims[1],
        nlay=dims[2],
        name=name_nactive,
        values=ncount_active_values,
    )

    logger.info(f"Write parameter: {name_mean}")
    xtgeo_mean.to_file(result_mean_file_path, fformat="roff")

    logger.info(f"Write parameter: {name_stdev}")
    xtgeo_stdev.to_file(result_stdev_file_path, fformat="roff")

    logger.info(f"Write parameter: {name_nactive}")
    xtgeo_ncount_active.to_file(result_nactive_file_path, fformat="roff")


def write_fraction_nactive(
    ensemble_path,
    iter_number,
    zone_name,
    facies_name,
    fraction_masked,
    result_path,
    ncount_active_values=None,
):
    output_path = result_path
    if not output_path.exists():
        # Create the directory
        output_path.mkdir()
    dims = fraction_masked.shape
    name_fraction = (
        "ertbox--prob_" + zone_name + "_" + facies_name + "_" + str(iter_number)
    )
    name_nactive = "ertbox--nactive_" + zone_name + "_" + str(iter_number)

    result_fraction_file_path = output_path / Path(name_fraction + ".roff")
    result_nactive_file_path = output_path / Path(name_nactive + ".roff")

    # Fill masked values with 0
    fraction = fraction_masked.filled(fill_value=0.0)

    xtgeo_fraction = xtgeo.GridProperty(
        ncol=dims[0], nrow=dims[1], nlay=dims[2], name=name_fraction, values=fraction
    )

    logger.info(f"Write parameter: {name_fraction}")
    xtgeo_fraction.to_file(result_fraction_file_path, fformat="roff")

    if ncount_active_values is not None:
        xtgeo_ncount_active = xtgeo.GridProperty(
            ncol=dims[0],
            nrow=dims[1],
            nlay=dims[2],
            name=name_nactive,
            values=ncount_active_values,
        )

        logger.info(f"Write parameter: {name_nactive}")
        xtgeo_ncount_active.to_file(result_nactive_file_path, fformat="roff")


def get_specifications(input_dict, ertbox_size, ert_config_path):
    key = "zone_code_names"
    if key in input_dict:
        zone_code_names = input_dict[key]
    else:
        raise KeyError(
            f"Missing keyword:  {key} specifying " "zone name for each zone number."
        )

    if not ertbox_size:
        # ertbox size does not exist, read it from this scripts config file instead
        print("ERTBOX size is not defined, need to get it from the config file")
        key = "ertbox_size"
        if key in input_dict:
            ertbox_size = input_dict[key]
        else:
            raise KeyError(
                "Missing keyword 'ertbox_size'."
                "Is required if the ERTBOX.EGRID is not found in the "
                "configuration directory of the FMU project under: "
                f" {ert_config_path + '/../../rms/output/aps/ERTBOX.EGRID'}"
            )

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
    key = "use_zones"
    zone_names_used = copy.copy(list(zone_code_names.values()))
    if key in input_dict:
        zone_names_input = input_dict[key]
        if zone_names_input is not None and len(zone_names_input) > 0:
            zone_names_used = zone_names_input
    check_use_zones(zone_code_names, zone_names_used)

    key = "zone_conformity"
    if key in input_dict:
        zone_conformity = input_dict[key]
    else:
        raise KeyError(f"Missing keyword:  {key} specifying conformity per zone.")
    check_zone_conformity(zone_code_names, zone_names_used, zone_conformity)

    key = "use_population_stdev"
    use_population_stdev = False
    if key in input_dict:
        use_population_stdev = input_dict[key]

    param_name_dict = None
    key = "continuous_property_param_per_zone"
    if key in input_dict:
        param_name_dict = input_dict[key]
    check_param_name_dict(zone_code_names, param_name_dict)

    disc_param_name_dict = None
    key = "discrete_property_param_per_zone"
    if key in input_dict:
        disc_param_name_dict = input_dict[key]
    check_disc_param_name_dict(zone_code_names, disc_param_name_dict)

    check_used_params(zone_names_used, param_name_dict, disc_param_name_dict)

    return (
        ertbox_size,
        nreal,
        iter_list,
        zone_names_used,
        zone_conformity,
        zone_code_names,
        use_population_stdev,
        param_name_dict,
        disc_param_name_dict,
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
    input_dict, ens_path, facies_per_zone, result_path, ert_config_path, ertbox_size
):
    (
        ertbox_size,
        nreal,
        iter_list,
        zone_names,
        zone_conformity,
        zone_code_names,
        use_population_stdev,
        param_name_dict,
        disc_param_name_dict,
    ) = get_specifications(input_dict, ertbox_size, ert_config_path)

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
                    logger.info(f"Property: {param_name}")
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
                            result_path,
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
                    logger.info(f"Property: {param_name}")
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
                            txt1 = f"Average number of active cells: {sum_total_active}"
                            logger.info(txt1)

                            txt2 = (
                                f"Average number of cells with facies "
                                f"{facies_name} is {sum_total_code}"
                            )
                            logger.info(txt2)

                            txt3 = (
                                "Average estimated facies probability for facies "
                                f"{facies_name}: {fraction}"
                            )
                            logger.info(txt3)

                            sum_fraction += fraction

                            # Write fraction (estimated facies probability from ensemble

                            if not has_written_nactive:
                                # The parameter for number of realization for each grid
                                # cell value is not already written
                                write_fraction_nactive(
                                    ensemble_path,
                                    iter_number,
                                    zone_name,
                                    facies_name,
                                    prob_with_code,
                                    result_path,
                                    ncount_active_values=sum_active,
                                )
                                has_written_nactive = True
                            else:
                                write_fraction_nactive(
                                    ensemble_path,
                                    iter_number,
                                    zone_name,
                                    facies_name,
                                    prob_with_code,
                                    result_path,
                                )
                        txt4 = f"Sum facies volume fraction: {sum_fraction}"
                        logger.info(txt4)
                    else:
                        txt = (
                            "No probability estimate calculated for "
                            f"{param_name} for zone {zone_name}"
                            f" for ensemble iteration {iter_number}"
                        )
                        logger.info(txt)


def generate_script(
    rms_load_script, ert_config_path, result_path, field_stat_config_file
):
    template_string = """#!/usr/bin/env python
# -*- coding: utf-8 -*-

from  pathlib import Path
import xtgeo
import yaml
import fmu.config.utilities as utils

PRJ = project

GRIDNAME = "ERTBOX"

ERT_CONFIG_PATH = "{ert_config_path}"

GLOBAL_VARIABLES_FILE  = \
    ERT_CONFIG_PATH / Path("../../fmuconfig/output/global_variables.yml")

FIELD_STAT_CONFIG_FILE = "{field_stat_config_file}"

RESULT_PATH = "{result_path}"


LABEL = "drogon"

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
    zone_code_names = field_stat["zone_code_names"]
    facies_per_zone = get_facies_per_zone(GLOBAL_VARIABLES_FILE)
    result_path = RESULT_PATH
    zone_list= list(zone_code_names.values())
    stat_list= ["mean", "stdev"]
    iter_list = field_stat["iterations"]

    cont_prop_dict = field_stat["continuous_property_param_per_zone"]

    discrete_prop_dict = field_stat["discrete_property_param_per_zone"]

    label = LABEL
    for stat in stat_list:
        for zone in zone_list:
            for iteration in iter_list:
                if cont_prop_dict:
                    if zone in cont_prop_dict:
                        for prop_name in cont_prop_dict[zone]:
                            name = \
                            "ertbox--" + stat + "_" + zone + "_" + prop_name \
                            + "_" + str(iteration)
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
                        name = "ertbox--nactive_" + zone + "_" + str(iteration)
                        print(f"Read: {{name}} into {{GRIDNAME}}")
                        filename =  Path(result_path) / Path(name + ".roff")
                        prop_param = xtgeo.gridproperty_from_file(
                            filename,
                            fformat="roff"
                        )
                        new_name = name
                        if label:
                            new_name = name + "_" + label
                        prop_param.name = new_name
                        prop_param.to_roxar(PRJ, GRIDNAME, new_name)
                if discrete_prop_dict:
                    code_names_per_zone = facies_per_zone[zone]
                    for _, fname in code_names_per_zone.items():
                        name = \
                        "ertbox--prob_" + zone + "_" + fname + "_" + str(iteration)
                        print(f"Read: {{name}} into {{GRIDNAME}}")
                        filename = Path(result_path) / Path(name + ".roff")
                        prop_param = \
                            xtgeo.gridproperty_from_file(filename, fformat="roff")
                        new_name = name
                        if label:
                            new_name = name + "_" + label
                        prop_param.name = new_name
                        prop_param.to_roxar(PRJ, GRIDNAME, new_name)
                    name = "ertbox--nactive_" + zone + "_" + str(iteration)
                    print(f"Read: {{name}} into {{GRIDNAME}}")
                    filename =  Path(result_path) / Path(name + ".roff")
                    prop_param = xtgeo.gridproperty_from_file(filename, fformat="roff")
                    new_name = name
                    if label:
                        new_name = name + "_" + label
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


class FieldStatistics(ErtScript):
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
        parser = get_parser()
        parsed_args = parser.parse_args(args)
        field_stat(parsed_args)


@ert.plugin(name="subscript")
def legacy_ertscript_workflow(config):
    """A hook for usage of this script in an ERT workflow,
    using the legacy hook format."""

    workflow = config.add_workflow(FieldStatistics, "FIELD_STATISTICS")
    workflow.parser = get_parser
    workflow.description = DESCRIPTION
    workflow.examples = EXAMPLES
    workflow.category = CATEGORY


if __name__ == "__main__":
    main()
