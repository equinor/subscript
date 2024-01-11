import re
from pathlib import Path
from subscript.fmuobs import gen_obs_writers
import pytest

TEST_DATA = "testdata_fmuobs"


@pytest.mark.parametrize("string", ["16/07/72", "16-07-1972", "1972-07-16"])
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
    "folder_path, num_entries",
    [
        ("drogon/rft/", 5),
        ("somewhere/completely/different/rft_ERT_use_MDadjusted/", 159),
    ],
)
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


@pytest.mark.parametrize(
    "folder_path",
    [
        "drogon/rft/",
        "somewhere/completely/different/rft_ERT_use_MDadjusted/",
    ],
)
def test_extract_wells_and_dates(folder_path):
    """Test function extract_wells_and_dates

    Args:
        folder_path (str): path to folder with potential well file
    """
    found = gen_obs_writers.extract_wells_and_dates(folder_path)
    assert found is not None  # , f"Didn't find anything in {folder_path}"


# def test_add_extra_well_data_if_rft(dict_to_change: dict, parent_dir):
# def test_attach_spatial_data_if_exists(file_path: PosixPath, primary_content: dict) -> dict:
# def test_dump_content_to_dict(
