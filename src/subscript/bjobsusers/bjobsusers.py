import argparse
import os
import re
import subprocess
from typing import Callable

import pandas as pd

from subscript import __version__

DESCRIPTION = """
Print list of users running on cluster, sorted by number of jobs.

This is statistics derived from the system command `bjobs` and `pinky`.
"""


def call_bjobs(status: str = "RUN") -> str:
    """Call the system bjobs utility

    Filter on a specific status, and to only the username
    and the nodecount

    Args:
        status (str): A string that the bjobs output will be grepped to
            should typically be RUN or PEND

    Returns:
        str: Multiline string in ascii, looking like::

              foobart 4*computenode1
              foobarter 2*computenode4
              foober computenode1

        where the optional number in front a compute node name denotes
        the number of allocated cores to the job.
    """
    cmd = f"bjobs -u all | grep {status} | awk '{{print $2,$6;}}'"
    return subprocess.check_output(cmd, shell=True).decode("utf-8")


def get_jobs(status: str, bjobs_function: Callable) -> pd.DataFrame:
    """Make a Pandas dataframe out of the bjobs output

    Sums the cpu/core usage pr. user.

    Args:
        status (str): Type of job to list, RUN or PEND
        bjobs_function: Function handle to a function that can return a string
             with bjobs output.

    Returns:
        pd.DataFrame: Dataframe with the columns user and ncpu.
        Only one row pr username. Sorted descending by ncpu.
    """
    cmdoutput = bjobs_function(status)
    rex = re.compile(r".*(\d+)\*.*")
    # Split bjobs output into a list of list:
    slines = [line.split() for line in str.splitlines(str(cmdoutput))]
    # We only accept lines with two components:
    slines = list(filter(lambda x: len(x) == 2, slines))
    if not slines:
        # Empty bjobs-output should just return empty dataframe.
        return pd.DataFrame(columns=("user", "ncpu"))
    data = [
        [
            uname,
            1 if rex.match(hname) is None else int(rex.match(hname).group(1)),  # type: ignore
        ]
        for (uname, hname) in slines
    ]
    return (
        pd.DataFrame(data, columns=("user", "ncpu"))
        .groupby("user")
        .sum()
        .sort_values("ncpu", ascending=False)
    )


def call_pinky(username: str) -> str:
    """Call the system utility 'pinky' on a specific username

    Returns:
        Unicode string with the first line of output from 'pinky'
        Example return value::

          Login name: foobert      In real life: Foo Barrer (FOO BAR COM)"
    """
    cmd = f"pinky -l {username} | head -n 1"
    pinky_output = None
    try:
        with open(os.devnull, "w", encoding="utf8") as devnull:
            pinky_output = (
                subprocess.check_output(cmd, shell=True, stderr=devnull)
                .strip()
                .decode("utf-8")
            )
    except AttributeError:
        pass
    if pinky_output:
        return pinky_output
    # When pinky fails, return something similar and usable
    return f"Login name: {username}  In real life: ?? ()"


def userinfo(username: str, pinky_function: Callable) -> str:
    """Get information on a user based on the username

    Args:
        username: user shortname/loginname
        pinky_function: Function handle that can provide output
            from the system pinky program (/usr/bin/pinky).
            The output must be a Unicode string

    Returns:
        str: String with full user name, organization from pinky output and
        the shortname
    """
    pinky_output = pinky_function(username)
    rex_with_org = re.compile(
        r".*Login name:\s+(.*)\s+In real life:\s+(.*)\s+\((.*)\).*"
    )
    rex_no_org = re.compile(r".*Login name:\s+(.*)\s+In real life:\s+(.*)")
    if rex_with_org.match(pinky_output):
        matches = rex_with_org.match(pinky_output).groups()  # type: ignore
        fullname = matches[1].strip()
        org = matches[2].strip()
    elif rex_no_org.match(pinky_output):
        matches = rex_no_org.match(pinky_output).groups()  # type: ignore
        fullname = matches[1].strip()
        org = ""
    else:
        fullname = username
        org = ""

    return f"{fullname} ({org}) ({username})"


def show_status(status: str = "RUN", title: str = "Running", umax: int = 10) -> None:
    """Print job statistics to console user"""
    dframe = get_jobs(status, call_bjobs).iloc[:umax]
    print(f"{title} jobs:")
    print("--------------")
    for user, count in dframe.iterrows():
        print(
            count.iloc[0],
            userinfo(  # lgtm [py/clear-text-logging-sensitive-data]
                str(user), call_pinky
            ),
        )
    print("- - - - - - - - - - -")
    print(f"Total: {dframe['ncpu'].sum()}")


def get_parser() -> argparse.ArgumentParser:
    """Prepare a parser for argument parsing and documentation"""
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "-u", "--usercount", type=int, default=10, help="Number of users to display"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + __version__ + ")",
    )
    return parser


def main() -> None:
    """For invocation on command line"""
    parser = get_parser()
    args = parser.parse_args()

    show_status("RUN", "Running", umax=args.usercount)
    print("")
    show_status("PEND", "Pending", umax=args.usercount)


if __name__ == "__main__":
    main()
