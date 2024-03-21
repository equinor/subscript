import pytest
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
        csv_config (pandas.DataFrame): the dataframe to put through function
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