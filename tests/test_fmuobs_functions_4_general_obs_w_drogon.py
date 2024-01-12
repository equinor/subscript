"""Test functions with drogon data"""
import pandas as pd
import pytest
from subscript.fmuobs.parsers import ertobs2df
from subscript.fmuobs.writers import general_df2obsdict
from ._common_fmuobs import (
    _find_observation_file,
    _assert_compulsories_are_correct,
    _compare_to_results_in_file,
)


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


@pytest.fixture(name="ert-doc_df")
def _fix_ert_obs():
    """Return path to observation file

    Returns:
        PosixPath: the path to observation file
    """
    all_obs_df = pd.read_csv(_find_observation_file("ert-doc.csv", ""))
    return all_obs_df.set_index("CLASS").loc[["GENERAL_OBSERVATION"]]


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
    "fixture_name",
    ["ert-doc_df", "drogon_tracer_df", "drogon_seismic_df", "drogon_rft_df"],
)
def test_general_df2obsdict(fixture_name, drogon_full_obs_file, request):
    """Test function general_df2obsdict

    Args:
        dataframe (str): name of dataframe fixture
        drogon_full_obs_file (PosixPath): path to file where dataframe will be read from
        request (pytest.fixture): fixture that enable use of fixture in parametrization
    """
    if fixture_name == "ert-doc_df":
        # special fix for ert-doc
        parent_dir = drogon_full_obs_file.parent.parent
        correct_result_file = "ert-doc"
        where = ""
    else:
        parent_dir = drogon_full_obs_file.parent
        correct_result_file = fixture_name
        where = "drogon"
    results = general_df2obsdict(request.getfixturevalue(fixture_name), parent_dir)
    import yaml

    stream = open("res.yml", "w")
    yaml.dump(results, stream)
    stream.close()
    _assert_compulsories_are_correct(results)
    if fixture_name != "ert-doc_df":
        # Comparison with file not done for ert-doc, the ert-doc file is for
        # not just for general_obs
        _compare_to_results_in_file(results, correct_result_file, where)


def test_general_df2obsdict_rft(drogon_full_obs_file, request):
    fixture_name = "drogon_rft_df"
    results = general_df2obsdict(
        request.getfixturevalue(fixture_name), drogon_full_obs_file.parent
    )
    # _assert_compulsories_are_correct(results)

    # _compare_to_results_in_file(results, fixture_name)
