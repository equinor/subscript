"""
NPV calculation of oil and gas production income
"""

import os
import datetime
import sys
import warnings
import argparse

import numpy
import pandas

# import resscript.header as header
from scipy.optimize import newton

from ecl.summary import EclSum

DESCRIPTION = """Calculated present value of oil and gas streams from an Eclipse
simulation. Optional yearly costs, and optional variation in prices."""

BARRELSPRCUBIC = 6.28981077

NOKUNIT = 1000000.0  # all NOK figures are scaled by this value (input and output)


def get_parser():
    """Parser for command line arguments and for documentation"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter, description=DESCRIPTION
    )
    parser.add_argument("datafiles", nargs="+", help="Input Eclipse DATA files")
    parser.add_argument(
        "--oilprice", type=float, default=60, help="Constant oil price in $/bbl"
    )
    parser.add_argument(
        "--gasprice", type=float, default=1.7, help="Constant gas price in MNOK/Gsm3"
    )
    parser.add_argument(
        "--usdtonok", type=float, default=7.0, help="USD to NOK conversion"
    )
    parser.add_argument(
        "--discountrate", type=float, default=8, help="Discount rate in percent"
    )
    parser.add_argument(
        "--discountto",
        type=int,
        default=datetime.datetime.now().year,
        help="Which year to discount to",
    )
    parser.add_argument(
        "--writetoparams",
        action="store_true",
        default=False,
        help="Write results to parameters.txt",
    )
    parser.add_argument(
        "--paramname",
        type=str,
        default="PresentValue",
        help="Parameter-name in parameters.txt",
    )
    parser.add_argument(
        "--oilvector",
        type=str,
        help=(
            "Eclipse vector to read cumulative oil production from. "
            "Use None to ignore."
        ),
        default="FOPT",
    )
    parser.add_argument(
        "--gasvector",
        type=str,
        help=(
            "Eclipse vector to read cumulative gas production from. "
            "Use None to ignore."
        ),
        default="FGPT",
    )
    parser.add_argument(
        "--gasinjvector",
        type=str,
        help=(
            "Eclipse vector to read cumulative gas injection from. "
            "Use None to ignore."
        ),
        default="FGIT",
    )
    parser.add_argument(
        "--cutoffyear",
        type=int,
        default=2100,
        help="Ignore data beyond 1 Jan this year",
    )
    parser.add_argument(
        "--econtable",
        type=str,
        help=(
            "Comma separated table with years as rows, and column names specifying "
            "economical parameters. Supported column names: oilprice (USD/bbl), "
            "gasprice (NOK/sm3), usdtonok, costs (MNOK)"
        ),
    )
    parser.add_argument(
        "--basedatafiles",
        nargs="+",
        default=[],
        help=(
            "Input Eclipse DATA files to be used as base "
            "cases to calculate delta production profiles"
        ),
    )
    parser.add_argument(
        "--bepcalcmethod",
        type=int,
        default=0,
        help=(
            "Select a method to be used to calculate the break-even price. "
            "(0) EPA Q4 2015 External Assumptions; "
            "there is a link between gas and oil prices and the "
            "resulting break-even price is in USD/boe; "
            "(1) Fixed gas prices, the resulting break-even price "
            "is in USD/bbl. This can be used to evaluate "
            "gas injection/deferral projects."
        ),
    )
    parser.add_argument("--verbose", action="store_true", help="Be verbose")
    parser.add_argument("--quiet", "-q", action="store_true", help="Be quiet")
    return parser


def main():
    """Function for command line invocation"""
    parser = get_parser()
    args = parser.parse_args()

    filenameswithoutpath = [os.path.split(x)[1] for x in args.datafiles]

    # Check the number of supplied base cases.
    if not (
        len(args.basedatafiles) == 0
        or len(args.basedatafiles) == 1
        or len(args.basedatafiles) == len(filenameswithoutpath)
    ):
        sys.exit(
            (
                "Supply either no base cases, a single base case or "
                "exactly as many base cases as datafiles. Script stopped."
            )
        )

    # Are filenames (dir-names stripped) uniquely describing each submitted datafile?
    filenamesunique = False
    if len(set(filenameswithoutpath)) == len(args.datafiles):
        filenamesunique = True

    # Read table from user input
    if args.econtable:
        economics = pandas.read_csv(args.econtable, index_col=0)
        # Allow user to have spaces around commas in table header:
        economics.columns = economics.columns.map(str.strip)
    else:
        economics = pandas.DataFrame(
            index=[1900]
        )  # Add an irrelevant year for providing default values

    # Fill in missing pieces
    if "oilprice" not in economics.columns:
        economics["oilprice"] = args.oilprice
    if "gasprice" not in economics.columns:
        economics["gasprice"] = args.gasprice
    if "usdtonok" not in economics.columns:
        economics["usdtonok"] = args.usdtonok
    if "costs" not in economics.columns:
        economics["costs"] = 0

    if args.verbose:
        print("================================================")
        print(" Economical parameters")
        print("  Discount rate:    " + str(args.discountrate))
        print("  Cutoff year:      " + str(args.cutoffyear))
        print("  Discount to year: " + str(args.discountto))
        print("===============================================")
        print(economics)
        print("===============================================")

    for eclcase in args.datafiles:

        if len(args.datafiles) > 1:
            if (
                filenamesunique
            ):  # Print less information if the DATA filenames themselves are unique.
                sys.stdout.write(os.path.split(eclcase)[1].replace(".DATA", "") + " ")
            else:
                sys.stdout.write(eclcase.replace(".DATA", "") + " ")
        try:
            if args.quiet:
                # Catch stderr from EclSum, as EclSum
                # almost always complains for restarted runs
                devnull = os.open(os.devnull, os.O_RDWR)
                stderr_saved = os.dup(2)
                os.dup2(devnull, 2)
            summ = EclSum(eclcase)
            if args.quiet:
                os.dup2(stderr_saved, 2)
                os.close(devnull)
        except OSError:
            if len(args.datafiles) == 1:
                print("ERROR: Was not able to read " + eclcase)
                sys.exit(1)
            else:
                print("WARNING: Unreadable " + eclcase + ", skipping..")
            continue

        # Choose
        if len(args.basedatafiles) == 1:
            baseeclcase = args.basedatafiles[0]
        elif len(args.basedatafiles) > 1:
            baseeclcase = args.basedatafiles[args.datafiles.index(eclcase)]
        else:
            baseeclcase = None
        if baseeclcase:
            try:
                if args.quiet:
                    # Catch stderr from EclSum, as EclSum
                    # almost always complains for restarted runs
                    devnull = os.open(os.devnull, os.O_RDWR)
                    stderr_saved = os.dup(2)
                    os.dup2(devnull, 2)
                basesumm = EclSum(baseeclcase)
                if args.quiet:
                    os.dup2(stderr_saved, 2)
                    os.close(devnull)
            except OSError:
                if len(args.basedatafiles) == 1:
                    print("ERROR: Was not able to read " + baseeclcase)
                    sys.exit(1)
                else:
                    print("WARNING: Unreadable " + baseeclcase + ", skipping..")
                    continue

        last_year = summ.end_time.year
        first_date = summ.data_start.date()
        # If restart information can't be loaded,
        # we must use this instead of summ.start_time.
        cutoffyear = min(args.cutoffyear, last_year)

        def datetimeyear(year):
            return datetime.date(year, 1, 1)

        janfirsts = list(map(datetimeyear, list(range(args.discountto, last_year + 1))))
        janfirsts = [
            max(x, first_date) for x in janfirsts
        ]  # Don't ask for dates occuring before Eclipse production startup.
        if len(janfirsts) == 0:
            print(
                "ERROR: No first of Januaries found. Discount to "
                + str(args.discountto)
                + ", last year in sim: "
                + str(last_year)
            )
            continue

        production = pandas.DataFrame(index=list(range(args.discountto, last_year + 1)))
        if args.oilvector != "None":
            if args.oilvector in summ:
                production["OPT"] = summ.get_interp_vector(
                    args.oilvector, date_list=janfirsts
                )
                if baseeclcase:
                    if args.oilvector in basesumm:
                        production["OPT"] = production[
                            "OPT"
                        ] - basesumm.get_interp_vector(
                            args.oilvector, date_list=janfirsts
                        )
                    else:
                        print(
                            "ERROR: Oilvector "
                            + args.oilvector
                            + " not found in base summary file"
                        )
                        sys.exit(1)
            else:
                print(
                    "ERROR: Oilvector " + args.oilvector + " not found in summary file"
                )
                sys.exit(1)
        else:
            production["OPT"] = 0
        if args.gasvector != "None":
            if args.gasvector in summ:
                production["GPT"] = summ.get_interp_vector(
                    args.gasvector, date_list=janfirsts
                )
                if baseeclcase:
                    if args.gasvector in basesumm:
                        production["GPT"] = production[
                            "GPT"
                        ] - basesumm.get_interp_vector(
                            args.gasvector, date_list=janfirsts
                        )
                    else:
                        print(
                            "ERROR: Gasvector "
                            + args.gasvector
                            + " not found in base summary file"
                        )
                        sys.exit(1)
            else:
                print(
                    "ERROR: Gasvector " + args.gasvector + " not found in summary file"
                )
                sys.exit(1)
        else:
            production["GPT"] = 0
        if args.gasinjvector in summ:
            production["GIT"] = summ.get_interp_vector(
                args.gasinjvector, date_list=janfirsts
            )
            if baseeclcase:
                if args.gasinjvector in basesumm:
                    production["GIT"] = production["GIT"] - basesumm.get_interp_vector(
                        args.gasinjvector, date_list=janfirsts
                    )
        else:
            production["GIT"] = 0

        numberofyears = len(janfirsts)
        # Calculate yearly production; use EclSum.getBlockedProduction???

        opr = list(
            production["OPT"][1:numberofyears].values
            - production["OPT"][0 : numberofyears - 1].values
        )
        opr.append(0)  # Add the trailing number after creating the difference vector
        production["OPR"] = opr
        gpr = list(
            production["GPT"][1:numberofyears].values
            - production["GPT"][0 : numberofyears - 1].values
        )
        gpr.append(0)  # Add the trailing number after creating the difference vector
        production["GPR"] = gpr

        if args.gasinjvector in summ:
            gir = list(
                production["GIT"][1:numberofyears].values
                - production["GIT"][0 : numberofyears - 1].values
            )
            gir.append(0)
            production["GIR"] = gir
        else:
            production["GIR"] = 0

        # Deduct gas injection
        production["GSR"] = production["GPR"] - production["GIR"]

        production["discountfactors"] = 1.0 / (
            1.0 + args.discountrate / 100.0
        ) ** numpy.array(list(range(0, len(janfirsts))))

        # Merge with econonics table, ffill NaN's coming
        # from limited economics information
        prodecon = pandas.concat([production, economics], axis=1, sort=True)
        prodecon[["oilprice", "gasprice", "usdtonok"]] = prodecon[
            ["oilprice", "gasprice", "usdtonok"]
        ].fillna(method="ffill")
        # Avoid ffilling costs...
        # There could be situations where we need to bfill prices as well,
        # if the user provided a econtable
        prodecon[["oilprice", "gasprice", "usdtonok"]] = prodecon[
            ["oilprice", "gasprice", "usdtonok"]
        ].fillna(method="bfill")
        prodecon.fillna(value=0, inplace=True)  # Zero-pad other data (costs)
        prodecon["presentvalue"] = (
            prodecon["OPR"]
            * BARRELSPRCUBIC
            * prodecon["oilprice"]
            * prodecon["usdtonok"]
            + prodecon["GSR"] * prodecon["gasprice"]
            - prodecon["costs"] * NOKUNIT
        ) * prodecon["discountfactors"]

        # Remove the year 1900 that was added for flat prices:
        prodecon = prodecon[prodecon.index != 1900]

        pvalue = prodecon.loc[: cutoffyear - 1]["presentvalue"].sum() / NOKUNIT

        if args.verbose:
            pandas.set_option(
                "expand_frame_repr", False
            )  # Avoid line wrapping in tabular output
            print("===============================================")
            print(" Production and economic parameters:")
            print(prodecon.loc[: cutoffyear - 1])
            print("===============================================")

        print("PresentValue", pvalue, end=" ")

        if prodecon["costs"].sum() > 0:
            # When costs are supplied, the break-even
            # price IRR and CEI can be calculated.

            # Do not print Newton iteration warnings to the screen
            warnings.filterwarnings("ignore")

            def calc_pv_bep(price):
                # "9.3*3.7912679516/100/100" comes from
                # cell D123 EPA Q4 2015 (external assumptions)

                production["bep_prices"] = price
                if args.bepcalcmethod == 0:

                    prodecon["pv_bep"] = (
                        prodecon["OPR"]
                        * BARRELSPRCUBIC
                        * production["bep_prices"]
                        * prodecon["usdtonok"]
                        + (
                            prodecon["GSR"]
                            * production["bep_prices"]
                            * 9.3
                            * 3.7912679516
                            / 100
                            / 100
                            * prodecon["usdtonok"]
                        )
                        - prodecon["costs"] * NOKUNIT
                    ) * prodecon["discountfactors"]

                elif args.bepcalcmethod == 1:
                    prodecon["pv_bep"] = (
                        prodecon["OPR"]
                        * BARRELSPRCUBIC
                        * production["bep_prices"]
                        * prodecon["usdtonok"]
                        + (prodecon["GSR"] * prodecon["gasprice"])
                        - prodecon["costs"] * NOKUNIT
                    ) * prodecon["discountfactors"]

                else:
                    sys.exit("No valid break-even calculation method requested.")

                pv_bep = prodecon.loc[: cutoffyear - 1]["pv_bep"].sum() / NOKUNIT

                return pv_bep

            try:
                bep = newton(calc_pv_bep, 50, maxiter=50)
                if not abs(calc_pv_bep(bep)) < 0.01:
                    bep = "NaN"
                if bep < 0:
                    bep = "NaN"
                print("BEP", bep, end=" ")

            except ArithmeticError:
                print("BEP", str(0), end=" ")

            def calc_pv_irr(rate):
                production["discountfactors_irr"] = 1.0 / (
                    1.0 + rate / 100.0
                ) ** numpy.array(list(range(0, len(janfirsts))))

                prodecon["pv_irr"] = (
                    prodecon["OPR"]
                    * BARRELSPRCUBIC
                    * prodecon["oilprice"]
                    * prodecon["usdtonok"]
                    + prodecon["GSR"] * prodecon["gasprice"]
                    - prodecon["costs"] * NOKUNIT
                ) * production["discountfactors_irr"]

                pv_irr = prodecon.loc[: cutoffyear - 1]["pv_irr"].sum() / NOKUNIT

                return pv_irr

            try:
                irr = newton(calc_pv_irr, 10, maxiter=50)
                if not abs(calc_pv_irr(irr)) < 0.01:
                    irr = "NaN"
                print("IRR", irr, end=" ")
            except ArithmeticError:
                print("IRR", str(0), end=" ")
                irr = "NaN"

            # Print CEI
            pv_negativecashflow = abs(
                prodecon.loc[: cutoffyear - 1]["presentvalue"][
                    prodecon["presentvalue"] < 0
                ].sum()
                / NOKUNIT
            )
            cei = pvalue / pv_negativecashflow if pv_negativecashflow > 0 else 999
            print("CEI", cei, end=" ")

        print("")
        cwd = os.getcwd()

        if args.writetoparams:
            os.chdir(os.path.dirname(os.path.realpath(eclcase)))
            paramlocations = [
                "parameters.txt",
                "../parameters.txt",
                "../../parameters.txt",
            ]
            for paramfile in paramlocations:
                if os.path.isfile(
                    paramfile
                ):  # Looking relative to the directory containing the DATA file
                    handle = open(paramfile, "a")
                    handle.write(args.paramname + " " + str(pvalue) + "\n")
                    if prodecon["costs"].sum() > 0:
                        handle.write(args.paramname + "_BEP" + " " + str(bep) + "\n")
                        handle.write(args.paramname + "_IRR" + " " + str(irr) + "\n")
                        handle.write(args.paramname + "_CEI" + " " + str(cei) + "\n")
                    handle.close()
                    continue  # (only write to one parameters.txt)
            os.chdir(cwd)


if __name__ == "__main__":
    main()
