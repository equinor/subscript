import logging
from typing import Union, List
import pandas as pd
from pathlib import PosixPath
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


def convert_obs_df_to_list(frame: pd.DataFrame) -> list:
    """Converts dataframe with observation to dictionary format

    Args:
        frame (pd.DataFrame): the input dataframe

    Returns:
        dict: the dictionary derived from dataframe
    """
    logger = logging.getLogger(__name__ + ".convert_obs_df_to_dict")
    logger.debug("Frame to extract from \n%s", frame)
    obs_list = []
    if "vector" in frame.columns:
        unique_id = "vector"
    else:
        unique_id = "label"
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
    logger.debug("\ndataframe at input: \n%s", frame)
    logger.debug("\nFrame as list of dictionaries \n%s\n", obs_list)
    return obs_list


def add_or_modify_error(frame: pd.DataFrame, error: str):
    """Complete error column in dataframe

    Args:
        frame (pd.DataFrame): the dataframe to be modified
        error (str): the error to add when it is undefined or not included
    """
    logger = logging.getLogger(__name__ + ".add_or_modify_error")
    logger.debug("Frame before error addition/modification \n%s\n", frame)
    logger.debug("Error to apply %s", error)
    error = str(error)  # convert to ensure that code is simpler further down
    try:
        error_holes = frame.error.isna()
    except AttributeError:
        logger.info("No error column provided, error will be added for all entries")
        error_holes = pd.Series([True] * frame.shape[0])
        frame["error"] = None
    if error.endswith("%"):
        logger.debug("Error is percent, will be multiplied with value")

        frac_error = float(error[:-1]) / 100
        logger.debug("Factor to multiply with %s", frac_error)
        frame.error[error_holes] = frame.value[error_holes] * frac_error
    else:
        logger.debug("Error is absolute, will be added as constant")
        abs_error = float(error)
        logger.debug("Error to add %s", abs_error)
        frame.error.loc[error_holes] = abs_error
    logger.debug("After addition/modification errors are \n%s\n", frame.error)
    # return frame


def split_one_and_many_columns(frame: pd.DataFrame) -> tuple:
    """Make lists that distinguishes between columns that should be one column and not

    Args:
        frame (pd.DataFrame): the datframe to interrogate

    Returns:
        tuple: list with columns that have only one, followed by list of those that have many
    """
    # TODO: check if zone should be in must_be_many
    must_be_many = ["value", "error", "x", "y", "z", "md"]
    logger = logging.getLogger(__name__ + ".split_one_and_many_columns")
    cols_to_classify = [name for name in frame.columns if name != "content"]
    one_liners = [
        col_name
        for col_name in cols_to_classify
        if (
            len(frame[col_name].unique().tolist()) == 1 and col_name not in must_be_many
        )
    ]
    many_liners = [
        col_name for col_name in cols_to_classify if col_name not in one_liners
    ]
    logger.debug("oneliners:\n%s\nmany liners:\n%s", one_liners, many_liners)
    return one_liners, many_liners


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
    # TODO: vector name for timeseries should not be wrapped into list?
    # or maybe contained, but add key name or summat as idenfier
    # Are there exceptions where it should not be list?
    logger = logging.getLogger(__name__ + ".extract_from_row")
    input_file = parent_folder / row["observation"]
    logger.debug("File reference in row %s", input_file)
    content = row["type"]
    obs_frame = read_obs_frame(input_file, content)
    logger.info("Results after reading observations as dataframe:\n%s\n", obs_frame)

    add_or_modify_error(obs_frame, row["error"])
    logger.debug("\nThese are the observation results:\n %s", obs_frame)

    converted = convert_obs_df_to_list(obs_frame)
    logger.debug("Converted results %s", converted)

    return converted


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
