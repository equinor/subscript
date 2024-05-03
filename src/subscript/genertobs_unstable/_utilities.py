import logging
import re
from typing import Union, List
from warnings import warn
from pathlib import PosixPath
import pandas as pd
from fmu.dataio.datastructure.meta.enums import ContentEnum


def _fix_column_names(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Make column names lower case, strip leading and trailing whitespace

    Args:
        dataframe (pd.DataFrame): the dataframe to modify

    Returns:
        pd.DataFrame: the modified dataframe
    """
    dataframe.columns = [col.lower().strip() for col in dataframe.columns]
    return dataframe


def remove_undefined_values(frame: pd.DataFrame) -> pd.DataFrame:
    """Remove rows that have undefined values in Dataframe

    Args:
        frame (pd.DataFrame): the dataframe to sanitize

    """
    undefined_vals = ["-999.999", "-999.25"]
    if "value" in frame:
        frame = frame.loc[~frame.value.isin(undefined_vals) | ~frame.value.isnull()]


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

    dataframe = _fix_column_names(dataframe)
    inactivate_rows(dataframe)
    remove_undefined_values(dataframe)

    dataframe.rename({"key": "vector"}, inplace=True, axis="columns")
    logger.debug("Returning dataframe %s", dataframe)
    return dataframe


def inactivate_rows(dataframe: pd.DataFrame):
    """Inactivate rows in dataframe

    Args:
        dataframe (pd.DataFrame): the dataframe to decimate
    """
    logger = logging.getLogger(__name__ + ".inactivate_rows")
    try:
        inactivated = dataframe.active == "no"
        nr_rows = inactivated.sum()
        logger.info(
            "%s rows inactivated (%s percent)",
            nr_rows,
            100 * nr_rows / dataframe.shape[0],
        )
        dataframe = dataframe.loc[inactivated]
    except AttributeError:
        logger.info("No inactivation done")


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


def check_and_fix_str(string_to_sanitize: str) -> str:
    """Replace some unwanted strings in str

    Args:
        string_to_sanitize (str): the input string

    Returns:
        str: the sanitized string
    """
    logger = logging.getLogger(__name__ + ".check_and_fix_str")
    unwanted_pattern = re.compile(r"(\s+|\\|-)")
    unwanted = unwanted_pattern.findall(string_to_sanitize)
    logger.debug("Unwanted characters %s", unwanted)
    if len(unwanted) > 0:
        warn(
            f"Well name: {string_to_sanitize} contains {unwanted} will be replaced\n"
            "But might be an indication that something is not right"
        )
        sanitized = unwanted_pattern.sub("_", string_to_sanitize)

        return sanitized
    else:
        return string_to_sanitize


def convert_rft_to_list(frame: pd.DataFrame) -> list:
    """Convert dataframe to list of dictionaries

    Args:
        frame (pd.DataFrame): the input dataframe

    Returns:
        list: the extracted results
    """
    output = []
    logger = logging.getLogger(__name__ + ".convert_rft_to_list")
    logger.debug("frame to convert %s", frame)
    keepers = [
        "value",
        "error",
        "x",
        "y",
        "tvd",
        "md",
        "zone",
    ]
    additionals = [
        "well_name",
        "date",
    ]
    relevant_columns = keepers + additionals
    narrowed_down = frame.loc[:, frame.columns.isin(relevant_columns)]
    well_names = narrowed_down.well_name.unique().tolist()
    logger.debug("%s wells to write (%s)", len(well_names), well_names)
    for well_name in well_names:
        well_name = check_and_fix_str(well_name)
        well_observations = narrowed_down.loc[narrowed_down.well_name == well_name]
        dates = well_observations.date.unique().tolist()
        logger.debug("Well %s has %s dates", well_name, len(dates))
        restart = 1
        for date in dates:
            well_date_observations = well_observations.loc[
                well_observations.date == date
            ]
            output.append(
                {
                    "well_name": well_name,
                    "date": date,
                    "restart": restart,
                    "label": f"{well_name}_{date}".replace("-", "_"),
                    "data": well_date_observations[keepers],
                }
            )
            restart += 1

    return output


def convert_summary_to_list(frame: pd.DataFrame) -> list:
    """Convert dataframe with summary obs to list of dictionaries

    Args:
        frame (pd.DataFrame): the input dataframe

    Returns:
        list: the extracted results
    """
    output = []
    logger = logging.getLogger(__name__ + ".convert_summary_to_list")
    logger.debug("frame to convert %s", frame)
    keepers = ["date", "value", "error"]
    additional = ["vector"]
    relevant_columns = keepers + additional
    narrowed_down = frame.loc[:, frame.columns.isin(relevant_columns)]
    vectors = frame.vector.unique().tolist()
    logger.debug("%s vectors to write (%s)", len(vectors), vectors)
    for vector in vectors:
        vector_observations = narrowed_down.loc[narrowed_down.vector == vector].copy()
        vector_observations["label"] = (
            vector_observations["vector"].str.replace(":", "_").replace("-", "_")
            + "_"
            + [str(num) for num in range(vector_observations.shape[0])]
        )
        output.append(
            {
                "vector": vector,
                "data": vector_observations[keepers + ["label"]],
            }
        )
    return output


def convert_obs_df_to_list(frame: pd.DataFrame, content: str) -> list:
    """Converts dataframe with observation to dictionary format

    Args:
        frame (pd.DataFrame): the input dataframe

    Returns:
        dict: the dictionary derived from dataframe
    """
    logger = logging.getLogger(__name__ + ".convert_obs_df_to_dict")
    logger.debug("Frame to extract from \n%s", frame)
    obs_list = []
    if content == "timeseries":
        obs_list = convert_summary_to_list(frame)
    elif content == "rft":
        obs_list = convert_rft_to_list(frame)
    logger.debug("\nFrame as list of dictionaries \n%s\n", obs_list)
    return obs_list


def add_or_modify_error(
    frame: pd.DataFrame,
    error: str,
    err_min: Union[float, int] = None,
    err_max: Union[float, int] = None,
):
    """Complete error column in dataframe

    Args:
        frame (pd.DataFrame): the dataframe to be modified
        error (str): the error to add when it is undefined or not included
    """
    logger = logging.getLogger(__name__ + ".add_or_modify_error")
    logger.debug("Frame before error addition/modification \n%s\n", frame)
    logger.debug("Frame has columns %s", frame.columns)
    logger.debug("Error to apply %s", error)

    ensure_numeric(frame, "value")
    ensure_numeric(frame, "error")
    error = str(error)  # convert to ensure that code is simpler further down
    try:
        error_holes = frame.error.isna()
    except AttributeError:
        logger.info("No error column provided, error will be added for all entries")
        error_holes = pd.Series([True] * frame.shape[0])
        frame["error"] = None
    if error_holes.sum() == 0:
        logger.info("Error allready set, nothing will be changed")
        frame.error = frame.error.astype(float)

    if error.endswith("%"):
        logger.debug("Error is percent, will be multiplied with value")

        frac_error = float(error[:-1]) / 100
        logger.debug("Factor to multiply with %s", frac_error)
        frame.loc[error_holes, "error"] = frame.loc[error_holes, "value"] * frac_error
        if err_min is not None:
            frame.loc[frame["error"] < err_min, "error"] = err_min

        if err_max is not None:
            frame.loc[frame["error"] > err_max, "error"] = err_max

    else:
        if err_max is not None or err_min is not None:
            mess = f"""Truncation of error when error is absolute
                    has no effect min: {err_min}, max: {err_max}
            """
            warn(mess)

        logger.debug("Error is absolute, will be added as constant")
        abs_error = float(error)
        logger.debug("Error to add %s", abs_error)
        frame.loc[error_holes, "error"] = abs_error

    dubious_errors = frame.error > frame.value
    if dubious_errors.sum() > 0:
        warn(
            "Some errors are larger than the values"
            f"({frame.loc[dubious_errors]}), is this intentional?"
        )
    logger.debug("After addition/modification errors are \n%s\n", frame.error)


def ensure_numeric(frame: pd.DataFrame, key: str):
    """Convert certain column to numeric if it isn't

    Args:
        frame (pd.DataFrame): the dataframe
        key (str): the column name for the column
    """
    logger = logging.getLogger(__name__ + ".ensure_numeric")
    try:
        if frame[key].dtype.kind not in "iuf":
            if frame[key].astype(str).str.contains(".").sum() > 0:
                converter = float
            else:
                converter = int
            frame[key] = frame[key].astype(converter)
    except KeyError:
        logger.debug("No %s column", key)


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

    add_or_modify_error(
        obs_frame, row["error"], row.get("min_error", None), row.get("max_error", None)
    )
    logger.debug("\nThese are the observation results:\n %s", obs_frame)

    converted = convert_obs_df_to_list(obs_frame, content)
    logger.debug("Converted results %s", converted)

    return converted


def read_obs_frame(input_file: PosixPath, content: str) -> pd.DataFrame:
    """Read obs table, generate summary to be converted to ert esotheric format

    Args:
        input_file (PosixPath): the file where the data is
        label (str): lable to be added for general obs
        content (Str): what content to be read

    Returns:
        tuple: the actual observation data, the summary of observations for csv output
    """
    logger = logging.getLogger(__name__ + ".read_obs_frame")
    if content not in ["timeseries", "rft"]:
        label = input_file.stem
        obs_frame = extract_general(read_tabular_file(input_file), label)
    else:
        obs_frame = read_tabular_file(input_file)

    try:
        obs_frame["date"] = pd.to_datetime(obs_frame["date"]).dt.strftime("%Y-%m-%d")
    except KeyError:
        logger.warning("No date column for this dataframe")
    logger.debug("Returning %s", obs_frame)
    return obs_frame
