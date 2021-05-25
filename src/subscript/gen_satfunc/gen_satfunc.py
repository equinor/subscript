import sys
import argparse
import logging
import warnings
from pathlib import Path

import pyscal
import subscript

# Non-conforming names are in use here, as they follow a different norm.
# pylint: disable=invalid-name


logger = subscript.getLogger(__name__)


def get_parser():
    """Make a parser for command line arg parsing and for documentation"""
    parser = argparse.ArgumentParser(
        prog="gen_satfunc",
        description="Deprecated tool for making SWOF/SGOF files for Eclipse. "
        "Use pyscal instead.",
    )
    parser.add_argument(
        "config_file",
        help=("Path to configuration file."),
    )
    parser.add_argument(
        "output_file",
        help="Path to output file with SWOF and/or SGOF tables.",
    )
    return parser


def main():
    """Used for invocation on the command line"""
    parser = get_parser()
    args = parser.parse_args()

    warnings.warn("gen_satfunc is deprecated, use pyscal", FutureWarning)

    logger.setLevel(logging.INFO)

    if not Path(args.config_file).exists():
        sys.exit(f"Could not find the configuration file: {args.config_file}")

    output = ""

    for line in open(args.config_file).readlines():
        tmp = line.strip()
        if not tmp[0:2] == "--" and len(tmp) > 0:
            if tmp[0:7] == "RELPERM":

                # Parse relperm parameters from the rest of the line:
                relperm_input = tuple(tmp[8:].split("--")[0].split())
                relperm_input = [float(i) for i in relperm_input]

                if len(relperm_input) < 9:
                    logger.error("Too few relperm parameters in line:\n%s", line)
                    raise ValueError("Erroneous relperm parameters")

                # Unpack parameter list to explicitly named parameters:
                (Lw, Ew, Tw, Lo, Eo, To, Sorw, Swl, Krwo) = relperm_input[0:9]

                if len(relperm_input) > 9:
                    num_sw_steps = relperm_input[9]
                else:
                    num_sw_steps = 20

                wo = pyscal.WaterOil(h=1.0 / (num_sw_steps + 2), sorw=Sorw, swl=Swl)
                wo.add_LET_oil(Lo, Eo, To, kroend=1)
                wo.add_LET_water(Lw, Ew, Tw, krwend=Krwo)

                if 10 < len(relperm_input) < 15:
                    logger.error("Too few parameter for pc in line:\n%s", line)
                    raise ValueError("Erroneous pc parameters")

                if len(relperm_input) == 15:
                    (PERM, PORO, a, b, sigma_costau) = relperm_input[10:15]
                    wo.add_normalized_J(
                        a=a, b=b, poro=PORO, perm=PERM, sigma_costau=sigma_costau
                    )

                output += wo.SWOF(header=False)

            elif tmp[0:7] == "COMMENT":
                logger.info("Printing comment")
                comment = tmp[8:].split("--")[0]
                output = output + "--" + comment + "\n"
            elif tmp[0:4] == "SWOF":
                logger.info("Generating SWOF table")
                output = output + "SWOF\n"
            elif tmp[0:4] == "SGOF":
                logger.info("Generating SGOF table")
                output = output + "SGOF\n"
            else:
                raise ValueError('Error while interpreting line: "%s"' % line.strip())

    logger.info("Writing output file...")

    Path(args.output_file).write_text(output)

    logger.info("Done")


if __name__ == "__main__":
    main()
