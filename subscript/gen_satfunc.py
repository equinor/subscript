import argparse
import os
import sys

import pyscal


def get_parser():
    parser = argparse.ArgumentParser(prog="gen_satfunc.py")
    parser.add_argument(
        "config_file",
        help=(
            "Path to configuration file. See "
            "http://wiki.statoil.no/wiki/index.php/"
            "ResScript:Python:Scripts:gen_satfunc.py"
        ),
    )
    parser.add_argument(
        "output_file",
        help="Path to output file. That is, the newly created SWOG and/or SGOF table.",
    )
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    if not os.path.isfile(args.config_file):
        sys.exit("Could not find the configuration file: %s" % args.config_file)

    output = ""

    for line in open(args.config_file).readlines():
        tmp = line.strip()
        if not tmp[0:2] == "--" and len(tmp) > 0:
            if tmp[0:7] == "RELPERM":

                # Parse relperm parameters from the rest of the line:
                relperm_input = tuple(tmp[8:].split("--")[0].split())
                relperm_input = [float(i) for i in relperm_input]

                # Unpack parameter list to explicitly named parameters:
                (Lw, Ew, Tw, Lo, Eo, To, Sorw, Swirr, Krwo) = relperm_input[0:9]

                if len(relperm_input) > 9:
                    num_sw_steps = relperm_input[9]
                else:
                    num_sw_steps = 20

                wo = pyscal.WaterOil(h=1.0 / (num_sw_steps + 2), sorw=Sorw, swirr=Swirr)
                wo.add_LET_oil(Lo, Eo, To, kroend=1)
                wo.add_LET_water(Lw, Ew, Tw, krwend=Krwo)

                if len(relperm_input) == 13:
                    (PERM, PORO, a, b, sigma_costau) = relperm_input[10:14]
                    wo.add_pc(
                        a=a,
                        b=b,
                        poro_ref=PORO,
                        perm_ref=PERM,
                        sigma_costau=sigma_costau,
                    )

                output += wo.SWOF(header=False)

            elif tmp[0:7] == "COMMENT":
                print("Printing comment")
                comment = tmp[8:].split("--")[0]
                output = output + "--" + comment + "\n"
            elif tmp[0:4] == "SWOF":
                print("Generating SWOF table")
                output = output + "SWOF\n"
            elif tmp[0:4] == "SGOF":
                print("Generating SGOF table")
                output = output + "SGOF\n"
            else:
                sys.exit('Error while interpreting line: "%s"' % line.strip())

    print("Writing output file...")
    with open(args.output_file, "w") as fh:
        fh.write(output)

    print("Done")


if __name__ == "__main__":
    main()
