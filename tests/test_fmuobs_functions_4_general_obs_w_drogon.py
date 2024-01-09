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


def _assert_compulsories_are_correct(results):
    """Assert that the compulsory components of general observations are in place

    Args:
        results (dict): results extracted from function general_df2obsdict
    """
    for primary_key, obs_set in results.items():
        assert isinstance(primary_key, str)
        for data_key, obs_dict in obs_set.items():
            assert isinstance(
                data_key, str
            ), f"key {data_key} in {primary_key} is not string"
            for num in ("observations", "error"):
                result_sum = sum(obs_dict[num])
                assert isinstance(
                    result_sum, (float, int)
                ), f"Sum of {num} should be numeric but is {type(result_sum)}"
            assert isinstance(
                obs_dict["data"], str
            ), f"data key is of {obs_dict['data']}, but should be str"


def _compare_number_of_keys(to_be_tested, correct, key):
    """Check that length of two sequences are the same

    Args:
        to_be_tested (sequence): the sequence to be tested
        correct (dict): the dict to compare to
        key (str): name of part to be tested
    """
    correct_data = correct[key]
    try:
        len_of_tested = len(to_be_tested)
        correct_len = len(correct_data)
        assert (
            len_of_tested == correct_len
        ), f"{key} should have {correct_len} entries, but have {len_of_tested}"
    except TypeError:
        correct_type = type(correct_data)
        assert isinstance(
            to_be_tested, correct_type
        ), f"{key} should have type {correct_type}, but is {type(to_be_tested)}"


def _compare_to_results_in_file(obs_dict, name_of_dataset):
    """Compare dictionary to results on disk

    Args:
        obs_dict (dict): dictionary to compare
        name_of_dataset (str): name of file with expected results
    """

    answer = {}
    with open(
        Path(__file__).parent / TEST_DATA / f"{name_of_dataset}.yml",
        "r",
        encoding="utf-8",
    ) as stream:
        answer = yaml.safe_load(stream)
    for primary_key, primary_set in obs_dict.items():
        _compare_number_of_keys(primary_set, answer, primary_key)
        for obs_key, obs_set in primary_set.items():
            _compare_number_of_keys(obs_set, answer[primary_key], obs_key)
            for data_key, data_dict in obs_set.items():
                _compare_number_of_keys(
                    data_dict, answer[primary_key][obs_key], data_key
                )
    assert (
        obs_dict == answer
    ), f"Results of {name_of_dataset} should be {answer}, but are {obs_dict}"


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


# def test_ertobs2df(drogon_full_obs_file):
# input_str = drogon_full_obs_file.read_text()
# print(input_str)
# full_df = ertobs2df(input_str)
# print(full_df)


@pytest.mark.parametrize(
    "fixture_name", ["drogon_tracer_df", "drogon_seismic_df", "drogon_rft_df"]
)
def test_general_df2obsdict(fixture_name, drogon_full_obs_file, request):
    """Test function general_df2obsdict

    Args:
        dataframe (str): name of dataframe fixture
        drogon_full_obs_file (PosixPath): path to file where dataframe will be read from
        request (pytest.fixture): fixture that enable use of fixture in parametrization
    """
    results = general_df2obsdict(
        request.getfixturevalue(fixture_name), drogon_full_obs_file.parent
    )
    # with open(
    #     Path(__file__).parent / TEST_DATA / f"{dataframe}.yml", "w", encoding="utf-8"
    # ) as stream:
    #     yaml.dump(results, stream)
    _assert_compulsories_are_correct(results)

    _compare_to_results_in_file(results, fixture_name)


def test_general_df2obsdict_rft(drogon_full_obs_file, request):
    fixture_name = "drogon_rft_df"
    results = general_df2obsdict(
        request.getfixturevalue(fixture_name), drogon_full_obs_file.parent
    )
    # with open(
    # Path(__file__).parent / TEST_DATA / f"{dataframe}.yml", "w", encoding="utf-8"
    # ) as stream:
    # yaml.dump(results, stream)
    _assert_compulsories_are_correct(results)

    _compare_to_results_in_file(results, fixture_name)
