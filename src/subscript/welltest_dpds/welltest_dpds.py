#!/usr/bin/env python

import sys
import os
import argparse
import numpy as np
from ecl.summary import EclSum


DESCRIPTION = """
Script to extract simulated welltest results from simulator output.

Required summary vectors in sim deck:
  -days,
  -wbhp:well_name,
  -wwpr:well_name,
  -wopr:well_name if main_phase == OIL
  -wgpr:well_name if main_phase == GAS

Outputs pressure vs superpositioned time derivative

"""

"""

Script is a rewrite of a legacy script originally developed and improved by:
 * Jon Sætrom
 * Bjørn Kåre Hegstad
 * Cecile Otterlei
 * Hodjat Moradi

AUTHOR: Eivind Smørgrav

TODO
 - Support pseudo pressure vs time relevant for gas and gas condensate fields.
 - Make error handling more robust, eg:
     - check if all necessary vectors are present wbhp, wopr or wgpr, wwpr is optional
- decide how the output files should be handled, there are many and messy as of now
- make an ERT JOB
- submit to subscript and ert handle in komodo
- old script did not exist(1) with invalid input, but reported nans in the outfiles,
  which is very bad practice. Discuss with users
"""

CATEGORY = "modelling.reservoir"

EXAMPLES = """
.. code-block:: console

 FORWARD_MODEL WELLTEST_DPDS(<ECLBASE>, <WELLNAME>=DST_WELL)

"""

def get_parser():
    """
    Define the argparse parser

    Returns:
        parser (argparse.ArgumentParser)
    """
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "eclcase",
        type=str,
        help="Eclipse case to extract from",
    )
    parser.add_argument(
        "wellname",
        type=str,
        help="Name of well to extract results from",
    )
    parser.add_argument(
        "--outfilessufix",
        type=str,
        help='Sufix to be added to result files. Default: ""',
        default="",
    )
    parser.add_argument(
        "-n",
        "--buildup_nr",
        type=int,
        help="Buildup nr, eg which buildup to extract. Counting from 1. Default: 1 ",
        default=1,
    )
    parser.add_argument(
        "-o",
        "--outputdirectory",
        type=str,
        help="Directory to put the output files. Detault: .",
        default="./",
    )
    parser.add_argument(
        "--phase",
        type=str,
        choices=["OIL", "GAS"],
        help="Main fluid phase in test (OIL/GAS). Default: OIL",
        default="OIL",
        required=False,
    )
    return parser


def get_summary_vec(summary, key):
    """
    Read vector corresponding to key from summary instance

    Args:
       summary: (ecl.summary.EclSum)
       key: (str)

    Returns:
        vec  : np.array
    """

    try:
        return summary.numpy_vector(key)
    except KeyError:
        print("No such key in summary file:" + key)
        raise


def get_buildup_indices(rates):
    """
    Go through the simulated rate and identify bu periods, as defined by zero flow.

    Returns:
    buildup_incices     : list of indices associated with start of the buildups
    buildup_end_incices : list of indices associated with end of the buildups

    Args:
       rates: np.array

    Returns:
       buildup_indices (list)
       buildup_end_indices (list)


    """

    buildup_indices = []
    buildup_end_indices = []

    last = 0
    for i, rate in enumerate(rates):
        if rate == 0 and last > 0.0:
            buildup_indices.append(i)
        if rate > 0 and last == 0:
            buildup_end_indices.append(i - 1)
        if i == len(rates) - 1 and rate == 0:
            buildup_end_indices.append(i)
        last = rate

    if rates[0] == 0:
        del buildup_end_indices[0]

    return buildup_indices, buildup_end_indices


def get_supertime(time, rate, bu_start_ind, bu_end_ind):
    """
    Calculate supertime

    Args:
        time (np.array)
        rate (np.array)
        bu_start_ind (int)
        bu_end_ind (int)

    Returns:
        supertime (np.array)
    """

    rdiff = np.diff(rate)
    rdiff = np.hstack((rate[0] - 0, rdiff))

    super_time = np.zeros(bu_end_ind + 1 - bu_start_ind)
    coeff1 = 1 / (0.0 - rate[bu_start_ind - 1])
    # 1/(q_n - q_n-1)  where q_n is zero (start of BU and q_n-1 is last rate before BU

    for bu_time_ind in range(1, bu_end_ind - bu_start_ind + 1):
        # Cannot start from zero. Hence from 1 and not 0 in loop. (Avoid ln(0))
        tot = 0.0
        for i in range(0, bu_start_ind):
            # End at len-1 because n is not included - only n-1 in formula
            tot = tot + rdiff[i] * np.log(time[bu_start_ind + bu_time_ind] - time[i])
        super_time[bu_time_ind] = coeff1 * tot + np.log(
            time[bu_start_ind + bu_time_ind] - time[bu_start_ind]
        )

    return super_time[1:]


def get_weighted_avg_press_time_derivative_lag1(dp, dspt):
    """
    Compute weighted average of pressure time derivative,
    one time step to each side. Lag1

    Formula: (  (dp_f/dspt_f)*dspt_b + (dp_b/dspt_b)*dspt_f )/(dspt_f + dspt_b)

    spt is SuperPositionedTime and dspt is delta spt

    Args:
        dp (np.array)
        dspt (np.array)

    Returns:
        dpdspt_weighted (np.array)

    """

    dpdspt = dp / dspt
    dspt_forward = np.hstack((dspt, 1))
    # dspt_forward not defined for last time step; set to 1
    dspt_forward[0] = 0
    # To make sure values in the denominator is correct (formula above)

    dspt_backward = np.hstack((1, dspt))
    # dspt_backward not defined for first time step; set to 1
    dspt_backward[-1] = 0
    # To make sure that values in the denominator is correct (formula above)

    dpdspt_forward = np.hstack((dpdspt, 0))
    # Make sure that the last  dpdspt_forward  is set to zero. I.e. not really defined
    dpdspt_backward = np.hstack((0, dpdspt))
    # Make sure that the first dpdspt_backward is set ot zero. I.e. not really defined.

    dpdspt_weighted = (
        dpdspt_forward * dspt_backward + dpdspt_backward * dspt_forward
    ) / (dspt_forward + dspt_backward)

    return dpdspt_weighted


def get_weighted_avg_press_time_derivative_lag2(
    dp, dspt, super_time, wbhp, bu_start_ind, bu_end_ind
):

    """
    Compute weighted average using LAG 2 for pressure time derivative

    Args:
        dp (np.array)
        dspt (np.array)
        supertime (np.array)
        wbhp (np.array)
        bu_start_ind (int)
        bu_end_ind (int)

    Returns:
        dpdspt_weighted_lag2 (np.array)
    """

    spt_raw = super_time

    p_raw = wbhp[bu_start_ind + 1 : bu_end_ind + 1]
    n_lag2 = len(spt_raw) - 2
    dspt_lag2 = np.zeros(n_lag2)
    dp_lag2 = np.zeros(n_lag2)

    # find Lag 2 diff for supertime and pressure
    for i in range(n_lag2):
        dspt_lag2[i] = spt_raw[i + 2] - spt_raw[i]
        dp_lag2[i] = p_raw[i + 2] - p_raw[i]

    # Get the end points right
    dspt_lag2_forward = np.hstack((dspt_lag2, dspt[-1], 1))
    # Last forward step does not exist, Second Last forward  step is only one step

    dp_lag2_forward = np.hstack((dp_lag2, dp[-1], 0))  # As for dspt_forward

    dspt_lag2_backward = np.hstack((1, dspt[0], dspt_lag2))
    # First backward step does not exist. Second backward step is only one step

    dp_lag2_backward = np.hstack((0, dp[0], dp_lag2))  # As for dspt_backward

    # Calculate the lag2 weighted derivative
    dpdspt_lag2_forward = dp_lag2_forward / dspt_lag2_forward
    dpdspt_lag2_backward = dp_lag2_backward / dspt_lag2_backward

    # To get right values in denominator. It has value 1 above,
    # to avoid division on zero.
    dspt_lag2_forward[0] = 0
    dspt_lag2_backward[-1] = 0

    dpdspt_weighted_lag2 = (
        dpdspt_lag2_forward * dspt_lag2_backward
        + dpdspt_lag2_backward * dspt_lag2_forward
    ) / (dspt_lag2_backward + dspt_lag2_forward)

    return dpdspt_weighted_lag2


def to_csv(filen, field_list, header_list, sep=","):
    """
    Dump vectors to csv file. Handles arbitrarly number of fields

    Args:
        filen (str)
        field_list (list of np.array)
        header_list (list of str)
        sep (str)
    Returns:
        pass
    """

    fileh = open(filen, "w")

    fileh.write(header_list[0])
    for header in header_list[1:]:
        fileh.write(sep + header)
    fileh.write("\n")
    for i in range(len(field_list[0])):
        fileh.write("%0.10f" % field_list[0][i])
        for field in field_list[1:]:
            fileh.write(sep + "%0.10f" % field[i])
        fileh.write("\n")
    fileh.close()


def main():
    """
    Main entry point for the script

    Args:

    Returns:
        pass

    """

    print("Running the " + sys.argv[0])
    args = get_parser().parse_args()

    eclcase = args.eclcase
    well_name = args.wellname
    buildup_nr = args.buildup_nr
    main_phase = args.phase
    outf_sufix = args.outfilessufix
    outdir = args.outputdirectory

    if outf_sufix and not outf_sufix.startswith("_"):
        outf_sufix = "_" + outf_sufix

    if outdir == "":
        outdir = "./"

    if not os.path.exists(outdir):
        raise FileNotFoundError("No such outputdirectory:", outdir)

    summary = EclSum(eclcase)

    wbhp = get_summary_vec(summary, "WBHP:" + well_name)
    wwpr = get_summary_vec(summary, "WWPR:" + well_name)
    wopr = None
    wgpr = None
    if main_phase == "OIL":
        wopr = get_summary_vec(summary, "WOPR:" + well_name)
    else:
        wgpr = get_summary_vec(summary, "WGPR:" + well_name)
    time = np.array(summary.days) * 24.0

    if main_phase == "OIL":
        buildup_indices, buildup_end_indices = get_buildup_indices(wopr)
    else:
        buildup_indices, buildup_end_indices = get_buildup_indices(wgpr)

    print("Time step number for start of each buildup period " + str(buildup_indices))
    print(
        "Time step number for end   of each buildup period "
        + str(buildup_end_indices)
        + "\n"
    )

    if buildup_nr > len(buildup_indices):
        sys.stderr.write(
            "There are %d build ups detected for well %s. You asked for nr %d\n"
            % (len(buildup_indices), well_name, buildup_nr)
        )
        sys.exit(1)
    else:
        bu_start_ind = buildup_indices[buildup_nr - 1]
        print(
            "The time step for the start of the %d'th buildup period is %d"
            % (buildup_nr, bu_start_ind)
        )

    # Find end of buildup period.
    bu_end_ind = buildup_end_indices[buildup_nr - 1]
    print(
        "The time step for the end of the %d'th buildup period is %d"
        % (buildup_nr, bu_end_ind)
    )

    if main_phase == "OIL":
        super_time = get_supertime(time, wopr, bu_start_ind, bu_end_ind)
    else:
        super_time = get_supertime(time, wgpr, bu_start_ind, bu_end_ind)

    # print("Supertime (length %d) = " % len(super_time))
    # print(super_time)
    # print("\n")

    # Calculate delta pressure             - lag 1 only
    dp = np.diff(wbhp[bu_start_ind + 1 : bu_end_ind + 1])
    # print("dp (length %d) = " % len(dp))
    # print(dp)
    # print("\n")

    # Calculate delta superpositioned time - lag 1 only
    dspt = np.diff(super_time)  # Supertime at Tn is not defined.
    # print("dspt (length dsupertime %d) = " % len(dspt))
    # print(dspt)
    # print("\n")

    # Cumulative time used from start of buildup
    cum_time = time[bu_start_ind + 1 : bu_end_ind + 1] - time[bu_start_ind]
    # print("cumulative time in buildup of interest (length %d) = " % len(cum_time))
    # print(cum_time)
    # print("\n")

    dpdspt_weighted_lag1 = get_weighted_avg_press_time_derivative_lag1(dp, dspt)
    print(
        "dpdspt_weighted_lag1 (length dpdspt_weighted = %d" % len(dpdspt_weighted_lag1)
    )
    # print(dpdspt_weighted_lag1)

    dpdspt_weighted_lag2 = get_weighted_avg_press_time_derivative_lag2(
        dp, dspt, super_time, wbhp, bu_start_ind, bu_end_ind
    )
    print(
        "dpdspt_weighted_lag2 (length dpdspt_weighted_alg2 = %d"
        % len(dpdspt_weighted_lag2)
    )
    # print(dpdspt_weighted_lag2)

    to_csv(
        outdir + "/dpds_lag1" + outf_sufix + ".csv",
        [cum_time, dpdspt_weighted_lag1],
        ["Hours", "dpd(supt)_w"],
    )
    to_csv(
        outdir + "/dpds_lag2" + outf_sufix + ".csv",
        [cum_time, dpdspt_weighted_lag2],
        ["Hours", "dpd(supt)_w2"],
    )
    to_csv(
        outdir + "/sspt" + outf_sufix + ".csv",
        [super_time],
        ["Superpositioned_time"],
    )
    to_csv(
        outdir + "/wbhp" + outf_sufix + ".csv",
        [time[: bu_end_ind + 1], wbhp[: bu_end_ind + 1]],
        ["Hours", "WBHP"],
    )
    to_csv(
        outdir + "/wwpr" + outf_sufix + ".csv",
        [time[: bu_end_ind + 1], wwpr[: bu_end_ind + 1]],
        ["Hours", "WWPR"],
    )
    if main_phase == "OIL":
        to_csv(
            outdir + "/wopr" + outf_sufix + ".csv",
            [time[: bu_end_ind + 1], wopr[: bu_end_ind + 1]],
            ["Hours", "WOPR"],
        )
    if main_phase == "GAS":
        to_csv(
            outdir + "/wgpr" + outf_sufix + ".csv",
            [time[: bu_end_ind + 1], wgpr[: bu_end_ind + 1]],
            ["Hours", "WGPR"],
        )


if __name__ == "__main__":
    main()
