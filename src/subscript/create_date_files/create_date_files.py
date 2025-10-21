import argparse
import datetime
import logging
import re
import sys
from typing import Any

import fmu.config.utilities as utils

import subscript

logger = subscript.getLogger(__name__)
logger.setLevel(logging.INFO)

DESCRIPTION = """Make 'single_dates.txt' and 'diff_dates.txt' files that can be used
with ECLRST2ROFF and ECLDIFF2ROFF. The output files are stored directly in runpath
folder.

The script extracts date lists from a global variables YAML file. The path to the
global variables YAML file is provided via an input argument, and the names of
the date lists in that YAML file are also provided via input arguments.

The date lists must be defined under global:dates: level in the YAML file.

Example of expected structure in global variable file:

    .. code-block:: yaml

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


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=CustomFormatter,
    )
    parser.add_argument("globvar_file", help="Name of global variable YAML file")
    parser.add_argument(
        "--single-dates",
        default=None,
        help="Name of single dates list in global variable file",
    )
    parser.add_argument(
        "--diff-dates",
        default=None,
        help="Name of diffdates list in global variable file",
    )
    return parser


def is_iso_date_item(item: Any) -> bool:  # noqa: ANN401
    """
    Return True if item is:
    - a datetime.date or datetime.datetime, OR
    - a string in ISO format YYYY-MM-DD (parsable by date.fromisoformat).
    """
    if isinstance(item, datetime.date):
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


def _validate_cfg_structure(cfg: dict[str, Any] | None) -> bool:
    """Validate basic config structure."""
    if cfg is None:
        logger.error("Configuration is empty or invalid.")
        return False

    if not isinstance(cfg, dict):
        logger.error("Configuration does not contain a valid dictionary.")
        return False

    if "global" not in cfg or not isinstance(cfg["global"], dict):
        logger.error("Missing or invalid 'global' section in config file.")
        return False

    if "dates" not in cfg["global"] or not isinstance(cfg["global"]["dates"], dict):
        logger.error("Missing or invalid 'global:dates:' section in config file.")
        return False

    return True


def _validate_single_dates(cfg_dates: dict[str, Any], single_dates: str) -> bool:
    """Validate single dates configuration."""
    if single_dates not in cfg_dates:
        logger.error(f"Key {single_dates} not found in global variable file.")
        return False

    if not isinstance(cfg_dates[single_dates], list):
        logger.error(f"Value for {single_dates} is not a list.")
        return False

    if not cfg_dates[single_dates]:
        logger.warning(f"{single_dates} is empty")

    if not all(is_iso_date_item(it) for it in cfg_dates[single_dates]):
        logger.error(f"{single_dates} is not in the recommended format YYYY-MM-DD.")
        return False

    return True


def _validate_diff_dates(cfg_dates: dict[str, Any], diff_dates: str) -> bool:
    """Validate diff dates configuration.
    Each element must be a list of two ISO date items.
    Accepts [['YYYY-MM-DD', date], ...].
    """
    if diff_dates not in cfg_dates:
        logger.error(f"Key {diff_dates} not found in global variable file.")
        return False

    if not isinstance(cfg_dates[diff_dates], list):
        logger.error(f"Value for {diff_dates} is not a list.")
        return False

    if not cfg_dates[diff_dates]:
        logger.warning(f"{diff_dates} is empty")

    for pair in cfg_dates[diff_dates]:
        if not isinstance(pair, list):
            logger.error("Each diff date entry must be a list of two dates.")
            return False
        if len(pair) != 2:
            logger.error("Diff dates must have two dates per item.")
            return False
        if not (is_iso_date_item(pair[0]) and is_iso_date_item(pair[1])):
            logger.error(f"{diff_dates} is not in the recommended format YYYY-MM-DD.")
            return False

    return True


def validate_cfg(
    cfg: dict[str, Any] | None, single_dates: str | None, diff_dates: str | None
) -> bool:
    """Validate the structure of the config dictionary

    Args:
        cfg: Configuration dictionary loaded from YAML (can be None)
        single_dates: Name of single dates list key (optional)
        diff_dates: Name of diff dates list key (optional)

    Returns:
        True if validation passes, False otherwise
    """
    # Validate basic structure
    if not _validate_cfg_structure(cfg):
        return False

    # At this point we know cfg is a valid dict
    assert isinstance(cfg, dict)
    cfg_dates = cfg["global"]["dates"]

    # Validate single_dates if provided
    if (single_dates is not None) and (
        not _validate_single_dates(cfg_dates, single_dates)
    ):
        return False

    # Validate diff_dates if provided - return the result directly
    if diff_dates is None:
        return True

    return _validate_diff_dates(cfg_dates, diff_dates)


def main() -> None:
    """Parse arguments and create date files compatible with ECLRST2ROFF and
    ECLDIFF2ROFF."""

    args: argparse.Namespace = get_parser().parse_args()
    globvar_file: str = args.globvar_file
    # Converts empty strings to None
    single_dates: str | None = args.single_dates or None
    diff_dates: str | None = args.diff_dates or None

    if single_dates is None and diff_dates is None:
        logger.error("At least one of --single-dates or --diff-dates must be provided.")
        return

    singledates_output_file = "single_dates.txt"
    diffdates_output_file = "diff_dates.txt"

    try:
        cfg = utils.yaml_load(globvar_file)
    except (OSError, ValueError, KeyError) as e:
        logger.error(f"Failed to load {globvar_file} file: {e}")
        sys.exit(1)

    if not validate_cfg(cfg, single_dates, diff_dates):
        sys.exit(1)

    # After validation passes, we know cfg is a valid dict with the expected structure
    # We can safely assert this for type checking
    assert isinstance(cfg, dict)  # Type narrowing for mypy
    cfg_dates = cfg["global"]["dates"]

    if single_dates is not None:
        logger.info(f"Create {singledates_output_file}")
        with open(singledates_output_file, "w", encoding="utf-8") as f_single:
            for date in cfg_dates[single_dates]:
                logger.info(f"{date}")
                f_single.write(f"{date}\n")

    if diff_dates is not None:
        logger.info(f"Create {diffdates_output_file}")
        with open(diffdates_output_file, "w", encoding="utf-8") as f_diff:
            for dates in cfg_dates[diff_dates]:
                logger.info(f"{dates[0]} {dates[1]}")
                f_diff.write(f"{dates[0]} {dates[1]}\n")

    logger.info("Done.")


if __name__ == "__main__":
    main()
