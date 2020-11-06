"""Parse ERT observation files"""
import os
import sys
import signal
import logging

import argparse
import yaml

import numpy as np
import pandas as pd

from subscript import getLogger

from subscript.ertobs2yml.ertobs_parser import (
    lowercase_dictkeys,
    ertobs2df,
)

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

__MAGIC_NONE__ = "__NONE__"  # For ERT hook defaults support.
__MAGIC_STDOUT__ = "-"

# Used in yaml file
CLASS_SHORTNAME = {
    "SUMMARY_OBSERVATION": "smry",
    "GENERAL_OBSERVATION": "general",
    "BLOCK_OBSERVATION": "rft",
    "HISTORY_OBSERVATION": "hist",
}


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
        "--resinsight",
        type=str,
        help="Name of ResInsight observations CSV file. Use '-' to write to stdout.",
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


def summary_df2obsdict(smry_df):
    """Generate a dictionary structure suitable for yaml
    for summary observations in dataframe representation

    Args:
        sum_df (pd.DataFrame)
    Returns:
        list: List of dictionaries, each dict has "key" and "observation"
    """
    assert isinstance(smry_df, pd.DataFrame)
    if "CLASS" in smry_df:
        assert len(smry_df["CLASS"].unique()) == 1
        smry_df.drop("CLASS", axis=1, inplace=True)

    smry_obs_list = []
    if isinstance(smry_df, pd.DataFrame):
        smry_df.dropna(axis=1, how="all", inplace=True)

    if "DATE" not in smry_df:
        raise ValueError("Can't have summary observation without a date")

    for smrykey, smrykey_df in smry_df.groupby("KEY"):
        if isinstance(smrykey_df, pd.DataFrame):
            smrykey_df.drop("KEY", axis=1, inplace=True)
        smry_obs_list.append(
            {
                "key": smrykey,
                "observations": [
                    lowercase_dictkeys(dict(keyvalues.dropna()))
                    for _, keyvalues in smrykey_df.iterrows()
                ],
            }
        )

    return smry_obs_list


def block_df2obsdict(block_df):
    """Generate a dictionary structure suitable for yaml
    for block observations in dataframe representation

    Args:
        block_df (pd.DataFrame)
    Returns:
        list: List of dictionaries, each dict has "well", "date" and
        "observations"
    """
    assert isinstance(block_df, pd.DataFrame)

    block_obs_list = []
    if "CLASS" in block_df:
        assert len(block_df["CLASS"].unique()) == 1
        block_df.drop("CLASS", axis=1, inplace=True)

    if "DATE" not in block_df:
        raise ValueError("Can't have rft/block observation without a date")

    block_df.dropna(axis=1, how="all", inplace=True)

    for blocklabel, blocklabel_df in block_df.groupby(["LABEL", "DATE"]):
        blocklabel_dict = {}
        if "WELL" not in blocklabel_df:
            blocklabel_dict["well"] = blocklabel[0]
        else:
            blocklabel_dict["well"] = blocklabel_df["WELL"].unique()[0]
            blocklabel_dict["label"] = blocklabel[0]
        blocklabel_dict["date"] = blocklabel[1]
        if "FIELD" in blocklabel_df:
            blocklabel_dict["field"] = blocklabel_df["FIELD"].unique()[0]
        blocklabel_dict["observations"] = [
            lowercase_dictkeys(dict(keyvalues.dropna()))
            for _, keyvalues in blocklabel_df.drop(
                ["FIELD", "LABEL", "DATE"],
                axis=1,
                errors="ignore",
            ).iterrows()
        ]
        block_obs_list.append(blocklabel_dict)
    return block_obs_list


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

    # Format dates as strings in yaml:
    if "DATE" in obs_df:
        obs_df = obs_df.copy()
        obs_df["DATE"] = obs_df["DATE"].astype(str)
        obs_df["DATE"].replace("NaT", np.nan, inplace=True)

    # Process SUMMARY_OBSERVATION:
    if "SUMMARY_OBSERVATION" in obs_df["CLASS"].values:
        obsdict[CLASS_SHORTNAME["SUMMARY_OBSERVATION"]] = summary_df2obsdict(
            obs_df.set_index("CLASS").loc[["SUMMARY_OBSERVATION"]]
        )

    # Process BLOCK_OBSERVATION:
    if "BLOCK_OBSERVATION" in obs_df["CLASS"].values:
        obsdict[CLASS_SHORTNAME["BLOCK_OBSERVATION"]] = block_df2obsdict(
            obs_df.set_index("CLASS").loc[["BLOCK_OBSERVATION"]]
        )

    return obsdict


def df2resinsight_df(obs_df):
    """Generate a dataframe observation representation supported by ResInsight.

    Only a subset of the observations can be written to this representation.

    See https://resinsight.org/import/observeddata

    The "Line based CSV" format is chosen by this function, as it is closer
    to the internal dataframe representation.

    Args:
        obs_df (pd.DataFrame): Dataframe representation of observations, this format
            is internal to this module, and is nothing but a flattening

    Returns:
        pd.DataFrame. This can be written directly to disk as CSV and
        imported into the ResInsight application"""

    ri_column_names = ["DATE", "VECTOR", "VALUE", "ERROR"]
    ri_df = obs_df.copy()

    # Only SUMMARY_OBSERVATION is supported:
    ri_df = ri_df[ri_df["CLASS"] == "SUMMARY_OBSERVATION"]

    ri_df.rename({"KEY": "VECTOR"}, axis="columns", inplace=True)

    # Ensure all vectors are present:
    for ri_vec in ri_column_names:
        if ri_vec not in ri_df:
            ri_df[ri_vec] = np.nan

    # Observations without a DATE (but probably with RESTART defined) cannot
    # be exported to ResInsight. Warn about those:
    obs_no_date = ri_df[ri_df["DATE"].isna()]
    if not obs_no_date.empty:
        logger.warning("Some observations are missing DATE, these are skipped")
        logger.warning("\n %s", str(obs_no_date.dropna(axis="columns", how="all")))

    # Slice out only the columns we want, in a predefined order:
    return ri_df[ri_column_names].dropna(axis="rows", subset=["DATE"])


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
