"""Code related to fmobs config stuff"""

import logging
from typing import Union, List
import yaml
from pathlib import Path, PosixPath
import pandas as pd
from fmu.dataio.datastructure.meta.enums import ContentEnum
from subscript.fmuobs.writers import summary_df2obsdict


def _ensure_low_caps_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Make all column names lower case

    Args:
        dataframe (pd.DataFrame): the dataframe to modify

    Returns:
        pd.DataFrame: the modified dataframe
    """
    dataframe.columns = [col.lower() for col in dataframe.columns]
    return dataframe


def _ensure_up_caps_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Make all column names upper case

    Args:
        dataframe (pd.DataFrame): the dataframe to modify

    Returns:
        pd.DataFrame: the modified dataframe
    """
    dataframe.columns = [col.upper() for col in dataframe.columns]
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
    frame.replace({"summary": "timeseries"}, inplace=True)
    unique_contents = frame.content.unique()
    for unique_content in unique_contents:
        if not hasattr(ContentEnum, unique_content):
            wrong_lines = frame.content == unique_content
            raise ValueError(
                f"{unique_content} is not a valid content  (used on {wrong_lines.sum()} lines",
            )
    frame_as_dict = frame.to_dict("records")
    logger.debug("Frame as dictionary %s", frame_as_dict)
    return frame_as_dict


def convert_obs_df_to_dict(frame: pd.DataFrame) -> dict:
    """Converts dataframe with observation to dictionary format

    Args:
        frame (pd.DataFrame): the input dataframe

    Returns:
        dict: the dictionary derived from dataframe
    """
    logger = logging.getLogger(__name__ + ".convert_obs_df_to_dict")

    frame = _ensure_low_caps_columns(frame)
    frame.content.replace({"summary": "timeseries"}, inplace=True)
    logger.debug("Frame to extract from \n%s", frame)
    obs_list = []
    content = frame["content"].values[0]
    if content == "timeseries":
        unique_id = "content"
    else:
        unique_id = "output"
    logger.debug("Using %s as unique id", unique_id)

    unique_ids = frame[unique_id].unique()
    logger.debug("%s unique values: (%s)", unique_ids.size, unique_ids)

    for unique_splitter in unique_ids:
        logger.debug("Working on unique_id %s", unique_splitter)
        sub_dict = {}
        unique_section = frame.loc[frame[unique_id] == unique_splitter]
        one_liners, many_liners = split_one_and_many_columns(unique_section)
        for one_liner in one_liners:
            sub_dict[one_liner] = str(unique_section[one_liner].values[0])

        for many_liner in many_liners:
            try:
                set_values = unique_section[many_liner].astype(float)
            except ValueError:
                set_values = unique_section[many_liner].astype(str)
            sub_dict[many_liner] = set_values.tolist()
        obs_list.append(sub_dict)
        logger.debug("subdict: %s\n", sub_dict)
    frame_as_dict = {content: obs_list}
    logger.debug("\ndataframe at input: \n%s", frame)
    logger.debug("\nFrame as list of dictionaries \n%s\n", frame_as_dict)
    return frame_as_dict


def split_one_and_many_columns(frame: pd.DataFrame) -> tuple:
    """Make lists that distingishes between columns that have only on column and not

    Args:
        frame (pd.DataFrame): the datframe to interrogate

    Returns:
        tuple: list with columns that have only one, followed by list of those that have many
    """
    # TODO: align with expectations, label, vector(aka key), and date can be oneliners
    # error, x, y, z, md and value should be list
    logger = logging.getLogger(__name__ + ".split_one_and_many_columns")
    cols_to_classify = [name for name in frame.columns if name != "content"]
    one_liners = [
        col_name
        for col_name in cols_to_classify
        if len(frame[col_name].unique().tolist()) == 1
    ]
    many_liners = [
        col_name for col_name in cols_to_classify if col_name not in one_liners
    ]
    logger.debug("oneliners:\n%s\nmany liners:\n%s", one_liners, many_liners)
    return one_liners, many_liners


def extract_rft(in_frame: pd.DataFrame) -> pd.DataFrame:
    """Extract rft from file

    Args:
        in_frame (pd.DataFrame): the dataframe to extract from

    Returns:
        pd.DataFrame: modified results from dataframe
    """
    logger = logging.getLogger(__name__ + ".extract_rft")
    in_frame["date"] = pd.to_datetime(in_frame["date"]).dt.strftime("%Y-%m-%d")
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
    logger.debug("concatenated %s", all_rft_obs)
    all_rft_obs["label"] = (
        all_rft_obs[unique_ids] + "_" + all_rft_obs["restart"].astype(str)
    )
    all_rft_obs.drop("unique_identifier", axis=1, inplace=True)
    all_rft_obs["output"] = all_rft_obs["well_name"].str.lower() + ".obs"
    logger.debug("Returning \n%s\n", all_rft_obs)
    return all_rft_obs


def extract_general(in_frame: pd.DataFrame, lable_name: str) -> pd.DataFrame:
    """Modify dataframe from general observations

    Args:
        in_frame (pd.DataFrame): the original dataframe
        lable_name (str): anme of label

    Returns:
        pd.DataFrame: modified dataframe
    """
    logger = logging.getLogger(__name__ + ".extract_general")
    general_observations = in_frame
    general_observations["lable"] = lable_name
    logger.debug("returning %s", general_observations)
    return general_observations


def extract_from_row(
    row: dict, parent_folder: Union[str, PosixPath]
) -> List[pd.DataFrame]:
    """Extract results from row in config file

    Args:
        row (pd.Series): the row to extract from
        parent_folder (str, PosixPath): the folder to use when reading file

    Returns:
        pd.DataFrame: the extracted results
    """
    logger = logging.getLogger(__name__ + ".extract_from_row")
    logger.debug("Input row is %s", row)
    input_file = parent_folder / row["observation"]
    # to_fmuobs = pd.DataFrame([row.values], columns=row.index)
    logger.debug("File reference in row %s", input_file)
    content = row["type"]
    obs_file = input_file.parent / (content + "/" + input_file.stem + ".obs")
    obs_frame = read_obs_frame(input_file, content)
    logger.info("Results after reading observations as dataframe:\n%s\n", obs_frame)
    # obs_frame["output"] = str(obs_file.resolve())
    class_name = "GENERAL_OBSERVATION"
    if content in ["summary", "timeseries"]:
        row_type = "timeseries"
        to_fmuobs = obs_frame
        to_fmuobs["CLASS"] = "SUMMARY_OBSERVATION"

    elif content == "rft":
        row_type = "rft"
        logger.debug("Well names are %s", obs_frame["well_name"])
        to_fmuobs = pd.DataFrame(
            (
                str(input_file.parent) + "/" + well_name + ".obs"
                for well_name in obs_frame["well_name"]
            ),
            columns=["OBS_FILE"],
        )
        # obs_frame["OUTPUT"] = to_fmuobs

        to_fmuobs["CLASS"] = class_name
        # to_fmuobs["DATA"] = to_fmuobs["label"]
        logger.debug("RFT")

    else:
        row_type = "general"
        to_fmuobs = pd.DataFrame(
            [[class_name, label, label, obs_file]],
            columns=["CLASS", "LABEL", "DATA", "OBS_FILE"],
        )

    obs_frame["CONTENT"] = content
    to_fmuobs.drop_duplicates(inplace=True)
    logger.debug("Row is %s (%s)", row_type, row)
    logger.debug("\nThese are the observation results:\n %s", obs_frame)
    logger.debug("\nThese are the results to send to fmuobs:\n %s", to_fmuobs)

    return convert_obs_df_to_dict(obs_frame), to_fmuobs


def read_obs_frame(
    input_file: PosixPath, content: str, label: str = None
) -> pd.DataFrame:
    """Read obs table, generate summary to be converted to ert esotheric format

    Args:
        input_file (PosixPath): the file where the data is
        label (str): lable to be added for general obs
        content (Str): what content to be read

    Returns:
        tuple: the actual observation data, the summary of observations for csv output
    """
    logger = logging.getLogger(__name__ + ".read_obs_frame")
    if pd.isna(content) or content.lower() == "timeseries":
        obs_frame = extract_summary(read_tabular_file(input_file))
    elif content.lower() != "rft":
        if label is None:
            label = input_file.stem
        obs_frame = extract_general(read_tabular_file(input_file), label)
    else:
        obs_frame = extract_rft(read_tabular_file(input_file))
    obs_frame.rename({"lable": "label"}, axis=1, inplace=True)
    logger.debug("Returning %s", obs_frame)
    obs_frame = _ensure_low_caps_columns(obs_frame)
    return obs_frame


def extract_summary(in_frame: pd.DataFrame, key_identifier="vector") -> pd.DataFrame:
    """Extract summary to pd.Dataframe format for fmu obs

    Args:
        in_frame (pd.DataFrame): the dataframe to extract from
        key_identifier (str, optional): name of column to make lables.
        Defaults to "vector".

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
            logger.debug("Just one row, using date as part of lable")
            obs_lable = key_frame["date"].values.tolist().pop().replace("-", "_")
            logger.debug(obs_lable)

        else:
            logger.debug("Multiple rows, lable will be restart number")
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
    all_summary_obs.columns = [name.upper() for name in all_summary_obs.columns]
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
    frame_to_fmuobs = []

    for rnr, row in config.iterrows():
        if row["active"] != "yes":
            logger.info("row %s is deactivated", rnr)
            continue

        row_obs, row_summary = extract_from_row(row, parent_folder)
        obs_data.append(row_obs)
        frame_to_fmuobs.append(row_summary)

    logger.debug("Summary to be exported is %s", frame_to_fmuobs)
    logger.debug("Observation data to be exported is %s", frame_to_fmuobs)
    frame_to_fmuobs = pd.concat(frame_to_fmuobs)
    obs_data = pd.concat(obs_data)
    return frame_to_fmuobs, obs_data


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
        tuple: dictionary with observations to send to sumo,
               pd.Dataframe to send to fmuobs
    """
    logger = logging.getLogger(__name__ + ".generate_data_from_config")
    logger.debug("Here is config to parse %s", config)
    ids = []
    data = []
    summaries = []
    for config_element in config:
        logger.info("Parsing element %s", config_element)
        data_element = {}
        data_element["name"] = config_element["name"]
        data_element["content"] = config_element["type"]
        obs, obs_summary = extract_from_row(config_element, parent)
        data_element["observations"] = obs
        data.append(data_element)
        summaries.append(obs_summary)

        # logger.debug("These are the observations:\n%s", data_element)
        logger.debug("And this is the summary:\n%s", obs_summary)
    # summaries = pd.concat(summaries)
    return data, summaries


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
