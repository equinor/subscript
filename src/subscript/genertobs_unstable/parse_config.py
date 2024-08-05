"""Code related to fmobs config stuff"""

import logging
from pathlib import Path
from warnings import warn

import yaml

from subscript.genertobs_unstable._datatypes import ObservationsConfig
from subscript.genertobs_unstable._utilities import extract_from_row

# def read_tabular_config(
#     config_file_name: Union[str, Path], parent_folder: Union[str, PosixPath] = None
# ) -> List[pd.DataFrame]:
#     """Parse config file in csv/excel like format

#     Args:
#         config_file_name (str): path to config file

#     Returns:
#         pd.DataFrame: the config file as dataframe
#     """
#     logger = logging.getLogger(__name__ + ".read_config_file")
#     config = read_tabular_file(config_file_name)
#     logger.debug("Shape of config : %s", config.shape)
#     if parent_folder is None:
#         parent_folder = Path(config_file_name).parent
#     else:
#         parent_folder = Path(parent_folder)

#     obs_data = []

#     for rnr, row in config.iterrows():
#         if row["active"] != "yes":
#             logger.info("row %s is deactivated", rnr)
#             continue

#         row_obs = extract_from_row(row, parent_folder)
#         obs_data.append(row_obs)

#     obs_data = pd.concat(obs_data)
#     return obs_data


def read_yaml_config(config_file_name: Path) -> ObservationsConfig:
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
    return ObservationsConfig.model_validate(config)


def generate_data_from_config(config: ObservationsConfig, parent: Path) -> list:
    """Generate tuple with dict and dataframe from config dict

    Args:
        config (ObservationConfig): the configuration pydantic model
        parent (PosixPath): path of parent folder of file containing dict

    Returns:
        dict: dictionary with observations
    """
    logger = logging.getLogger(__name__ + ".generate_data_from_config")
    logger.debug("Here is config to parse %s", config)
    data = []
    for config_element in config:
        logger.info("Parsing element %s", config_element.name)
        data_element = {
            "config": config_element,
            "data": extract_from_row(config_element, parent),
        }
        data.append(data_element)

    return data
