"""Code related to fmobs config stuff"""

import logging
from typing import Union, List
from pathlib import Path, PosixPath
import pandas as pd
from fmu.dataio.datastructure.meta.enums import ContentEnum


def _ensure_low_caps_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Make all column names lower case

    Args:
        dataframe (pd.DataFrame): the dataframe to modify

    Returns:
        pd.DataFrame: the modified dataframe
    """
    dataframe.columns = [col.lower() for col in dataframe.columns]
    return dataframe


def read_tabular_file(tabular_file_path: Union[str, PosixPath]) -> pd.DataFrame:
    """Read csv or excel file into pandas dataframe

    Args:
        tabular_file_path (str): path to file

    Returns:
        pd.DataFrame: the dataframe read from file
    """
    logger = logging.getLogger(__name__ + ".read_tabular_file")
    logger.info("Reading file %s", tabular_file_path)
    dataframe = pd.DataFrame()
    try:
        read_info = "csv, with sep ,"
        dataframe = pd.read_csv(tabular_file_path, sep=",", dtype=str)
    except UnicodeDecodeError:
        dataframe = pd.read_excel(tabular_file_path, dtype=str)
        read_info = "excel"
    nr_cols = dataframe.shape[1]
    logger.debug("Nr of columns are %s", nr_cols)
    if nr_cols == 1:
        logger.debug("Wrong number of columns, trying with other separators")
        for separator in [";", " "]:
            logger.debug("Trying with |%s| as separator", separator)
            dataframe = pd.read_csv(tabular_file_path, sep=separator, dtype=str)
            read_info = f"csv with sep {separator}"
            if dataframe.shape[1] > 1:
                break

    logger.debug("Way of reading %s", read_info)
    logger.debug("Shape of frame %s", dataframe.shape)

    if dataframe.shape[1] == 1:
        raise IOError(
            "File is not parsed correctly, check if there is something wrong!"
        )

    return _ensure_low_caps_columns(dataframe)


def convert_df_to_dict(frame: pd.DataFrame) -> dict:
    """Converts dataframe to dictionary format

    Args:
        frame (pd.DataFrame): the input dataframe

    Returns:
        dict: the dictionary derived from dataframe
    """
    logger = logging.getLogger(__name__ + ".convert_df_to_dict")
    frame.content.replace({"summary": "timeseries"}, inplace=True)
    unique_contents = frame.content.unique()
    for unique_content in unique_contents:
        if not hasattr(ContentEnum, unique_content):
            wrong_lines = frame.content == unique_content
            raise ValueError(
                f"{unique_content} is not a valid content  (used on {wrong_lines.sum()} lines",
            )
    logger.debug("dataframe at input %s", frame)
    frame_as_dict = frame.to_dict("records")
    logger.debug("Frame as dictionary %s", frame_as_dict)
    return frame_as_dict


def extract_rft(in_frame: pd.DataFrame) -> pd.DataFrame:
    """Extract rft from file

    Args:
        in_frame (pd.DataFrame): the dataframe to extract from

    Returns:
        pd.DataFrame: modified results from dataframe
    """
    logger = logging.getLogger(__name__ + ".extract_rft")
    all_rft_obs = []
    unique_ids = "unique_identifier"
    in_frame[unique_ids] = (
        in_frame["well_name"] + "_" + in_frame["date"].astype(str).str.replace("-", "_")
    )
    restart = 1
    for unique_id in in_frame[unique_ids].unique():
        logger.debug("Making obs frame for %s", unique_id)
        key_frame = in_frame.loc[in_frame[unique_ids] == unique_id]
        report_frame = key_frame.copy()
        report_frame["restart"] = restart
        restart += 1
        all_rft_obs.append(report_frame)
    all_rft_obs = pd.concat(all_rft_obs)
    all_rft_obs["label"] = (
        all_rft_obs[unique_ids] + "_" + all_rft_obs["restart"].astype(str)
    )
    return all_rft_obs


def extract_general(in_frame: pd.DataFrame, lable_name: str) -> pd.DataFrame:
    """Modify dataframe from general observations

    Args:
        in_frame (pd.DataFrame): the original dataframe
        lable_name (str): anme of label

    Returns:
        pd.DataFrame: modified dataframe
    """
    general_observations = in_frame
    general_observations["lable"] = lable_name
    return general_observations


def extract_from_row(
    row: pd.Series, parent_folder: Union[str, PosixPath]
) -> List[pd.DataFrame]:
    """Extract results from row in config file

    Args:
        row (pd.Series): the row to extract from
        parent_folder (str, PosixPath): the folder to use when reading file

    Returns:
        pd.DataFrame: the extracted results
    """
    logger = logging.getLogger(__name__ + ".extract_from_row")
    input_file = parent_folder / row["input_file"]
    # to_fmuobs = pd.DataFrame([row.values], columns=row.index)
    logger.debug("File reference in row %s", input_file)
    if row["label"] != "":
        label = Path(input_file).stem.upper()
    else:
        label = row["label"]

    content = row["content"]

    # if ~isinstance(content, str):
    #     content = "summary"

    obs_file = input_file.parent / (content + "/" + input_file.stem + ".obs")

    obs_frame = read_obs_frame(input_file, label, content)
    obs_frame["output"] = obs_file
    class_name = "GENERAL_OBSERVATION"
    if content in ["summary", "timeseries"]:
        row_type = "timeseries"
        to_fmuobs = obs_frame
        to_fmuobs["CLASS"] = "SUMMARY_OBSERVATION"
        obs_file = "main file"

    elif content == "rft":
        row_type = "rft"
        to_fmuobs = pd.DataFrame(
            (str(input_file.parent) + "/" + obs_frame["WELL_NAME"] + ".obs").values,
            columns=["OBS_FILE"],
        )
        obs_frame["OUTPUT"] = to_fmuobs

        to_fmuobs["LABEL"] = label + "_" + obs_frame["WELL_NAME"]
        to_fmuobs["CLASS"] = class_name
        to_fmuobs["DATA"] = label + "_" + obs_frame["WELL_NAME"]
        logger.debug("RFT")
        logger.debug("These are the results %s", to_fmuobs)

    else:
        row_type = "general"
        to_fmuobs = pd.DataFrame(
            [[class_name, label, label, obs_file]],
            columns=["CLASS", "LABEL", "DATA", "OBS_FILE"],
        )

    obs_frame["CONTENT"] = content
    logger.debug("Row is %s (%s)", row_type, row)
    logger.debug("These are the observation results: %s", obs_frame)
    logger.debug("These are the results to send to fmuobs: %s", to_fmuobs)

    return obs_frame, to_fmuobs


def read_obs_frame(input_file: PosixPath, label: str, content: str) -> tuple:
    """Read obs table, generate summary to be converted to ert esotheric format

    Args:
        input_file (PosixPath): the file where the data is
        label (str): lable to be added for general obs
        content (Str): what content to be read

    Returns:
        tuple: the actual observation data, the summary of observations for csv output
    """

    if pd.isna(content):
        content = "SUMMARY"
        obs_frame = extract_summary(read_tabular_file(input_file))
    elif content.upper() != "RFT":
        content = "SUMMARY"
        obs_frame = extract_general(read_tabular_file(input_file), label)
    else:
        content = "RFT"
        obs_frame = extract_rft(read_tabular_file(input_file))

    return obs_frame


def extract_summary(in_frame: pd.DataFrame, key_identifier="VECTOR") -> dict:
    """Extract summary to pd.Dataframe format for fmu obs

    Args:
        in_frame (pd.DataFrame): the dataframe to extract from
        key_identifier (str, optional): name of column to make lables.
        Defaults to "VECTOR".

    Returns:
        dict: the results as a dictionary
    """
    logger = logging.getLogger(__name__ + ".extract_summary")
    logger.debug("Columns in dataframe %s", in_frame.columns.tolist())
    all_summary_obs = []
    for key in in_frame[key_identifier].unique():
        logger.debug("Making obs frame for %s", key)
        key_frame = in_frame.loc[in_frame[key_identifier] == key]
        report_frame = key_frame.copy()
        logger.debug("shape of data for %s %s", key, report_frame.shape)
        if key_frame.shape[0] == 1:
            logger.debug("Just one row")
            obs_lable = key_frame["date"].values.tolist().pop().replace("-", "_")
            logger.debug(obs_lable)

        else:
            logger.debug("Multiple rows")
            logger.debug(key_frame[key_identifier].shape)
            obs_lable = range(key_frame.shape[0])
            logger.debug(range(key_frame.shape[0]))
        logger.debug("Adding label(s) %s", obs_lable)
        report_frame["label"] = obs_lable
        all_summary_obs.append(report_frame)

    logger.debug("Concatenating %s summary series", len(all_summary_obs))
    logger.debug("Last object has columns %s", all_summary_obs[-1].columns)
    all_summary_obs = pd.concat(all_summary_obs)
    all_summary_obs["label"] = (
        all_summary_obs[key_identifier].str.replace(":", "_")
        + "_"
        + all_summary_obs["label"].astype(str)
    )
    logger.debug("Returning results %s", all_summary_obs)
    return all_summary_obs


def read_config_file(
    config_file_name: Union[str, PosixPath], parent_folder: Union[str, PosixPath] = None
) -> List[pd.DataFrame]:
    """Parse config file

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
    obs_sum_frame = []

    for rnr, row in config.iterrows():
        if row["active"] != "yes":
            logger.info("row %s is deactivated", rnr)
            continue

        row_obs, row_summary = extract_from_row(row, parent_folder)
        obs_data.append(row_obs)
        obs_sum_frame.append(row_summary)

    logger.debug("Summary to be exported is %s", obs_sum_frame)
    logger.debug("Observation data to be exported is %s", obs_sum_frame)
    obs_sum_frame = pd.concat(obs_sum_frame)
    obs_sum_frame.drop_duplicates(inplace=True)
    obs_data = pd.concat(obs_data)
    return obs_sum_frame, obs_data


def generate_rft_obs_files(rft_obs_data: pd.DataFrame, path):
    """generate ert observations files for rft from observational data

    Args:
        rft_obs_data (pd.DataFrame): input dataframe
        path (str): path to parent folder
    """
    logger = logging.getLogger(__name__ + ".generate_rft_obs_files")
    logger.debug("Extracting from dataframe %s", rft_obs_data.head())
    out_dir = Path(path)
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.debug("Exporting to %s", str(out_dir))

    well_info_name = out_dir / "well_name_time_restart.txt"

    pd.Series(rft_obs_data["unique_identifier"].unique()).to_csv(
        well_info_name, index=False, header=False
    )

    for well_name in rft_obs_data.WELL_NAME.unique():

        sub_set = rft_obs_data.loc[rft_obs_data.WELL_NAME == well_name]
        observations = sub_set[["value", "error"]]
        spatials = sub_set[["md", "tvd", "x", "y", "zone"]]
        obs_file_name = sub_set["OUTPUT"].values.tolist()[0]
        if not obs_file_name.parent.exists():
            obs_file_name.parent.mkdir(parents=True)
        observations.to_csv(obs_file_name, sep=" ", index=False, header=False)
        logger.debug("Exporting observations to %s", str(obs_file_name))
        # space_file_name = obs_file_name.stem + ".txt"
        space_file_name = obs_file_name.parent / (obs_file_name.stem + ".txt")
        logger.debug("Exporting spacial extras to %s", str(space_file_name))
        spatials.to_csv(space_file_name, sep=" ", index=False, header=False)
