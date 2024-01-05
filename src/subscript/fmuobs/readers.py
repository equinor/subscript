"""Read contents from simple text files"""
import logging
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
                datetime.strptime(string, valid_format), "%Y-%m-%dT%H:%M:%SZ"
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


def dump_content_to_dict(file_path: PosixPath, col_names: list) -> dict:
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
    return content_dict
