"""Test functions with drogon data"""
from pathlib import Path
import pandas as pd
import pytest
from subscript.fmuobs.writers import general_df2obsdict


def _find_observation_file(file_path):
    """Return path to observation file

    Args:
        file_path (str): ert observation file to parse

    Returns:
        PosixPath: the path to observation file
    """
    obs_file_path = Path(__file__).parent / file_path
    if not obs_file_path.exists():
        raise FileNotFoundError(f"Cannot find observation file {obs_file_path}")
    return obs_file_path


@pytest.fixture(name="drogon_tracer_obs_file")
def _fix_drogon_tracer_file():
    """Return path to observation file

    Returns:
        PosixPath: the path to observation file
    """
    return _find_observation_file("testdata_fmuobs/drogon/drogon_tracer.obs")


@pytest.fixture(name="drogon_tracer_df")
def _fix_drogon_tracer():
    """Return path to observation file

    Returns:
        PosixPath: the path to observation file
    """
    return pd.read_csv(
        _find_observation_file("testdata_fmuobs/drogon/drogon_tracer.csv")
    )


@pytest.fixture(name="drogon_full_obs_file")
def _fix_drogon_full_file():
    """Return path to observation file

    Returns:
        PosixPath: the path to observation file
    """
    return _find_observation_file(
        "testdata_fmuobs/drogon/drogon_wbhp_rft_wct_gor_tracer_4d_plt.obs"
    )


def test_general_df2obsdict(drogon_tracer_df, drogon_tracer_obs_file):
    """test function general_df2obsdict

    Args:
        drogon_tracer_df (pd.DataFrame): dataframe with tracer line
        drogon_tracer_obs_file (PosixPath): path to ert tracer obs file
    """
    results = general_df2obsdict(drogon_tracer_df, drogon_tracer_obs_file.parent)
    assert isinstance(results, dict), "Function did not return dictionary"
