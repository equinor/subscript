import logging
import re
from pathlib import Path
from typing import List, Optional, Union
from warnings import warn

import pandas as pd

from subscript.genertobs_unstable._datatypes import (
    ConfigElement,
    ObservationType,
    RftConfigElement,
)


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
    logger = logging.getLogger(__name__ + ".remove_undefined_values")
    undefined_vals = ["-999.999", "-999.25", -999.25, -999.9, ""]
    if "value" in frame.columns:
        logger.debug("Have a value column, will remove undefined, if there are any")
        not_undefs = (~frame.value.isin(undefined_vals)) & (~frame.value.isnull())
        logger.debug("%s row(s) will be removed", frame.shape[0] - not_undefs.sum())
        return frame.loc[not_undefs]

    logger.debug("No value column, cannot remove undefs")
    return frame


def remove_whitespace(dataframe: pd.DataFrame):
    """Remove whitespace in str columns for pandas dataframe

    Args:
        dataframe (pd.DataFrame): the dataframe to modify
    """
    logger = logging.getLogger(__name__ + ".remove_whitespace")
    for col_name in dataframe.columns:

        try:

            dataframe[col_name] = dataframe[col_name].map(str.strip)
        except TypeError:
            logger.debug("%s is not str column", col_name)


def read_tabular_file(tabular_file_path: Union[str, Path]) -> pd.DataFrame:
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
        dataframe = pd.read_csv(tabular_file_path, sep=",", dtype=str, comment="#")
    except UnicodeDecodeError:
        dataframe = pd.read_excel(tabular_file_path, dtype=str)
        read_info = "excel"
    except FileNotFoundError as fnerr:
        raise FileNotFoundError(f"|{tabular_file_path}| could not be found") from fnerr
    nr_cols = dataframe.shape[1]
    logger.debug("Nr of columns are %s", nr_cols)
    if nr_cols == 1:
        logger.debug("Wrong number of columns, trying with other separators")
        for separator in [";", r"\s+"]:
            logger.debug("Trying with |%s| as separator", separator)
            try:
                dataframe = pd.read_csv(
                    tabular_file_path, sep=separator, dtype=str, comment="#"
                )
            except pd.errors.ParserError as pepe:
                raise IOError(
                    f"Failing to read {tabular_file_path} with separator {separator}"
                ) from pepe
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
    remove_whitespace(dataframe)
    dataframe = remove_undefined_values(dataframe)
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
        inactivated = ~dataframe.active
        logger.debug("Filter is %s", inactivated)
        nr_rows = inactivated.sum()
        logger.info(
            "%s rows inactivated (%s percent)",
            nr_rows,
            100 * nr_rows / dataframe.shape[0],
        )
        dataframe = dataframe.loc[~inactivated]
        logger.debug("shape after deactivation %s", dataframe.shape)
    except AttributeError:
        logger.info("No inactivation done")
    return dataframe


def check_and_fix_str(string_to_sanitize: str) -> str:
    """Replace some unwanted strings in str

    Args:
        string_to_sanitize (str): the input string

    Returns:
        str: the sanitized string
    """
    logger = logging.getLogger(__name__ + ".check_and_fix_str")
    logger.debug("Initial string before sanitization |%s|", string_to_sanitize)
    unwanted_characters = re.compile(r"(\s+|/)")
    country_code = re.compile(r"^[a-zA-Z]+\s+")
    unwanted_chars = unwanted_characters.findall(string_to_sanitize)
    logger.debug("%s unwanted characters found %s", len(unwanted_chars), unwanted_chars)
    if len(unwanted_chars) > 0:
        warn(
            f"String: {string_to_sanitize} contains {unwanted_chars} will be replaced\n"
            "But might be an indication that something is not right!!"
        )
        sanitized = unwanted_characters.sub(
            "_", country_code.sub("", string_to_sanitize.strip())
        )

        logger.debug("After sanitization %s", sanitized)
        return sanitized

    logger.debug("String was good to go")
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
    logger.debug("Hoping for these columns %s, available are %s", 
                 relevant_columns, frame.columns.to_list())
    narrowed_down = frame.loc[:, frame.columns.isin(relevant_columns)]      
    well_names = narrowed_down.well_name.unique().tolist()
    logger.debug("%s wells to write (%s)", len(well_names), well_names)
    for well_name in well_names:
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


def convert_obs_df_to_list(frame: pd.DataFrame, content: ObservationType) -> list:
    """Converts dataframe with observation to dictionary format

    Args:
        frame (pd.DataFrame): the input dataframe

    Returns:
        dict: the dictionary derived from dataframe
    """
    logger = logging.getLogger(__name__ + ".convert_obs_df_to_dict")
    logger.debug("Frame to extract from \n%s", frame)
    obs_list = []
    if content == ObservationType.SUMMARY:
        obs_list = convert_summary_to_list(frame)
    elif content == ObservationType.RFT:
        obs_list = convert_rft_to_list(frame)
    logger.debug("\nFrame as list of dictionaries \n%s\n", obs_list)
    return obs_list


def add_or_modify_error(
    frame: pd.DataFrame,
    error: Union[str, float, int],
    err_min: Optional[Union[float, int]] = None,
    err_max: Optional[Union[float, int]] = None,
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
        logger.debug("Error holes are %s", error_holes)
        try:
            frame.loc[error_holes, "error"] = abs_error
        except TypeError:
            # TODO: This exception shows that the code is not ideal, but works for now
            logger.error("Fixing via a backdoor solution.. Code should be improved")
            frame["error"] = abs_error

    dubious_errors = frame.error > frame.value
    if dubious_errors.sum() > 0:
        warn(
            "Some errors are larger than the values"
            f"\n{frame.loc[dubious_errors]}\n Is this intentional?"
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
                converter = int  # type: ignore
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
    row: Union[RftConfigElement, ConfigElement],
    parent_folder: Path,
) -> List[pd.DataFrame]:
    """Extract results from row in config file

    Args:
        row (pd.Series): the row to extract from
        parent_folder (str, Path): the folder to use when reading file

    Returns:
        pd.DataFrame: the extracted results
    """
    # TODO: vector name for timeseries should not be wrapped into list?
    # or maybe contained, but add key name or summat as idenfier
    # Are there exceptions where it should not be list?
    logger = logging.getLogger(__name__ + ".extract_from_row")
    logging.debug("Extracting from this element %s", row)
    input_file = parent_folder / row.observation
    logger.debug("File reference in row %s", input_file)
    content = row.type
    obs_frame = read_obs_frame(input_file, content, row.alias_file)

    if not row.active:
        obs_frame["active"] = "no"

    else:
        if "active" not in obs_frame.columns:
            obs_frame["active"] = "yes"

    obs_frame["active"] = obs_frame["active"] != "no"

    logger.info("Results after reading observations as dataframe:\n%s\n", obs_frame)

    add_or_modify_error(obs_frame, row.default_error, row.min_error, row.max_error)
    logger.debug("\nThese are the observation results:\n %s", obs_frame)

    converted = convert_obs_df_to_list(obs_frame, content)
    logger.debug("Converted results %s", converted)

    return converted


def replace_names(name_series: pd.Series, replacer: pd.DataFrame) -> pd.Series:
    """Replace name in a pandas dataseries with values from dataframe

    Args:
        name_series (pd.Series): the series to replace in
        replacer (pd.DataFrame): the dataframe to replace with

    Raises:
        ValueError: if replacer cannot be converted to dictionary to replace with

    Returns:
        pd.Series: the dataseries with replaced values
    """
    logger = logging.getLogger(__name__ + ".replace_names")
    if replacer.shape[1] != 2:
        raise ValueError(
            "This dataframe cannot be used to replace names, has the wrong shape"
        )

    replace_dict = dict(
        zip(replacer[replacer.columns[0]], replacer[replacer.columns[1]])
    )
    logger.info("Will replace names with dictionary %s", replace_dict)
    replaced_names = name_series.replace(replace_dict)
    if replaced_names.equals(name_series):
        warn("No replacement is done, column is unchanged")
    logger.info("New column: %s", replaced_names)
    return replaced_names


def read_obs_frame(
    input_file: Path, content: ObservationType, alias_file
) -> pd.DataFrame:
    """Read obs table, generate summary to be converted to ert esotheric format

    Args:
        input_file (Path): the file where the data is
        label (str): lable to be added for general obs
        content (Str): what content to be read

    Returns:
        tuple: the actual observation data, the summary of observations for csv output
    """
    logger = logging.getLogger(__name__ + ".read_obs_frame")
    logger.debug("Trying to read from %s", input_file)
    if content not in [ObservationType.SUMMARY, ObservationType.RFT]:
        label = input_file.stem
        obs_frame = extract_general(read_tabular_file(input_file), label)
    else:
        obs_frame = read_tabular_file(input_file)

    try:
        obs_frame["date"] = pd.to_datetime(obs_frame["date"]).dt.strftime("%Y-%m-%d")
    except KeyError:
        logger.warning("No date column for this dataframe")

    try:
        obs_frame["well_name"] = obs_frame["well_name"].map(check_and_fix_str)
        if alias_file is not None:
            logger.debug("Reading alias file |%s|", alias_file)
            aliases = read_tabular_file(alias_file)
            logger.debug("Will replace names with aliases %s", aliases)
            obs_frame["well_name"] = replace_names(obs_frame["well_name"], aliases)

    except KeyError:
        logger.debug("No well_name column for this dataframe")
    logger.debug("Returning %s", obs_frame)
    return obs_frame
