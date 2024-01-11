from pathlib import Path
from subscript.fmuobs.fmuobs import autoparse_file, ertobs2df, df2obsdict
from pandas import DataFrame
import pytest

TEST_DATA = "testdata_fmuobs/"


def _find_observation_file(file_path):
    """Return path to observation file

    Args:
        file_path (str): ert observation file to parse

    Returns:
        PosixPath: the path to observation file
    """
    obs_file_path = Path(__file__).parent / TEST_DATA / file_path
    if not obs_file_path.exists():
        raise FileNotFoundError(f"Cannot find observation file {obs_file_path}")
    return obs_file_path


@pytest.mark.parametrize(
    "obs_file",
    ["drogon/drogon_wbhp_rft_wct_gor_tracer_4d_plt.obs", "snorre/all_obs_230310.txt"],
)
def test_from_autoparse_file_to_df2obsdict(obs_file):
    full_data_path = _find_observation_file(obs_file)
    file_type, dataframe = autoparse_file(full_data_path)
    print("\n", file_type)
    print("-------")
    print(dataframe)
    assert file_type == "ert"
    assert isinstance(dataframe, DataFrame)
    result_dict = df2obsdict(dataframe, full_data_path.parent)
    print(result_dict)
