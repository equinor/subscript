# import logging
import shutil
from pathlib import Path

import fmu.config.utilities as utils
import numpy as np
import pytest

# import yaml
import xtgeo

from subscript.field_statistics.field_statistics import (
    calc_stats,
    check_disc_param_name_dict,
    check_param_name_dict,
    check_use_zones,
    check_zone_conformity,
    get_specifications,
    set_subgrid_names,
)

# logger = subscript.getLogger(__name__)
# logger.setLevel(logging.INFO)

TESTDATA = Path("testdata_field_statistics")
ENSEMBLE = Path("ensemble")
RESULT_PATH = Path("share/grid_statistics")
ERT_CONFIG_PATH = Path("ert/model")
DATADIR = Path(__file__).absolute().parent / TESTDATA
GLOBAL_VARIABLES_FILE = Path("../../fmuconfig/output/global_variables.yml")
RMS_LOAD_SCRIPT_NAME = "tmp_import_field_stat_results.py"

CONFIG_DICT = {
    "nreal": 10,
    "iterations": [0, 3],
    "use_population_stdev": False,
    "geogrid_fields": {
        "use_zones": ["A", "B", "C"],
        "zone_code_names": {
            1: "A",
            2: "B",
            3: "C",
        },
        "zone_conformity": {
            "A": "Top_conform",
            "B": "Proportional",
            "C": "Base_conform",
        },
        "discrete_property_param_per_zone": {
            "A": ["facies"],
            "B": ["facies"],
            "C": ["facies"],
        },
        "continuous_property_param_per_zone": {
            "A": ["P1", "P2"],
            "B": ["P1"],
            "C": ["P2"],
        },
        "ertbox_size": [5, 6, 5],
    },
}


def make_box_grid(dimensions, grid_name, result_path):
    filename = result_path / Path(grid_name + ".roff")
    filename_egrid = result_path / Path(grid_name.upper() + ".EGRID")

    grid = xtgeo.create_box_grid(dimensions)
    grid.name = grid_name.lower()
    print(f"Grid name:  {grid.name}")
    print(f"Grid dimensions: {grid.dimensions}")
    print(f"Write grid to file:  {filename}")
    grid.to_file(filename, fformat="roff")
    grid.to_file(filename_egrid, fformat="egrid")


def make_file_names(ensemble_path, iter_number, real_number, param_name):
    filedir = ensemble_path / Path("realization-" + str(real_number))
    if not filedir.exists():
        filedir.mkdir()
    filedir = filedir / Path("iter-" + str(iter_number))
    if not filedir.exists():
        filedir.mkdir()
    filedir = filedir / Path("share")
    if not filedir.exists():
        filedir.mkdir()
    filedir = filedir / Path("results")
    if not filedir.exists():
        filedir.mkdir()
    filedir = filedir / Path("grids")
    if not filedir.exists():
        filedir.mkdir()
    filename = filedir / Path("geogrid--" + param_name + ".roff")
    filename_active = filedir / Path("geogrid--active.roff")
    filename_grid = filedir / Path("geogrid.roff")
    return filename, filename_active, filename_grid


def make_ensemble_test_data(
    config_dict,
    facies_per_zone,
    nx,
    ny,
    nz_ertbox,
    ensemble_path,
    print_info=False,
):
    if print_info:
        print("Start make test data")

    iteration_list = [0, 3]
    zone_code_names = config_dict["geogrid_fields"]["zone_code_names"]
    discrete_param_name_per_zone = config_dict["geogrid_fields"][
        "discrete_property_param_per_zone"
    ]
    param_name_per_zone = config_dict["geogrid_fields"][
        "continuous_property_param_per_zone"
    ]
    nreal = 10
    vparam = 1.0
    for iter_number in iteration_list:
        for zone_number, zone_name in zone_code_names.items():
            param_name_list = []
            if zone_name in param_name_per_zone:
                param_name_list = param_name_per_zone[zone_name]
            disc_param_name_list = []
            if zone_name in discrete_param_name_per_zone:
                disc_param_name_list = discrete_param_name_per_zone[zone_name]
            if len(param_name_list):
                for n, param_name in enumerate(param_name_list):
                    if print_info:
                        print(
                            f"Ensemble iteration: {iter_number} "
                            f"Zone name: {zone_name} Param name:  {param_name}"
                        )
                    for real_number in range(nreal):
                        values = np.ma.masked_all(
                            (nx, ny, 3 * nz_ertbox), dtype=np.float32
                        )
                        filename, filename_active, filename_grid = make_file_names(
                            ensemble_path, iter_number, real_number, param_name
                        )
                        values = assign_values_continuous_param(
                            nz_ertbox,
                            nreal,
                            vparam * (n + 1),
                            iter_number,
                            len(iteration_list),
                            real_number,
                            values,
                        )
                        xtgeo_param = xtgeo.GridProperty(
                            ncol=nx,
                            nrow=ny,
                            nlay=3 * nz_ertbox,
                            discrete=False,
                            values=values,
                            name=param_name,
                        )
                        xtgeo_param.to_file(filename, fformat="roff")

                        active = ~values.mask
                        xtgeo_active = xtgeo.GridProperty(
                            ncol=nx,
                            nrow=ny,
                            nlay=3 * nz_ertbox,
                            discrete=False,
                            values=active,
                            name=param_name,
                        )
                        xtgeo_active.to_file(filename_active, fformat="roff")

                        # The geogrid is here not realization dependent
                        # but need to be saved for each realization anyway
                        xtgeo_geogrid = xtgeo.create_box_grid((nx, ny, 3 * nz_ertbox))
                        subgrid_dict = {
                            "A": nz_ertbox,
                            "B": nz_ertbox,
                            "C": nz_ertbox,
                        }

                        xtgeo_geogrid.set_actnum(xtgeo_active)
                        set_subgrid_names(xtgeo_geogrid, new_subgrids=subgrid_dict)
                        xtgeo_geogrid.to_file(filename_grid, fformat="roff")

            if len(disc_param_name_list):
                for param_name in disc_param_name_list:
                    if print_info:
                        print(
                            f"Ensemble iteration: {iter_number} "
                            f"Zone name: {zone_name} Param name:  {param_name}"
                        )
                    for real_number in range(nreal):
                        values = np.ma.masked_all(
                            (nx, ny, 3 * nz_ertbox), dtype=np.uint8
                        )
                        filename, filename_active, filename_grid = make_file_names(
                            ensemble_path, iter_number, real_number, param_name
                        )

                        values, code_names = assign_values_discrete_param(
                            nz_ertbox,
                            facies_per_zone,
                            zone_code_names,
                            real_number,
                            values,
                        )
                        xtgeo_param = xtgeo.GridProperty(
                            ncol=nx,
                            nrow=ny,
                            nlay=3 * nz_ertbox,
                            discrete=True,
                            values=values,
                            codes=code_names,
                            name=param_name,
                        )
                        xtgeo_param.to_file(filename, fformat="roff")

                        active = ~values.mask
                        xtgeo_active = xtgeo.GridProperty(
                            ncol=nx,
                            nrow=ny,
                            nlay=3 * nz_ertbox,
                            discrete=False,
                            values=active,
                            name=param_name,
                        )
                        xtgeo_active.to_file(filename_active, fformat="roff")
                        # The geogrid is here not realization dependent
                        # but need to be saved for each realization anyway
                        xtgeo_geogrid = xtgeo.create_box_grid((nx, ny, 3 * nz_ertbox))
                        subgrid_dict = {
                            "A": nz_ertbox,
                            "B": nz_ertbox,
                            "C": nz_ertbox,
                        }

                        xtgeo_geogrid.set_actnum(xtgeo_active)
                        set_subgrid_names(xtgeo_geogrid, new_subgrids=subgrid_dict)
                        xtgeo_geogrid.to_file(filename_grid, fformat="roff")

            if print_info:
                print(
                    "Testdata for ensemble for zone "
                    f"{zone_name} for iteration {iter_number} completed."
                )
    print("Finished making testdata ensemble")


def assign_values_continuous_param(
    nz, nreal, vparam, iter_number, niter, real_number, values
):
    layer_values = np.ma.masked_all(3 * nz, dtype=np.float32)
    for k in range(3 * nz):
        if real_number < (nreal - 1):
            if 0 <= k <= (nz - 2):
                # Zone 1 Top conform (layer 0,..,nz-1)
                # Bottom layer of zone is inactive for most realizations
                layer_values[k] = (
                    1.0
                    * vparam
                    * k
                    * (real_number + 1)
                    / nreal
                    * (iter_number + 1)
                    / niter
                )
            elif (2 * nz + 1) <= k <= (3 * nz - 1):
                # Zone 3 Base conform  (layer nz,..,2*nz-1)
                # Top layer of zone is inactive for most realizations
                layer_values[k] = (
                    3.0
                    * vparam
                    * k
                    * (real_number + 1)
                    / nreal
                    * (iter_number + 1)
                    / niter
                )
            elif nz <= k <= (2 * nz - 1):
                # Zone 2 Proportional (layer nz,.. 2*nz-1)
                # All layer of zone is active
                layer_values[k] = (
                    2.0
                    * vparam
                    * k
                    * (real_number + 1)
                    / nreal
                    * (iter_number + 1)
                    / niter
                )
        else:
            # For 1 realizations, fill all layers
            if 0 <= k <= (nz - 1):
                # Zone 1 Top conform (layer 0,..,nz-1)
                # Bottom layer of zone is active for some realizations
                layer_values[k] = (
                    1.0
                    * vparam
                    * k
                    * (real_number + 1)
                    / nreal
                    * (iter_number + 1)
                    / niter
                )
            elif (2 * nz) <= k <= (3 * nz - 1):
                # Zone 3 Base conform  (layer nz,..,2*nz-1)
                # Top layer of zone is active for some realizations
                layer_values[k] = (
                    3.0
                    * vparam
                    * k
                    * (real_number + 1)
                    / nreal
                    * (iter_number + 1)
                    / niter
                )
            elif nz <= k <= (2 * nz - 1):
                # Zone 2 Proportional (layer nz,.. 2*nz-1)
                # All layer of zone is active
                layer_values[k] = (
                    2.0
                    * vparam
                    * k
                    * (real_number + 1)
                    / nreal
                    * (iter_number + 1)
                    / niter
                )
    for k in range(3 * nz):
        values[:, :, k] = layer_values[k]
    return values


def assign_values_discrete_param(
    nz, facies_per_zone, zone_code_names, real_number, values
):
    # Test data made for nz = 5 and nreal = 10
    nreal = 10
    assert real_number < 10
    assert nz * 3 == 15
    facies_code_per_layer_per_realization = [
        [1, 1, 3, 3, 2, 2, 1, 3, 1, 2],
        [2, 3, 1, 1, 2, 1, 2, 3, 1, 1],
        [2, 1, 2, 2, 2, 2, 1, 3, 3, 3],
        [1, 1, 1, 3, 2, 1, 1, 3, 3, 3],
        [3, 3, 1, 3, 2, 2, 1, 3, 1, 3],
        [3, 3, 1, 3, 1, 2, 2, 3, 2, 1],
        [3, 3, 3, 1, 2, 3, 1, 3, 1, 1],
        [3, 3, 1, 3, 2, 2, 1, 3, 1, 1],
        [2, 3, 1, 3, 1, 3, 3, 3, 1, 2],
        [1, 3, 1, 1, 3, 2, 1, 3, 2, 3],
        [2, 3, 1, 3, 3, 1, 3, 3, 1, 3],
        [1, 1, 2, 3, 3, 1, 1, 3, 1, 2],
        [3, 3, 2, 3, 2, 1, 1, 3, 1, 2],
        [3, 3, 1, 3, 2, 2, 2, 3, 2, 1],
        [3, 3, 1, 3, 2, 2, 1, 3, 1, 2],
    ]

    all_code_names = {}
    for zone_name in zone_code_names.values():
        code_names = facies_per_zone[zone_name]
        for code, name in code_names.items():
            if code not in all_code_names:
                all_code_names[code] = name

    for code, name in all_code_names.items():
        assert code in [1, 2, 3]

    for k in range(nz * 3):
        if real_number < (nreal - 1):
            if 0 <= k <= (nz - 2):
                # Zone 1 Top conform (layer 0,..,nz-1)
                # Bottom layer of zone is inactive for most realizations
                values[:, :, k] = facies_code_per_layer_per_realization[k][real_number]
            elif (2 * nz + 1) <= k <= (3 * nz - 1):
                # Zone 3 Base conform  (layer nz,..,2*nz-1)
                # Top layer of zone is inactive for most realizations
                values[:, :, k] = facies_code_per_layer_per_realization[k][real_number]
            elif nz <= k <= (2 * nz - 1):
                # Zone 2 Proportional (layer nz,.. 2*nz-1)
                # All layer of zone is active'
                values[:, :, k] = facies_code_per_layer_per_realization[k][real_number]
        else:
            # For 1 realizations, fill all layers
            values[:, :, k] = facies_code_per_layer_per_realization[k][real_number]

    return values, all_code_names


def make_test_case(tmp_path, config_dict):
    """Makes a test data set based on the input config_dict"""
    tmp_testdata_path = tmp_path / TESTDATA
    shutil.copytree(DATADIR, tmp_testdata_path)

    ens_path = tmp_testdata_path / ENSEMBLE
    ert_config_path = tmp_testdata_path / ERT_CONFIG_PATH
    result_path = ens_path / RESULT_PATH

    glob_cfg_path = ert_config_path / GLOBAL_VARIABLES_FILE
    cfg_global = utils.yaml_load(glob_cfg_path)["global"]
    keyword = "FACIES_ZONE"
    if keyword in cfg_global:
        facies_per_zone = cfg_global[keyword]
    else:
        raise KeyError(f"Missing keyword: {keyword} in {glob_cfg_path}")

    (nx, ny, nz) = config_dict["geogrid_fields"]["ertbox_size"]

    # Write file with ERTBOX grid for the purpose to import to visualize
    # the test data in e.g. RMS. Saved in share directory at
    # top of ensemble directory
    make_box_grid((nx, ny, nz), "ERTBOX", result_path)

    # Write file with geogrid for the purpose to import to visualize
    # the test data in e.g. RMS". Geogrid for the test data has 3 zones,
    # each with 5 layers. Saved in share directory at top of ensemble directory
    make_box_grid((nx, ny, nz * 3), "Geogrid", result_path)

    # Make ensemble of test data
    make_ensemble_test_data(
        config_dict, facies_per_zone, nx, ny, nz, ens_path, print_info=True
    )
    return facies_per_zone, ens_path, result_path, ert_config_path, (nx, ny, nz)


def compare_with_referencedata(ens_path, result_path, print_check=False):
    lines = []
    file_list = result_path / Path("referencedata/files.txt")
    with open(file_list, "r") as file:
        lines = file.readlines()
    is_ok = []

    ncount = 0
    if print_check:
        print("Compare results from test with reference data:")
    for nameinput in lines:
        name = nameinput.strip()
        words = name.split("_")
        if words[0] in ["mean", "stdev", "prob"]:
            fullfilename = result_path / Path("ertbox--" + name)
            reference_filename = result_path / Path("referencedata") / Path(name)
            grid_property = xtgeo.gridproperty_from_file(fullfilename, fformat="roff")
            grid_property_reference = xtgeo.gridproperty_from_file(
                reference_filename, fformat="roff"
            )
            values = grid_property.values
            ref_values = grid_property_reference.values
            ncount += 1
            if np.ma.allequal(values, ref_values):
                if print_check:
                    print(f" {name}  OK")
                is_ok.append(True)
            else:
                if print_check:
                    print(f" {name}  Failed")
                    print(f"Not equal to reference for {fullfilename}")
                is_ok.append(False)
    is_success = True
    if ncount < 34:
        is_success = False
    for i in range(ncount):
        if not is_ok[i]:
            is_success = False
    return is_success


@pytest.mark.parametrize(
    "config_dict",
    [CONFIG_DICT],
)
def test_calc_statistics(
    tmp_path,
    config_dict,
    ertbox_size=None,
):
    # Create testdata for an ensemble to be used
    facies_per_zone, ens_path, result_path, ert_config_path, ertbox_size = (
        make_test_case(tmp_path, config_dict)
    )

    # Run the calculations of mean, stdev, prob
    print("Calculate statistics")
    calc_stats(
        config_dict,
        ens_path,
        facies_per_zone,
        result_path,
        ert_config_path,
        ertbox_size,
    )

    # Check that the result is equal to reference data set
    assert compare_with_referencedata(ens_path, result_path, print_check=True)


@pytest.mark.parametrize(
    "zone_code_names, zone_names_used, zone_conformity, expected_error",
    [
        (
            {
                1: "A",
                2: "B",
                3: "C",
            },
            ["A", "B"],
            {
                "A": "Top_conform",
                "B": "Proportional",
                "D": "Base_conform",
            },
            "Unknown zone names in keyword 'zone_conformity'.",
        ),
        (
            {
                1: "A",
                2: "B",
                3: "C",
            },
            ["A", "B", "C"],
            {
                "A": "Top_conform",
                "B": "Proportional",
                "C": "BaseConform",
            },
            "Undefined zone conformity specified "
            "(Must be Top_conform, Base_conform or Proportional).",
        ),
        (
            {
                1: "A",
                2: "B",
                3: "C",
            },
            ["A", "B"],
            {
                "A": "Top_conform",
                "C": "Base_conform",
            },
            "is missing in keyword 'zone_conformity'.",
        ),
    ],
)
def test_zone_conformity(
    zone_code_names, zone_names_used, zone_conformity, expected_error
):
    if expected_error is not None:
        with pytest.raises(ValueError) as validation_error:
            check_zone_conformity(zone_code_names, zone_names_used, zone_conformity)
        assert expected_error in str(validation_error)


@pytest.mark.parametrize(
    "zone_code_names, param_name_dict, expected_error",
    [
        (
            {
                1: "A",
                2: "B",
                3: "C",
            },
            {
                "A": ["P1", "P2"],
                "B": ["P1"],
                "D": ["P2"],
            },
            "Unknown zone name in specification of keyword "
            "'continuous_property_param_per_zone'.",
        ),
        (
            {
                1: "A",
                2: "B",
                3: "C",
            },
            {
                "A": ["P1", "P2"],
                "B": None,
                "C": ["P2"],
            },
            "Missing list of property names for a specified zone "
            "in keyword 'continuous_property_param_per_zone'.",
        ),
        (
            {
                1: "A",
                2: "B",
                3: "C",
            },
            {
                "A": ["P1", "P2"],
                "B": [],
                "C": ["P2"],
            },
            "Missing list of property names for a specified zone in "
            "keyword 'continuous_property_param_per_zone'.",
        ),
    ],
)
def test_param_name_dict(zone_code_names, param_name_dict, expected_error):
    if expected_error is not None:
        with pytest.raises(ValueError) as validation_error:
            check_param_name_dict(zone_code_names, param_name_dict)
        assert expected_error in str(validation_error)


@pytest.mark.parametrize(
    "zone_code_names, disc_param_name_dict, expected_error",
    [
        (
            {
                1: "A",
                2: "B",
                3: "C",
            },
            {
                "A": ["facies"],
                "B": ["facies"],
                "D": ["facies"],
            },
            "Unknown zone name in specification of keyword "
            "'discrete_property_param_per_zone'.",
        ),
        (
            {
                1: "A",
                2: "B",
                3: "C",
            },
            {
                "A": ["facies"],
                "B": None,
                "C": ["facies"],
            },
            "Missing list of property names for a specified zone "
            "in keyword 'discrete_property_param_per_zone'.",
        ),
        (
            {
                1: "A",
                2: "B",
                3: "C",
            },
            {
                "A": ["facies"],
                "B": [],
                "C": ["facies"],
            },
            "Missing list of property names for a specified zone "
            "in keyword 'discrete_property_param_per_zone'.",
        ),
    ],
)
def test_disc_param_name_dict(zone_code_names, disc_param_name_dict, expected_error):
    if expected_error is not None:
        with pytest.raises(ValueError) as validation_error:
            check_disc_param_name_dict(zone_code_names, disc_param_name_dict)
        assert expected_error in str(validation_error)


@pytest.mark.parametrize(
    "zone_code_names, zone_names, expected_error",
    [
        (
            {
                1: "A",
                2: "B",
                3: "C",
            },
            ["A", "D"],
            "Unknown zone name in specification of keyword 'use_zones'.",
        ),
    ],
)
def test_check_use_zones_errors(zone_code_names, zone_names, expected_error):
    if expected_error is not None:
        with pytest.raises(ValueError) as validation_error:
            check_use_zones(zone_code_names, zone_names)
        assert expected_error in str(validation_error)


CONFIG_DICT_REF = {
    "nreal": 10,
    "iterations": [0, 3],
    "geogrid_fields": {
        "use_zones": ["A", "B", "C"],
        "zone_code_names": {
            1: "A",
            2: "B",
            3: "C",
        },
        "zone_conformity": {
            "A": "Top_conform",
            "B": "Proportional",
            "C": "Base_conform",
        },
        "discrete_property_param_per_zone": {
            "A": ["facies"],
            "B": ["facies"],
            "C": ["facies"],
        },
        "continuous_property_param_per_zone": {
            "A": ["P1", "P2"],
            "B": ["P1"],
            "C": ["P2"],
        },
        "ertbox_size": [5, 6, 5],
    },
    "use_population_stdev": False,
}

CONFIG_A = {
    "nreal": 10,
    "iterations": [0],
    "geogrid_fields": {
        "zone_code_names": {
            1: "A",
            2: "B",
        },
        "zone_conformity": {
            "A": "Base_conform",
            "B": "Top_conform",
        },
        "discrete_property_param_per_zone": {
            "A": ["facies"],
        },
        "continuous_property_param_per_zone": {
            "A": ["P1", "P2"],
            "B": ["P1"],
        },
        "ertbox_size": [50, 60, 50],
    },
}

CONFIG_A_REF = {
    "nreal": 10,
    "iterations": [0],
    "geogrid_fields": {
        "zone_code_names": {
            1: "A",
            2: "B",
        },
        "zone_conformity": {
            "A": "Base_conform",
            "B": "Top_conform",
        },
        "discrete_property_param_per_zone": {
            "A": ["facies"],
        },
        "continuous_property_param_per_zone": {
            "A": ["P1", "P2"],
            "B": ["P1"],
        },
        "ertbox_size": [50, 60, 50],
        "use_zones": ["A", "B"],
    },
    "use_population_stdev": False,
}

CONFIG_B = {
    "nreal": 10,
    "iterations": [0],
    "geogrid_fields": {
        "zone_code_names": {
            1: "A",
            2: "B",
            3: "C",
            4: "D",
        },
        "use_zones": ["B", "D"],
        "zone_conformity": {
            "B": "Top_conform",
            "D": "Proportional",
        },
        "continuous_property_param_per_zone": {
            "D": ["P1", "P2"],
            "B": ["P1"],
        },
        "ertbox_size": [10, 6, 15],
    },
    "use_population_stdev": True,
}

CONFIG_B_REF = {
    "nreal": 10,
    "iterations": [0],
    "geogrid_fields": {
        "zone_code_names": {
            1: "A",
            2: "B",
            3: "C",
            4: "D",
        },
        "zone_conformity": {
            "B": "Top_conform",
            "D": "Proportional",
        },
        "continuous_property_param_per_zone": {
            "D": ["P1", "P2"],
            "B": ["P1"],
        },
        "discrete_property_param_per_zone": None,
        "ertbox_size": [10, 6, 15],
        "use_zones": ["B", "D"],
    },
    "use_population_stdev": True,
}

CONFIG_C = {
    "nreal": 10,
    "iterations": [0],
    "geogrid_fields": {
        "zone_code_names": {
            1: "A",
            2: "B",
            3: "C",
            4: "D",
        },
        "zone_conformity": {
            "A": "Base_conform",
            "B": "Top_conform",
            "C": "Top_conform",
            "D": "Proportional",
        },
        "discrete_property_param_per_zone": {
            "A": ["facies1", "facies2"],
            "D": ["facies1", "facies2"],
            "B": ["facies3"],
            "C": ["facies1", "facies2"],
        },
        "ertbox_size": [10, 6, 15],
    },
    "use_population_stdev": True,
}

CONFIG_C_REF = {
    "nreal": 10,
    "iterations": [0],
    "geogrid_fields": {
        "zone_code_names": {
            1: "A",
            2: "B",
            3: "C",
            4: "D",
        },
        "zone_conformity": {
            "A": "Base_conform",
            "B": "Top_conform",
            "C": "Top_conform",
            "D": "Proportional",
        },
        "discrete_property_param_per_zone": {
            "A": ["facies1", "facies2"],
            "D": ["facies1", "facies2"],
            "C": ["facies1", "facies2"],
            "B": ["facies3"],
        },
        "property_param_per_zone": None,
        "ertbox_size": [10, 6, 15],
        "use_zones": ["A", "B", "C", "D"],
    },
    "use_population_stdev": True,
}


@pytest.mark.parametrize(
    "input_dict, reference_dict,ert_config_path",
    [
        (CONFIG_DICT, CONFIG_DICT_REF, ERT_CONFIG_PATH),
        (CONFIG_A, CONFIG_A_REF, ERT_CONFIG_PATH),
        (CONFIG_B, CONFIG_B_REF, ERT_CONFIG_PATH),
    ],
)
def test_get_specification(
    input_dict, reference_dict, ert_config_path, ertbox_size=None
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
    assert ertbox_size == reference_dict["geogrid_fields"]["ertbox_size"]
    assert zone_names == reference_dict["geogrid_fields"]["use_zones"]
    assert nreal == reference_dict["nreal"]
    assert iter_list == reference_dict["iterations"]
    assert zone_conformity == reference_dict["geogrid_fields"]["zone_conformity"]
    assert zone_code_names == reference_dict["geogrid_fields"]["zone_code_names"]
    assert use_population_stdev == reference_dict["use_population_stdev"]
    assert (
        param_name_dict
        == reference_dict["geogrid_fields"]["continuous_property_param_per_zone"]
    )
    assert (
        disc_param_name_dict
        == reference_dict["geogrid_fields"]["discrete_property_param_per_zone"]
    )


@pytest.mark.parametrize(
    "config_file, config_dict",
    [(Path("config_example.yml"), CONFIG_DICT)],
)
def test_main(tmp_path, config_file, config_dict, print_info=True):
    import subprocess

    # First make an ensemble to be used as testdata. This is based on the config_dict
    _, ens_path, result_path, ert_config_path, _ = make_test_case(tmp_path, config_dict)
    tmp_testdata_path = tmp_path / TESTDATA
    config_path = tmp_testdata_path / Path(config_file)
    ert_config_path = tmp_testdata_path / ERT_CONFIG_PATH
    ens_path = tmp_testdata_path / ENSEMBLE
    result_path = ens_path / RESULT_PATH

    rms_load_script = result_path / RMS_LOAD_SCRIPT_NAME

    # Run the main script as a subprocess
    subprocess.run(
        [
            "field_statistics",
            "-c",
            config_path.as_posix(),
            "-p",
            ert_config_path.as_posix(),
            "-e",
            ens_path.as_posix(),
            "-r",
            result_path.as_posix(),
            "-z",
            rms_load_script.as_posix(),
            "-g",
        ]
    )
    # For this test not to fail, the CONFIG_DICT and the specified
    # config file in yaml format must define the same setup
    assert compare_with_referencedata(ens_path, result_path, print_check=True)
