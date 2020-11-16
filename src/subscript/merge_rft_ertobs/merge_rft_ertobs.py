import os
import glob
import argparse
import logging

import numpy as np
import pandas as pd

import subscript

logger = subscript.getLogger(__name__)

DESCRIPTION = """Collect ERT RFT observations and merge with CSV output
from GENDATA_RFT. Dump to CSV file for visualization in Webviz.

Only works with a single report step pr RFT measurement.
"""

CATEGORY = "utility.transformation"

EXAMPLES = """
.. code-block:: console

  FORWARD_MODEL MERGE_RFT_ERTOBS(<GENDATACSV>=gendata_rft.csv, <OBSDIR>=<CONFIG_PATH>/input/observations/rft)

"""  # noqa


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """Multiple inheritance used for argparse to get both defaults
    and raw description formatter"""

    # pylint: disable=unnecessary-pass
    pass


def get_parser():
    """Set up a parser for the command line utility"""
    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter, description=DESCRIPTION
    )

    parser.add_argument(
        "gendatacsv",
        type=str,
        help=(
            "Filename with simulated RFT information in CSV,"
            " assumed produced by GENDATA_RFT"
        ),
    )

    parser.add_argument("obsdir", type=str, help="Directory with ERT observation data")
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    parser.add_argument("-o", "--output", type=str, help="Output CSV file")
    return parser


def get_observations(obsdir="", filepattern="*.obs"):
    """
    Gather observation data from a directory of input filenames, or later
    from ERT storage api.

    Reads all files matching `*.obs` in the given directory.
    *This means that multiple report steps are not supported*.

    The dataframe will have the columns:

    order
        order of measurements as they appeared in the obsfile.
    obs
        observed pressure
    error
        assumed pressure error
    well
        name of well, deduced from filenames.

    Column names are made to match Webviz RFT plotter,

    https://github.com/equinor/webviz-subsurface/blob/master/webviz_subsurface/plugins/_rft_plotter/rft_plotter.py

    The column names are intentionally made compatible with columns
    emitted by ``semeio/gendata_rft``

    Args:
        obsfile (str): Path to a directory with observation files
        filepattern (str): Glob-filename pattern for observation files,
            default `*.obs`. If this is changed, deducing name of well
            from filename might fail.
    Return:
        pd.DataFrame

    """  # noqa
    if "/" in filepattern:
        raise ValueError("Do not include paths in filepattern")

    obs_dfs = []
    for obsfilename in glob.glob(os.path.join(obsdir, filepattern)):
        # Warning: Deducing the wellname this way will fail for
        # exotic filepatterns.
        wellname = os.path.basename(obsfilename).split(filepattern.replace("*", ""))[
            0:-1
        ][0]
        try:
            wellobs = (
                pd.read_csv(
                    obsfilename,
                    sep=r"\s+",
                    header=None,
                    names=["observed", "error"],
                    dtype=np.float64,
                )
                .reset_index()
                .rename({"index": "order"}, axis="columns")
                .assign(well=wellname)
            )[["order", "well", "observed", "error"]].dropna()
            if not wellobs.empty:
                obs_dfs.append(wellobs)
        except ValueError:
            logger.warning(
                "File %s could not be parsed as ERT observations, skipped.", obsfilename
            )

    if obs_dfs:
        return pd.concat(obs_dfs)
    logger.warning("No observation data was parsed from %s", obsdir)
    return pd.DataFrame()


def merge_rft_ertobs(gendatacsv, obsdir):
    """Main function for merge_rft_ertobs named arguments.

    Arguments correspond to argparse documentation
    """

    sim_df = pd.read_csv(gendatacsv)
    if not {"well", "order", "pressure"}.issubset(set(sim_df.columns)):
        raise ValueError(
            "Need at least the columns well, order and pressure in {}".format(
                gendatacsv
            )
        )
    # Replace "-1" in simulated data with NaN, to avoid trouble later.
    inactive_rows = np.isclose(sim_df["pressure"], -1)
    if inactive_rows.any():
        sim_df.loc[inactive_rows, "pressure"] = np.nan
        logger.info(
            "Found %s active and %s inactive pressure points",
            str(len(inactive_rows) - sum(inactive_rows)),
            str(sum(inactive_rows)),
        )
    else:
        logger.info("Found %s active pressure points", str(len(sim_df)))
    obs_df = get_observations(obsdir)

    # For each simulated well, look up
    logger.info("Parsed %s observations from files in %s", str(len(obs_df)), obsdir)

    return pd.merge(sim_df, obs_df, how="left", on=["well", "order"])


def main():
    """Main function when called as a command line application.

    Will get arguments from command line, and wrap around merge_rft_ertobs_main().
    """
    parser = get_parser()
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)

    dframe = merge_rft_ertobs(gendatacsv=args.gendatacsv, obsdir=args.obsdir)

    if not dframe.empty:
        dframe.to_csv(args.output, index=False)
        logger.info(
            "Written merged RFT simulated and observed values to %s", args.output
        )
    else:
        logger.error("Empty dataframe from merge of simulated and observed values")


if __name__ == "__main__":
    main()
