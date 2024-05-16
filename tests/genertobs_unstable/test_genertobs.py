import os
import sys
import pytest
import pandas as pd
import pickle
import yaml
from pathlib import Path
from shutil import copytree
from subscript.genertobs_unstable import parse_config as conf
from subscript.genertobs_unstable import _utilities as ut
from subscript.genertobs_unstable import _writers as wt
from subscript.genertobs_unstable import main
from subscript.fmuobs.writers import summary_df2obsdict

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
        ("summary_gor.csv", "timeseries", 9),
        ("drogon_rft_input.ods", "rft", 2),
        ("drogon_seismic_input.csv", "seismic", 1),
    ],
)
def test_read_obs_frame(drogon_project, infile, content, nrlabels):
    input_file = drogon_project / "ert/input/observations/" / infile
    results = ut.read_obs_frame(input_file, content)
    print(results)
    # len_labels = len(results["label"].unique().tolist())
    # assert len_labels == nrlabels, f"should have {nrlabels}, but has {len_labels}"


def test_convert_config_to_dict(csv_config):
    """Test function convert_df_to_dict

    Args:
        csv_config (PosixPath): the dataframe to put through function
    """
    required_fields = ["name", "content", "input_file"]
    config_dict = ut.convert_df_to_dict(ut.read_tabular_file(csv_config))
    assert isinstance(
        config_dict, list
    ), f"Should be list but is {type(config_dict)} ({config_dict})"
    for i, element in enumerate(config_dict):
        for key in required_fields:
            assert (
                key in element.keys()
            ), f"{key} not in required fields {required_fields} for line {i}"


@pytest.mark.parametrize(
    "line_input, shape_obs, shape_tofmuobs",
    [
        (
            ["summary observations", "timeseries", "summary_gor.csv", "10%"],
            (9, 8),
            (9, 8),
        ),
        (
            ["rft pressure observations", "rft", "drogon_rft_input.ods", "10"],
            (3, 15),
            (2, 4),
        ),
    ],
)
def test_extract_from_row(
    line_input, shape_obs, shape_tofmuobs, drogon_project, tmp_path
):
    """Test function extract_from_row

    Args:
        line_input (pd.Series): a row to test
        drogon_project (PosixPath): parent folder for files to be read
    """
    os.chdir(tmp_path)
    summary_row = pd.Series(line_input, index=["name", "type", "observation", "error"])
    obs = ut.extract_from_row(
        summary_row.to_dict(), drogon_project / "ert/input/observations"
    )
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


def test_read_yaml_config(yaml_config_file):
    """Test function read_yaml_config"""
    config = conf.read_yaml_config(yaml_config_file)
    assert isinstance(config, list)
    len_config = len(config)
    assert len_config > 0
    print("Length of configuration:", len_config)


@pytest.mark.parametrize(
    "invalid_config,exception,error_mess",
    [
        (
            {"type": "timeseries"},
            KeyError,
            "Key name not in obs number 0",
        ),
        (
            {"name": "banana", "type": "timeseries"},
            AssertionError,
            "banana, does not contain all of ['name', 'observation', 'type'], only ['name', 'type']",
        ),
        (
            {"name": "banana", "type": "banana", "observation": "dummy.csv"},
            AssertionError,
            f"banana not in {VALID_FORMATS}",
        ),
        (
            {
                "name": "banana",
                "type": "rft",
                "observation": "dummy.csv",
                "hulahoop": "kefir",
            },
            AssertionError,
            "{'hulahoop'} are found in config, these are not allowed",
        ),
    ],
)
def test_validate_config_exceptions(invalid_config, exception, error_mess):
    """Test function validate_config"""
    config = [invalid_config]
    with pytest.raises(exception) as exception_info:
        conf.validate_config(config)

    extracted_mess = str(exception_info.value.args[0])
    print(len(extracted_mess))
    print(len(error_mess))
    print(error_mess)
    print(extracted_mess)
    assert extracted_mess == error_mess


def test_generate_data_from_config(yaml_config, drogon_project, expected_results):
    print(yaml_config)
    data = conf.generate_data_from_config(
        yaml_config, drogon_project / "ert/input/observations"
    )
    # Activate if something in results change
    # with open(Path(__file__).parent / "data/pickled_data.pkl", "wb") as stream:
    #     pickle.dump(data, stream)

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


def test_export_with_dataio(expected_results, drogon_project, fmuconfig, tmp_path):
    correct_num = 6
    print(fmuconfig)
    tmp_drog = tmp_path / "drog"
    copytree(drogon_project, tmp_drog)
    os.chdir(tmp_drog)
    export_path = wt.export_with_dataio(expected_results, fmuconfig, tmp_drog)

    files = list(export_path.glob("*.arrow"))
    print(files)
    assert len(files) == correct_num
    metas = list(export_path.glob("*.arrow.yml"))
    assert len(metas) == correct_num

    # assert isinstance(data, list), f"Data should be list, but is {type(data)}"
    # assert isinstance(
    #     summary_to_fmuobs, pd.DataFrame
    # ), f"summary should be dataframe but is {type(summary_to_fmuobs)}"
    # print("\n\n", data)


def test_main_run(drogon_project, tmp_path, masterdata_config):
    tmp_drog = tmp_path / "drog"
    copytree(drogon_project, tmp_drog)
    os.chdir(tmp_drog)
    print(tmp_drog)
    genert_config_name = "genertobs_config.yml"
    tmp_observations = tmp_drog / "ert/input/observations/genertobs"
    test_config = tmp_drog / f"ert/input/observations/{genert_config_name}"

    main.run(test_config, tmp_observations, masterdata_config)
    obs_files = list(tmp_observations.glob("*"))
    assert len(obs_files) == 6, f"Have not generated 12 files, but {len(obs_files)}"
    for obs_file in obs_files:
        print(obs_file)
        obs_text = obs_file.read_text()
        # assert (
        #     "%" not in obs_text
        # ), f"{str(obs_file)} contains percent sign, ({obs_text})"
        assert obs_text.startswith("--")

    sumo_table_location = tmp_drog / "share/preprocessed/tables"
    sumo_tables = list(sumo_table_location.glob("*.csv"))
    assert (
        len(sumo_tables) == 6
    ), f"Have not exported 6 tables for sumo, but {len(sumo_tables)}"


def test_sumo_upload():
    pass
