"""Read contents from simple text files"""
import logging
import re
import warnings
from datetime import datetime
from pathlib import PosixPath
from typing import List, Optional, Tuple, Union

from subscript.fmuobs.util import ERT_DATE_FORMAT, ERT_ISO_DATE_FORMAT

LOGGER = logging.getLogger("gen_obs_writers")


def try_converting_to_date(string):
    """Test if string can be converted to string

    Args:
        string (str): the string to be checked

    Returns:
        bool: true if it can be converted
    """
    valid_formats = ["%d-%m-%Y", ERT_ISO_DATE_FORMAT, ERT_DATE_FORMAT, ERT_DATE_FORMAT]
    for valid_format in valid_formats:
        try:
            string = datetime.strftime(
                datetime.strptime(string, valid_format), "%Y-%m-%d"
            )
            break
        except ValueError:
            LOGGER.debug("%s is not in format %s", string, valid_format)

    return string


def convert(element):
    """Convert string to number when possible

    Args:
        element (str): to be converted

    Returns:
        (str|float|int): the (possibly) converted str
    """
    num_pattern = re.compile(r"^(-)?[\d]+(\.[\d]+)?(e(\+|-)\d+)?$")
    int_pattern = re.compile(r"^[\d]+(\.[0]+)?$")
    if num_pattern.match(element):
        if int_pattern.match(element):
            element = int(float(element))
        else:
            element = float(element)
    else:
        element = try_converting_to_date(element)

    return element


def ensure_correct_well_info_format(info):
    """Ensure that list with dates is shrunk to three entries

    Args:
        info (list): the list to keep or shrink

    Raises:
        ValueError: if list does not have either 5 or three entries

    Returns:
        list: list with date as middle entry
    """
    LOGGER.debug("Checking list %s", info)
    if len(info) == 5:
        info = [info[0], "-".join(info[1:-1]), info[-1]]
    elif len(info) != 3:
        raise ValueError("list needs to have 5 or 3 in length")
    return info


def find_well_file_path(folder_path: PosixPath) -> Optional[PosixPath]:
    """Find file with well information in folder

    Args:
        folder_path (PosixPath): the path to search

    Returns:
        pd.DataFrame: the digested results
    """
    well_file_pattern = re.compile(r"well.*rft.*\.txt", re.IGNORECASE)
    potential_candidates = list(folder_path.glob("*.*"))
    found = []
    for candidate in potential_candidates:
        # LOGGER.debug(candidate)
        if well_file_pattern.match(candidate.name):
            found.append(candidate)
    if len(found) > 1:
        warnings.warn(f"Oh no! More than one candidate {found}, picking the first")
    try:
        the_one = found[0]
    except IndexError:
        warnings.warn(f"Code looking for well file in {folder_path}, found None")
        the_one = None

    return the_one


def find_well_file_info(folder_path: PosixPath):
    """Find file with well information in folder

    Args:
        folder_path (PosixPath): the path to search

    Returns:
        pd.DataFrame: the digested results
    """
    well_info = None
    well_file_path = find_well_file_path(folder_path)
    if well_file_path is not None:
        well_info = dump_content_to_dict(
            well_file_path, ["well_name", "date", "restart_number"]
        )

    LOGGER.debug("Returning %s", well_info)
    return well_info


def extract_wells_and_dates(obs_parent):
    """Extract additional well info

    Args:
        obs_parent (PosixPath): parent folder, in case relative path

    Returns:
        list: contains list that are the lines extracted
    """

    well_info = {}
    try:
        well_info = find_well_file_info(obs_parent)
    except FileNotFoundError:
        warnings.warn("No file to read", UserWarning)
    return well_info


def add_extra_well_data_if_rft(dict_to_change: dict, parent_dir, obs_folders):
    """Add information about well name and date if keys with rft exists in dict

    Args:
        dict_to_change (dict): the dictionary up for potential modifications
        parent_dir (PosixPath): folder path to look for file with relevant information
    """
    rft_keys = [key for key in dict_to_change.keys() if "rft" in key]
    if len(rft_keys) > 0:
        for rft_key in rft_keys:
            names_and_dates = extract_wells_and_dates(parent_dir / obs_folders[rft_key])
            if len(names_and_dates) > 0:
                well_names = names_and_dates["well_name"]
                restarts = names_and_dates["restart_number"]
                print(names_and_dates)
                for obs_key, obs_dict in dict_to_change[rft_key].items():
                    print(obs_dict["restart"])
                    well_pattern = re.compile(
                        ".*" + re.sub(r"(RFT_|_OBS)", "", obs_key) + ".*"
                    )
                    potential_lines = [
                        i
                        for i in range(len(well_names))
                        if (
                            well_pattern.match(well_names[i])
                            and restarts[i] == obs_dict["restart"]
                        )
                    ]
                    try:
                        right_index = potential_lines.pop()
                    except IndexError as ind_err:
                        raise IndexError(
                            f"After using match pattern {well_pattern.pattern}"
                            + " no matches where found"
                        ) from ind_err
                    obs_dict["well_name"] = well_names[right_index]
                    obs_dict["date"] = names_and_dates["date"][right_index]
    print("After modification dict is ", dict_to_change)


def attach_spatial_data_if_exists(file_path: PosixPath, primary_content: dict):
    """Attach data from secondary file if it exists

    Args:
        file_path (PosixPath): path to primary file

    Returns:
        dict: results from reading the secondary file
    """
    LOGGER.debug("Checking if %s has twin", str(file_path))
    spatial_content = {}
    if file_path.suffix == ".obs":
        well_file_path = file_path.parent / re.sub(
            r"_\d+\.obs$", r".obs", file_path.name
        ).replace(file_path.suffix, ".txt")

        if well_file_path.exists():
            LOGGER.debug("Yup")
            spatial_content = dump_content_to_dict(
                well_file_path, ["X", "Y", "Z", "MD", "Zone"]
            )
            LOGGER.debug("Extracted %s", spatial_content)
        else:
            LOGGER.debug("Nope")
    primary_content.update(spatial_content)


def dump_content_to_dict(
    file_path: PosixPath,
    col_names: Union[List, Tuple] = ("observations", "error"),
) -> dict:
    """Read contents of file into list

    Args:
        file_path (str): path to file

    Returns:
        list: contents of file as list
    """
    content = file_path.read_text(encoding="utf-8")
    content_dict = {}
    LOGGER.debug("Connecting contents of file %s with names %s", file_path, col_names)
    for line in content.splitlines():
        LOGGER.debug(line)
        split_line = line.rstrip().split()
        if col_names[0] == "well_name":
            split_line = ensure_correct_well_info_format(split_line)

        LOGGER.debug(split_line)
        for i, element in enumerate(split_line):
            col_name = col_names[i]
            if col_name not in content_dict:
                content_dict[col_name] = [convert(element)]
            else:
                content_dict[col_name].append(convert(element))
    attach_spatial_data_if_exists(file_path, content_dict)

    return content_dict


def tidy_general_obs_keys(generals):
    """Convert keys in dict to something like standard names, when possible

    Args:
        generals (dict): the dict up for modification
    """
    white_list = ["rft", "tracer", "seismic"]
    general_keys = list(generals.keys())
    conversions = {
        general_key: correct_key
        for general_key in general_keys
        for correct_key in white_list
        if correct_key in general_key
    }
    rouges = set(conversions.keys()).symmetric_difference(general_keys)
    if len(rouges) > 0:
        warnings.warn(
            f"Some keys not recognized ({rouges}) as standards, but kept as is"
        )
        LOGGER.debug("Have tidied, results are %s", generals)
    for convertable_key, correct_key in conversions.items():
        generals[correct_key] = generals[convertable_key].copy()
        if correct_key != convertable_key:
            del generals[convertable_key]
