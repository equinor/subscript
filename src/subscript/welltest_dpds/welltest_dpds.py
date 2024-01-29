#!/usr/bin/env python

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from resdata.summary import Summary
from scipy.interpolate import interp1d

from subscript import __version__

DESCRIPTION = """
Script to extract simulated welltest results. Typically used to compare with welltest
analysis, from eg Kappa Saphir.

Required summary vectors in sim deck:
  * wbhp:well_name
  * wopr:well_name if phase == OIL
  * wgpr:well_name if phase == GAS (do not yet use pseudo-pressure)
  * wwpr:well_name if phase == WATER

Outputs files according to naming convention under outputdirectory/:
  * dpdspt_lag1_suffix.csv; cumtime and superpositioned time derivative of pressure lag1
  * dpdspt_lag2_suffix.csv; cumtime and superpositioned time derivative of pressure lag2
  * spt_suffix.csv; superpositioned time
  * welltest_output_suffix.csv; file with vectors: cumtime, wbhp, wopr, wgpr, wwpr
  * dpdspt_lag1_genobs_suffix_bunr.csv; if --genobs_resultfile is invoked
  * dpdspt_lag2_genobs_suffix_bunr.csv; if --genobs_resultfile is invoked
  * wbhp_genobs_suffix_bunr.csv; if --genobs_resultfile is invoked

suffix is specified by argument outfilesuffix
bunr is specified by argument buildup_nr
genobs_resultfile expects a file with welltest results used to define the time steps
to be reported (typically exported from Saphir with time and pressure derivative).
genobs_resultfile is to generate files used with GENERAL_OBSERVATION/GEN_DATA in ERT.
note: the outfilesuffix argument is then used to pass on the RESTART/report step number.
(in example below outfilesuffix=wellname_reportstep).

.. note:: GAS phase results do not include yet pseudo-time and pseudo-pressure.

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
Example for cases without HM:
-----------------------------
::

   FORWARD_MODEL WELLTEST_DPDS(<ECLBASE>, <WELLNAME>=DST_WELL)

   or

   FORWARD_MODEL  WELLTEST_DPDS(<ECLBASE>, <WELLNAME>=OP_1, <PHASE>=GAS, <BUILDUP_NR>=1,
                 <OUTPUTDIRECTORY>=dst, <OUTFILESSUFFIX>=OP_1)

Example for cases with HM:
--------------------------
::

   FORWARD_MODEL  WELLTEST_DPDS(<ECLBASE>, <WELLNAME>=OP_1, <PHASE>=GAS, <BUILDUP_NR>=2,
                 <OUTPUTDIRECTORY>=dst, <OUTFILESSUFFIX>=OP_1_1,
                 <GENOBS_RESULTFILE>=OP_1_dpdt_bu2_saphir.txt )

Then set-up of GEN_DATA can be
::

   GEN_DATA DPDT_SIM INPUT_FORMAT:ASCII REPORT_STEPS:1
            RESULT_FILE:dpdspt_lag2_genobs_OP_1_%d_2

result_file corresponds to dpdspt_lag2_genobs_<WELLNAME>_%d_<BUILDUP_NR>

.. warning:: Remember to remove line breaks in argument list when copying the
   examples into your own ERT config.
"""


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """
    Multiple inheritance used for argparse to get both
    defaults and raw description formatter
    """

    # pylint: disable=unnecessary-pass


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
            "Option to trigger export of result files compatible with ERT"
            "GENERAL_OBSERVATION file format to be used in history matching. "
            "Expected argument is a file with welltest results used to define"
            "the time steps to be reported (file typically exported from Saphir.)"
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
       summary: (resdata.summary.Summary)
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
    for idx, rate in enumerate(rates):
        if np.isclose(rate, 0) and last > 0.0:
            buildup_indices.append(idx)
        if rate > 0 and np.isclose(last, 0) and idx != 0:
            buildup_end_indices.append(idx - 1)
        if idx == len(rates) - 1 and np.isclose(rate, 0):
            buildup_end_indices.append(idx)
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
        for idx in range(bu_start_ind):
            # End at len-1 because n is not included - only n-1 in formul a
            tot = tot + rdiff[idx] * np.log(
                time[bu_start_ind + bu_time_ind] - time[idx]
            )
        super_time[bu_time_ind] = coeff1 * tot + np.log(
            time[bu_start_ind + bu_time_ind] - time[bu_start_ind]
        )

    return super_time[1:]


def weighted_avg_press_time_derivative_lag1(delta_p, dspt):
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

    dpdspt = delta_p / dspt
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

    return (dpdspt_forward * dspt_backward + dpdspt_backward * dspt_forward) / (
        dspt_forward + dspt_backward
    )


def weighted_avg_press_time_derivative_lag2(
    delta_p, dspt, super_time, wbhp, bu_start_ind, bu_end_ind
):
    """
    Compute weighted average using LAG 2 for pressure time derivative

    Args:
        delta_p (np.array)
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
    for idx in range(n_lag2):
        dspt_lag2[idx] = spt_raw[idx + 2] - spt_raw[idx]
        dp_lag2[idx] = p_raw[idx + 2] - p_raw[idx]

    # Get the end points right
    dspt_lag2_forward = np.hstack((dspt_lag2, dspt[-1], 1))
    # Last forward step does not exist, Second Last forward  step is only one step

    dp_lag2_forward = np.hstack((dp_lag2, delta_p[-1], 0))  # As for dspt_forward

    dspt_lag2_backward = np.hstack((1, dspt[0], dspt_lag2))
    # First backward step does not exist. Second backward step is only one step

    dp_lag2_backward = np.hstack((0, delta_p[0], dp_lag2))  # As for dspt_backward

    # Calculate the lag2 weighted derivative
    dpdspt_lag2_forward = dp_lag2_forward / dspt_lag2_forward
    dpdspt_lag2_backward = dp_lag2_backward / dspt_lag2_backward

    # To get right values in denominator. It has value 1 above,
    # to avoid division on zero.
    dspt_lag2_forward[0] = 0
    dspt_lag2_backward[-1] = 0

    return (
        dpdspt_lag2_forward * dspt_lag2_backward
        + dpdspt_lag2_backward * dspt_lag2_forward
    ) / (dspt_lag2_backward + dspt_lag2_forward)


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

    with open(filen, "w", encoding="utf8") as fileh:
        if header_list:
            fileh.write(header_list[0])
            for header in header_list[1:]:
                fileh.write(sep + header)
            fileh.write("\n")
        for idx in range(len(field_list[0][start:end])):
            fileh.write(f"{field_list[0][idx]:0.10f}")
            for field in field_list[1:]:
                if len(field) != 0:
                    fileh.write(sep + f"{field[idx]:0.10f}")
                else:
                    fileh.write(sep)
            fileh.write("\n")
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

    dframe = pd.read_csv(filen, sep="\t")
    obs_time = dframe["dTime"][1:None].dropna().to_numpy(dtype=float)

    gen_data = np.zeros(len(obs_time))

    interp = interp1d(time, vec)

    for idx, timepoint in enumerate(obs_time):
        if timepoint < time[0]:
            gen_data[idx] = vec[0]
        elif timepoint > time[-1]:
            gen_data[idx] = vec[-1]
        else:
            gen_data[idx] = interp(timepoint)

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

    summary = Summary(eclcase)
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

    if main_phase == "OIL":
        buildup_indices, buildup_end_indices = get_buildup_indices(wopr)
    elif main_phase == "GAS":
        buildup_indices, buildup_end_indices = get_buildup_indices(wgpr)
    else:
        buildup_indices, buildup_end_indices = get_buildup_indices(wwpr)

    print(f"Identified {len(buildup_indices)} buildup periods:")
    print(f"Starting at time steps: {buildup_indices} Corresponding to: ")
    for idx in buildup_indices:
        print(f"  {time[idx]:0.5f} Hours")
    print(f"Ending at time step: {buildup_end_indices} Corresponding to: ")
    for idx in buildup_end_indices:
        print(f"  {time[idx]:0.5f} Hours")

    if buildup_nr > len(buildup_indices):
        raise SystemExit(
            f"There are {len(buildup_indices)} build ups detected "
            f"for well {well_name}. You asked for nr {buildup_nr}."
        )
    bu_start_ind = buildup_indices[buildup_nr - 1]
    print(
        f"Selected buildup period is nr {buildup_nr}, "
        f"starting at: {time[buildup_indices[buildup_nr - 1]]:0.5f} Hours"
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
    delta_p = np.diff(wbhp[bu_start_ind + 1 : bu_end_ind + 1])

    # Calculate delta superpositioned time - lag 1 only
    dspt = np.diff(super_time)  # Supertime at Tn is not defined.

    # Cumulative time used from start of buildup
    cum_time = time[bu_start_ind + 1 : bu_end_ind + 1] - time[bu_start_ind]

    dpdspt_weighted_lag1 = weighted_avg_press_time_derivative_lag1(delta_p, dspt)

    dpdspt_weighted_lag2 = weighted_avg_press_time_derivative_lag2(
        delta_p, dspt, super_time, wbhp, bu_start_ind, bu_end_ind
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
