import logging
import re
import pandas as pd
from pathlib import Path, PosixPath
from shutil import rmtree
from fmu.dataio import ExportData


def write_timeseries_ertobs(obs_dict: dict):
    """Make ertobs string to from dictionary

    Args:
        obs_dict (dict): the dictionary to extract from

    Returns:
        str: string to write into ertobs file
    """
    logger = logging.getLogger(__name__ + ".write_timeseries_ertobs")
    logger.debug("%s observations to write", obs_dict)
    obs_frames = []
    for element in obs_dict:
        key = element["vector"]
        logger.debug(key)
        obs_frame = element["data"]
        obs_frame["class"] = "SUMMARY_OBSERVATION"
        obs_frame["key"] = key + ";};"
        order = ["class", "label", "value", "error", "date", "key"]
        obs_frame = obs_frame[order]
        obs_frame["value"] = "{VALUE=" + obs_frame["value"].astype(str) + ";"
        obs_frame["error"] = "ERROR=" + obs_frame["error"].astype(str) + ";"
        obs_frame["date"] = "DATE=" + obs_frame["date"].astype(str) + ";"
        obs_frames.append(obs_frame)
    obs_frames = pd.concat(obs_frames)
    obs_str = re.sub(r" +", " ", obs_frames.to_string(header=False, index=False)) + "\n"
    logger.info("Returning %s", obs_str)
    return obs_str


def select_from_dict(keys: list, full_dict: dict):
    """Select some keys from a bigger dictionary

    Args:
        keys (list): the keys to select
        full_dict (dict): the dictionary to extract from

    Returns:
        dict: the subselection of dict
    """
    return {key: full_dict[key] for key in keys}


def create_rft_ertobs_str(well_name: str, restart: int, obs_file: PosixPath) -> str:
    """Create the rft ertobs string for specific well

    Args:
        well_name (str): well name
        restart (str): restart number
        obs_file (str): name file with corresponding well observations

    Returns:
        str: the string
    """
    return (
        f"GENERAL_OBSERVATION {well_name}_OBS "
        + "{"
        + f"DATA={well_name}_SIM ;"
        + f" RESTART = {restart}; "
        + f"OBS_FILE = {obs_file.name}"
        + ";};\n"
    )


def create_rft_gendata_str(well_name: str, restart: int) -> str:
    """Create the string to write as gendata call

    Args:
        well_name (str): well name
        restart (str): restart number

    Returns:
        str: the string
    """
    return (
        f"GEN_DATA {well_name}_SIM "
        + f"RESULT_FILE:RFT_{well_name}_%d "
        + f"REPORT_STEPS:{restart}\n"
    )


def write_genrft_str(
    parent: PosixPath, well_date_path: str, layer_zone_table: str
) -> str:
    """write the string to define the GENDATA_RFT call

    Args:
        parent (str): path where rfts are stored
        well_date_path (str): path where the well, date, and restart number are written
        layer_zone_table (str): path to where the zones and corresponding layers are stored

    Returns:
        str: the string
    """
    string = (
        f"DEFINE RFT_INPUT <CONFIG_PATH>/../input/observations/{parent}/rft\n"
        + "FORWARD_MODEL MAKE_DIRECTORY(<DIRECTORY>=gendata_rft)\n"
        + "FORWARD_MODEL GENDATA_RFT(<PATH_TO_TRAJECTORY_FILES>=<RFT_INPUT>,"
        + f"<WELL_AND_TIME_FILE>=<RFT_INPUT>/{well_date_path}"
        + f"<ZONEMAP>=<RFT_INPUT>/{layer_zone_table}"
        + " <OUTPUTDIRECTORY>=gendata_rft)\n"
    )
    return string


def write_rft_ertobs(rft_dict: dict, parent_folder: PosixPath) -> str:
    """Write all rft files for rft dictionary, pluss info str

    Args:
        rft_dict (dict): the rft information
        parent_folder (str, optional): path to parent folder to write to. Defaults to "".

    Returns:
        str: ertobs strings for rfts
    """
    logger = logging.getLogger(__name__ + ".write_rft_ertobs")
    parent_folder = Path(parent_folder)
    logger.debug("%s observations to write", rft_dict)
    well_date_list = []
    rft_ertobs_str = ""
    gen_data = ""
    try:
        metadata = rft_dict["metadata"]
    except KeyError:
        logger.warning("No metadata for %s", rft_dict["name"])
        metadata = {}
    columns = metadata.get("columns", {"value": {"unit": "bar"}})
    rft_format = columns["value"]["unit"]
    valid_sat_format = ["fraction", "saturation"]
    logger.debug("Rft format is : %s", rft_format)
    if rft_format in valid_sat_format:
        prefix = "saturation"
    else:
        prefix = "pressure"

    logger.debug("prefix is %s", prefix)
    for element in rft_dict["observations"]:
        well_name = element["well_name"]
        logger.debug(well_name)
        date = element["date"]
        restart = element["restart"]
        obs_file = write_well_rft_files(parent_folder, prefix, element)
        well_date_list.append([well_name, date, restart])
        rft_ertobs_str += create_rft_ertobs_str(well_name, restart, obs_file)
        gen_data += create_rft_gendata_str(well_name, restart)
    well_date_frame = pd.DataFrame(
        well_date_list, columns=["well_name", "date", "restart"]
    )

    well_date_file = parent_folder / "well_date_restart.txt"
    well_date_frame.to_csv(well_date_file, index=False, header=False, sep=" ")
    logger.debug("Written %s", str(well_date_file))
    gen_data_file = parent_folder / "gendata_include.ert"

    gen_data_file.write_text(gen_data)
    logger.debug("Written %s", str(gen_data_file))

    return rft_ertobs_str


def write_well_rft_files(
    parent_folder: PosixPath, prefix: str, element: dict
) -> PosixPath:
    """Write rft files for rft element for one well

    Args:
        parent_folder (str): parent to write all files to
        prefix (str): prefix defining if it is pressure or saturation
        element (dict): the info about the element

    Returns:
        str: ertobs string for well
    """
    logger = logging.getLogger(__name__ + ".write_well_rft_files")
    well_name = element["well_name"]
    obs_file = parent_folder / f"{prefix}_{well_name}.obs"
    position_file = parent_folder / f"{prefix}_{well_name}.txt"
    logger.debug("Writing %s and %s", obs_file, position_file)
    obs_frame = element["data"][["value", "error"]]
    logger.debug("observations\n%s", obs_frame)
    obs_frame.to_csv(obs_file, index=False, header=False, sep=" ")
    position_frame = element["data"][["x", "y", "md", "tvd", "zone"]]
    logger.debug("positions for\n%s", position_frame)
    position_frame.to_csv(position_file, index=False, header=False, sep=" ")
    return obs_file


def write_dict_to_ertobs(obs_list: list, parent: PosixPath) -> str:
    """Write all observation data for ert

    Args:
        obs_list (list): the list of all observations
        parent (str, optional): location to write to. Defaults to "".

    Returns:
        str: parent folder for all written info
    """
    logger = logging.getLogger(__name__ + ".write_dict_to_ertobs")
    logger.debug("%s observations to write", len(obs_list))
    if parent.exists():
        logger.warning("%s exists, deleting and overwriting contents", str(parent))
        rmtree(parent)
    parent.mkdir()
    obs_str = ""
    for obs in obs_list:
        logger.debug(obs)
        content = obs["content"]
        obs_str += f"--\n--{obs['name']}\n"
        if content == "timeseries":
            obs_str += write_timeseries_ertobs(obs["observations"])

        elif content == "rft":
            obs_str += write_rft_ertobs(obs, parent)
        else:
            logger.warning(
                "Currently not supporting other formats than timeseries and rft"
            )
    ertobs_file = parent / "ert_observations.obs"
    ertobs_file.write_text(obs_str)

    return obs_str


def export_with_dataio(data: list, config: dict, case_path: str):
    """Export observations from list of input dicts

    Args:
        data (list): the data stored as dict
        config (dict): config file needed for dataio
        case_path (str): path to where to store
    """
    logger = logging.getLogger(__name__ + ".export_with_dataio")
    logger.debug("Will be exporting from %s", data)
    exporter = ExportData(config=config)
    for data_element in data:
        logger.debug("Exporting element %s", data_element)
        content = data_element["content"]
        for observation in data_element["observations"]:
            try:
                name = observation["vector"].replace(":", "_")
            except KeyError:
                name = observation["well_name"]
            obs_data = observation["data"]
            logger.debug("Observations to export %s", obs_data)
            export_path = exporter.export(
                obs_data,
                name=name,
                tagname=content,
                casepath=case_path,
                fmu_context="preprocessed",
                content=content,
            )
        logger.info("Exporting to %s", export_path)