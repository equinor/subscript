"""Parse ERT observation files"""
import os
import re
import sys
import signal
import logging
import datetime

import argparse
import yaml

import pandas as pd

from subscript import getLogger

logger = getLogger(__name__)

DESCRIPTION = """Parser for ERT observation files.

Parses text files into a nested dictionary structure and a Pandas DataFrame
structure. Can be exported to yaml and to CSV.

Observation file syntax:
https://fmu-docs.equinor.com/docs/ert/reference/configuration/observations.html
"""

CATEGORY = "utility.transformation"

EXAMPLES = """
.. code-block:: console
  FORWARD_MODEL ERTOBS2YML(<OBS_FILE>=observations.txt, <CSV_OUTPUT>=observations.csv, <YML_OUTPUT>=observations.yml)
"""  # noqa

# Regular expressions for matching ERT observation files.
# Note that lower-case is supported by the regexp's, but might not be supported
# by ERT.
_WHITESPACE = r"[\s]*"
_KEY_VALUE_CHARS = r"\nA-Za-z:/=_\-\.,0-9\s"
_OBS_CLASS = r"([A-Z_]+)"
_OBS_LABEL = r"([A-Za-z0-9_\-]+)"
_SEMICOLON = _WHITESPACE + ";" + _WHITESPACE

# This avoids nested {}, and avoids capturing trailing ; in matched group
_OPTIONAL_CURLY_SUBGROUP = r"(\{[A-Za-z=0-9\.,_;/\s]*\})?" + _SEMICOLON

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

# Used in yaml file
CLASS_SHORTNAME = {
    "SUMMARY_OBSERVATION": "smry",
    "GENERAL_OBSERVATION": "general",
    "BLOCK_OBSERVATION": "block",
    "HISTORY_OBSERVATION": "hist",
}

ERT_DATE_FORMAT = "%d/%m/%Y"

__MAGIC_NONE__ = "__NONE__"  # For ERT hook defaults support.
__MAGIC_STDOUT__ = "-"


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """Multiple inheritance used for argparse to get both defaults
    and raw description formatter"""

    # pylint: disable=unnecessary-pass
    pass


def get_parser():
    """Return a parser for the command line client, and for
    generating help text"""
    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter, description=DESCRIPTION
    )

    parser.add_argument("obs_file", help="Name of ERT input observation file", type=str)
    parser.add_argument(
        "-o",
        "--yml",
        type=str,
        help="Name of output YAML file. Use '-' to write to stdout.",
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="Name of output CSV file. Use '-' to write to stdout.",
    )
    parser.add_argument(
        "--includedir",
        type=str,
        help=(
            "Path to directory to be used for resolving include filenames. "
            "This path should be set to the directory of the ERT config file, "
            "and the include file statements must be relative to this."
        ),
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    parser.add_argument("--debug", action="store_true", help="Print debugging messages")
    return parser


def expand_includes(input_str, cwd="."):
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
        include_filename = os.path.join(cwd, match.groups()[1])
        logger.info(
            "Injecting include file: %s into observation file", include_filename
        )
        with open(include_filename) as f_handle:
            include_txt = f_handle.read()
        input_str = input_str.replace("".join(match.groups()), include_txt)
        match = INCLUDE_RE.search(input_str)
    return input_str


def mask_curly_braces(string, mask_char="X"):
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
        r"(\{["
        + _KEY_VALUE_CHARS
        + mask_char
        + r";]+\})"
    ).findall(string):
        if match:
            string = string.replace(match, mask_char * len(match))
    return string


def split_by_sep_in_masked_string(string, masked_string, sep=";"):
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
        string (str): The string that should be split
        masked_string (str): Same length as first argument, but where
            only a subset of the separator characters need to match up.
        sep (str): Separator character, defaults to ";"

    Yields:
        string: Each part of the input string. Separator
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
    return filter(
        len,
        (
            string[i + 1 : j].strip()
            for i, j in zip(sep_positions, sep_positions[1:] + [len(string)])
        ),
    )


def filter_comments(input_str, comment_identifier="--"):
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
    lines = (line.strip().split(comment_identifier)[0].strip() for line in lines)

    # Drop empty lines:
    lines = filter(len, lines)

    return "\n".join(lines)


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
            return datetime.datetime.strptime(value, ERT_DATE_FORMAT)
        except ValueError:
            return str(value)


def remove_enclosing_curly_braces(string):
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


def parse_observation_unit(obsunit):
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


def parse_subobservation_args(string):
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


def flatten_observation_unit(obsunit, subunit_label="obs_sub_id"):
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
    if any(["SEGMENT" in key for key in subunit_keys]):
        obs_subunits.append({**{"SEGMENT": "DEFAULT"}, **keyvalues})

    for subunit in subunit_keys:
        if len(subunit.split()) < 2:
            # It must be two strings, like "OBS P1", or "SEGMENT FIRST_YEAR".
            raise ValueError("Wrong observation subunit syntax: " + str(subunit))
        obs_subunits.append(
            {
                **{subunit.split()[0]: subunit.split()[1]},
                **keyvalues,
                **obsunit[subunit],
            }
        )
    return obs_subunits


def ertobs2df(input_str, cwd="."):
    """Parse a string with ERT observations and convert to
    an equivalent tabular format, represented by a Pandas dataframe.

    Args:
        input_str (str): String in ERT observation syntax. Newlines and
            comments are allowed.
        cwd (str): Path to what should be used as current working directory
            when resolving include statements (for include files). Defaults
            to current directory, but the ERT observation format assumes
            it is the directory of the ERT config file.

    Returns:
        pd.DataFrame
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
        obs_unit = {"CLASS": obs_unit_split[0], "LABEL": obs_unit_split[1]}
        logger.info("Parsing observation %s %s", obs_unit["CLASS"], obs_unit["LABEL"])
        if len(obs_unit_split) > 2:
            obs_args = " ".join(obs_unit_split[2:])
            logger.debug("Subunit data: %s", str(obs_args))
            for obs_subunit in flatten_observation_unit(
                parse_observation_unit(obs_args)
            ):
                obs_list.append({**obs_unit, **obs_subunit})
        else:
            obs_list.append(obs_unit)
    return pd.DataFrame(obs_list)


def validate_dframe(obs_df):
    """Validate a dataframe of observations"""
    failed = False
    if obs_df.empty:
        logger.warning("Observation dataframe empty")
        return True
    if "CLASS" not in obs_df:
        logger.error("CLASS is not in dataframe - not valid")
        failed = True
    if "LABEL" not in obs_df:
        logger.error("LABEL is not in dataframe - not valid")
        failed = True
    non_supported_classes = set(CLASS_SHORTNAME.keys()) - set(obs_df["CLASS"])
    if non_supported_classes:
        logger.error("Unsupported observation classes: %s", str(non_supported_classes))
        failed = True

    index = {"CLASS", "LABEL", "OBS", "SEGMENT"}.intersection(set(obs_df.columns))
    repeated_rows = obs_df[obs_df.set_index(list(index)).index.duplicated(keep=False)]
    if not repeated_rows.empty:
        logger.error("Non-unique observation classes and labels")
        logger.error("\n%s", str(repeated_rows))
        failed = True

    # check that segment has start and end if not default.
    # summary obs requires four arguments.
    # block requires two global, and i,j,k,value,error for each subunit.
    # general requires data, restart, obs_file. index_list, index_file,
    # error_covariance is optional.
    return not failed


def df2obsdict(obs_df):
    """Generate a dictionary structure of all observations, this data structure
    is designed to look good in yaml, and is supported by WebViz and
    fmu-ensemble.

    Args:
        obs_df (pd.DataFrame): Dataframe representing ERT observations.

    Returns:
        dict
    """
    obsdict = {}
    if "CLASS" not in obs_df:
        return {}
    if "DATE" in obs_df:
        obs_df = obs_df.copy()
        obs_df["DATE"] = obs_df["DATE"].astype(str)

    if "SUMMARY_OBSERVATION" in obs_df["CLASS"].values:
        # Start with an empty list:
        obsdict[CLASS_SHORTNAME["SUMMARY_OBSERVATION"]] = []
        # Now group by KEY:
        for key in obs_df[obs_df["CLASS"] == "SUMMARY_OBSERVATION"]["KEY"].unique():
            sum_key_dict = {"key": key}
            sum_key_observations = []
            for _, obs_unit in obs_df[
                (obs_df["CLASS"] == "SUMMARY_OBSERVATION") & (obs_df["KEY"] == key)
            ].iterrows():

                # print(str({**(obs_unit.dropna())}))
                obs_unit_dict = {**(obs_unit.dropna())}
                del obs_unit_dict["KEY"]
                del obs_unit_dict["CLASS"]
                if "DATE" in obs_unit_dict and obs_unit_dict["DATE"] == "NaT":
                    del obs_unit_dict["DATE"]
                obs_unit_dict = {
                    key.lower(): value for key, value in obs_unit_dict.items()
                }
                if obs_unit_dict:
                    sum_key_observations.append(obs_unit_dict)
            if sum_key_observations:
                sum_key_dict["observations"] = sum_key_observations
            obsdict[CLASS_SHORTNAME["SUMMARY_OBSERVATION"]].append(sum_key_dict)
    return obsdict


def main():
    """Command line client, parse command line arguments and run function."""
    parser = get_parser()
    args = parser.parse_args()

    if args.verbose:
        if __MAGIC_STDOUT__ in (args.csv, args.yml):
            raise SystemExit("Don't use verbose mode when writing to stdout")
        logger.setLevel(logging.INFO)

    if args.debug:
        logger.setLevel(logging.DEBUG)

    with open(args.obs_file) as f_handle:
        input_str = f_handle.read()

    if not args.includedir or args.includedir == __MAGIC_NONE__:
        # Try and error for the location of include files, first in current
        # dir, then in the directory of the input file. The proper default
        # for cwd is the location of the ert config file, which is not
        # available in this parser, and must be supplied on command line.
        try:
            dframe = ertobs2df(input_str, cwd=".")
        except FileNotFoundError:
            dframe = ertobs2df(input_str, cwd=os.path.dirname(args.obs_file))
    else:
        dframe = ertobs2df(input_str, cwd=args.includedir)

    if not validate_dframe(dframe):
        logger.error("Observation dataframe is invalid!")

    dump_results(dframe, args.csv, args.yml)


def dump_results(dframe, csvfile=None, yamlfile=None):
    """Dump dataframe with ERT observations to CSV and/or YML
    format to disk. Writes to stdout if filenames are "-". Skips
    export if filenames are empty.

    Args:
        dframe (pd.DataFrame)
        csvfile (str): Filename
        yamlfile (str): Filename
    """

    if csvfile and csvfile != __MAGIC_NONE__:
        if csvfile != __MAGIC_STDOUT__:
            logger.info("Writing observations as CSV to %s", csvfile)
            dframe.to_csv(csvfile, index=False)
        else:
            # Ignore pipe errors when writing to stdout:
            signal.signal(signal.SIGPIPE, signal.SIG_DFL)
            dframe.to_csv(sys.stdout, index=False)

    if yamlfile and yamlfile != __MAGIC_NONE__:
        obs_dict_for_yaml = df2obsdict(dframe)
        yaml_str = yaml.safe_dump(obs_dict_for_yaml)

        if yamlfile != __MAGIC_STDOUT__:
            with open(yamlfile, "w") as f_handle:
                f_handle.write(yaml_str)
        else:
            print(yaml_str)


if __name__ == "__main__":
    main()
