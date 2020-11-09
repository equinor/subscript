import numpy as np
import pandas as pd

from subscript import getLogger


from subscript.ertobs.parsers import lowercase_dictkeys

logger = getLogger(__name__)

# Used in yaml file
CLASS_SHORTNAME = {
    "SUMMARY_OBSERVATION": "smry",
    "GENERAL_OBSERVATION": "general",
    "BLOCK_OBSERVATION": "rft",
    "HISTORY_OBSERVATION": "hist",
}


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
                ["FIELD", "LABEL", "DATE"], axis=1, errors="ignore",
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
