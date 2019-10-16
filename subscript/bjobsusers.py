from __future__ import print_function

import os
import re
import subprocess
import argparse

import pandas as pd

DESCRIPTION = """
Print list of users running on cluster, sorted by number of jobs.

This is statistics derived from the system command `bjobs` and `finger`.
"""


def call_bjobs(status="RUN"):
    """Call the system bjobs utility

    Filter on a specific status, and to only the username
    and the nodecount

    Args:
        status (str): A string that the bjobs output will be grepped to
            should typically be RUN or PEND

    Returns:
        Multiline string in ascii, looking like
            foobart 4*computenode1
            foobarter 2*computenode4
            foober computenode1

        where the optional number in front a compute node name denotes
        the number of allocated cores to the job.
    """
    cmd = "bjobs -u all | grep {} | awk '{{print $2,$6;}}'".format(status)
    cmdoutput = subprocess.check_output(cmd, shell=True).decode("ascii")
    return cmdoutput


def get_jobs(status, bjobs_function):
    """Make a Pandas dataframe out of the bjobs output

    Sums the cpu/core usage pr. user.

    Args:
        status (str): Type of job to list, RUN or PEND
        bjobs_function: Function handle to a function that can return a string
             with bjobs output.

    Returns:
        pd.DataFrame with the columns user and ncpu. Only one row pr username.
            Sorted descending by ncpu.
    """
    cmdoutput = bjobs_function(status)
    rex = re.compile(r".*(\d+)\*.*")
    # Split bjobs output into a list of list:
    slines = [line.split() for line in str.splitlines(str(cmdoutput))]
    # We only accept lines with two components:
    slines = filter(lambda x: len(x) == 2, slines)
    if not slines:
        # Empty bjobs-output should just return empty dataframe.
        return pd.DataFrame(columns=("user", "ncpu"))
    else:
        data = [
            [uname, 1 if rex.match(hname) is None else int(rex.match(hname).group(1))]
            for (uname, hname) in slines
        ]
    return (
        pd.DataFrame(data, columns=("user", "ncpu"))
        .groupby("user")
        .sum()
        .sort_values("ncpu", ascending=False)
    )


def call_finger(username):
    """Call the system utility 'finger' on a specific username

    Returns:
        UTF-8 encoded string with the first line of output from 'finger'
        Example return value: "Login: foobert      Name: Foo Barrer (FOO BAR COM)"
    """
    cmd = "finger {} | head -n 1".format(username)
    try:
        with open(os.devnull, "w") as devnull:
            finger_output = (
                subprocess.check_output(cmd, shell=True, stderr=devnull)
                .decode("utf-8")
                .strip()
            )
    except AttributeError:
        pass
    if finger_output:
        return finger_output
    else:
        # When finger fails, return something similar and usable
        return "Login: {}  Name: ?? ()".format(username)


def userinfo(username, finger_function):
    """Get information on a user based on the username

    Args:
        username: user shortname/loginname
        finger_function: Function handle that can provide output
            from the system finger program (/usr/bin/finger)

    Returns:
        string with full user name, organization from finger output and
            the shortname
    """
    finger_output = finger_function(username)
    rex = re.compile(r".*Login:\s+(.*)\s+Name:\s+(.*)\s+\((.*)\).*")
    [u2, fullname, org] = [x.strip() for x in rex.match(finger_output).groups()]
    return "{} ({}) ({})".format(fullname, org, username)


def show_status(status="RUN", title="Running", umax=10):
    df = get_jobs(status, call_bjobs).iloc[:umax]
    print("{} jobs:".format(title))
    print("--------------")
    for u, n in df.iterrows():
        print(n[0], userinfo(u, call_finger))
    print("- - - - - - - - - - -")
    print("Total: {}".format(df["ncpu"].sum()))


def get_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "-u", "--usercount", type=int, default=10, help="Number of users to display"
    )
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    show_status("RUN", "Running", umax=args.usercount)
    print("")
    show_status("PEND", "Pending", umax=args.usercount)


if __name__ == "__main__":
    main()
