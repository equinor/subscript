"""Parse ERT observation files"""
import os
import sys
import signal
import logging

import argparse
import yaml

import pandas as pd

from subscript import getLogger

from subscript.ertobs.parsers import ertobs2df
from subscript.ertobs.writers import df2obsdict, df2resinsight_df, CLASS_SHORTNAME

logger = getLogger(__name__)

DESCRIPTION = """Parser for ERT observation files.

Will read ERT observation file format, YAML file format, CSV file format
or ResInsight file format, and can write to any of the other formats.

Internal data structure for all data formats is a Pandas DataFrame, which can
be dumped as CSV. YAML and ResInsight formats only supports a subset of
observation data in ERT observation files, while YAML file may also contain more
information that cannot be brought over to other formats.

ERT observation file syntax:
https://fmu-docs.equinor.com/docs/ert/reference/configuration/observations.html
"""

CATEGORY = "utility.transformation"

EXAMPLES = """
.. code-block:: console
  FORWARD_MODEL ERTOBS(<INPUT_FILE>=observations.txt, <RESINSIGHT_OUTPUT>=observations-ri.csv, <YML_OUTPUT>=observations.yml)
"""  # noqa

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

    parser.add_argument(
        "input_file",
        help="Input file, in any of the supported observation formats",
        type=str,
    )
    parser.add_argument(
        "-o",
        "--yml",
        "--yaml",
        type=str,
        help="Name of output YAML file. Use '-' to write to stdout.",
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="Name of output CSV file. Use '-' to write to stdout.",
    )
    parser.add_argument(
        "--resinsight",
        type=str,
        help="Name of ResInsight observations CSV file. Use '-' to write to stdout.",
    )
    parser.add_argument(
        "--ertobs",
        type=str,
        help="Name of ERT observation file. Use '-' to write to stdout.",
    )
    parser.add_argument(
        "--starttime",
        "--startdate",
        type=str,
        default=None,
        help="Starttime or startdate to be used for converting DAYS to date(time)s",
    )
    parser.add_argument(
        "--includedir",
        type=str,
        help=(
            "Path to directory to be used for resolving include filenames "
            "when parsing ERT observation files. "
            "This path should be set to the directory of the ERT config file, "
            "and the include file statements must be relative to this."
        ),
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    parser.add_argument("--debug", action="store_true", help="Print debugging messages")
    return parser


def validate_internal_dframe(obs_df):
    """Validate the internal dataframe format for observations. """
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
    non_supported_classes = set(obs_df["CLASS"]) - set(CLASS_SHORTNAME.keys())
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
    # block requires two global, and j,k,value,error for each subunit.
    # general requires data, restart, obs_file. index_list, index_file,
    # error_covariance is optional.
    logger.info("Observation dataframe validated")
    return not failed


def autoparse_file(filename):
    """Detects which kind of observation file format a given filename has. This
    is done by attempting to parse its content.

    Args:
        filename (str)

    Returns:
        tuple: First element is a string in [resinsight, csv, yaml, ert], second
        element is a dataframe or a dict (if input was yaml).
    """
    try:
        dframe = pd.read_csv(filename, sep=";")
        if {"DATE", "VECTOR", "VALUE", "ERROR"}.issubset(
            set(dframe.columns)
        ) and not dframe.empty:
            return ("resinsight", dframe)
    except ValueError:
        pass

    try:
        dframe = pd.read_csv(filename, sep=",")
        if {"CLASS", "LABEL"}.issubset(dframe.columns) and not dframe.empty:
            return ("csv", dframe)
    except ValueError:
        pass

    try:
        with open(filename) as f_handle:
            obsdict = yaml.safe_load(f_handle.read())
        if "smry" or "rft" in obsdict:
            return ("yaml", obsdict)
    except ValueError:
        pass

    try:
        with open(filename) as f_handle:
            dframe = ertobs2df(f_handle.read())
        if {"CLASS", "LABEL"}.issubset(dframe.columns) and not dframe.empty:
            return ("ert", dframe)
    except ValueError:
        pass

    logger.error("Unable to parse %s as any supported observation file format")
    return (None, pd.DataFrame)


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

    with open(args.input_file) as f_handle:
        input_str = f_handle.read()

    if not args.includedir or args.includedir == __MAGIC_NONE__:
        # Try and error for the location of include files, first in current
        # dir, then in the directory of the input file. The proper default
        # for cwd is the location of the ert config file, which is not
        # available in this parser, and must be supplied on command line.
        try:
            dframe = ertobs2df(input_str, cwd=".", starttime=args.starttime)
        except FileNotFoundError:
            dframe = ertobs2df(
                input_str,
                cwd=os.path.dirname(args.input_file),
                starttime=args.starttime,
            )
    else:
        dframe = ertobs2df(input_str, cwd=args.includedir, starttime=args.starttime)

    if not validate_internal_dframe(dframe):
        logger.error("Observation dataframe is invalid!")

    dump_results(dframe, args.csv, args.yml, args.resinsight)


def dump_results(dframe, csvfile=None, yamlfile=None, resinsightfile=None):
    """Dump dataframe with ERT observations to CSV and/or YML
    format to disk. Writes to stdout if filenames are "-". Skips
    export if filenames are empty or None.

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
        if not obs_dict_for_yaml and not dframe.empty:
            logger.error("None of your observations are supported in YAML")
        yaml_str = yaml.safe_dump(obs_dict_for_yaml)

        if yamlfile != __MAGIC_STDOUT__:
            with open(yamlfile, "w") as f_handle:
                f_handle.write(yaml_str)
        else:
            print(yaml_str)

    if resinsightfile and resinsightfile != __MAGIC_NONE__:
        ri_dframe = df2resinsight_df(dframe)
        if resinsightfile != __MAGIC_STDOUT__:
            logger.info(
                "Writing observations in ResInsight format to CSV-file: %s",
                resinsightfile,
            )
            ri_dframe.to_csv(resinsightfile, index=False, sep=";")
        else:
            # Ignore pipe errors when writing to stdout:
            signal.signal(signal.SIGPIPE, signal.SIG_DFL)
            ri_dframe.to_csv(sys.stdout, index=False, sep=";")


if __name__ == "__main__":
    main()
