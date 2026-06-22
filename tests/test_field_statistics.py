# import logging
import copy
import shutil
import subprocess
from pathlib import Path

import fmu.config.utilities as utils
import gaussianfft as sim
import numpy as np
import pytest
import xtgeo

from subscript.field_statistics.field_statistics import (
    calc_stats,
    calc_temporary_field_stats,
    check_disc_param_name_dict,
    check_param_name_dict,
    check_use_zones,
    check_zone_conformity,
    get_specifications,
    set_subgrid_names,
)

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
    "relative_path_ertbox_grids": "../../rms/output/aps",
    "ertbox_per_zone": {
        "A": "ertbox_A",
        "B": "ertbox_B",
        "C": "ertbox_C",
    },
    "ertbox_default": "ERTBOX",
    "zone_code_names": {
        1: "A",
        2: "B",
        3: "C",
    },
    "geogrid_fields": {
        "geogrid_name": "geogrid",
        "use_zones": ["A", "B", "C"],
        "facies_per_zone": {
            "A": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
            "B": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
            "C": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
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
    },
    "temporary_ertbox_fields": {
        "initial_field_relative_path": "rms/output/aps",
        "parameter_name_per_zone": {
            "A": ["A_GRF1", "A_GRF2"],
            "B": ["B_GRF2"],
        },
    },
}


def make_file_names_result_path(
    ensemble_path: str | Path,
    iter_number: int,
    real_number: int,
    param_name: str,
    geogrid_name: str | None = None,
):
    # filedir for multizone geogrid with field parameters
    filedir = ensemble_path / Path("realization-" + str(real_number))
    if not filedir.exists():
        filedir.mkdir()
    filedir /= Path("iter-" + str(iter_number))
    if not filedir.exists():
        filedir.mkdir()
    filedir /= Path("share")
    if not filedir.exists():
        filedir.mkdir()
    filedir /= Path("results")
    if not filedir.exists():
        filedir.mkdir()
    filedir /= Path("grids")
    if not filedir.exists():
        filedir.mkdir()
    result_field_filename = filedir / Path(
        f"{geogrid_name.strip()}--{param_name.strip()}.roff"
    )
    result_active_filename = filedir / Path(f"{geogrid_name.strip()}--active.roff")
    result_grid_filename = filedir / Path(f"{geogrid_name.strip()}.roff")

    return (
        result_field_filename,
        result_active_filename,
        result_grid_filename,
    )


def make_file_names_field_path(
    ensemble_path: str | Path,
    iter_number: int,
    real_number: int,
    param_name: str,
    zone_name: str,
):
    # filedir for single zone ertbox grid per zone with field parameters
    filedir = ensemble_path / Path("realization-" + str(real_number))
    if not filedir.exists():
        filedir.mkdir()
    filedir /= Path("iter-" + str(iter_number))
    if not filedir.exists():
        filedir.mkdir()

    if iter_number == 0:
        filedir_init = copy.copy(filedir)
        filedir_init /= Path("rms")
        if not filedir_init.exists():
            filedir_init.mkdir()
        filedir_init /= Path("output")
        if not filedir_init.exists():
            filedir_init.mkdir()
        filedir_init /= Path("aps")
        if not filedir_init.exists():
            filedir_init.mkdir()

        grf_field_filename = filedir_init / Path(f"{param_name.strip()}.roff")
        grf_active_filename = filedir_init / Path(f"{zone_name.strip()}_active.roff")
    else:
        grf_field_filename = filedir / Path(f"{param_name.strip()}.roff")
        grf_active_filename = filedir / Path(f"{zone_name.strip()}_active.roff")

    return (
        grf_field_filename,
        grf_active_filename,
    )


def simulate_continuous_ensemble_test_data(
    ensemble_path: str | Path,
    nreal: int,
    iteration_list: list[int],
    geogrid_name: str | Path,
    ertbox_size_per_zone: dict,
    grid_increments: tuple[float],
    param_names_per_zone: dict,
    start_seed: int,
    make_test_data_for_geogrid: bool = True,
):

    # Define the geogrid to have zones with size
    # equal to the ertbox size for each zone
    nz_geogrid = 0
    for _, dims in ertbox_size_per_zone.items():
        (nx, ny, nz_zone) = dims
        nz_geogrid += nz_zone

    variogram = sim.variogram("exponential", 25.0, 25.0, 1.0, 45.0, 0.0)
    dx = grid_increments[0]
    dy = grid_increments[1]
    dz = grid_increments[2]

    # List of all parameters found in all zones
    param_list_all = []
    param_values_dict = {}
    for _, param_list_for_zone in param_names_per_zone.items():
        for param_name in param_list_for_zone:
            if param_name not in param_list_all:
                param_list_all.append(param_name)
                # Allocate space for the property
                param_values_dict[param_name] = np.ma.masked_all(
                    (nx, ny, nz_geogrid), dtype=np.float32
                )

    # Simulate the field parameters for all iterations,
    # realizations, zones and parameters
    for iter_number in iteration_list:
        # Want to use same set of realizations for all iterations here
        # to simplify tests where some realizations will be inactivated
        # for ensemble with iter_number > 0 compared
        # with ensemble with iter_number = 0
        sim.seed(start_seed)
        for real_number in range(nreal):
            # Simulate gaussian random fields per continuous parameter
            # and save to file under 'run path/share/results/grids
            for param_name in param_list_all:
                start_layer = 0
                for zone_name, zone_dimensions in ertbox_size_per_zone.items():
                    (nx, ny, nz_zone) = zone_dimensions

                    # Initialize to 0 for values to non-existing parameters
                    field_3d_zone = np.zeros((nx, ny, nz_zone), dtype=np.float32)

                    if (zone_name in param_names_per_zone) and (
                        param_name in param_names_per_zone[zone_name]
                    ):
                        gauss_vector = sim.simulate(
                            variogram, nx, dx, ny, dy, nz_zone, dz
                        )
                        field_3d_zone = gauss_vector.reshape(
                            (nx, ny, nz_zone), order="F"
                        )
                        if not make_test_data_for_geogrid:
                            # Save test data for field parameters
                            (grf_field_filename, grf_active_filename) = (
                                make_file_names_field_path(
                                    ensemble_path,
                                    iter_number,
                                    real_number,
                                    param_name,
                                    zone_name,
                                )
                            )

                            xtgeo_param = xtgeo.GridProperty(
                                ncol=nx,
                                nrow=ny,
                                nlay=nz_zone,
                                discrete=False,
                                values=field_3d_zone,
                                name=param_name,
                            )
                            xtgeo_param.to_file(grf_field_filename, fformat="roff")

                            active = np.ones((nx, ny, nz_zone), dtype=np.int32)
                            xtgeo_active = xtgeo.GridProperty(
                                ncol=nx,
                                nrow=ny,
                                nlay=nz_zone,
                                discrete=False,
                                values=active,
                                name="active",
                            )
                            xtgeo_active.to_file(grf_active_filename, fformat="roff")

                    if make_test_data_for_geogrid:
                        # Add to geogrid multizone field parameter
                        end_layer = start_layer + nz_zone
                        param_values_dict[param_name][:, :, start_layer:end_layer] = (
                            field_3d_zone
                        )
                        start_layer += nz_zone

                if make_test_data_for_geogrid:
                    # Write field parameter for multizone geogrid
                    (
                        result_field_filename,
                        result_active_filename,
                        result_grid_filename,
                    ) = make_file_names_result_path(
                        ensemble_path,
                        iter_number,
                        real_number,
                        param_name,
                        geogrid_name,
                    )
                    xtgeo_param = xtgeo.GridProperty(
                        ncol=nx,
                        nrow=ny,
                        nlay=nz_geogrid,
                        discrete=False,
                        values=param_values_dict[param_name],
                        name=param_name,
                    )

                    xtgeo_param.to_file(result_field_filename, fformat="roff")

                    active = ~param_values_dict[param_name].mask
                    xtgeo_active = xtgeo.GridProperty(
                        ncol=nx,
                        nrow=ny,
                        nlay=nz_geogrid,
                        discrete=False,
                        values=active,
                        name="active",
                    )

                    xtgeo_active.to_file(result_active_filename, fformat="roff")

            if make_test_data_for_geogrid:
                # Create multizone geogrid, one per realization
                nz_geogrid = 0
                zone_names = list(ertbox_size_per_zone.keys())
                nx = ertbox_size_per_zone[zone_names[0]][0]
                ny = ertbox_size_per_zone[zone_names[0]][1]
                subgrid_dict = {}
                for zone_name, dims in ertbox_size_per_zone.items():
                    assert dims[0] == nx
                    assert dims[1] == ny
                    nz_geogrid += dims[2]
                    subgrid_dict[zone_name] = dims[2]

                xtgeo_geogrid = xtgeo.create_box_grid(
                    (nx, ny, nz_geogrid), increment=grid_increments
                )
                set_subgrid_names(xtgeo_geogrid, new_subgrids=subgrid_dict)

                # Write the geogrid to each realization
                xtgeo_geogrid.to_file(result_grid_filename, fformat="roff")

    return param_list_all


def remove_some_realizations_from_ensemble(
    ensemble_path: Path | str, iter_number: int, nreal: int, nreal_to_remove: int
):
    if nreal_to_remove > 0:
        # Select randomly realizations to remove
        # from ensembles for iter_number > 0
        real_number_list = np.arange(nreal)
        selected = np.random.choice(real_number_list, nreal_to_remove, replace=False)
        if iter_number > 0:
            for real_number in selected:
                filedir = ensemble_path / Path("realization-" + str(real_number))
                filedir /= Path("iter-" + str(iter_number))
                filedir /= Path("share")
                filedir /= Path("results")
                filedir /= Path("grids")
                try:
                    shutil.rmtree(filedir)
                except Exception as e:
                    print(f"Error deleting directory {filedir}: {e}")


def define_discrete_test_data(
    ensemble_path: str | Path,
    nreal: int,
    iteration_list: list[int],
    geogrid_name: str,
    disc_param_name_per_zone: dict,
    continuous_param_name: str,
    facies_per_zone: dict[str, dict],
):
    for iter_number in iteration_list:
        for real_number in range(nreal):
            continuous_field_filename, _, result_grid_filename = (
                make_file_names_result_path(
                    ensemble_path,
                    iter_number,
                    real_number,
                    continuous_param_name,
                    geogrid_name,
                )
            )
            # Read continuous parameter to use to create a discrete parameter
            # by truncation
            xtgeo_param = xtgeo.gridproperty_from_file(
                continuous_field_filename, fformat="roff"
            )
            continuous_values = xtgeo_param.values

            disc_param_name_list = []
            for _, disc_param_names in disc_param_name_per_zone.items():
                for param_name in disc_param_names:
                    if param_name not in disc_param_name_list:
                        disc_param_name_list.append(param_name)

            # Make discrete parameters
            for param_name in disc_param_name_list:
                result_filename_facies, _, _ = make_file_names_result_path(
                    ensemble_path,
                    iter_number,
                    real_number,
                    param_name,
                    geogrid_name,
                )
                # Read multizone geogrid
                xtgeo_grid = xtgeo.grid_from_file(result_grid_filename, fformat="roff")
                dims = xtgeo_grid.dimensions

                # Create facies parameter for multizone geogrid
                values = np.zeros(dims, dtype=np.int32)
                zone_names = list(facies_per_zone.keys())
                facies_table = facies_per_zone[zone_names[0]]
                facies_codes = list(facies_table.keys())
                threshold1 = -0.5
                threshold2 = 0.5
                values[continuous_values < threshold1] = facies_codes[0]
                values[
                    (threshold1 <= continuous_values) & (continuous_values < threshold2)
                ] = facies_codes[1]
                values[continuous_values >= threshold2] = facies_codes[2]

                xtgeo_facies_param = xtgeo.GridProperty(
                    ncol=dims[0],
                    nrow=dims[1],
                    nlay=dims[2],
                    name=param_name,
                    discrete=True,
                    codes=facies_table,
                    values=values,
                )

                xtgeo_facies_param.to_file(result_filename_facies, fformat="roff")


def make_test_case_for_grids_and_fields(
    tmp_path: Path,
    config_dict: dict,
    number_of_realizations_to_remove: int = 0,
    start_seed: int = 123456789,
):
    """
    Makes a test data set based on the input config_dict
    """
    # Copy data directory tree
    tmp_testdata_path = tmp_path / TESTDATA
    shutil.copytree(DATADIR, tmp_testdata_path)

    ens_path = tmp_testdata_path / ENSEMBLE
    ert_config_path = tmp_testdata_path / ERT_CONFIG_PATH
    result_path = ens_path / RESULT_PATH

    glob_cfg_path = ert_config_path / GLOBAL_VARIABLES_FILE
    cfg_global = utils.yaml_load(glob_cfg_path)["global"]
    keyword = "FACIES_ZONE"
    facies_per_zone = cfg_global.get(keyword, None)
    (
        use_geogrid_fields,
        use_temporary_fields,
        nreal,
        iter_list,
        _use_population_stdev,
        relative_ertbox_path,
        ertbox_per_zone,
        ertbox_default,
        _zone_code_names,
        geo_zone_names_used,
        _geo_zone_conformity,
        geo_facies_per_zone,
        geo_geogrid_name,
        geo_param_name_dict,
        geo_disc_param_name_dict,
        __loader__field_init_path,
        field_param_per_zone_dict,
    ) = get_specifications(config_dict)

    if geo_facies_per_zone:
        facies_per_zone = geo_facies_per_zone

    ertbox_config_path = ert_config_path / Path(relative_ertbox_path)

    # Grid cell size
    dx = 50.0
    dy = 50.0
    dz = 1.0
    grid_increments = (dx, dy, dz)
    ertbox_size_per_zone_dict = {"A": (5, 6, 10), "B": (5, 6, 5), "C": (5, 6, 15)}
    ertbox_size_default = (5, 6, 5)

    # Create ertbox grids
    if ertbox_per_zone:
        for zone_name in geo_zone_names_used:
            dimensions = ertbox_size_per_zone_dict[zone_name]
            grid = xtgeo.create_box_grid(dimensions, increment=grid_increments)
            grid_name = config_dict["ertbox_per_zone"][zone_name]
            filename_roff = ertbox_config_path / Path(grid_name + ".roff")
            filename_egrid = ertbox_config_path / Path(grid_name + ".EGRID")
            grid.to_file(filename_roff, fformat="roff")
            grid.to_file(filename_egrid, fformat="egrid")

    if ertbox_default:
        dimensions = ertbox_size_default
        grid = xtgeo.create_box_grid(dimensions, increment=grid_increments)
        grid_name = config_dict["ertbox_default"]
        filename_roff = ertbox_config_path / Path(grid_name + ".roff")
        filename_egrid = ertbox_config_path / Path(grid_name + ".EGRID")
        grid.to_file(filename_roff, fformat="roff")
        grid.to_file(filename_egrid, fformat="egrid")

    if use_geogrid_fields:
        # Make geogrid_field test case
        # Simulate realizations and save to directory where
        # usually rms output realizations for geogrid is saved:
        # ensemble_path/realizations-*/iter-*/share/results/grids

        # Directory path to save ertbox grids under 'config path'
        ertbox_config_path = Path(ert_config_path) / Path(relative_ertbox_path)

        # Simulate realizations and save to directory where
        # usually rms output realizations for geogrid is saved:
        # ensemble_path/realizations-*/iter-*/share/results/grids
        if geo_param_name_dict:
            param_name_list = simulate_continuous_ensemble_test_data(
                ens_path,
                nreal,
                iter_list,
                geo_geogrid_name,
                ertbox_size_per_zone_dict,
                grid_increments,
                geo_param_name_dict,
                start_seed,
                make_test_data_for_geogrid=True,
            )

        # Create discrete parameters for multizone geogrid
        # Save to ensemble_path/realizations-*/iter-*/share/results/grids
        if geo_disc_param_name_dict and geo_param_name_dict:
            # Use param_name_list[0] simulated above as input
            # to be truncated to get facies
            define_discrete_test_data(
                ens_path,
                nreal,
                iter_list,
                geo_geogrid_name,
                geo_disc_param_name_dict,
                param_name_list[0],
                facies_per_zone,
            )

    if use_temporary_fields:
        # Create test data for field parameters
        # where rms usually save initial field parameters in ertbox grids:
        # ensemble_path/realizations-*/iter-*/rms/output/aps
        simulate_continuous_ensemble_test_data(
            ens_path,
            nreal,
            iter_list,
            geo_geogrid_name,
            ertbox_size_per_zone_dict,
            grid_increments,
            field_param_per_zone_dict,
            start_seed,
            make_test_data_for_geogrid=False,
        )
        remove_some_realizations_from_ensemble(
            ens_path, iter_list[-1], nreal, number_of_realizations_to_remove
        )

    return (
        facies_per_zone,
        ens_path,
        result_path,
        ert_config_path,
        ertbox_size_per_zone_dict,
    )


def compare_field_stat_with_referencedata(
    result_path, reference_file_list, compare_result_stat=True, print_check=False
):
    lines = []
    file_list = result_path / Path("referencedata2") / Path(reference_file_list)
    with open(file_list, encoding="utf-8") as file:
        lines = file.readlines()
    is_ok = []
    nfiles = 34 if compare_result_stat else 12

    ncount = 0
    if print_check:
        print("Compare results from test with reference data:")
    for nameinput in lines:
        name = nameinput.strip()
        words = name.split("_")
        if words[0] in {"mean", "stdev", "prob"}:
            if compare_result_stat:
                fullfilename = result_path / Path("ertbox--" + name)
                reference_filename = (
                    result_path / Path("referencedata2") / Path("ertbox--" + name)
                )
            else:
                fullfilename = result_path / Path(name)
                reference_filename = result_path / Path("referencedata2") / Path(name)

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
    if ncount < nfiles:
        is_success = False
    for i in range(ncount):
        if not is_ok[i]:
            is_success = False
    return is_success


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
    "use_population_stdev": False,
    "relative_path_ertbox_grids": "../../rms/output/aps",
    "ertbox_per_zone": {
        "A": "ertbox_A",
        "B": "ertbox_B",
        "C": "ertbox_C",
    },
    "ertbox_default": "ERTBOX",
    "zone_code_names": {
        1: "A",
        2: "B",
        3: "C",
    },
    "geogrid_fields": {
        "geogrid_name": "geogrid",
        "use_zones": ["A", "B", "C"],
        "facies_per_zone": {
            "A": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
            "B": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
            "C": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
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
    },
    "temporary_ertbox_fields": {
        "initial_field_relative_path": "rms/output/aps",
        "parameter_name_per_zone": {
            "A": ["A_GRF1", "A_GRF2"],
            "B": ["B_GRF2"],
        },
    },
}

CONFIG_A = {
    "nreal": 10,
    "iterations": [0],
    "relative_path_ertbox_grids": "../../rms/output/aps",
    "ertbox_default": "ERTBOX",
    "ertbox_per_zone": {
        "A": "ertbox_A",
        "B": "ertbox_B",
        "C": "ertbox_C",
    },
    "zone_code_names": {
        1: "A",
        2: "B",
    },
    "geogrid_fields": {
        "geogrid_name": "geogrid",
        "zone_conformity": {
            "A": "Base_conform",
            "B": "Top_conform",
        },
        "facies_per_zone": {
            "A": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
            "B": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
        },
        "discrete_property_param_per_zone": {
            "A": ["facies"],
        },
        "continuous_property_param_per_zone": {
            "A": ["P1", "P2"],
            "B": ["P1"],
        },
    },
}

CONFIG_A_REF = {
    "nreal": 10,
    "iterations": [0],
    "use_population_stdev": False,
    "relative_path_ertbox_grids": "../../rms/output/aps",
    "ertbox_default": "ERTBOX",
    "ertbox_per_zone": {
        "A": "ertbox_A",
        "B": "ertbox_B",
        "C": "ertbox_C",
    },
    "zone_code_names": {
        1: "A",
        2: "B",
    },
    "geogrid_fields": {
        "geogrid_name": "geogrid",
        "facies_per_zone": {
            "A": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
            "B": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
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
        "use_zones": ["A", "B"],
    },
}

CONFIG_B = {
    "nreal": 10,
    "iterations": [0],
    "use_population_stdev": True,
    "relative_path_ertbox_grids": "../../rms/output/aps",
    "ertbox_default": "ERTBOX",
    "ertbox_per_zone": {
        "A": "ertbox_A",
        "B": "ertbox_B",
        "C": "ertbox_C",
    },
    "zone_code_names": {
        1: "A",
        2: "B",
        3: "C",
        4: "D",
    },
    "geogrid_fields": {
        "geogrid_name": "geogrid",
        "facies_per_zone": {
            "A": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
            "B": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
            "C": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
            "D": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
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
}

CONFIG_B_REF = {
    "nreal": 10,
    "iterations": [0],
    "use_population_stdev": True,
    "relative_path_ertbox_grids": "../../rms/output/aps",
    "ertbox_default": "ERTBOX",
    "ertbox_per_zone": {
        "A": "ertbox_A",
        "B": "ertbox_B",
        "C": "ertbox_C",
    },
    "zone_code_names": {
        1: "A",
        2: "B",
        3: "C",
        4: "D",
    },
    "geogrid_fields": {
        "geogrid_name": "geogrid",
        "facies_per_zone": {
            "A": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
            "B": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
            "C": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
            "D": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
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
}

CONFIG_C = {
    "nreal": 10,
    "iterations": [0],
    "use_population_stdev": True,
    "relative_path_ertbox_grids": "../../rms/output/aps",
    "ertbox_default": "ERTBOX",
    "zone_code_names": {
        1: "A",
        2: "B",
        3: "C",
        4: "D",
    },
    "geogrid_fields": {
        "geogrid_name": "geogrid",
        "facies_per_zone": {
            "A": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
            "B": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
            "C": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
            "D": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
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
        "continuous_property_param_per_zone": {
            "A": ["GRF1"],
        },
    },
}

CONFIG_C_REF = {
    "nreal": 10,
    "iterations": [0],
    "use_population_stdev": True,
    "relative_path_ertbox_grids": "../../rms/output/aps",
    "ertbox_default": "ERTBOX",
    "zone_code_names": {
        1: "A",
        2: "B",
        3: "C",
        4: "D",
    },
    "geogrid_fields": {
        "geogrid_name": "geogrid",
        "use_zones": ["A", "B", "C", "D"],
        "facies_per_zone": {
            "A": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
            "B": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
            "C": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
            "D": {
                1: "F1",
                2: "F2",
                3: "F3",
            },
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
        "continuous_property_param_per_zone": {
            "A": ["GRF1"],
        },
    },
}


@pytest.mark.parametrize(
    "input_dict, reference_dict",
    [
        (CONFIG_DICT, CONFIG_DICT_REF),
        (CONFIG_A, CONFIG_A_REF),
        (CONFIG_B, CONFIG_B_REF),
        (CONFIG_C, CONFIG_C_REF),
    ],
)
def test_get_specification(
    input_dict,
    reference_dict,
):
    (
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
    ) = get_specifications(
        input_dict,
    )

    # Global keywords
    assert nreal == reference_dict["nreal"]
    assert iter_list == reference_dict["iterations"]
    assert use_population_stdev == reference_dict["use_population_stdev"]
    assert relative_path_ertbox_grids == reference_dict["relative_path_ertbox_grids"]
    if "ertbox_per_zone" in reference_dict:
        assert ertbox_per_zone == reference_dict["ertbox_per_zone"]
    if "ertbox_default" in reference_dict:
        assert ertbox_default == reference_dict["ertbox_default"]
    assert zone_code_names == reference_dict["zone_code_names"]

    if "geogrid_fields" in input_dict:
        # Sub keywords for geogrid_fields
        assert use_geogrid_fields
        assert geo_geogrid_name == reference_dict["geogrid_fields"]["geogrid_name"]
        if "use_zones" in reference_dict["geogrid_fields"]:
            assert geo_zone_names_used == reference_dict["geogrid_fields"]["use_zones"]
        if "facies_per_zone" in reference_dict["geogrid_fields"]:
            assert (
                geo_facies_per_zone
                == reference_dict["geogrid_fields"]["facies_per_zone"]
            )
        assert (
            geo_zone_conformity == reference_dict["geogrid_fields"]["zone_conformity"]
        )
        if "discrete_property_param_per_zone" in reference_dict["geogrid_fields"]:
            assert (
                geo_disc_param_name_dict
                == reference_dict["geogrid_fields"]["discrete_property_param_per_zone"]
            )
        if "continuous_property_param_per_zone" in reference_dict["geogrid_fields"]:
            assert (
                geo_param_name_dict
                == reference_dict["geogrid_fields"][
                    "continuous_property_param_per_zone"
                ]
            )

    # Sub keywords for temporary_ertbox_fields
    if "temporary_ertbox_fields" in input_dict:
        assert use_temporary_fields
        assert (
            field_init_path
            == reference_dict["temporary_ertbox_fields"]["initial_field_relative_path"]
        )
        assert (
            field_param_per_zone_dict
            == reference_dict["temporary_ertbox_fields"]["parameter_name_per_zone"]
        )


@pytest.mark.parametrize(
    "config_dict, nreal, nreal_lost",
    [
        (CONFIG_DICT, 10, 0),
        (CONFIG_DICT, 10, 2),
        (CONFIG_DICT, 10, 8),
    ],
)
def test_compare_mean_stdev_of_ensembles_version_2(
    tmp_path, config_dict, nreal, nreal_lost
):
    field_name = "A_GRF1"
    # simulate_ensembles(nreal, nx, ny, nz, nreal_lost, tmp_path, field_name)
    assert (nreal - nreal_lost) >= 2
    _facies_per_zone, ens_path, result_path, ert_config_path, _ = (
        make_test_case_for_grids_and_fields(
            tmp_path, config_dict, number_of_realizations_to_remove=nreal_lost
        )
    )

    calc_temporary_field_stats(config_dict, ens_path, result_path, ert_config_path)
    compare_ensemble_stats(result_path, field_name)


def compare_ensemble_stats(result_path, field_name, tolerance=1e-8):
    mean_file_name1 = Path(result_path) / Path("mean_" + field_name + "_0.roff")
    mean_file_name2 = Path(result_path) / Path("mean_" + field_name + "_3.roff")
    xtgeo_mean1_field = xtgeo.gridproperty_from_file(mean_file_name1, fformat="roff")
    xtgeo_mean2_field = xtgeo.gridproperty_from_file(mean_file_name2, fformat="roff")
    diff_values = np.abs(xtgeo_mean1_field.values - xtgeo_mean2_field.values)
    assert np.all(diff_values < tolerance)

    sdev_file_name1 = Path(result_path) / Path("stdev_" + field_name + "_0.roff")
    sdev_file_name2 = Path(result_path) / Path("stdev_" + field_name + "_3.roff")
    xtgeo_sdev1_field = xtgeo.gridproperty_from_file(sdev_file_name1, fformat="roff")
    xtgeo_sdev2_field = xtgeo.gridproperty_from_file(sdev_file_name2, fformat="roff")
    diff_values = np.abs(xtgeo_sdev1_field.values - xtgeo_sdev2_field.values)
    assert np.all(diff_values < tolerance)


@pytest.fixture
def configuration():
    return CONFIG_DICT


@pytest.fixture
def generated_test_data(tmp_path, configuration):
    """Fixture to generate test data for geogrid fields."""
    config_dict = configuration
    return make_test_case_for_grids_and_fields(tmp_path, config_dict)


def test_calc_geogrid_field_stats(generated_test_data, configuration):
    # Run the calculations of mean, stdev, prob
    print(
        "\nCalculate statistics for geogrid parameters "
        "but per zone in ertbox for the zone"
    )

    facies_per_zone, ens_path, result_path, ert_config_path, _ = generated_test_data
    config_dict = configuration
    calc_stats(config_dict, ens_path, facies_per_zone, result_path, ert_config_path)

    # Check that the result is equal to reference data set
    reference_file_list = "result_field_files.txt"
    assert compare_field_stat_with_referencedata(
        result_path, reference_file_list, compare_result_stat=True, print_check=True
    )


def test_calc_temporary_field_stats(generated_test_data, configuration):
    # Create testdata for an ensemble to be used
    print(
        "\nMake test data for fields for ertbox grids:\n"
        "      realization-*/iter-0/rms/output/aps/<field_name>.roff\n"
        "      realization-*/iter-3/<field_name>.roff"
    )
    _, ens_path, result_path, ert_config_path, _ = generated_test_data
    config_dict = configuration
    # Run the calculations of mean, stdev, prob
    print("Calculate statistics for temporary ertbox grid parameters")
    calc_temporary_field_stats(config_dict, ens_path, result_path, ert_config_path)

    # Check that the result is equal to reference data set
    reference_file_list = "temporary_field_files.txt"
    assert compare_field_stat_with_referencedata(
        result_path, reference_file_list, compare_result_stat=False, print_check=True
    )


def test_main(generated_test_data):
    (
        _facies_per_zone,
        ens_path,
        result_path,
        ert_config_path,
        _ertbox_size_per_zone_dict,
    ) = generated_test_data

    tmp_testdata_path = ens_path.parent
    config_path = tmp_testdata_path / Path("config_example.yml")
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
        ],
        check=True,
    )

    # Verify field statistics results
    assert compare_field_stat_with_referencedata(
        result_path,
        "result_field_files.txt",
        compare_result_stat=True,
        print_check=True,
    )
    assert compare_field_stat_with_referencedata(
        result_path,
        "temporary_field_files.txt",
        compare_result_stat=False,
        print_check=True,
    )
