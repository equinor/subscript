"""Code related to fmobs config stuff"""

import logging
from pathlib import Path, PosixPath
from typing import Union, List
import yaml
import pandas as pd
from fmu.dataio.datastructure.meta.enums import ContentEnum
from subscript.genertobs_unstable._utilities import extract_from_row


def validate_config(config: dict):
    """Validate that content of dictionary is correct

    Args:
        config (dict): the dictionary to check

    Raises:
        KeyError: if key name not in config
        AssertionError: if incorrect keys are used or incorrect type is used
    """
    valids = {"name", "type", "observation"}
    optionals = {"error", "min_error", "max_error", "plugin_arguments", "metadata"}
    for i, element in enumerate(config):
        el_valids = valids.copy()
        try:
            name = element["name"]
        except KeyError as keye:
            raise KeyError(f"Key {'name'} not in obs number {i}") from keye
        common = valids.intersection(element.keys())
        el_type = element["type"]
        assert sorted(common) == sorted(
            valids
        ), f"{name}, does not contain all of {sorted(valids)}, only {sorted(common)}"

        assert hasattr(
            ContentEnum, el_type
        ), f"{el_type} not in {ContentEnum._member_names_}"
        el_valids.update(optionals)
        non_valid = set(element.keys()).difference(el_valids)
        assert (
            len(non_valid) == 0
        ), f"{non_valid} are found in config, these are not allowed"

        try:
            error = str(element["error"])
            if "%" not in error:
                invalids = ["min_error", "max_error"]
                for invalid in invalids:
                    assert (
                        invalid not in element.keys()
                    ), f"Obs {name}: {invalid} should not be used if absolute error used"
        except KeyError:
            logger.debug("No global error added, nothing to check")


def read_tabular_config(
    config_file_name: Union[str, PosixPath], parent_folder: Union[str, PosixPath] = None
) -> List[pd.DataFrame]:
    """Parse config file in csv/excel like format

    Args:
        config_file_name (str): path to config file

    Returns:
        pd.DataFrame: the config file as dataframe
    """
    logger = logging.getLogger(__name__ + ".read_config_file")
    config = read_tabular_file(config_file_name)
    logger.debug("Shape of config : %s", config.shape)
    if parent_folder is None:
        parent_folder = Path(config_file_name).parent
    else:
        parent_folder = Path(parent_folder)

    obs_data = []

    for rnr, row in config.iterrows():
        if row["active"] != "yes":
            logger.info("row %s is deactivated", rnr)
            continue

        row_obs = extract_from_row(row, parent_folder)
        obs_data.append(row_obs)

    obs_data = pd.concat(obs_data)
    return obs_data


def read_yaml_config(config_file_name: str) -> dict:
    """Read configuration from file

    Args:
        config_file_name (str): path to yaml file

    Raises:
        RuntimeError: If something goes wrong

    Returns:
        dict: the configuration as dictionary
    """
    logger = logging.getLogger(__name__ + ".read_yaml_config")

    config = {}
    try:
        with open(config_file_name, "r", encoding="utf-8") as stream:
            config = yaml.safe_load(stream)
    except OSError as ose:
        raise RuntimeError(f"Could not read {config_file_name}") from ose
    logger.debug("Returning %s", config)
    validate_config(config)
    return config


def generate_data_from_config(config: dict, parent: PosixPath) -> tuple:
    """Generate tuple with dict and dataframe from config dict

    Args:
        config (dict): the configuration dictionary
        parent (PosixPath): path of parent folder of file containing dict

    Returns:
        dict: dictionary with observations
    """
    logger = logging.getLogger(__name__ + ".generate_data_from_config")
    logger.debug("Here is config to parse %s", config)
    data = []
    for config_element in config:
        logger.info("Parsing element %s", config_element)
        data_element = {}
        data_element["name"] = config_element["name"]
        data_element["content"] = config_element["type"]
        try:
            data_element["metadata"] = config_element["metadata"]
        except KeyError:
            logger.debug("No metadata for %s", data_element["name"])

        obs = extract_from_row(config_element, parent)
        data_element["observations"] = obs

        logger.debug("These are the observations:\n%s", data_element)
        data.append(data_element)

    return data
