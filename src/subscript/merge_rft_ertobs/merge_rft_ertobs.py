import argparse
import logging
from os.path import abspath, isdir
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

import subscript

logger = subscript.getLogger(__name__)

DESCRIPTION = """Collect ERT RFT observations and merge with CSV output
from GENDATA_RFT. Dump to CSV file for visualization in Webviz.

Observation are found in ``*.obs`` files in the ``OBSDIR`` argument. From the
observation filename, both the wellname and "report_step" are extracted,
assuming a filename syntax ``<wellname>_<report_step>.obs`` where the
report_step is less than 10. If filenames are not like this, report_step is
interpreted to 1.

"report_step" in this context refers to the ``GEN_DATA``
keyword in the ERT config and the ``RESTART`` argument for
``GENERAL_OBSERVATION`` in the ERT config.
"""

CATEGORY = "utility.transformation"

EXAMPLES = """
.. code-block:: console

  FORWARD_MODEL MERGE_RFT_ERTOBS(<GENDATACSV>=gendata_rft.csv, <OBSDIR>=<CONFIG_PATH>/input/observations/rft, <OUTPUT>=rft_ertobs_sim.csv)

"""  # noqa


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """Multiple inheritance used for argparse to get both defaults
    and raw description formatter"""

    # pylint: disable=unnecessary-pass


def get_parser() -> argparse.ArgumentParser:
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
    parser.add_argument(
        "-o", "--output", type=str, default="rft_ertobs_sim.csv", help="Output CSV file"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + subscript.__version__ + ")",
    )
    return parser


def split_wellname_reportstep(wellname_reportstep: str) -> Tuple[str, int]:
    """Split a string that might contain both a wellname and a report step,
    at least it should contain a wellname.

    The reportstep is a number at the end, following an underscore.

    This function is needed and complex due differing standards on whether
    the report step should be present in the filename or not.

    Reporsteps larger than 9 is not supported, this is a compromise.

    Examples::

        "F_A-3" gives (F_A-3, 1)
        "F_A-4_1" gives (F_A-4, 1)
        "F_A-4_2" gives (F_A-4, 2)
        A-4 gives (A-4, 1)
        A-5_99 gives (A-5_99, 1)  # report steps more than 10 not supported.
        "R_A4_1" gives (R_A4, 1)
        "R_A4" gives (R_A4, 1)
        "R_A_4" gives (R_A, 4)  # Warning, this is probably unintended!

    Args:
        wellname_reportstep

    Returns:
        wellname and reportstep. Reportstep defaulted to 1 if not found
    """
    components = wellname_reportstep.split("_")
    if len(components[-1]) > 1:
        return ("_".join(components), 1)
    try:
        report_step = int(components[-1])
        return ("_".join(components[:-1]), report_step)
    except ValueError:
        return ("_".join(components), 1)


def get_observations(obsdir: str = "", filepattern: str = "*.obs") -> pd.DataFrame:
    """
    Gather observation data from a directory of input filenames, or later
    from ERT storage api.

    Reads all files matching `*.obs` in the given directory.  From the
    observation filename, both the wellname and "report_step" is extracted,
    assuming a filename syntax ``<wellname>_<report_step>.obs`` where the
    report_step is less than 10. If filenames are not like this, report_step is
    interpreted to 1.

    "report_step" in this context refers to the ``GEN_DATA`` keyword in the ERT
    config and the ``RESTART`` argument for ``GENERAL_OBSERVATION`` in the ERT
    config.

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
    if not isdir(obsdir):
        raise ValueError(f'Observation directory "{abspath(obsdir)}" doesn\'t exist')

    obs_dfs = []
    for obsfilename in Path(obsdir).glob(filepattern):
        # Warning: Deducing the wellname this way will fail for
        # exotic filepatterns.
        wellname_reportstep = Path(obsfilename).name.split(
            filepattern.replace("*", "")
        )[0:-1][0]
        (wellname, report_step) = split_wellname_reportstep(wellname_reportstep)
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
                .assign(well=wellname, report_step=report_step)
            )[["order", "well", "report_step", "observed", "error"]].dropna()
            if not wellobs.empty:
                obs_dfs.append(wellobs)
        except ValueError:
            logger.warning(
                "File %s could not be parsed as ERT observations, skipped.", obsfilename
            )

    if obs_dfs:
        return (
            pd.concat(obs_dfs)
            .sort_values(["well", "order", "report_step"])
            .reset_index(drop=True)
        )
    logger.warning("No observation data was parsed from %s", obsdir)
    return pd.DataFrame()


def merge_rft_ertobs(gendatacsv: str, obsdir: str) -> pd.DataFrame:
    """Main function for merge_rft_ertobs named arguments.

    Arguments correspond to argparse documentation
    """

    sim_df = pd.read_csv(gendatacsv)
    if not {"well", "order", "pressure"}.issubset(set(sim_df.columns)):
        raise ValueError(
            f"Need at least the columns well, order and pressure in {gendatacsv}"
        )
    # Replace "-1" in simulated data with NaN, to avoid trouble later.
    # pylint: disable=unsubscriptable-object
    inactive_rows = np.isclose(sim_df["pressure"], -1)
    if inactive_rows.any():
        sim_df.loc[inactive_rows, "pressure"] = np.nan
        logger.info(
            "Found %s active and %s inactive pressure points",
            str(len(inactive_rows) - sum(inactive_rows)),  # type: ignore
            str(sum(inactive_rows)),  # type: ignore
        )
    else:
        logger.info("Found %s active pressure points", str(len(sim_df)))

    obs_df = get_observations(obsdir)
    # For each simulated well, look up
    logger.info("Parsed %s observations from files in %s", str(len(obs_df)), obsdir)

    # Replace "-1" in observation data with NaN, to avoid trouble later.
    # pylint: disable=unsubscriptable-object
    inactive_rows = np.isclose(obs_df["observed"], -1)
    if inactive_rows.any():
        obs_df.loc[inactive_rows, "observed"] = np.nan
        logger.info(
            "Found %s active and %s inactive observation points",
            str(len(inactive_rows) - sum(inactive_rows)),  # type: ignore
            str(sum(inactive_rows)),  # type: ignore
        )
    else:
        logger.info("Found %s active observation points", str(len(obs_df)))

    if "report_step" in sim_df.columns:
        return pd.merge(sim_df, obs_df, how="left", on=["well", "order", "report_step"])
    # Ensure backward compatibility where gendata_rft doesn't have report_step
    return pd.merge(sim_df, obs_df, how="left", on=["well", "order"])


def main() -> None:
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
