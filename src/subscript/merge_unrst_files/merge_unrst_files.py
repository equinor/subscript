import argparse
import logging
from typing import Any

import resfo

from subscript import __version__, getLogger

# Type aliases
KWEntry = tuple[str, Any]
Chunk = list[KWEntry]


DESCRIPTION = """Read two ``UNRST`` files and export a merged version. This is useful in
cases where history and prediction are run separately and one wants to calculate
differences across dates in the two files. One should give hist file as first positional
argument and pred file as the second positional argument (i.e. in the order of smallest
to largest report step numbers).
"""


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
        "--priority",
        type=str,
        choices=["hist", "pred"],
        default="hist",
        help="Which file to keep on overlapping report steps (default: hist)",
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s (subscript version {__version__})",
    )
    return parser


def _get_overlap_interval(
    hist_chunks: list[Chunk],
    pred_chunks: list[Chunk],
) -> tuple[int, int] | None:
    """Determine the overlapping interval between hist and pred.

    The overlap is defined as:
        [max(min_hist, min_pred), min(max_hist, max_pred)]

    Returns:
        tuple: (overlap_start, overlap_end) or None if no overlap.
    """
    hist_seqnums: list[int] = [
        s for c in hist_chunks if (s := _get_seqnum(c)) is not None
    ]
    pred_seqnums: list[int] = [
        s for c in pred_chunks if (s := _get_seqnum(c)) is not None
    ]

    if not hist_seqnums or not pred_seqnums:
        return None

    logger.info(f"Hist report steps: {hist_seqnums}")
    logger.info(f"Pred report steps: {pred_seqnums}")

    overlap_start = max(hist_seqnums[0], pred_seqnums[0])
    overlap_end = min(hist_seqnums[-1], pred_seqnums[-1])

    if overlap_start <= overlap_end:
        return (overlap_start, overlap_end)
    return None


def _is_in_interval(seqnum: int | None, interval: tuple[int, int] | None) -> bool:
    """Check if a seqnum falls within the overlap interval."""
    if interval is None or seqnum is None:
        return False
    return interval[0] <= seqnum <= interval[1]


def _split_by_seqnum(data: list[KWEntry]) -> list[Chunk]:
    """Split UNRST keyword list into chunks, one per report step.

    Each chunk starts with a SEQNUM keyword and contains all keywords
    until the next SEQNUM (or end of data).

    Args:
        data: List of (keyword, value) tuples as returned by
            resfo.read().

    Returns:
        List of chunks, where each chunk is a list of
        (keyword, value) tuples.
    """
    chunks: list[Chunk] = []
    current_chunk: Chunk = []
    for kw, val in data:
        if kw == "SEQNUM  " and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
        current_chunk.append((kw, val))
    if current_chunk:
        chunks.append(current_chunk)
    return chunks


def _get_seqnum(chunk: Chunk) -> int | None:
    """Extract the SEQNUM value from a chunk."""
    for kw, val in chunk:
        if kw == "SEQNUM  ":
            return int(val[0])
    return None


def main() -> None:
    """Parse command line arguments and run"""

    args: argparse.Namespace = get_parser().parse_args()

    logger.info(f"Merge unrst files {args.UNRST1} and {args.UNRST2}.")
    unrst_hist = resfo.read(args.UNRST1)
    unrst_pred = resfo.read(args.UNRST2)

    hist_chunks = _split_by_seqnum(unrst_hist)
    pred_chunks = _split_by_seqnum(unrst_pred)

    overlap_interval = _get_overlap_interval(hist_chunks, pred_chunks)

    if overlap_interval:
        logger.info(
            "Overlapping report step interval detected: "
            f"SEQNUM {overlap_interval[0]} to {overlap_interval[1]}"
        )
        logger.info(f"Keeping {args.priority} data in overlapping interval")
    else:
        logger.info("No overlapping report steps detected.")

    if args.priority == "hist":
        filtered_hist = hist_chunks
        filtered_pred = [
            c
            for c in pred_chunks
            if not _is_in_interval(_get_seqnum(c), overlap_interval)
        ]
    else:
        filtered_hist = [
            c
            for c in hist_chunks
            if not _is_in_interval(_get_seqnum(c), overlap_interval)
        ]
        filtered_pred = pred_chunks

    merged = [item for chunk in filtered_hist for item in chunk] + [
        item for chunk in filtered_pred for item in chunk
    ]

    resfo.write(args.output, merged)
    logger.info(f"Done. Merged file is written to {args.output}")


if __name__ == "__main__":
    main()
