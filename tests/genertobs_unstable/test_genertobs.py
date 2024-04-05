import os
import pytest
import pandas as pd
import yaml
from subscript.genertobs_unstable import _config as conf

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
    table = conf.read_tabular_file(
        drogon_project / "ert/input/observations/" / table_file_name
    )
    assert table.shape[1] > 1, f"{table_file_name} read as only one column"


@pytest.mark.parametrize(
    "frame,error",
    [
        (frame, error)
        for error in ["10", "10%"]
        for frame in [
            pd.DataFrame({"value": [100, 200]}),
            pd.DataFrame({"value": [100, 200], "error": [None, 40]}),
            pd.DataFrame({"value": [100, 200], "error": [1, 1]}),
        ]
    ],
)
def test_add_or_modify_error(frame, error):
    print(frame)
    print(error)
    conf.add_or_modify_error(frame, error)
    print(frame)
    print("-------------")


def test_caps_converters():

    mytest = pd.DataFrame({"banana": [1, 2], "COBlai": [3, 4], "COPPER": [5, 6]})
    caps_results = [name.upper() for name in mytest.columns]
    low_caps_results = [name.lower() for name in mytest.columns]
    assert conf._ensure_up_caps_columns(mytest).columns.tolist() == caps_results
    assert conf._ensure_low_caps_columns(mytest).columns.tolist() == low_caps_results


def test_extract_summary(drogon_project):
    results = conf.extract_summary(
        conf.read_tabular_file(
            drogon_project / "ert/input/observations/summary_gor.csv"
        )
    )
    print(results)
    assert_dataframe(results)
    # assert_list_of_dicts(results)


def test_extract_rft(drogon_project):
    results = conf.extract_rft(
        conf.read_tabular_file(
            drogon_project / "ert/input/observations/drogon_rft_input.ods"
        )
    )
    print(results)
    assert_dataframe(results)
    assert results["output"].unique().size == 2


def test_extract_general(drogon_project):
    results = conf.extract_general(
        conf.read_tabular_file(
            drogon_project / "ert/input/observations/drogon_seismic_input.csv"
        ),
        lable_name="tut",
    )
    print(results)
    assert_dataframe(results)


def test_convert_obs_df_to_dict_dummy_data():
    dummy = pd.DataFrame(
        {
            "well_name": ["A", "B"],
            "value": [1, 2],
            "not": ["wa", "wa"],
            "content": "timeseries",
        }
    )
    results = conf.convert_obs_df_to_dict(dummy)
    # assert_list_of_dicts(results)
    with open("converted.yaml", "w") as stream:
        yaml.safe_dump(results, stream)
    check_string = ""
    with open("converted.yaml", "r") as stream:
        check_string = stream.read()
        assert (
            "&id001" not in check_string
        ), f"goodammit, anchor in produced file ({check_string})"


def test_convert_obs_df_to_dict(rft_as_frame):
    print(rft_as_frame)
    results = conf.convert_obs_df_to_dict(rft_as_frame)
    # assert_list_of_dicts(results)
    with open("converted.yaml", "w") as stream:
        yaml.safe_dump(results, stream)
    for element in results["rft"]:

        print(element)


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
    results = conf.read_obs_frame(input_file, content)
    print(results)
    len_labels = len(results["label"].unique().tolist())
    assert len_labels == nrlabels, f"should have {nrlabels}, but has {len_labels}"


def test_convert_config_to_dict(csv_config):
    """Test function convert_df_to_dict

    Args:
        csv_config (PosixPath): the dataframe to put through function
    """
    required_fields = ["name", "content", "input_file"]
    config_dict = conf.convert_df_to_dict(conf.read_tabular_file(csv_config))
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
            [
                "summary observations",
                "timeseries",
                "summary_gor.csv",
            ],
            (9, 8),
            (9, 8),
        ),
        (
            ["rft pressure observations", "rft", "drogon_rft_input.ods"],
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
    summary_row = pd.Series(line_input, index=["name", "type", "observation"])
    obs, to_fmuobs = conf.extract_from_row(
        summary_row.to_dict(), drogon_project / "ert/input/observations"
    )
    with open("row_results.yaml", "w") as stream:
        yaml.safe_dump(obs, stream)
    print("\n\n", obs)
    print("\n\n", to_fmuobs)
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
    to_fmuobs, observation_data = conf.read_config_file(csv_config)
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


def test_generate_data_from_config(yaml_config, drogon_project):
    ert_path = drogon_project / "ert/model"
    os.chdir(ert_path)
    data, summary_to_fmuobs = conf.generate_data_from_config(
        yaml_config, ert_path  #  / "../input/observations"
    )
    # assert isinstance(data, list), f"Data should be list, but is {type(data)}"
    # assert isinstance(
    #     summary_to_fmuobs, pd.DataFrame
    # ), f"summary should be dataframe but is {type(summary_to_fmuobs)}"
    # print("\n\n", data)
    with open("genertobs_dict.yaml", "w") as stream:
        yaml.safe_dump(data, stream)
