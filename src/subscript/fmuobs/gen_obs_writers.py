"""Read contents from simple text files"""
import logging
import warnings
import re
from datetime import datetime
from pathlib import Path, PosixPath

LOGGER = logging.getLogger("general_readers")


def try_converting_to_date(string):
    """Test if string can be converted to string

    Args:
        string (str): the string to be checked

    Returns:
        bool: true if it can be converted
    """
    valid_formats = ["%d-%m-%Y", "%Y-%m-%d"]
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


def find_well_file_info(folder_path: PosixPath):
    """Find file with well information in folder

    Args:
        folder_path (PosixPath): the path to search

    Returns:
        pd.DataFrame: the digested results
    """
    well_file_pattern = re.compile(r"well.*rft.*\.txt", re.IGNORECASE)
    the_one = None
    well_info = None
    potential_candidates = list(folder_path.glob("*.*"))
    for candidate in potential_candidates:
        # LOGGER.debug(candidate)
        if well_file_pattern.match(candidate.name):
            the_one = candidate
    # LOGGER.debug(the_one)
    if the_one is not None:
        well_info = dump_content_to_dict(
            the_one, ["well_name", "date", "restart_number"]
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


def add_extra_well_data_if_rft(dict_to_change: dict, parent_dir):
    """Add information about well name and date if keys with rft exists in dict

    Args:
        dict_to_change (dict): the dictionary up for potential modifications
        parent_dir (PosixPath): folder path to look for file with relevant information
    """
    rft_keys = [key for key in dict_to_change.keys() if "rft" in key]
    if len(rft_keys) > 0:
        for rft_key in rft_keys:
            names_and_dates = extract_wells_and_dates(parent_dir / rft_key)
            if len(names_and_dates) > 0:
                well_names = names_and_dates["well_name"]
                restarts = names_and_dates["restart_number"]
                print(names_and_dates)
                for obs_key, obs_dict in dict_to_change[rft_key].items():
                    print(obs_dict["restart"])
                    well_pattern = re.compile(".*" + obs_key.replace("_OBS", "") + ".*")
                    potential_lines = [
                        i
                        for i in range(len(well_names))
                        if (
                            well_pattern.match(well_names[i])
                            and restarts[i] == obs_dict["restart"]
                        )
                    ]
                    right_index = potential_lines.pop()
                    obs_dict["well_name"] = well_names[right_index]
                    obs_dict["date"] = names_and_dates["date"][right_index]
    print("After modification dict is ", dict_to_change)


def attach_spatial_data_if_exists(file_path: PosixPath, primary_content: dict) -> dict:
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
    file_path: PosixPath, col_names: list = ("observations", "error")
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
