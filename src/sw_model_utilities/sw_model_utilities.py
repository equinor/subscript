#!/usr/bin/env python
#
# Script for some useful Sw calculations
#
# JRIV
from copy import deepcopy
import matplotlib.pyplot as plt
import numpy as np
import math as math


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
    h = np.arange(0.01, hmax, 0.1)

    for i in range(0, len(av)):
        if option == 3:
            txt = (
                desc[i]
                + "  a="
                + str(av[i])
                + " b="
                + str(bv[i])
                + " $\\phi=$"
                + str(poro[i])
                + " $\\kappa=$"
                + str(perm[i])
            )
        else:
            txt = (
                desc[i]
                + "(inverse)  A="
                + str(avorig[i])
                + " B="
                + str(bvorig[i])
                + " $\\phi=$"
                + str(poro[i])
                + " $\\kappa=$"
                + str(perm[i])
            )

        swn = av[i] * (h * math.sqrt(perm[i] / poro[i])) ** bv[i]
        sw = swirra[i] + (1.0 - swirra[i]) * swn
        plt.plot(sw, h, label=txt)
        if (swirra[i] > 0.0):
            plt.plot(np.zeros(h.size) + swirra[i], h, "--", color="grey", )

    plt.axis([0, 1, 0, hmax])
    plt.legend(loc="upper right", shadow=True, fontsize=10)
    plt.xlabel("$S_w$")
    plt.ylabel("Height above FWL")
    plt.text(1.2, 15, "$\\phi=$")
    plt.show()


if __name__ == "__main__":

    option, inverse, av, bv, poro, perm, swirra, desc, hmax = menu()

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
