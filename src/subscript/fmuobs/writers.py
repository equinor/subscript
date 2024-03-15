"""Support functions for usage with fmuobs, for converting from the internal
dataframe format to ERT observation format, YAML format and ResInsight
format"""

import re
from typing import List

import numpy as np
import pandas as pd

from subscript import getLogger
from subscript.fmuobs.util import (
    CLASS_SHORTNAME,
    ERT_ISO_DATE_FORMAT,
    lowercase_dictkeys,
)

logger = getLogger(__name__)


def dfsummary2ertobs(obs_df: pd.DataFrame) -> str:
    """Write SUMMARY_OBSERVATION as ERT observations

    Args:
        obs_df: Observations in internal dataframe
            representation

    Returns:
        ERT observation format string, multiline
    """
    ertobs_str = ""
    smry_df = obs_df[obs_df["CLASS"] == "SUMMARY_OBSERVATION"].copy()
    for _, row in smry_df.iterrows():
        ertobs_str += "SUMMARY_OBSERVATION " + str(row["LABEL"]) + "\n"
        ertobs_str += "{\n"
        if "COMMENT" in row and not pd.isnull(row["COMMENT"]):
            ertobs_str += (
                "    -- "
                + str(row["COMMENT"]).replace("\n", "\n    -- ").strip()
                + "\n"
            )
        if "DATE" in row and not pd.isnull(row["DATE"]):
            ertobs_str += (
                "    DATE = "
                + str(pd.to_datetime(row["DATE"]).strftime(ERT_ISO_DATE_FORMAT))
                + ";\n"
            )
        for dataname in ["KEY", "DAYS", "RESTART", "VALUE", "ERROR", "SOURCE"]:
            if dataname in row and not pd.isnull(row[dataname]):
                ertobs_str += "    " + dataname + " = " + str(row[dataname]) + ";\n"
        ertobs_str += "};\n"
    return ertobs_str


def dfblock2ertobs(obs_df: pd.DataFrame) -> str:
    """Write BLOCK_OBSERVATION from dataframe rows as ERT observations

    Args:
        obs_df: Observations in internal dataframe
            representation

    Returns:
        ERT observation format string, multiline
    """
    ertobs_str = ""
    block_obs_df = obs_df[obs_df["CLASS"] == "BLOCK_OBSERVATION"].copy()
    if "DATE" in block_obs_df:
        block_obs_df["DATE"] = pd.to_datetime(block_obs_df["DATE"]).dt.strftime(
            ERT_ISO_DATE_FORMAT
        )
    for obslabel, block_df in block_obs_df.groupby("LABEL"):
        ertobs_str += "BLOCK_OBSERVATION " + obslabel + "\n{\n"
        if "COMMENT" in block_df and not pd.isnull(block_df["COMMENT"]).any():
            if len(block_df["COMMENT"].dropna().unique()) != 1:
                logger.warning("Inconsistency in COMMENT in block dataframe")
            ertobs_str += (
                "    -- "
                + str(block_df["COMMENT"].values[0]).replace("\n", "\n    -- ").strip()
                + "\n"
            )
        for dataname in ["FIELD", "DATE"]:
            if dataname in block_df.columns:
                if len(block_df[dataname].unique()) == 1:
                    ertobs_str += (
                        "    "
                        + dataname
                        + " = "
                        + str(block_df[dataname].values[0])
                        + ";\n"
                    )
                else:
                    # This inconsistency is critical
                    raise ValueError(
                        f"block dataframe for one label has multiple {dataname}"
                    )
        for _, row in block_df.iterrows():
            if "SUBCOMMENT" in row and not pd.isnull("SUBCOMMENT"):
                ertobs_str += (
                    "    -- "
                    + str(row["SUBCOMMENT"]).strip().replace("\n", "\n    -- ").strip()
                    + "\n"
                )
            ertobs_str += "    OBS " + row["OBS"] + " {"
            for dataname in ["I", "J", "K", "VALUE", "ERROR", "SOURCE"]:
                if dataname in row and not pd.isnull(row[dataname]):
                    ertobs_str += " " + dataname + " = " + str(row[dataname]) + ";"
            ertobs_str += "};\n"
        ertobs_str += "};\n"
    return ertobs_str


def dfhistory2ertobs(obs_df: pd.DataFrame) -> str:
    """Write HISTORY_OBSERVATION from dataframe rows as ERT observations

    The SEGMENT structure is a little bit peculiar, as its presence means
    an extra DEFAULT segment is present in the internal dataframe representation.

    Args:
        obs_df: Observations in internal dataframe
            representation

    Returns:
        ERT observation format string, multiline
    """
    ertobs_str = ""
    history_obs_df = obs_df[obs_df["CLASS"] == "HISTORY_OBSERVATION"]
    for histlabel, history_df in history_obs_df.groupby("LABEL"):
        if "SEGMENT" not in history_df:
            history_df["SEGMENT"] = "DEFAULT"
        else:
            history_df["SEGMENT"] = history_obs_df["SEGMENT"].fillna(value="DEFAULT")
        ertobs_str += "HISTORY_OBSERVATION " + histlabel + " \n"
        ertobs_str += "{\n"
        # Write statements for the implicit DEFAULT segment.
        default_row = (
            history_df[history_df["SEGMENT"] == "DEFAULT"]
            .dropna(axis="columns")
            .to_dict(orient="records")[0]
        )
        for dataname in ["ERROR", "ERROR_MODE", "ERROR_MIN"]:
            if dataname in default_row and not pd.isnull(default_row[dataname]):
                ertobs_str += (
                    "  " + dataname + " = " + str(default_row[dataname]) + ";\n"
                )
        for _, row in history_df.iterrows():
            if "SEGMENT" in row and not pd.isnull(row["SEGMENT"]):
                if row["SEGMENT"] == "DEFAULT":
                    continue
                ertobs_str += "  SEGMENT " + row["SEGMENT"] + " {"
                for dataname in ["START", "STOP", "ERROR", "ERROR_MODE"]:
                    if dataname in row and not pd.isnull(row[dataname]):
                        ertobs_str += " " + dataname + " = " + str(row[dataname]) + ";"
                ertobs_str += "};\n"
        ertobs_str += "};\n"

    # Remove empty curly braces and return
    return re.compile(r"\s*{\s*}\s*;").sub(";", ertobs_str)


def dfgeneral2ertobs(obs_df: pd.DataFrame) -> str:
    """Write GENERAL_OBSERVATION from dataframe rows as ERT observations


    Args:
        obs_df: Observations in internal dataframe
            representation

    Returns:
        ERT observation format string, multiline
    """
    ertobs_str = ""
    gen_obs_df = obs_df[obs_df["CLASS"] == "GENERAL_OBSERVATION"]
    if "DATE" in gen_obs_df:
        gen_obs_df["DATE"] = pd.to_datetime(gen_obs_df["DATE"]).dt.strftime(
            ERT_ISO_DATE_FORMAT
        )
    for _, row in gen_obs_df.iterrows():
        ertobs_str += "GENERAL_OBSERVATION " + str(row["LABEL"]) + " {\n"
        for dataname in [
            "DATA",
            "RESTART",
            "DATE",
            "DAYS",
            "OBS_FILE",
            "INDEX_LIST",
            "ERROR_COVAR",
        ]:
            if dataname in row and not pd.isnull(row[dataname]):
                ertobs_str += "    " + dataname + " = " + str(row[dataname]) + ";\n"
        ertobs_str += "};\n"

    # Remove empty curly braces and return
    return re.compile(r"\s*{\s*}\s*;").sub(";", ertobs_str)


def df2ertobs(obs_df: pd.DataFrame) -> str:
    """Generate a complete set of ERT observations from a dataframe
    with potentially all classes of observations.

    The order of observation classes is hardcoded.

    The order of observations within each class follows the order in the
    dataframe.

    Args:
        obs_df: Observations in internal dataframe format

    Returns:
        ERT observations as multiline string.
    """
    assert isinstance(obs_df, pd.DataFrame)
    ertobs_str = ""
    if "CLASS" not in obs_df:
        return ertobs_str
    ertobs_str += dfsummary2ertobs(obs_df[obs_df["CLASS"] == "SUMMARY_OBSERVATION"])
    ertobs_str += dfblock2ertobs(obs_df[obs_df["CLASS"] == "BLOCK_OBSERVATION"])
    ertobs_str += dfhistory2ertobs(obs_df[obs_df["CLASS"] == "HISTORY_OBSERVATION"])
    ertobs_str += dfgeneral2ertobs(obs_df[obs_df["CLASS"] == "GENERAL_OBSERVATION"])
    return ertobs_str


def summary_df2obsdict(smry_df: pd.DataFrame) -> List[dict]:
    """Generate a dictionary structure suitable for yaml
    for summary observations in dataframe representation

    At level 2 in the obs-dict, "key" is the Eclipse summary vector name
    The label is an artificial label used in the ERT observation format, and
    is superfluous in the dict format. The "key" cannot in general be
    used as label, since it is not unique over dates, while the label has to be.

    Note: The labels in ert observation format is not possible to preserve while going
    through the dictionary format (because the way dates are rolled over). But
    a potential column LABEL will be included as "label".

    Args:
        sum_df
    Returns:
        List of dictionaries, each dict has "key" and "observation"
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

    smry_df = convert_dframe_date_to_str(smry_df)

    if "KEY" not in smry_df:
        logger.warning("KEY not provided when generating YAML for summary observations")
        logger.warning("Using LABEL, but this might not be Eclipse summary vectors.")
        smry_df["KEY"] = smry_df["LABEL"]
    for smrykey, smrykey_df in smry_df.groupby("KEY"):
        smry_obs_element = {}
        smry_obs_element["key"] = smrykey
        if "COMMENT" in smrykey_df and not pd.isnull(smrykey_df["COMMENT"]).all():
            smry_obs_element["comment"] = smrykey_df["COMMENT"].unique()[0]
        if isinstance(smrykey_df, pd.DataFrame):
            smrykey_df.drop("KEY", axis=1, inplace=True)
        if "SUBCOMMENT" in smrykey_df:
            smrykey_df["COMMENT"] = smrykey_df["SUBCOMMENT"]
            del smrykey_df["SUBCOMMENT"]
        observations = [
            lowercase_dictkeys(dict(keyvalues.dropna()))
            for _, keyvalues in smrykey_df.iterrows()
        ]
        smry_obs_element["observations"] = observations
        smry_obs_list.append(smry_obs_element)

    return smry_obs_list


def convert_dframe_date_to_str(dframe: pd.DataFrame) -> pd.DataFrame:
    """Convert the DATE column in a dataframe to a string.
    Replace "NaT" (Not-a-Time) with np.nan after conversion

    Returns a copy of the dataframe if something is modified

    Returns the input if DATE is not found in the input frame.

    Args:
        dframe (pd.DataFrame): dataframe to manipulate

    Returns:
        pd.DataFrame: DATE as a string type
    """
    if "DATE" in dframe:
        dframe = dframe.copy()
        dframe["DATE"] = (
            dframe["DATE"]
            .astype(str)
            .replace(["NaT", "NaN", "nan"], np.nan)
            .infer_objects()
        )

    return dframe


def block_df2obsdict(block_df: pd.DataFrame) -> List[dict]:
    """Generate a dictionary structure suitable for yaml
    for block observations in dataframe representation

    Args:
        block_df

    Returns:
        List of dictionaries, each dict has "well", "date" and
        "observations"
    """
    assert isinstance(block_df, pd.DataFrame)

    block_obs_list = []
    if "CLASS" in block_df:
        assert len(block_df["CLASS"].unique()) == 1
        block_df.drop("CLASS", axis=1, inplace=True)

    if "DATE" not in block_df:
        raise ValueError("Can't have rft/block observation without a date")

    block_df = convert_dframe_date_to_str(block_df)

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
        if "COMMENT" in blocklabel_df:
            blocklabel_dict["comment"] = blocklabel_df["COMMENT"].unique()[0]
        # Now overwrite the COMMENT column in order to inject
        # the SUBCOMMENT at the lower level in the dict.
        if "SUBCOMMENT" in blocklabel_df:
            blocklabel_df["COMMENT"] = blocklabel_df["SUBCOMMENT"]
        blocklabel_dict["observations"] = [
            lowercase_dictkeys(dict(keyvalues.dropna()))
            for _, keyvalues in blocklabel_df.drop(
                ["FIELD", "LABEL", "DATE", "WELL", "SUBCOMMENT"],
                axis=1,
                errors="ignore",
            ).iterrows()
        ]
        # if "subcomment" in blocklabel_dict:
        #    blocklabel_dict["comment"] = blocklabel_dict.pop("subcomment")
        block_obs_list.append(blocklabel_dict)
    return block_obs_list


def df2obsdict(obs_df: pd.DataFrame) -> dict:
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


def df2resinsight_df(obs_df: pd.DataFrame) -> pd.DataFrame:
    """Generate a dataframe observation representation supported by ResInsight.

    Only a subset of the observations can be written to this representation.

    See https://resinsight.org/import/observeddata

    The "Line based CSV" format is chosen by this function, as it is closer
    to the internal dataframe representation.

    Args:
        obs_df: Dataframe representation of observations, this format
            is internal to this module, and is nothing but a flattening

    Returns:
        This can be written directly to disk as CSV and
        imported into the ResInsight application"""

    ri_column_names = ["DATE", "VECTOR", "VALUE", "ERROR"]
    ri_dframe = obs_df.copy()

    # Only SUMMARY_OBSERVATION is supported:
    ri_dframe = ri_dframe[ri_dframe["CLASS"] == "SUMMARY_OBSERVATION"]

    ri_dframe.rename({"KEY": "VECTOR"}, axis="columns", inplace=True)

    # Ensure all vectors are present:
    for ri_vec in ri_column_names:
        if ri_vec not in ri_dframe:
            ri_dframe[ri_vec] = np.nan

    # Observations without a DATE (but probably with RESTART defined) cannot
    # be exported to ResInsight. Warn about those:
    obs_no_date = ri_dframe[ri_dframe["DATE"].isna()]
    if not obs_no_date.empty:
        logger.warning("Some observations are missing DATE, these are skipped")
        logger.warning("\n %s", str(obs_no_date.dropna(axis="columns", how="all")))

    # Slice out only the columns we want, in a predefined order:
    return ri_dframe[ri_column_names].dropna(axis="rows", subset=["DATE"])
