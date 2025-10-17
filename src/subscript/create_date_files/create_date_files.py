import argparse
import datetime
import logging
import re

import fmu.config.utilities as utils

import subscript

logger = subscript.getLogger(__name__)
logger.setLevel(logging.INFO)

DESCRIPTION = """ Make 'single_dates.txt' and 'diff_dates.txt' files that can be used
with ECLRST2ROFF and ECLDIFF2ROFF. The output files are stored directly in runpath
folder.

The script will extract dates the global variable yaml file. Name of the global variable
file is read from input argument. Name of the date lists are also read from input
arguments.

The date lists must be defined under global:dates: level in the global variable file.
Example of expected structure in global variable file:

global:
  dates:
    SEISMIC_HIST_DATES:
    - 2018-01-01
    - 2020-07-01
    SEISMIC_HIST_DIFFDATES:
    - - 2020-07-01
      - 2018-01-01

"""

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """Multiple inheritance used for argparse to get both defaults
    and raw description formatter"""


def get_parser():
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=CustomFormatter,
    )
    parser.add_argument("globvar_file", type=str, help="Name of global variable file")
    parser.add_argument(
        "--single-dates",
        type=str,
        default=None,
        help="Name of single dates list in global variable file",
    )
    parser.add_argument(
        "--diff-dates",
        type=str,
        default=None,
        help="Name of diffdates list in global variable file",
    )
    return parser


def is_iso_date_item(item) -> bool:
    """
    Return True if item is:
    - a datetime.date or datetime.datetime, OR
    - a string in ISO format YYYY-MM-DD (parsable by date.fromisoformat).
    """
    if isinstance(item, datetime.date | datetime.datetime):
        return True
    if isinstance(item, str):
        if not ISO_RE.match(item):
            return False
        try:
            datetime.date.fromisoformat(item)
            return True
        except ValueError:
            return False
    return False


def is_iso_date_list(date_list) -> bool:
    """All items must be valid ISO date items (date objects or ISO strings)."""
    if not isinstance(date_list, list | tuple):
        return False
    return all(is_iso_date_item(it) for it in date_list)


def is_iso_diffdate_list(diffdate_list) -> bool:
    """
    Each element must be a 2-tuple/list of ISO date items.
    Accepts [(date, date), ['YYYY-MM-DD', date], ...].
    """
    if not isinstance(diffdate_list, list | tuple):
        return False
    for pair in diffdate_list:
        if not isinstance(pair, list | tuple) or len(pair) != 2:
            return False
        if not (is_iso_date_item(pair[0]) and is_iso_date_item(pair[1])):
            return False
    return True


def validate_cfg(cfg, single_dates: str | None, diff_dates: str | None) -> bool:
    """Validate the structure of the config dictionary"""

    if "global" not in cfg or "dates" not in cfg["global"]:
        logger.error("Missing 'global:dates:' section in config file.")
        return False

    cfg_global = cfg["global"]["dates"]

    if single_dates is not None:
        if single_dates not in cfg_global:
            logger.error(f"Key {single_dates} not found in global variable file.")
            return False
        if not isinstance(cfg_global[single_dates], list):
            logger.error(f"Value for {single_dates} is not a list.")
            return False
        if not is_iso_date_list(cfg_global[single_dates]):
            logger.warning(
                f"{single_dates} is not in the recommended format YYYY-MM-DD."
            )

    if diff_dates is not None:
        if diff_dates not in cfg_global:
            logger.error(f"Key {diff_dates} not found in global variable file.")
            return False
        if not isinstance(cfg_global[diff_dates], list):
            logger.error(f"Value for {diff_dates} is not a list.")
            return False
        if not is_iso_diffdate_list(cfg_global[diff_dates]):
            logger.warning(f"{diff_dates} is not in the recommended format YYYY-MM-DD.")

    return True


def main():
    """Parse arguments and create date files compatible with ECLRST2ROFF and
    ECLDIFF2ROFF."""

    args: argparse.Namespace = get_parser().parse_args()
    globvar_file: str = args.globvar_file
    single_dates: str | None = args.single_dates
    diff_dates: str | None = args.diff_dates

    singledates_output_file = "single_dates.txt"
    diffdates_output_file = "diff_dates.txt"

    try:
        cfg = utils.yaml_load(globvar_file)
    except Exception as e:
        logger.error(f"Failed to load {globvar_file} file: {e}")
        return

    if not validate_cfg(cfg, single_dates, diff_dates):
        return

    cfg_global = cfg["global"]["dates"]

    if single_dates is not None:
        logger.info(f"Create {singledates_output_file}")
        with open(singledates_output_file, "w") as f_single:
            for date in cfg_global[single_dates]:
                logger.info(f"{date}")
                f_single.write(f"{date!s}\n")

    if diff_dates is not None:
        logger.info(f"Create {diffdates_output_file}")
        with open(diffdates_output_file, "w") as f_diff:
            for dates in cfg_global[diff_dates]:
                logger.info(f"{dates[0]} {dates[1]}")
                f_diff.write(f"{dates[0]!s} {dates[1]!s}\n")

    logger.info("Done.")


if __name__ == "__main__":
    main()
