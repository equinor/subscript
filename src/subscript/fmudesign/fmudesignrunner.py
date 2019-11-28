# -*- coding: utf-8 -*-
"""Script for generating a design matrix from config input"""

from __future__ import division, print_function, absolute_import

import argparse
import sys
import os.path

from create_design import DesignMatrix
from _excel2dict import excel2dict_design


def _do_parse_args(args):

    if args is None:
        args = sys.argv[1:]
    else:
        args = args

    parser = argparse.ArgumentParser(
        description="Generate design matrix to be used with ert DESIGN2PARAMS",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # positional:
    parser.add_argument(
        "config", type=str, help=("Input design config filename " "in Excel format")
    )
    parser.add_argument(
        "destination",
        type=str,
        help="Destination filename for design matrix",
        default="generateddesignmatrix.xlsx",
    )
    parser.add_argument(
        "--designinput",
        type=str,
        help=("Alternative sheetname for the " "worksheet designinput"),
        default="designinput",
    )
    parser.add_argument(
        "--defaultvalues",
        type=str,
        help=("Alternative sheetname for " "worksheet defaultvalues"),
        default="defaultvalues",
    )
    parser.add_argument(
        "--general_input",
        type=str,
        help=("Alternative sheetname for the" "worksheet general_input"),
        default="general_input",
    )

    args = parser.parse_args(args)

    # Defaulted options should be reset to None, so that the other
    # defaulting level inside _excel2dict can do its work.
    if args.designinput == parser.get_default("designinput"):
        args.designinput = None
    if args.defaultvalues == parser.get_default("defaultvalues"):
        args.defaultvalues = None
    if args.general_input == parser.get_default("general_input"):
        args.general_input = None

    return args


def main(args=None):
    """fmudesign is a command line utility for generating design matrices

    Wrapper for the the fmu.tools.sensitivities module"""

    args = _do_parse_args(args)

    sheetnames = dict()
    if args.designinput:
        sheetnames["designinput"] = args.designinput
    if args.defaultvalues:
        sheetnames["defaultvalues"] = args.defaultvalues
    if args.general_input:
        sheetnames["general_input"] = args.general_input

    if sheetnames:
        print("Worksheets changed from default:")
        print(sheetnames)

    if isinstance(args.config, str):
        if not os.path.isfile(args.config):
            raise IOError("Input file {} does not exist".format(args.config))
        input_dict = excel2dict_design(args.config, sheetnames)

    design = DesignMatrix()

    design.generate(input_dict)

    folder = os.path.dirname(args.destination)

    if folder and not os.path.exists(folder):
        os.makedirs(folder)

    design.to_xlsx(args.destination)


if __name__ == "__main__":
    main()
