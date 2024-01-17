import pytest
from pandas import DataFrame

from subscript.fmuobs.fmuobs import autoparse_file, df2obsdict

from ._common_fmuobs import _find_observation_file

TEST_DATA = "testdata_fmuobs/"


@pytest.mark.integration
@pytest.mark.parametrize(
    "obs_file",
    ["drogon/drogon_wbhp_rft_wct_gor_tracer_4d_plt.obs", "snorre/all_obs_230310.txt"],
)
def test_from_autoparse_file_to_df2obsdict(obs_file):
    """Test dictionaries produced for drogon and snorre are as expected

    Args:
        obs_file (str): ert observation file
    """
    full_data_path = _find_observation_file(obs_file, "")
    file_type, dataframe = autoparse_file(full_data_path)
    assert file_type == "ert"
    assert isinstance(dataframe, DataFrame)
    result_dict = df2obsdict(dataframe, full_data_path.parent)
    assert isinstance(
        result_dict, dict
    ), f"Results from dfobsdict should be dictionary, but is {type(result_dict)}"
    for primary_key, enclosed_list in result_dict.items():
        assert isinstance(
            enclosed_list, list
        ), f"key {primary_key} from df2obsdict should be list"
        for item_dict in enclosed_list:
            assert isinstance(
                item_dict, dict
            ), f"{item_dict} is expected to be list but is {type(item_dict)}"
    # _compare_to_results_in_file(
    #     result_dict,
    #     Path(__file__).parent
    #     / TEST_DATA
    #     / re.sub(r"\..*", "", obs_file.split("/")[-1]),
    # )
