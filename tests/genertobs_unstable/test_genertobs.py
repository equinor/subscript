import pytest
import pandas as pd
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
    "line_input",
    [
        ["summary observations", "summary", "drogon_summary_input.txt", "no", "10.00%"],
        ["rft pressure observations", "rft", "drogon_rft_input.ods", "yes", "5"],
    ],
)
def test_extract_from_row(line_input, drogon_project):
    """Test function extract_from_row

    Args:
        line_input (pd.Series): a row to test
        drogon_project (PosixPath): parent folder for files to be read
    """
    summary_row = pd.Series(
        line_input, index=["name", "content", "input_file", "label", "active" "error"]
    )
    obs, to_fmuobs = conf.extract_from_row(
        summary_row, drogon_project / "ert/input/observations"
    )
    print("\nObservations: \n", obs)
    print("\nTo fmuobs: \n", to_fmuobs)


def test_read_config_file(csv_config):
    """Test reading of config file

    Args:
        csv_config (PosixPath): path to config file
    """
    to_fmuobs, observation_data = conf.read_config_file(csv_config)
    print(to_fmuobs)
    print(observation_data)
