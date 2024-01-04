import argparse
import logging

import resfo

from subscript import __version__, getLogger

DESCRIPTION = """Read two ``UNRST`` files and export a merged version. This is useful in
cases where history and prediction are run separately and one wants to calculate
differences across dates in the two files. One should give hist file as first positional
argument and pred file as the second positional argument (i.e. in the order of smallest
to largest report step numbers).
"""

CATEGORY = "utility.eclipse"

EXAMPLES = """
.. code-block:: console

  DEFINE <RESTART_DIR>      iter-3
  FORWARD_MODEL MERGE_UNRST_FILES(<UNRST1>=../<RESTART_DIR>/<ECLBASE>.UNRST, <UNRST2>=<ECLBASE>.UNRST, <MERGED_FILE>=eclipse/model/ECLIPSE_MERGED.UNRST)

"""  # noqa

logger = getLogger(__name__)
logger.setLevel(logging.INFO)


def get_parser() -> argparse.ArgumentParser:
    """Function to create the argument parser that is going to be served to the user.

    Returns:
        argparse.ArgumentParser: The argument parser to be served

    """
    parser = argparse.ArgumentParser(
        prog="merge_unrst_files.py", description=DESCRIPTION
    )
    parser.add_argument("UNRST1", type=str, help="UNRST file 1, history part")
    parser.add_argument("UNRST2", type=str, help="UNRST file 2, prediction part")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Name of the merged UNRST file",
        default="MERGED.UNRST",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s (subscript version {__version__ })",
    )
    return parser


def _check_report_number(
    args: argparse.Namespace,
    max_report_number_hist: int,
    current_report_number: int,
) -> None:
    """Check that pred file report numbers are larger than in hist file.

    Args:
        args (argparse.Namespace): The Namespace object with the argument list.
        max_report_number_hist (int): The largest report number in hist file.
        current_report_number (int): The current restart report number in pred file.
    """

    if current_report_number <= max_report_number_hist:
        logger.warning(
            f"{args.UNRST2} file has a restart report number ({current_report_number})"
            + f" which is smaller than largest report number in {args.UNRST1}"
            + f" ({max_report_number_hist})"
        )
        logger.warning(
            "Check that you have entered arguments in correct order and/or"
            + " that the unrst files are compatible."
        )


def main() -> None:
    """Parse command line arguments and run"""

    args: argparse.Namespace = get_parser().parse_args()

    logger.info(f"Merge unrst files {args.UNRST1} and {args.UNRST2}.")
    unrst_hist = resfo.read(args.UNRST1)
    unrst_pred = resfo.read(args.UNRST2)

    max_first_seqnum: int = 1
    max_first_solver_step: int = 1
    max_first_report_step: int = 1

    for kw, val in unrst_hist:
        if kw == "SEQNUM  ":  # restart report number
            max_first_seqnum = max(max_first_seqnum, val[0])
        if kw == "INTEHEAD":
            max_first_solver_step = max(max_first_solver_step, val[67])
            max_first_report_step = max(max_first_report_step, val[68])

    for kw, val in unrst_pred:
        if kw == "SEQNUM  ":
            _check_report_number(args, max_first_seqnum, val[0])
            val[0] += max_first_seqnum
        if kw == "INTEHEAD":
            val[67] += max_first_solver_step
            val[68] += max_first_report_step

    resfo.write(args.output, unrst_hist + unrst_pred)
    logger.info(f"Done. Merged file is written to {args.output}")


if __name__ == "__main__":
    main()
