#!/usr/bin/env python

import sys
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from ecl.summary import EclSum

from subscript import __version__

DESCRIPTION = """
Script to extract simulated welltest results. Typically used to compare with welltest
analysis, from eg Kappa Saphir.

Required summary vectors in sim deck:
  * wbhp:well_name
  * wopr:well_name if phase == OIL
  * wgpr:well_name if phase == GAS
  * wwpr:well_name if phase == WATER

Outputs files according to naming convention outputdirectory/fname_outfilesuffix.csv:
  * dpdspt_lag1; cumtime and superpositioned time derivative of pressure lag 1
  * dpdspt_lag2; cumtime and superpositioned time derivative of pressure lag 2
  * spt; superpositioned time
  * welltest; unified csv file with vectors: cumtime, wbhp, wopr, wgpr, wwpr
  * dpdspt_lag1_genobs_suffix_bunr; if --genobs_resultfile is invoked
  * dpdspt_lag2_genobs_suffix_bunr; if --genobs_resultfile is invoked
  * wbhp_genobs_suffix_bunr; if --gen_obs_result_file is invoked

gen_obs_result_file is to generate files to be used with GENERAL_OBSERVATION in ERT.
Note: the outfilesuffix argument is then used to pass on the RESTART/report step number.

"""

"""
Script is a rewrite of legacy script originally developed and improved by:
 * Jon Sætrom
 * Bjørn Kåre Hegstad
 * Cecile Otterlei
 * Hodjat Moradi

AUTHOR:
 * Eivind Smørgrav

To do:
 * Support pseudo pressure vs time relevant for gas and gas condensate fields.
 * Add cli option to output other vectors in csv file

:meta private:
"""

CATEGORY = "modelling.reservoir"

EXAMPLES = """
.. code-block:: console

 FORWARD_MODEL WELLTEST_DPDS(<ECLBASE>, <WELLNAME>=DST_WELL)

 FORWARD_MODEL  WELLTEST_DPDS(<ECLBASE>, <WELLNAME>=OP_1, <PHASE>=GAS,
    <BUILDUP_NR>=1, <OUTPUTDIRECTORY>=dst, <OUTFILESSUFFIX>=OP_1_1)

Then GEN_DATA DPDT_SIM  INPUT_FORMAT:ASCII REPORT_STEPS:1
RESULTS_FILE:dpdspt_lag2_genobs_<WELLNAME>_%d_<BUILDUP_NR>
"""


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """
    Multiple inheritance used for argparse to get both
    defaults and raw description formatter
    """

    # pylint: disable=unnecessary-pass
    pass


def get_parser():
    """
    Define the argparse parser

    Returns:
        parser (argparse.ArgumentParser)
    """

    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=CustomFormatter,
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
        "--outfilessuffix",
        type=str,
        help="Suffix to be added to result files.",
        default="",
    )
    parser.add_argument(
        "-n",
        "--buildup_nr",
        type=int,
        help="Buildup nr, eg which buildup to extract. Counting from 1.",
        default=1,
    )
    parser.add_argument(
        "-o",
        "--outputdirectory",
        type=str,
        help="Directory to put the output files.",
        default=".",
    )
    parser.add_argument(
        "--phase",
        type=str,
        choices=["OIL", "GAS", "WATER"],
        help="Main fluid phase in test (OIL/GAS/WATER).",
        default="OIL",
        required=False,
    )
    parser.add_argument(
        "--genobs_resultfile",
        type=str,
        help=(
            "File with welltest results used to define time steps, "
            "typically exported from Saphir. If present, additional files "
            "to be used with GENERAL_OBSERVATION in ERT are produced"
        ),
        default=None,
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + __version__ + ")",
    )
    return parser


def summary_vec(summary, key, required=True):
    """
    Read vector corresponding to key from summary instance

    Args:
       summary: (ecl.summary.EclSum)
       key: (str)
       required: (bool)

    Returns:
        vec  : np.array

    """

    try:
        return summary.numpy_vector(key)
    except KeyError:
        print("No such key in summary file:" + key)
        if required:
            raise
    return np.array([])


def get_buildup_indices(rates):
    """
    Go through the simulated rate and identify bu periods, as defined by zero flow.

    Args:
       rates: np.array

    Returns:
       buildup_indices : (list) indices associated with start of buildups
       buildup_end_indices : (list) indices associated with end of buildups

    """

    buildup_indices = []
    buildup_end_indices = []

    last = 0
    for i, rate in enumerate(rates):
        if np.isclose(rate, 0) and last > 0.0:
            buildup_indices.append(i)
        if rate > 0 and np.isclose(last, 0) and not i == 0:
            buildup_end_indices.append(i - 1)
        if i == len(rates) - 1 and np.isclose(rate, 0):
            buildup_end_indices.append(i)
        last = rate

    if rates[0] == 0:
        del buildup_end_indices[0]

    return buildup_indices, buildup_end_indices


def supertime(time, rate, bu_start_ind, bu_end_ind):
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


def weighted_avg_press_time_derivative_lag1(dp, dspt):
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


def weighted_avg_press_time_derivative_lag2(
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


def to_csv(filen, field_list, header_list=None, start=0, end=None, sep=","):
    """
    Dump vectors to csv file. Handles arbitrarly number of fields

    Args:
        filen (str)
        field_list (list of np.array)
        header_list (list of str)
        start (int)
        end (int)
        sep (str)
    Returns:
        pass

    """

    fileh = open(filen, "w")

    if header_list:
        fileh.write(header_list[0])
        for header in header_list[1:]:
            fileh.write(sep + header)
        fileh.write("\n")
    for i in range(len(field_list[0][start:end])):
        fileh.write("%0.10f" % field_list[0][i])
        for field in field_list[1:]:
            if len(field) != 0:
                fileh.write(sep + "%0.10f" % field[i])
            else:
                fileh.write(sep)
        fileh.write("\n")
    fileh.close()
    print("Writing file:" + filen)


def genobs_vec(filen, vec, time):
    """
    Adjust vector to time axis defined by observation file.
    Used to create output compatible with ERTs GENERAL_OBSERVATION
    file format and directy comparable with output from eg Kappa Saphir.
    Note; csv files exported from Saphir are separated with \t
    and contain headers with space which makes parsing fragile.

    Args:
        filen : (str) csv file to extract time axis from, using colomn dTime
        vec   : (np.array) Vector to remap onto the axis
        time  : (np.array) Original time axis
    Returns:
        gen_data : (np.array)

    """

    if not Path(filen).exists():
        raise FileNotFoundError("No such file:", filen)

    df = pd.read_csv(filen, sep="\t")
    obs_time = df["dTime"][1:None].dropna().to_numpy(dtype=float)

    gen_data = np.zeros(len(obs_time))

    interp = interp1d(time, vec)

    for i, t in enumerate(obs_time):
        if t < time[0]:
            gen_data[i] = vec[0]
        elif t > time[-1]:
            gen_data[i] = vec[-1]
        else:
            gen_data[i] = interp(t)

    return gen_data


def main():
    """
    Main entry point for the script

    Args:

    Returns:
        pass

    """

    args = get_parser().parse_args()

    eclcase = args.eclcase
    well_name = args.wellname
    buildup_nr = args.buildup_nr
    main_phase = args.phase
    outf_suffix = args.outfilessuffix
    outdir = args.outputdirectory
    genobs_resultf = args.genobs_resultfile

    print("*" * 60)
    print("Running the " + sys.argv[0] + " script")
    print("Extracting results from eclcase:", eclcase)
    print("Extracting result from well:", well_name)
    print()

    if genobs_resultf == "None":
        genobs_resultf = None

    if outf_suffix and not outf_suffix.startswith("_"):
        outf_suffix = "_" + outf_suffix

    if not outdir.endswith("/"):
        outdir = outdir + "/"

    if not Path(outdir).exists():
        raise FileNotFoundError("No such outputdirectory:", outdir)

    summary = EclSum(eclcase)
    time = np.array(summary.days) * 24.0
    wbhp = summary_vec(summary, "WBHP:" + well_name)

    if main_phase == "OIL":
        wopr = summary_vec(summary, "WOPR:" + well_name)
        wgpr = summary_vec(summary, "WGPR:" + well_name, required=False)
        wwpr = summary_vec(summary, "WWPR:" + well_name, required=False)
    elif main_phase == "GAS":
        wopr = summary_vec(summary, "WOPR:" + well_name, required=False)
        wgpr = summary_vec(summary, "WGPR:" + well_name)
        wwpr = summary_vec(summary, "WWPR:" + well_name, required=False)
    else:
        wopr = summary_vec(summary, "WOPR:" + well_name, required=False)
        wgpr = summary_vec(summary, "WGPR:" + well_name, required=False)
        wwpr = summary_vec(summary, "WWPR:" + well_name)

    #    wwpr = summary_vec(summary, "WWPR:" + well_name, required=False)

    if main_phase == "OIL":
        buildup_indices, buildup_end_indices = get_buildup_indices(wopr)
    elif main_phase == "GAS":
        buildup_indices, buildup_end_indices = get_buildup_indices(wgpr)
    else:
        buildup_indices, buildup_end_indices = get_buildup_indices(wwpr)

    print("Identified %d buildup periods:" % (len(buildup_indices)))
    print("Starting at time steps:" + str(buildup_indices) + " Corresponding to:")
    for i in buildup_indices:
        print("  %0.5f Hours" % (time[i]))
    print("Ending at time step:" + str(buildup_end_indices) + " Corresponding to: ")
    for i in buildup_end_indices:
        print("  %0.5f Hours" % (time[i]))

    if buildup_nr > len(buildup_indices):
        sys.stderr.write(
            "There are %d build ups detected for well %s. You asked for nr %d\n"
            % (len(buildup_indices), well_name, buildup_nr)
        )
        sys.exit(1)
    else:
        bu_start_ind = buildup_indices[buildup_nr - 1]
        print(
            "Selected buildup period is nr %d, starting at: %0.5f Hours"
            % (buildup_nr, time[buildup_indices[buildup_nr - 1]])
        )
    print()

    # Find end of buildup period.
    bu_end_ind = buildup_end_indices[buildup_nr - 1]

    if main_phase == "OIL":
        super_time = supertime(time, wopr, bu_start_ind, bu_end_ind)
    elif main_phase == "GAS":
        super_time = supertime(time, wgpr, bu_start_ind, bu_end_ind)
    else:
        super_time = supertime(time, wwpr, bu_start_ind, bu_end_ind)
    # Calculate delta pressure             - lag 1 only
    dp = np.diff(wbhp[bu_start_ind + 1 : bu_end_ind + 1])

    # Calculate delta superpositioned time - lag 1 only
    dspt = np.diff(super_time)  # Supertime at Tn is not defined.

    # Cumulative time used from start of buildup
    cum_time = time[bu_start_ind + 1 : bu_end_ind + 1] - time[bu_start_ind]

    dpdspt_weighted_lag1 = weighted_avg_press_time_derivative_lag1(dp, dspt)

    dpdspt_weighted_lag2 = weighted_avg_press_time_derivative_lag2(
        dp, dspt, super_time, wbhp, bu_start_ind, bu_end_ind
    )

    if genobs_resultf:
        dpdspt_w1_gendata = genobs_vec(genobs_resultf, dpdspt_weighted_lag1, cum_time)
        dpdspt_w2_gendata = genobs_vec(genobs_resultf, dpdspt_weighted_lag2, cum_time)
        wbhp_gendata = genobs_vec(
            genobs_resultf, wbhp[bu_start_ind + 1 : bu_end_ind + 1], cum_time
        )

        to_csv(
            outdir + "dpdspt_lag1_genobs" + outf_suffix + "_" + str(buildup_nr),
            [dpdspt_w1_gendata],
        )
        to_csv(
            outdir + "dpdspt_lag2_genobs" + outf_suffix + "_" + str(buildup_nr),
            [dpdspt_w2_gendata],
        )
        to_csv(
            outdir + "wbhp_genobs" + outf_suffix + "_" + str(buildup_nr),
            [wbhp_gendata],
        )
    to_csv(
        outdir + "dpdspt_lag1" + outf_suffix + ".csv",
        [cum_time, dpdspt_weighted_lag1],
        ["HOURS", "dpd(supt)_w"],
    )
    to_csv(
        outdir + "dpdspt_lag2" + outf_suffix + ".csv",
        [cum_time, dpdspt_weighted_lag2],
        ["HOURS", "dpd(supt)_w2"],
    )
    to_csv(
        outdir + "spt" + outf_suffix + ".csv",
        [super_time],
        ["Superpositioned_time"],
    )

    header_list = [
        "HOURS",
        "WBHP:" + well_name,
        "WOPR:" + well_name,
        "WGPR:" + well_name,
        "WWPR:" + well_name,
    ]

    field_list = [time, wbhp, wopr, wgpr, wwpr]

    to_csv(
        outdir + "welltest_output" + outf_suffix + ".csv",
        field_list,
        header_list,
        start=0,
        end=bu_end_ind + 1,
    )


if __name__ == "__main__":
    main()
