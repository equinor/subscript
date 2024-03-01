"""Script for comparing RMS vs Eclipse volumetrics, provided
a mapping between Region and Zones in RMS, to FIPNUMs in Eclipse"""

import argparse
import logging
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import yaml
from fmu.tools.fipmapper import fipmapper
from fmu.tools.rms import volumetrics

from subscript import getLogger
from subscript.prtvol2csv.prtvol2csv import currently_in_place_from_prt

logger = getLogger(__name__)
logger.setLevel(logging.INFO)

DESCRIPTION = """Tool for comparing volumetrics from Eclipse PRT files
with volumetrics from RMS, when the mapping between FIPNUMs and
region/zones is provided in a yaml file.

This script is currently in BETA. The name and calling syntax might change.
"""


def get_parser() -> argparse.ArgumentParser:
    """Set up an argparse parser object for command line interface.

    This is also used to generate documentation."""
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "PRTFILE",
        type=str,
        help="PRT file from Eclipse, alternatively a CSV file with "
        "the output from prtvol2csv",
    )
    parser.add_argument(
        "volumetricsbase",
        type=str,
        help="Path to the filebase of RMS volumetrics output. "
        '"_oil_1.txt" and "_gas_1.txt" will be added this this filebase '
        "in order to locate files.",
    )
    parser.add_argument(
        "fipmapconfig",
        type=str,
        help="Filename to a YAML file providing the map "
        "between region, zones and FIPNUMs",
    )
    parser.add_argument(
        "--sets",
        type=str,
        help="YAML file for where fipnum-region-zone set lists are written",
    )
    parser.add_argument(
        "--output", type=str, help="Output CSV file with comparable volumetrics"
    )
    return parser


def _prefix_keys(prefix: str, somedict: Dict[str, Any]) -> Dict[str, Any]:
    """Add a string prefix to every key of a dictionary"""
    return {prefix + key: value for key, value in somedict.items()}


def _compare_volumetrics(
    disjoint_sets_df: pd.DataFrame,
    simvolumes_df: pd.DataFrame,
    volumetrics_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compare Eclipse and RMS volumetrics over the common disjoints sets.

    Columns stemming from Eclipse data are prefixed with "ECL" when returned,
    columns from RMS with "RMS". Returned columns starting with DIFF are
    absolute differences of eclipse volumes minus RMS volumes.
    """
    set_data_list = []
    for set_idx, regzonfip_set in disjoint_sets_df.groupby("SET"):
        set_results = {"SET": set_idx}
        # Slice and sum simvolumes_df for the FIPNUMS in this set:
        set_fipnums = set(regzonfip_set["FIPNUM"]).intersection(simvolumes_df.index)
        if not set_fipnums:
            # Skip sets for which there are no PRT volume data
            logger.warning(
                "Skipping FIPNUMs %s, no PRT volumes found",
                regzonfip_set["FIPNUM"].to_numpy(),
            )
            continue
        set_results.update(
            _prefix_keys("ECL_", dict(simvolumes_df.loc[list(set_fipnums)].sum()))
        )

        # Slicing in multiindex requires a list of unique tuples:
        regzones = {
            tuple(regzone) for regzone in regzonfip_set[["REGION", "ZONE"]].to_numpy()
        }.intersection({tuple(regzone) for regzone in volumetrics_df.index})
        if not regzones:
            # Skip sets for which there are not volumetrics:
            logger.warning(
                "Skipping regzones %s, no volumetrics found",
                regzonfip_set[["REGION", "ZONE"]].to_numpy(),
            )
            continue
        # Slice and sum RMS volumetrics:
        set_results.update(
            _prefix_keys("RMS_", dict(volumetrics_df.loc[list(regzones)].sum()))
        )

        if "RMS_FACIES" in set_results:
            del set_results["RMS_FACIES"]

        set_data_list.append(set_results)

    comparison_df = pd.DataFrame(set_data_list)

    common_columns = set(volumetrics_df.columns).intersection(simvolumes_df.columns)
    for common in common_columns:
        if "ECL_" + common in comparison_df and "RMS_" + common in comparison_df:
            comparison_df["DIFF_" + common] = (
                comparison_df["ECL_" + common] - comparison_df["RMS_" + common]
            )
    return comparison_df


def _disjoint_sets_to_dict(
    disjoint_sets_df: pd.DataFrame,
) -> Dict[int, Dict[str, list]]:
    """From the dataframe of sets, construct a dictionary indexed by set
    index provide lists of members in the set for FIPNUM, ZONE and REGION"""
    regions = disjoint_sets_df.groupby(["SET"])["REGION"].apply(
        lambda x: sorted(set(x))
    )
    zones = disjoint_sets_df.groupby(["SET"])["ZONE"].apply(lambda x: sorted(set(x)))
    fipnums = disjoint_sets_df.groupby(["SET"])["FIPNUM"].apply(
        lambda x: sorted(set(x))
    )
    return pd.concat([regions, zones, fipnums], axis=1).to_dict(orient="index")


def main() -> None:
    """Parse command line arguments and run"""
    args = get_parser().parse_args()

    if args.PRTFILE.endswith("csv"):
        simvolumes_df = pd.read_csv(args.PRTFILE, index_col="FIPNUM")
    else:
        simvolumes_df = currently_in_place_from_prt(args.PRTFILE, "FIPNUM")

    volumetrics_df = volumetrics.merge_rms_volumetrics(args.volumetricsbase).set_index(
        ["REGION", "ZONE"]
    )

    disjoint_sets_df = fipmapper.FipMapper(yamlfile=args.fipmapconfig).disjoint_sets()

    comparison_df = _compare_volumetrics(
        disjoint_sets_df, simvolumes_df, volumetrics_df
    )
    if args.sets:
        Path(args.sets).write_text(
            yaml.dump(_disjoint_sets_to_dict(disjoint_sets_df)), encoding="utf8"
        )
    if args.output:
        comparison_df.to_csv(args.output, float_format="%g", index=False)
        logger.info("Written %d rows to %s", len(comparison_df), args.output)
    else:
        pd.set_option("display.max_rows", 1000)
        pd.set_option("display.max_columns", 50)
        pd.set_option("display.width", 1000)
        print(disjoint_sets_df)
        print(comparison_df.set_index("SET"))


if __name__ == "__main__":
    main()
