import numpy as np
import math
import argparse
import os
import sys

import pyscal

# Parse input argument and show textual user interface
parser = argparse.ArgumentParser(prog="gen_satfunc.py")
parser.add_argument(
    "config_file",
    help="Path to configuration file. See http://wiki.statoil.no/wiki/index.php/ResScript:Python:Scripts:gen_satfunc.py",
)
parser.add_argument(
    "output_file",
    help="Path to output file. That is, the newly created SWOG and/or SGOF table.",
)
args = parser.parse_args()


def calcPc(SwJ, PERM, PORO, a, b, sigma_costau):
    """
        Calculate capillary pressure based on the water saturation, permeability, porosity, a, b and sigma*cos(tau)

        <-- Input
        SwJ             = Water saturation as a fraction
        PERM            = Permeability in mD (Typical value = formation average)
        PORO            = Porosity as a fraction (Typical value = formation average)
        a & b           = petrophysical J-function fitting parameters (Typical value, see below)
        sigma_costau    = Interfacial tension in mN/m (Typical value = 30 mN/m)
        Result -->l
        Pc              = Capillary pressure in bars

        --Typical values for the Heidrun a & b fitting parameters (as in FF13_2014a)
        zones           = Garn          Ile             Tilje2and3      Tilje 1-Aare3           Are1and2
        a               = 0.22411       0.2383          0.3797          0.3199                  0.3421
        b               = -0.52515      -0.292          -0.286          -0.263                  -0.343
        """

    Pc = (
        (
            ((SwJ / a) ** (1 / b))
            / (math.sqrt((float(0.0000000000009869233) * PERM / float(1000)) / PORO))
        )
        * (sigma_costau / float(1000))
    ) / float(101325)

    return Pc


def SWOF_Table(
    Lw,
    Ew,
    Tw,
    Lo,
    Eo,
    To,
    Sorw,
    Swirr,
    Krwo,
    num_sw_steps,
    PERM=None,
    PORO=None,
    a=None,
    b=None,
    sigma_costau=None,
):
    """
        Function that returns all information of a common SWOF table entry:
        sw, krw, kro, pc

        Required input is are the LET-parameters for the oil and water relative permeability curves, as
        well as the irriducable water and remain oil saturations and Krwo.

        Optionally you can supply the PERM, PORO, and sigma_costau

        PERM            = Permeability in mD
        PORO            = Porosity as a fraction
        a & b           = petrophysical J-function fitting parameters
        sigma_costau    = Interfacial tension in mN/m
        """

    swn = np.linspace(0, 1, num=num_sw_steps)
    sw = (swn * (1 - Swirr - Sorw)) + Swirr
    krw = np.true_divide(
        Krwo * np.power(swn, Lw),
        np.add(np.power(swn, Lw), Ew * np.power((1 - swn), Tw)),
    )
    krow = np.true_divide(
        np.power(1 - swn, Lo), np.add(np.power(1 - swn, Lo), Eo * np.power(swn, To))
    )
    pc = np.linspace(0, 0, num=num_sw_steps)

    # Add end entry
    sw = np.append(sw, 1)
    krw = np.append(krw, 1)
    krow = np.append(krow, 0)
    pc = np.append(pc, 0)

    if PERM and PORO and a and b and sigma_costau:
        # When all required values to calculate Pc have been entered, calculate Pc:
        for i in range(len(sw)):
            pc[i] = calcPc(sw[i], PERM, PORO, a, b, sigma_costau)

    return sw, krw, krow, pc


# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# ++++++++++++++++++++++++++++++++++++++++++ MAIN ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

if not os.path.isfile(args.config_file):
    sys.exit("Could not find the configuration file: %s" % args.config_file)

output = ""
f = open(args.config_file, "r")

for line in f:
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

            a = None
            if len(relperm_input) == 13: #??
                (PERM, PORO, a, b, sigma_costau) = relperm_input[10:14]

            wo = pyscal.WaterOil(h=1.0/(num_sw_steps+2), sorw=Sorw, swirr=Swirr)
            wo.add_LET_oil(Lo, Eo, To, kroend=1)
            wo.add_LET_water(Lw, Ew, Tw, krwend=Krwo)
            if a:
                wo.add_simple_J(a=a, b=b, poro_ref=PORO, perm_ref=PERM, )
            print(wo.SWOF(header=False))

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
f.close()

print("Writing output file...")
# Write output file
f = open(args.output_file, "w")
f.write(output)
f.close()
print("Done")
