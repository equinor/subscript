# -*- coding: utf-8 -*-
import argparse

from pack_sim_func import pack_simulation

DESCRIPTION = """
This script will read trough a data file and copy all include files to one include
directory in the so-called packing directory. It will also generate a new DATA file
in the packing directory with relative include paths. This way a simulation model
can be quickly packed to, for example, distribute to a partner company.
The script also works with include files in include files. The script does not
rename any include files: if two different include files are used with equal names
but different absolute locations in the original DATA-file you will have to rename
one of them manually before packing.
"""


def get_parser():
    """Function to create the argument parser that is going to be served to the user.

    Returns:
        parser (argparse.ArgumentParser): The argument parser to be served

    """
    parser = argparse.ArgumentParser(prog="pack_sim.py", description=DESCRIPTION)
    parser.add_argument(
        "ECLIPSE_CASE", type=str, help="Name of the Eclipse case to be packed "
    )
    parser.add_argument(
        "PACKING_PATH",
        type=str,
        help="Path towards the directory where the packed simulation model "
        "should end up.",
    )
    parser.add_argument(
        "-c",
        "--clearcomments",
        action="store_true",
        help="Set this switch (only -c, no further input required) to clear all "
        "comments during packing.",
    )
    parser.add_argument(
        "-fmu",
        "--fmu",
        default=False,
        action="store_true",
        help="Set this switch (only -fmu, no further input required) to save the the "
        "Eclipse model in standard fmu file structure (model/ and include/grid, "
        "include/props, etc folders)",
    )

    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    pack_simulation(args.ECLIPSE_CASE, args.PACKING_PATH, args.clearcomments, args.fmu)


if __name__ == "__main__":
    main()
