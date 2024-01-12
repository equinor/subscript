"""Unit tests for gen_obs_writers"""
from pathlib import Path

import pytest

from subscript.fmuobs import gen_obs_writers

TEST_DATA = "testdata_fmuobs"
RFT_FOLDERS = ["drogon/rft/", "somewhere/completely/different/rft_ERT_use_MDadjusted/"]


@pytest.mark.parametrize("string", ["5/09/1985", "05-09-1985", "1985-09-5"])
def test_try_converting_to_date(string):
    """Test function try_converting to date

    Args:
        string (str): string to be converted
    """
    date_string = gen_obs_writers.try_converting_to_date(string)
    print(date_string)
    assert isinstance(date_string, str)
    dateparts = date_string.split("-")
    assert (
        len(dateparts) == 3
    ), f"Not three date parts, but {len(dateparts)}, results are {dateparts}"
    year, month, day = dateparts
    assert year == "1985", f"year is {year}, should be 1985"
    assert month == "09", f"month is {month}, should be 09"
    assert day == "05", f"day is {day}, should be 05"


@pytest.mark.parametrize(
    "element, returned_type",
    [("16/07/72", str), ("banana", str), ("1", int), ("0.732", float)],
)
def test_convert(element, returned_type):
    """Test function convert

    Args:
        element (str): element to be converted
        returned_type (object): the expected object
    """
    converted = gen_obs_writers.convert(element)
    assert isinstance(
        converted, returned_type
    ), f"{element} returned as {type(converted)}, should be {returned_type}"


@pytest.mark.parametrize(
    "folder_path,expected_file_name",
    zip(RFT_FOLDERS, ["well_date_rft.txt", "WELLNAME_AND_RFT_TIME.txt"]),
)
def test_find_well_file_path(folder_path, expected_file_name):
    """Test function find_well_file_path

    Args:
        folder_path (str): path to folder to look
        file_name (str): expected file name
    """
    found_file = gen_obs_writers.find_well_file_path(
        Path(__file__).parent / TEST_DATA / folder_path
    )
    found_name = found_file.name
    assert (
        found_name == expected_file_name
    ), f"File name is {found_name}, should be {expected_file_name}"


@pytest.mark.parametrize("folder_path, num_entries", zip(RFT_FOLDERS, [5, 159]))
def test_find_well_file_info(folder_path, num_entries):
    """Test function find_well_file_info

    Args:
        folder_path (str): path to folder with potential well file
        num_entries (int): expected number of lines to be read from file
    """
    search_folder = Path(__file__).parent / TEST_DATA / folder_path
    assert (
        search_folder.exists()
    )  # , f"{str(search_folder)} does not exist, not possible to run tests"

    result = gen_obs_writers.find_well_file_info(search_folder)
    assert result is not None  # , f"Found nothing inside of {folder_path}"
    assert len(result["date"]) == num_entries


@pytest.mark.parametrize("folder_path", RFT_FOLDERS)
def test_extract_wells_and_dates(folder_path):
    """Test function extract_wells_and_dates

    Args:
        folder_path (str): path to folder with potential well file
    """
    found = gen_obs_writers.extract_wells_and_dates(
        Path(__file__).parent / TEST_DATA / folder_path
    )
    assert found is not None  # , f"Didn't find anything in {folder_path}"


def test_tidy_general_obs_keys():
    """Test function tidy_general_obs_keys"""
    test = {
        "banana_rft": {"banana": "nice"},
        "racoon": {"animal": "stripy"},
        "tracer_jungle": {"Tracing it": "to the moon"},
        "woo": {"wooly": "and furry"},
        "magic_seismic_data": {"big": "cube"},
    }
    original_keys = list(test.keys())
    gen_obs_writers.tidy_general_obs_keys(test)

    for unconvential_name in ["racoon", "woo"]:
        assert unconvential_name in test.keys()

    for standard_name in ["rft", "seismic", "tracer"]:
        assert standard_name in test.keys()

    assert set(original_keys).difference(test.keys()) == {
        "banana_rft",
        "tracer_jungle",
        "magic_seismic_data",
    }
