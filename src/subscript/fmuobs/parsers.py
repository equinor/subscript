"""Module for parsing and writing ERT observation files into/from an
equivalent DataFrame representation"""

import datetime
import re
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from subscript import getLogger
from subscript.fmuobs.util import (
    ERT_ALT_DATE_FORMAT,
    ERT_DATE_FORMAT,
    ERT_ISO_DATE_FORMAT,
    uppercase_dictkeys,
)

logger = getLogger(__name__)

# Regular expressions for matching ERT observation files.
# Note that lower-case is supported by the regexp's, but might not be supported
# by ERT.
_WHITESPACE = r"[\s]*"
_KEY_VALUE_CHARS = r"\nA-Za-z:/=_\+\-\.,0-9\s"
_OBS_CLASS = r"([A-Z_]+)"
_OBS_LABEL = r"([A-Za-z0-9_\-]+)"
_SEMICOLON = _WHITESPACE + ";" + _WHITESPACE

# This avoids nested {}, and avoids capturing trailing ; in matched group
_OPTIONAL_CURLY_SUBGROUP = r"(\{[A-Za-z=0-9\+\.,_;/\s]*\})?" + _SEMICOLON

OBS_ARGS_RE = re.compile(
    _WHITESPACE
    + "(["
    + _KEY_VALUE_CHARS
    + "]*)"
    + _WHITESPACE
    + _OPTIONAL_CURLY_SUBGROUP
)
"""Regular expression for splitting observation arguments into a
key-values element, and a curly-braces element. The curly braces
can not be nested."""

_QUOTE = r"[\"']*"
_FILENAME_CHARS = r"\w\s\.\-_"
INCLUDE_RE = re.compile(
    r"\s*(include\s+"
    + _QUOTE
    + ")(["
    + _FILENAME_CHARS
    + "]+)("
    + _QUOTE
    + _WHITESPACE
    + ";)"
)
"""Regular expression for capturing include statements in input file"""


def expand_includes(input_str: str, cwd: str = ".") -> str:
    """Look for include 'filename.txt'; in the string, and replace
    it with the contents of that file. Filenames need not be quoted,
    but semicolons (and most other special characters) in filenames
    will not be resolved.

    Args:
        input_str (str): String with potential include-statements.
        cwd (str): Path to what should be used as current working directory
            when resolving include statements (for include files). Defaults
            to current directory, but the ERT observation format assumes
            it is the directory of the ERT config file.
    """
    match = INCLUDE_RE.search(input_str)
    while match:
        include_filename = Path(cwd) / Path(match.groups()[1])
        logger.info(
            "Injecting include file: %s into observation file", include_filename
        )
        include_txt = include_filename.read_text(encoding="utf8")
        input_str = input_str.replace("".join(match.groups()), include_txt)
        match = INCLUDE_RE.search(input_str)
    return input_str


def mask_curly_braces(string: str, mask_char: str = "X") -> str:
    """In order to support nested curly braces, a regular expression
    cannot be used to do the outermost "split-by-semicolon" operation.

    Instead we mask away the curly braces, so that all semicolons occuring
    in the string are at the outermost level - then we can split the
    unmasked string by the semicolon position in the masked string.
    """
    assert len(mask_char) == 1
    for match in re.compile(_OPTIONAL_CURLY_SUBGROUP).findall(string):
        if match:
            string = string.replace(match, mask_char * len(match))
    # When curly braces are nested, there are strings like {FOO=BAR; XXXX;} left
    # in the strings after the loop above, mask these also:
    for match in re.compile(
        # r"(\{[\sA-Za-z=\.,:;0-9\-_/" + mask_char + r";]+\})"
        r"(\{[" + _KEY_VALUE_CHARS + mask_char + r";]+\})"
    ).findall(string):
        if match:
            string = string.replace(match, mask_char * len(match))
    return string


def split_by_sep_in_masked_string(
    string: str, masked_string: str, sep: str = ";"
) -> List[str]:
    """Splits a string by a separator, but the separators are searched
    for in an auxiliary string, the "masked_string". This is so in order
    to mask out separator characters that should be ignored due to
    being enclosed in f.ex. curly braces.

    Splitting::
        "foo { bar; com}; hei hopp;"

    with a masked string like::

        "foo XXXXXXXXXXX; hei hopp;"

    results in two components::

        ["foo { bar; com}", "hei hopp"]

    Args:
        string: The string that should be split
        masked_string: Same length as first argument, but where
            only a subset of the separator characters need to match up.
        sep: Separator character, defaults to ";"

    Yields:
        Each part of the input string. Separator
        character is not included
    """

    if len(string) != len(masked_string):
        raise ValueError("string and masked_string do not have equal length")

    if not masked_string:
        return []

    # Delete trailing ";\s" from both masked_string and string
    while masked_string[-1] == " ":
        masked_string = masked_string[0:-1]
        string = string[0:-1]
    if masked_string[-1] == sep:
        masked_string = masked_string[0:-1]
        string = string[0:-1]

    sep_positions = [-1]
    for match in re.finditer(sep, masked_string):
        if string[match.start()] != sep:
            raise ValueError("string and masked_string do not match on separators")
        if match.start() < len(string) - 1:
            sep_positions.append(match.start())
    return list(
        filter(
            len,
            (
                string[i + 1 : j].strip()
                for i, j in zip(sep_positions, sep_positions[1:] + [len(string)])
            ),
        )
    )


def filter_comments(input_str: str, comment_identifier: str = "--") -> str:
    """Strip comments from a multiline string.

    If the comment_identifier, defaults to "--" is found, the remainder
    of the line is stripped. Empty lines are also dropped (being the
    result of comment stripping or not).

    Args:
        input_str (str): String to strip comments from
        comment_identifier (str): Character sequence that marks the rest
            of the line as a comment.

    Returns:
        str: String with newlines where there are no comments, and
        with no empty lines.
    """
    lines = input_str.split("\n")

    # Drop comments
    _lines = (line.strip().split(comment_identifier)[0].strip() for line in lines)

    return "\n".join(filter(len, _lines))


def fix_dtype(value):
    """Guess the correct datatype for an incoming value.

    If parseable as float, return as integer if it is, return float if not.
    If parseable as an ERT date (DD/MM/YYYY), return as datetime.date.

    If not, return as string.

    Args:
        value: Object of any type given it has a string representation.

    Returns:
        int, float, datetime.date or string.
    """
    try:
        int_value = int(float(value))
        float_value = float(value)
        if int_value == float_value:
            return int_value
        return float_value
    except ValueError:
        try:
            return datetime.datetime.strptime(value, ERT_ISO_DATE_FORMAT)
        except ValueError:
            try:
                return datetime.datetime.strptime(value, ERT_DATE_FORMAT)
            except ValueError:
                try:
                    return datetime.datetime.strptime(value, ERT_ALT_DATE_FORMAT)
                except ValueError:
                    return str(value)


def remove_enclosing_curly_braces(string: str) -> str:
    """Removes enclosing curly braces around a string, permitting
    whitespace at start and end, and also a trailing semicolon after
    the curly brace end"""
    if not string:
        return string
    string = string.strip()
    if string[0] == "{":
        string = string[1:].strip()
    if string[-1] == ";":
        string = string[:-1].strip()
    if string[-1] == "}":
        string = string[:-1].strip()
    return string


def parse_observation_unit(obsunit: str) -> dict:
    """Parse one observation, with all its arguments. The string should
    be the content of the curly braces after one of SUMMARYOBSERVATION,
    BLOCK_OBSERVATION,  GENERAL_OBSERVATION or HISTORY_OBSERVATION.

    The submitted string can contain so-called observation subunits
    within curly braces.

    Args:
        string (str): String with observation data to parse.

    Returns:
        dict: Parsed observation data. Data inside curly braces are
        returned in nested dicts.
    """
    obsunit = obsunit.replace("\n", "")
    if not obsunit:
        return {}

    obs_dict = {}
    subunits = {}
    # Split by semi-colons outside curly braces:
    for obs_subunit in OBS_ARGS_RE.findall(obsunit):
        if not obs_subunit[0]:
            # regexp sometimes give empty matches, ignore.
            continue
        if "=" in obs_subunit[0]:
            obs_dict[obs_subunit[0].split("=")[0].strip()] = fix_dtype(
                obs_subunit[0].split("=")[1].strip()
            )
        else:
            # If there is no =, it is not a key-value statement, but
            # a subunit with data in curly braces.
            subunits[obs_subunit[0].strip()] = parse_subobservation_args(obs_subunit[1])
    return {**obs_dict, **subunits}


def parse_subobservation_args(string: str) -> dict:
    """Parse the key=value arguments given to an observation sub-unit

    This is semicolon-separated list of key-values, optionally enclosed in curly
    braces. There should not be curly braces inside this data.

    Args:
        string (str): String to parse.

    Returns:
        dict: Parsed data. Strings are converted to numerical if possible.
    """

    keyvalues = {}
    for keyvalue in remove_enclosing_curly_braces(string).split(";"):
        if not keyvalue:
            continue
        if "=" in keyvalue:
            key, value = keyvalue.split("=")
            keyvalues[key.strip()] = fix_dtype(value.strip())
    return keyvalues


def flatten_observation_unit(
    obsunit: dict, subunit_label: str = "obs_sub_id"
) -> List[Dict[str, str]]:
    """Flatten/unroll a observation unit represented as a nested dict, return
    as a list of dicts.

    Example (written as in the ascii observation format)::

      { FIELD=PRESSURE; OBS P1 {I=1;}; OBS P2 {I=3;}}

    will be returned as::

      [ {'OBS': 'P1', 'FIELD': 'PRESSURE', 'I=1'},
        {'OBS': 'P2', 'FIELD': 'PRESSURE', 'I=3'}]

    If there are overlapping key-names at each nesting level, the
    lower nesting level wins, relevant for SEGMENT_START syntax.

    If there is no nested dict, a list of length 1 is returned.

    If the string "SEGMENT" (case-sensititive) is found,
    this is a special case where we need to inject a "default"
    segment in addition::

      { ERROR=10; SEGMENT S1 { START=2; END=4; ERROR=5;};};

    gives two elements::

      [ {'SEGMENT': 'DEFAULT', 'ERROR': 10},
        {'SEGMENT': 'S1',  'START': 2, 'END': 4, 'ERROR': 5} ]

    Args:
        obsunit (dict): Dictionary describing the contents of an observation.
            (nb: it does not hold the observation type or observation id). If
            there are "observation subunits", then this dict is nested.

    Returns:
        list: List of non-nested dictionaries.
    """
    if subunit_label in obsunit:
        raise ValueError("Conflict, subunit_label cannot be in use")
    subunit_keys = [
        subunit_key
        for subunit_key, subunit_value in obsunit.items()
        if isinstance(subunit_value, dict)
    ]
    if not subunit_keys:
        return [obsunit]
    keyvalue_keys = set(obsunit.keys()) - set(subunit_keys)
    keyvalues = {key: obsunit[key] for key in keyvalue_keys}
    obs_subunits = []

    # Inject a default segment if segments are in use:
    if any("SEGMENT" in key for key in subunit_keys):
        obs_subunits.append({"SEGMENT": "DEFAULT", **keyvalues})

    for subunit in subunit_keys:
        if len(subunit.split()) < 2:
            # It must be two strings, like "OBS P1", or "SEGMENT FIRST_YEAR".
            raise ValueError("Wrong observation subunit syntax: " + str(subunit))
        obs_subunits.append(
            {
                subunit.split()[0]: subunit.split()[1],
                **keyvalues,
                **obsunit[subunit],
            }
        )
    return obs_subunits


def ertobs2df(input_str: str, cwd=".", starttime: Optional[str] = None) -> pd.DataFrame:
    """Parse a string with ERT observations and convert into
    the internal dataframe format.

    Args:
        input_str (str): String in ERT observation syntax. Newlines and
            comments are allowed.
        cwd (str): Path to what should be used as current working directory
            when resolving include statements (for include files). Defaults
            to current directory, but the ERT observation format assumes
            it is the directory of the ERT config file.
        starttime (str): If provided, DAYS data will be interpreted relative
            to this starttime, and converted to DATE.

    Returns:
        pd.DataFrame. The DATE column is always of type datetime64
    """
    ertobs_str = expand_includes(filter_comments(input_str), cwd=cwd)

    # Helper string for splitting correctly on semicolons
    masked_string = mask_curly_braces(ertobs_str)
    obs_list = []
    for observation_unit_str in split_by_sep_in_masked_string(
        ertobs_str, masked_string
    ):
        obs_unit_split = observation_unit_str.replace("{", " {").split()
        # Two or three components depending on observation type.
        if len(obs_unit_split) < 2:
            print(observation_unit_str)
            print(obs_unit_split)
            raise ValueError
        obs_unit = {"CLASS": obs_unit_split[0], "LABEL": obs_unit_split[1]}
        logger.debug("Parsing observation %s %s", obs_unit["CLASS"], obs_unit["LABEL"])
        if len(obs_unit_split) > 2:
            obs_args = " ".join(obs_unit_split[2:])
            logger.debug("Subunit data: %s", str(obs_args))
            for obs_subunit in flatten_observation_unit(
                parse_observation_unit(obs_args)
            ):
                obs_list.append({**obs_unit, **obs_subunit})
        else:
            obs_list.append(obs_unit)

    return compute_date_from_days(pd.DataFrame(obs_list), starttime)


def compute_date_from_days(dframe: pd.DataFrame, starttime: Optional[str] = None):
    """Fill in DATE cells in a dataframe computed from
    a given starttime and data in DAYS cells.

    Args:
        dframe (pd.DataFrame): Any dataframe with a floating point column named DAYS
        starttime (str): If provided, DAYS data will be interpreted relative
            to this starttime, and converted to DATE.

    Returns:
        pd.DataFrame. DATE column is always of type datetime64
    """
    assert isinstance(dframe, pd.DataFrame)
    if starttime and "DAYS" in dframe:
        if "DATE" not in dframe:
            dframe["DATE"] = np.nan
        start = pd.to_datetime(starttime)
        date_needed_rows = ~dframe["DAYS"].isna() & dframe["DATE"].isna()
        dframe["DATE"] = pd.to_datetime(dframe["DATE"])
        dframe.loc[date_needed_rows, "DATE"] = start + pd.to_timedelta(
            dframe.loc[date_needed_rows, "DAYS"], "d"
        )
    if "DATE" in dframe:
        dframe["DATE"] = pd.to_datetime(dframe["DATE"])
    return dframe


def resinsight_df2df(ri_dframe: pd.DataFrame) -> pd.DataFrame:
    """Convert a ResInsight observation dataframe (as it is represented on
    disk) to the internal dataframe representation of observations.

    This is the reverse of writers.df2resinsight_df()

    Args:
        dframe (pd.DataFrame)

    Returns:
        pd.DataFrame
    """
    if ri_dframe.empty:
        return pd.DataFrame()

    dframe = ri_dframe.copy()
    dframe.rename({"VECTOR": "KEY"}, axis="columns", inplace=True)
    dframe["LABEL"] = (
        dframe["KEY"].astype(str)
        + "-"
        + (dframe.groupby("KEY").cumcount() + 1).astype(str)
    )
    dframe["CLASS"] = "SUMMARY_OBSERVATION"
    if "DATE" in dframe:
        dframe["DATE"] = pd.to_datetime(dframe["DATE"])
    return dframe


def smrydictlist2df(smrylist: List[dict]) -> pd.DataFrame:
    """Parse a list structure (subpart of yaml syntax) of summary observations
    into  dataframe format

    Args:
        blocklist (list): List of dictionaries with summary observations

    Returns:
        pd.DataFrame
    """
    rows = []
    for keylist in smrylist:
        if "observations" not in keylist:
            logger.warning("Missing 'observations' list in summary observation")
            continue
        for obs_idx, obs in enumerate(keylist["observations"]):
            rowdict = {"CLASS": "SUMMARY_OBSERVATION", "KEY": keylist["key"]}
            if "comment" in keylist:
                rowdict["COMMENT"] = keylist["comment"]
            # "comment" may be present at two levels in the dictionary, valid
            # for the whole observation, or for individual dated observations.
            # The latter is put into the column "SUBCOMMENT"
            if "comment" in obs:
                obs["subcomment"] = obs["comment"]
                del obs["comment"]
            rowdict.update(uppercase_dictkeys(obs))
            if "label" in keylist:
                logger.warning(
                    "label should be attached to dated observations, ignored label=%s",
                    keylist["label"],
                )
            if "label" not in obs:
                # We need to make up a unique label, indexed from 1 and upwards:
                rowdict["LABEL"] = keylist["key"] + "-" + str(obs_idx + 1)
            rows.append(rowdict)
    dframe = pd.DataFrame(rows)
    if "DATE" in dframe:
        dframe["DATE"] = pd.to_datetime(dframe["DATE"])
    return dframe


def blockdictlist2df(blocklist: List[dict]) -> pd.DataFrame:
    """Parse a list structure (subpart of yaml syntax) of block observations
    into  dataframe format

    The internal dataframe format uses "LABEL" and "OBS" as unique keys
    for individual observations. These are constructed if not present.

    Args:
        blocklist (list): List of dictionaries with block/rft observations

    Returns:
        pd.DataFrame
    """
    rows = []
    # "well" is a required field in yaml syntax, but is
    # not required in ert observation. But in ERT observation
    # syntax and internal dataframe format, a label is mandatory, but not in
    # YAML. A label is made up from well-name and index of observation for the
    # well.
    for keylist in blocklist:
        if "observations" not in keylist:
            logger.warning("Missing 'observations' in rft observation")
            continue
        for obs_idx, obs in enumerate(keylist["observations"]):
            rowdict = {"CLASS": "BLOCK_OBSERVATION"}
            rowdict.update(uppercase_dictkeys(keylist))
            if "OBSERVATIONS" in rowdict:
                del rowdict["OBSERVATIONS"]
            if "label" not in obs:
                rowdict["LABEL"] = keylist["well"]
            if "obs" not in obs:
                # Make up a label for the particular 3D-point for the
                # observation, using P1, P2, etc. as in the ERT doc example.
                rowdict["OBS"] = "P" + str(obs_idx + 1)
            if "comment" in obs:
                # Comments can be present at two level in yaml format, the
                # lower level (pr. individual obs indices) are stored in
                # SUBCOMMENT
                rowdict["SUBCOMMENT"] = obs["comment"]
                del obs["comment"]
            rowdict.update(uppercase_dictkeys(obs))
            rows.append(rowdict)
    dframe = pd.DataFrame(rows)
    if "DATE" in dframe:
        dframe["DATE"] = pd.to_datetime(dframe["DATE"])
    return dframe


def obsdict2df(obsdict: dict) -> pd.DataFrame:
    """Convert an observation dictionary (with YAML file format structure)
    into the internal dataframe representation

    Args:
        obsdict (dict): Dictionary of observations. Top level keys are "smry"
            and/or "rft", pointing to list of dictionaries.

    Returns:
        pd.DataFrame
    """
    if not isinstance(obsdict, dict):
        raise ValueError("obsdict must be a dictionary")

    dframes = []  # List of dicts
    if "smry" in obsdict:
        dframes.append(smrydictlist2df(obsdict["smry"]))
    if "rft" in obsdict:
        dframes.append(blockdictlist2df(obsdict["rft"]))
    return pd.concat(dframes, ignore_index=True)
