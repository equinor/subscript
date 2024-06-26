import os
import sys
import pytest
import pandas as pd
import pickle
from pathlib import Path
from datetime import datetime
from shutil import copytree
from subscript.genertobs_unstable import parse_config as conf
from subscript.genertobs_unstable import _utilities as ut
from subscript.genertobs_unstable import _writers as wt
from subscript.genertobs_unstable import main
from subscript.genertobs_unstable._datatypes import (
    ConfigElement,
    ObservationsConfig,
    ObservationType,
    RftConfigElement,
)


VALID_FORMATS = [
    "depth",
    "facies_thickness",
    "fault_lines",
    "field_outline",
    "field_region",
    "fluid_contact",
    "inplace_volumes",
    "khproduct",
    "lift_curves",
    "parameters",
    "pinchout",
    "property",
    "pvt",
    "regions",
    "relperm",
    "rft",
    "seismic",
    "subcrop",
    "thickness",
    "time",
    "timeseries",
    "transmissibilities",
    "velocity",
    "volumes",
    "volumetrics",
    "wellpicks",
]


def assert_list_of_dicts(results):
    assert isinstance(results, list), f"Expected list, got {type(results)} ({results})"
    for i, element in enumerate(results):
        assert isinstance(
            element, dict
        ), f"Expected element to be dict, but is {type(element)} (nr {i})"


def assert_dataframe(results):
    assert isinstance(
        results, pd.DataFrame
    ), f"Expected pd.Dataframe, got {type(results) ({results})}"


@pytest.mark.parametrize("well_name", ["NO 34\4-12 A"])
def test_check_and_fix_str(well_name):
    well_name = ut.check_and_fix_str(well_name)
    print(well_name)


@pytest.mark.parametrize(
    "table_file_name",
    [
        "drogon_rft_input.ods",
        "drogon_seismic_input.csv",
        "drogon_summary_input.txt",
        "config.ods",
        "summary_gor.csv",
        "summary_wwct.csv",
        "summary_wbhp.csv",
    ],
)
def test_read_tabular_file(drogon_project, table_file_name):
    """Test that parsing of all formats splits correctly the columns"""
    table = ut.read_tabular_file(
        drogon_project / "ert/input/observations/" / table_file_name
    )
    assert table.shape[1] > 1, f"{table_file_name} read as only one column"


@pytest.mark.parametrize(
    "frame_err, expected_result",
    zip(
        [
            [frame, error]
            for error in ["10", "10%"]
            for frame in [
                pd.DataFrame({"value": [100, 200]}),
                pd.DataFrame({"value": [100, 200], "error": [None, 40]}),
                pd.DataFrame({"value": [100, 200], "error": [1, 1]}),
                pd.DataFrame({"value": [100]}),
            ]
        ],
        [[10, 10], [10, 40], [1, 1], [10], [10, 20], [10, 40], [1, 1], [10]],
    ),
)
def test_add_or_modify_error(frame_err, expected_result):
    frame, error = frame_err
    print("frame: \n", frame)
    print("error: ", error)
    print("-------------")
    ut.add_or_modify_error(frame, error)
    print("Result: \n", frame)
    print("***********************************  ")
    assert [int(val) for val in frame.error.tolist()] == [
        int(expected) for expected in expected_result
    ]


def test_extract_general(drogon_project):
    results = ut.extract_general(
        ut.read_tabular_file(
            drogon_project / "ert/input/observations/drogon_seismic_input.csv"
        ),
        lable_name="tut",
    )
    print(results)
    assert_dataframe(results)


def test_convert_obs_df_to_list(rft_as_frame):
    print(rft_as_frame)
    results = ut.convert_obs_df_to_list(rft_as_frame, "rft")
    # assert_list_of_dicts(results)


@pytest.mark.parametrize(
    "infile,content,nrlabels",
    [
        ("summary_gor.csv", "summary", 9),
        ("drogon_rft_input.ods", "rft", 2),
        ("drogon_seismic_input.csv", "seismic", 1),
    ],
)
def test_read_obs_frame(drogon_project, infile, content, nrlabels):
    input_file = drogon_project / "ert/input/observations/" / infile
    print(input_file)
    alias_file = None
    results = ut.read_obs_frame(input_file, content, alias_file)
    print(results)
    # len_labels = len(results["label"].unique().tolist())
    # assert len_labels == nrlabels, f"should have {nrlabels}, but has {len_labels}"


@pytest.mark.parametrize(
    "element_nr",
    range(3),
)
def test_extract_from_row(observation_config, drogon_project, element_nr):
    """Test function extract_from_row

    Args:
        line_input (pd.Series): a row to test
        drogon_project (PosixPath): parent folder for files to be read
    """
    # os.chdir(tmp_path)
    element_row = observation_config[element_nr]

    obs = ut.extract_from_row(element_row, drogon_project / "ert/input/observations")
    print(obs)
    # if shape_obs == shape_tofmuobs:
    #     assert obs.equals(to_fmuobs), "dataframes have same shape but aren't equal"
    # assert obs.shape == shape_obs
    # assert to_fmuobs.shape == shape_tofmuobs
    # print("\nObservations: \n", obs)
    # print("\nTo fmuobs: \n", to_fmuobs)
    # for df in (to_fmuobs, obs):
    #     duplex = df.duplicated()
    #     assert duplex.sum() == 0, f"{df.loc[duplex]} are duplicated lines"


@pytest.mark.skip(reason="Reading from csv config is not developed currently")
def test_read_config_file(csv_config):
    """Test reading of config file

    Args:
        csv_config (PosixPath): path to config file
    """
    to_fmuobs, observation_data = conf.read_tabular_config(csv_config)
    print("\nObservations: \n", observation_data)
    print("\nTo fmuobs: \n", to_fmuobs)


def test_read_yaml_config(yaml_config_file, drogon_project, monkeypatch):
    """Test function read_yaml_config"""
    ert_obs = drogon_project / "ert/input/observations"
    monkeypatch.chdir(ert_obs)
    config = conf.read_yaml_config(yaml_config_file)
    configelements = [ConfigElement, ConfigElement, RftConfigElement, RftConfigElement]
    assert isinstance(config, ObservationsConfig)
    for i, element in enumerate(config):
        cnfgelement = configelements[i]
        assert isinstance(
            element, cnfgelement
        ), f"Element {i} should be {cnfgelement}, but is {type(element)}"
    len_config = len(config)
    assert len_config == 4, f"Should be 4 elements, but is {len_config}"
    print("Length of configuration:", len_config)
    # print(config)
    # with open(Path(__file__).parent / "data/config.pkl", "wb") as stream:
    #     pickle.dump(config, stream)


def test_generate_data_from_config(
    observation_config, drogon_project, expected_results
):
    print(observation_config)
    data = conf.generate_data_from_config(
        observation_config, drogon_project / "ert/input/observations"
    )
    # Activate if something in results change
    with open(Path(__file__).parent / "data/pickled_data.pkl", "wb") as stream:
        pickle.dump(data, stream)

    for element in data:
        print("---\n", element["name"], "\n")
        print(element)
        # print("---\n", element["error"], "\n")
        for obs in element["observations"]:
            print(obs["data"])

    # assert_list_of_dicts(data)
    # print("-------------\n", data)
    # print("-------------\n", expected_results, "-------------\n")
    # assert len(data) == len(
    #     expected_results
    # ), f"extracted has {len(data)}, but should be {len(expected_results)}"

    # assert data == expected_results


def test_inactivate_rows():
    frame = pd.DataFrame({"test": [1, 2, 3], "active": [True, False, True]})
    frame = ut.inactivate_rows(frame)
    assert frame.shape == (2, 2)


def test_convert_rft_to_list(rft_as_frame):
    print(rft_as_frame)
    results = ut.convert_rft_to_list(rft_as_frame)
    print(f"Nr of entries {len(results)}")
    print(results)


def test_convert_summary_to_list(summary_as_frame):
    print(summary_as_frame)
    results = ut.convert_summary_to_list(summary_as_frame)
    print(f"Nr of entries {len(results)}")
    print(results)


def test_write_timeseries_ertobs(expected_results):
    ertobs = wt.write_timeseries_ertobs(expected_results[0]["observations"])
    # print(ertobs)


def test_write_rft_ertobs(expected_results, tmp_path):
    ertobs = wt.write_rft_ertobs(expected_results[2], tmp_path)
    print(ertobs)


def test_write_dict_to_ertobs(expected_results, tmp_path, drogon_project):
    tmp_drog = tmp_path / "drog"
    copytree(drogon_project, tmp_drog)
    os.chdir(tmp_drog)

    obs_include = tmp_drog / "ert/input/observations/genertobs"
    obs_include.mkdir(parents=False)
    ertobs = wt.write_dict_to_ertobs(expected_results, obs_include)


def test_main_run(drogon_project, tmp_path, monkeypatch):
    correct_nr = 4
    tmp_drog = tmp_path / "drog"
    copytree(drogon_project, tmp_drog)
    tmp_obs_dir = tmp_drog / "ert/input/observations"
    monkeypatch.chdir(tmp_obs_dir)
    print(tmp_drog)
    genert_config_name = "genertobs_config.yml"
    tmp_observations = tmp_obs_dir / "genertobs_config"
    test_config = tmp_drog / f"ert/input/observations/{genert_config_name}"

    main.run(test_config)
    obs_files = list(tmp_observations.glob("*"))
    assert (
        len(obs_files) == 4
    ), f"Have not generated {correct_nr} elements, but {len(obs_files)}"
    for obs_file in obs_files:
        print(obs_file)
        try:
            obs_text = obs_file.read_text()
            # assert (
            #     "%" not in obs_text
            # ), f"{str(obs_file)} contains percent sign, ({obs_text})"
            assert obs_text.startswith("--")
        except IsADirectoryError:
            print(obs_file)
