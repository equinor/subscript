"""Test functions with drogon data"""
from pathlib import Path
import yaml
import pandas as pd
import pytest
from subscript.fmuobs.parsers import ertobs2df
from subscript.fmuobs.writers import general_df2obsdict

TEST_DATA = "testdata_fmuobs/drogon/"


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


@pytest.fixture(name="drogon_tracer_obs_file")
def _fix_drogon_tracer_file():
    """Return path to observation file

    Returns:
        PosixPath: the path to observation file
    """
    return _find_observation_file("drogon_tracer.obs")


@pytest.fixture(name="drogon_tracer_df")
def _fix_drogon_tracer():
    """Return path to observation file

    Returns:
        PosixPath: the path to observation file
    """
    return pd.read_csv(_find_observation_file("drogon_tracer.csv"))


@pytest.fixture(name="drogon_seismic_df")
def _fix_drogon_seismic():
    """Return path to observation file

    Returns:
        PosixPath: the path to observation file
    """
    return pd.read_csv(_find_observation_file("drogon_seismic.csv"))


@pytest.fixture(name="drogon_allgen_df")
def _fix_drogon_allgen():
    """Return path to observation file

    Returns:
        PosixPath: the path to observation file
    """
    return pd.read_csv(_find_observation_file("drogon_allgen.csv"))


@pytest.fixture(name="drogon_rft_df")
def _fix_drogon_rft():
    """Return path to observation file

    Returns:
        PosixPath: the path to observation file
    """
    return pd.read_csv(_find_observation_file("drogon_rft.csv"))


@pytest.fixture(name="drogon_full_obs_file")
def _fix_drogon_full_file():
    """Return path to observation file

    Returns:
        PosixPath: the path to observation file
    """
    return _find_observation_file("drogon_wbhp_rft_wct_gor_tracer_4d_plt.obs")


def test_ertobs2df(drogon_full_obs_file):
    input_str = drogon_full_obs_file.read_text()
    print(input_str)
    full_df = ertobs2df(input_str)
    print(full_df)


@pytest.mark.parametrize("dataframe", ["drogon_tracer_df", "drogon_seismic_df"])
def test_general_df2obsdict(dataframe, drogon_full_obs_file, request):
    """test function general_df2obsdict

    Args:
        drogon_tracer_df (pd.DataFrame): dataframe with tracer line
        drogon_tracer_obs_file (PosixPath): path to ert tracer obs file
    """
    results = general_df2obsdict(
        request.getfixturevalue(dataframe), drogon_full_obs_file.parent
    )

    answer = {
        "observations": [421, 904, 912, 912, 912, 912, 773, 912],
        "error": [30, 30, 30, 30, 30, 30, 30, 30],
        "label": "TRACER_OBS",
        "data": "TRACER_SIM",
        "restart": 1,
    }
    answer = {}
    with open(
        Path(__file__).parent / TEST_DATA / f"{dataframe}.yml", "r", encoding="utf-8"
    ) as stream:
        answer = yaml.safe_load(stream)

    assert isinstance(results, dict), "Function did not return dictionary"
    assert results == answer
    for primary_key, obs_dict in results.items():
        assert isinstance(primary_key, str)
        assert isinstance(
            obs_dict, dict
        ), f"{obs_dict} should be dict, but is {type(obs_dict)}"
        for num in ("observations", "error"):
            res_sum = sum(obs_dict[num])
            assert isinstance(
                res_sum, (float, int)
            ), f"Sum of {num} should be numeric but is {type(res_sum)}"
        for string in ("label", "data"):
            assert isinstance(
                string, str
            ), f"{string} is {type(string)}, but should be str"
        for key, values in obs_dict.items():
            assert (
                values == answer[primary_key][key]
            ), f"{key} not equal to what it should be like"


def test_general_df2obsdict_rft(drogon_allgen_df, drogon_full_obs_file):
    results = general_df2obsdict(drogon_allgen_df, drogon_full_obs_file.parent)
