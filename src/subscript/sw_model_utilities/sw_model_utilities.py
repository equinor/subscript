#!/usr/bin/env python
#
# Script for some useful Sw calculations
# This is an interactive script, and is not used as a part of a FMU run
#
# https://wiki.equinor.com/wiki/index.php/Res:The_sw_model_utilities_script
#
# JRIV

import argparse
import math
from copy import deepcopy
import matplotlib.pyplot as plt
import numpy as np


def get_parser():
    epilog = """This is a simple interactive script for converting
    'a', 'b' between normal and inverse Leverett SwJ formulations. This is in
    particular useful for RMS, which uses the inverse formulation while,
    input from petrphysiscist is usually on the normal form.
    In addition, interactive plotting of Sw vs height is provided
    (simplified Leverett).
    """

    parser = argparse.ArgumentParser(epilog=epilog)

    return parser


def menu():

    print("Choices:\n")
    print("1. Convert a TO A and b to B from Sw = aJ^b to Sw=(J/A)^(1/B)")
    print("2. Convert A to a and B to b from Sw = (J/A)^(1/B) to Sw=aJ^b")
    print("3. Plot height function (input as Sw = aJ^b) with swirra: ")
    print("4. Plot height function (input as Sw = (J/A)^(1/B) with swirra: ")
    print("")
    try:
        mode = int(input("Choose: "))
    except ValueError:
        print("Not a number")

    # initial
    av = []
    bv = []
    poro = []
    perm = []
    swirra = []
    desc = []
    inverse = False
    hmax = 0.0

    if mode == 1:
        aval = float(input("a: "))
        bval = float(input("b: "))
        av.append(aval)
        bv.append(bval)

    elif mode == 2:
        aval = float(input("A: "))
        bval = float(input("B: "))
        av.append(aval)
        bv.append(bval)
        inverse = True

    elif mode >= 3:
        nplot = int(input("Number of curves: "))

        hmax = float(input("Height maximum: "))

        for i in range(0, nplot):
            print("Set no. ", i + 1)
            poro.append(float(input("Poro (frac): ")))
            perm.append(float(input("Perm (mD): ")))
            swirra.append(float(input("Swirra (frac): ")))
            desc.append(input("Short description: "))

            if mode == 3:
                av.append(float(input("a: ")))
                bv.append(float(input("b: ")))

            if mode == 4:
                av.append(float(input("A: ")))
                bv.append(float(input("B: ")))

    return mode, inverse, av, bv, poro, perm, swirra, desc, hmax


def autoformat(num):
    """Autoformat to 'f' or 'e' format ,depending on size of number"""
    if abs(num) > 0.01:
        num = "{:.4f}".format(num)
    else:
        num = "{:.4e}".format(num)
    return num


# ==============================================================================
# A and B algebraic conversion
# ==============================================================================


def convert_normal2inverse(aval, bval):
    # same formula both ways!
    bval2 = 1.0 / bval
    aval2 = (1.0 / aval) ** (bval2)

    return aval2, bval2


# # ==============================================================================
# # Plotting
# # ==============================================================================


def plotting(option, av, bv, avorig, bvorig, poro, perm, swirra, desc, hmax):

    # height array; create an array from min to max, with step:
    hei = np.arange(0.01, hmax, 0.1)

    for ix, _vec in enumerate(av):
        if option == 3:
            txt = (
                desc[ix]
                + "  a="
                + str(av[ix])
                + " b="
                + str(bv[ix])
                + " $\\phi=$"
                + str(poro[ix])
                + " $\\kappa=$"
                + str(perm[ix])
            )
        else:
            txt = (
                desc[ix]
                + "(inverse)  A="
                + str(avorig[ix])
                + " B="
                + str(bvorig[ix])
                + " $\\phi=$"
                + str(poro[ix])
                + " $\\kappa=$"
                + str(perm[ix])
            )

        swn = av[ix] * (hei * math.sqrt(perm[ix] / poro[ix])) ** bv[ix]
        sw = swirra[ix] + (1.0 - swirra[ix]) * swn
        plt.plot(sw, hei, label=txt)
        if swirra[ix] > 0.0:
            plt.plot(np.zeros(hei.size) + swirra[ix], hei, "--", color="grey")

    plt.axis([0, 1, 0, hmax])
    plt.legend(loc="upper right", shadow=True, fontsize=10)
    plt.xlabel("$S_w$")
    plt.ylabel("Height above FWL")
    plt.text(1.2, 15, "$\\phi=$")
    plt.show()


def main():
    """Entry point from command line"""

    parser = get_parser()
    _args = parser.parse_args()

    option, _inverse, av, bv, poro, perm, swirra, desc, hmax = menu()

    if option == 1:
        aval2, bval2 = convert_normal2inverse(av[0], bv[0])
        print(
            "\nInverse values are: A={0} and  B={1}\n".format(
                autoformat(aval2), autoformat(bval2)
            )
        )

    if option == 2:
        aval2, bval2 = convert_normal2inverse(av[0], bv[0])
        print(
            "\nNormal values are: a={0} and  b={1}\n".format(
                autoformat(aval2), autoformat(bval2)
            )
        )

    if option >= 3:

        avorig = av
        bvorig = bv

        if option == 4:
            newav = []
            newbv = []
            for aval, bval in zip(av, bv):
                avx, bvx = convert_normal2inverse(aval, bval)
                newav.append(avx)
                newbv.append(bvx)

            avorig = deepcopy(av)
            bvorig = deepcopy(bv)
            av = newav
            bv = newbv

        plotting(option, av, bv, avorig, bvorig, poro, perm, swirra, desc, hmax)

    print("\nThat's all folks")


if __name__ == "__main__":
    main()
