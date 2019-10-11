from __future__ import print_function

import os
import re
import subprocess
import argparse

import pandas

DESCRIPTION = """
Print list of users running on cluster, sorted by
number of jobs.
"""


def get_jobs(status="RUN"):
    cmd = "bjobs -u all | grep %s | awk '{print $2,$6;}'" % (status)
    cmdoutput = subprocess.check_output(cmd, shell=True).decode("ascii")
    rex = re.compile(r".*(\d+)\*.*")
    slines = [line.split() for line in str.splitlines(str(cmdoutput))]
    if len(slines[0]) < 1:
        data = pandas.DataFrame(columns=("user", "ncpu"))
    else:
        data = [
            [uname, 1 if rex.match(hname) is None else int(rex.match(hname).group(1))]
            for (uname, hname) in slines
        ]
    return (
        pandas.DataFrame(data, columns=("user", "ncpu"))
        .groupby("user")
        .sum()
        .sort_values("ncpu", ascending=False)
    )


def userinfo(u):
    cmd = "finger %s | head -n 1" % (u)
    retval = "?? (%s)" % u
    try:
        with open(os.devnull, "w") as devnull:
            line = (
                subprocess.check_output(cmd, shell=True, stderr=devnull)
                .decode("utf-8")
                .strip()
            )
        rex = re.compile(r".*Login:\s+(.*)\s+Name:\s+(.*)\s+\((.*)\).*")
        [u2, uname, org] = [x.strip() for x in rex.match(line).groups()]
        retval = "%s (%s) (%s)" % (uname, org, u)
    except AttributeError:
        pass
    return retval


def show_status(status="RUN", title="Running", umax=10):
    df = get_jobs(status).iloc[:umax]
    print("%s jobs:" % (title))
    print("--------------")
    for u, n in df.iterrows():
        print(n[0], userinfo(u))
    print("- - - - - - - - - - -")
    print("Total: %d" % (df["ncpu"].sum()))


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
