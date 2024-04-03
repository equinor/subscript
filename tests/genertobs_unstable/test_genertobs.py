import os
import pytest
import pandas as pd
import yaml
from subscript.genertobs_unstable import _config as conf


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


def test_extract_general(drogon_project):
    results = conf.extract_general(
        conf.read_tabular_file(
            drogon_project / "ert/input/observations/drogon_seismic_input.csv"
        ),
        lable_name="tut",
    )
    print(results)
    assert_dataframe(results)


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
