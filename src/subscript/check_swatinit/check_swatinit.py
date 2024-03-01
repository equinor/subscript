"""SWATINIT qc tool"""

import argparse
import sys
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import res2df
from matplotlib import pyplot

import subscript
from subscript.check_swatinit import plotter
from subscript.check_swatinit.constants import (
    __FINE_EQUIL__,
    __HC_BELOW_FWL__,
    __PC_SCALED__,
    __PPCWMAX__,
    __SWATINIT_1__,
    __SWL_TRUNC__,
    __UNKNOWN__,
    __WATER__,
)

logger = subscript.getLogger(__name__)

QC_FLAGS = [
    __FINE_EQUIL__,
    __HC_BELOW_FWL__,
    __PC_SCALED__,
    __PPCWMAX__,
    __SWATINIT_1__,
    __SWL_TRUNC__,
    __UNKNOWN__,
    __WATER__,
]

DESCRIPTION = "QC tool for SWATINIT vs SWAT in Eclipse runs"

CATEGORY = "utility.eclipse"

EXAMPLES = """
.. code-block:: console

  FORWARD_MODEL CHECK_SWATINIT(<DATAFILE>=<ECLBASE>, <OUTPUT>=check_swatinit.csv)

where ``ECLBASE`` is already defined in your ERT config.
"""


def main() -> None:
    """Executed when called from the command line.

    Acts on command line arguments, loads data, performs qc and dumps to
    CSV if requested."""
    parser = get_parser()
    args = parser.parse_args()

    if args.DATAFILE.endswith(".csv"):
        qc_frame = pd.read_csv(args.DATAFILE)
    else:
        eclfiles = res2df.ResdataFiles(args.DATAFILE)

        # Fail hard if the deck is not suitable for this tool or
        # give warnings/hints to the user:
        check_applicability(eclfiles)

        qc_frame = make_qc_gridframe(eclfiles)

        if args.output != "":
            logger.info("Exporting CSV to %s", args.output)
            reorder_dframe_for_nonnans(qc_frame).to_csv(args.output, index=False)

    if "SWATINIT" not in qc_frame:
        print("Model did not use SWATINIT")
        return
    qc_vols = qc_volumes(qc_frame)
    print(human_report_qc_vols(qc_vols))
    qcsum = qc_vols["SWATINIT_WVOL"] + sum([qc_vols[qc_flag] for qc_flag in QC_FLAGS])
    diff = qc_vols["SWAT_WVOL"] - qcsum
    if not np.isclose(diff, 0, atol=1e-6):
        print(f"Unexplained difference: {diff} Rm3")

    print()
    print(human_report_pc_scaling(qc_frame))

    if args.volplot or args.volplotfile:
        plotter.wvol_waterfall(qc_vols)
    if args.volplot:
        pyplot.show()
    if args.volplotfile:
        print(f"Dumping volume plot to {args.volplotfile}")
        pyplot.savefig(args.volplotfile)

    if (args.plotfile or args.plot) and args.eqlnum not in qc_frame["EQLNUM"].values:
        sys.exit(f"Error: EQLNUM {args.eqlnum} does not exist in grid. No plotting.")
    if args.plot or args.plotfile:
        plotter.plot_qc_panels(qc_frame[qc_frame["EQLNUM"] == args.eqlnum])
    if args.plot:
        pyplot.show()
    if args.plotfile:
        print(f"Dumping plot to {args.plotfile}")
        pyplot.savefig(args.plotfile)


def check_applicability(eclfiles: res2df.ResdataFiles) -> None:
    """Check that the input is relevant for usage with check_swatinit. This
    function may raise exceptions, SystemExit or only give warnings"""

    deck = eclfiles.get_deck()

    init = eclfiles.get_initfile()
    if (
        "SWATINIT" not in [initheader[0] for initheader in init.headers]
        and "SWATINIT" not in deck
    ):
        logger.warning(
            "INIT-file/deck does not have SWATINIT, this tool has limited use."
        )

    if "RPTRST" not in deck:
        logger.warning(
            "RPTRST not found in DATA-file, UNRST file is expected to be missing"
        )

    try:
        eclfiles.get_rstfile()
    except FileNotFoundError as exception:
        if "UNIFOUT" not in deck:
            sys.exit(
                "Only unified RESTARTs are supported. Add UNIFOUT to your DATA file."
            )
        logger.error(str(exception))
        sys.exit(
            "No UNRST file found. This is required to get the initial water saturation"
        )


def reorder_dframe_for_nonnans(dframe: pd.DataFrame) -> pd.DataFrame:
    """Reorder a dataframe so that rows with less NaN comes first, this
    will aid data analysis application to deduce correct datatypes for
    columns"""
    null_count = "__NULL_COUNT__"
    dframe[null_count] = dframe.isnull().sum(axis=1)
    return (
        dframe.sort_values(null_count).drop(null_count, axis=1).reset_index(drop=True)
    )


def human_report_qc_vols(qc_vols: Dict[str, float]) -> str:
    """Produce a string with a human report for volumes

    Arguments:
        qc_vols: Dictionary with certain keys assumed to be present

    Returns:
        string (multiline)
    """
    string = ""

    skip_if_zero = [__UNKNOWN__, __WATER__]

    swatinit_hcvol = qc_vols["PORV"] - qc_vols["SWATINIT_WVOL"]
    swat_hcvol = qc_vols["PORV"] - qc_vols["SWAT_WVOL"]
    for key in ["VOLUME", "PORV"]:
        string += f"{key:25s} {qc_vols[key]/1e6:>10.4f} Mrm3\n"
    for key in ["SWATINIT_WVOL"]:
        string += f"{key:25s} {qc_vols[key]/1e6:>10.4f} Mrm3"
        string += 11 * " "
        string += f"HC: {swatinit_hcvol/1e6:>8.3f} Mrm3\n"
    for key in QC_FLAGS:
        if key in skip_if_zero and np.isclose(qc_vols[key], 0, atol=1):
            # Tolerance is 1 rm3, which is small in relevant contexts.
            continue

        string += f"+ {key:23s} {qc_vols[key]/1e6:>10.4f} Mrm3  "
        string += f" {qc_vols[key]/qc_vols['SWATINIT_WVOL']*100:>3.2f} %"
        if swatinit_hcvol > 0.0:
            string += f"         {-qc_vols[key]/swatinit_hcvol*100:>3.2f} %"
        string += "\n"
    for key in ["SWAT_WVOL"]:
        string += f"= {key:23s} {qc_vols[key]/1e6:>10.4f} Mrm3  "
        change = (qc_vols["SWAT_WVOL"] - qc_vols["SWATINIT_WVOL"]) / qc_vols[
            "SWATINIT_WVOL"
        ]
        string += f" {change*100:>3.2f} %"
        if swatinit_hcvol > 0.0:
            hc_change = (swat_hcvol - swatinit_hcvol) / swatinit_hcvol
            string += f"         {hc_change*100:>3.2f} %"
    return string


def human_report_pc_scaling(qc_frame: pd.DataFrame) -> str:
    """Produce a string for human report for capillary scaling

    Args:
        qc_frame: Dataframe with each row representing a reservoir cell.

    Returns:
        string (multiline)
    """
    string = ""
    string += "Maximal values:\n"
    string += "---------------\n"
    string += qc_frame.groupby("SATNUM").max()[["PCOW_MAX"]].to_string()
    string += "\n"
    string += (
        qc_frame.groupby(["EQLNUM", "SATNUM"]).max()[["PPCW", "PC_SCALING"]].to_string()
    )
    string += "\n\n"
    string += "EQUIL initialization option #9:\n"
    string += qc_frame.groupby("EQLNUM").max()[["OIP_INIT"]].astype(int).to_string()
    return string


def make_qc_gridframe(eclfiles: res2df.ResdataFiles) -> pd.DataFrame:
    """Construct a dataframe with needed information for swatinit qc from an
    Eclipse run.

    Makes a dataframe with one row for each active cell. Information from
    satfunc and equil merged in.
    """

    grid_df = res2df.grid.df(
        eclfiles,
        vectors=[
            # All of these are required.
            "FIPNUM",
            "EQLNUM",
            "SATNUM",
            "SWATINIT",  # Not outputted by OPM-flow, injected below
            "SWAT",
            "PORO",
            "PERMX",
            "NTG",
            "PRESSURE",
            "PCW",
            "PPCW",
            "SWL",
            "SWLPC",
            "SWU",
        ],
        rstdates="first",
    )

    # Circumvent bug in res2df that will pick SWL from both INIT and restart file:
    grid_df = grid_df.loc[:, ~grid_df.columns.duplicated()]

    # Merge in PPCWMAX from the deck, it is not reported in binary output files:
    if "PPCWMAX" in eclfiles.get_deck():
        grid_df["PPCWMAX"] = ppcwmax_gridvector(eclfiles)

    # This will be unneccessary from res2df 0.13.0:
    grid_df = grid_df.where(grid_df > -1e20 + 1e13)

    if "SWL" not in grid_df:
        logger.warning("SWL not found in model. Using SWL=0.")
        logger.warning("Consider adding FILLEPS to the PROPS section")
        grid_df["SWL"] = 0.0

    deck = eclfiles.get_deck()
    if "SWATINIT" in deck:
        swatinit_deckdata = deck["SWATINIT"][0][0].get_raw_data_list()
        # This list includes non-active cells, we must map via GLOBAL_INDEX:
        # GLOBAL_INDEX is 0-indexed.
        grid_df["SWATINIT_DECK"] = pd.Series(swatinit_deckdata)[
            grid_df["GLOBAL_INDEX"].astype(int).tolist()
        ].values

    if "SWATINIT" not in grid_df:
        # OPM-flow does not include SWATINIT in the INIT file.
        grid_df.rename({"SWATINIT_DECK": "SWATINIT"}, axis="columns", inplace=True)
    elif "SWATINIT_DECK" in grid_df:
        # (if SWATINIT is inputted using binary data in Eclipse deck, the code above
        # is not able to extract it)
        if not np.isclose(
            (grid_df["SWATINIT_DECK"] - grid_df["SWATINIT"]).abs().max(), 0, atol=1e-7
        ):
            logger.warning("SWATINIT from INIT was not close to SWATINIT  from deck")
        else:
            del grid_df["SWATINIT_DECK"]  # This is not needed

    # Exposed to issues with endpoint scaling in peculiar decks:
    satfunc_df = res2df.satfunc.df(eclfiles)

    # Merge in the input pcmax pr. satnum for each cell:
    grid_df = merge_pc_max(grid_df, satfunc_df)

    grid_df = merge_equil(grid_df, res2df.equil.df(eclfiles, keywords=["EQUIL"]))

    grid_df = augment_grid_frame_qc_vectors(grid_df)

    if "PPCW" not in grid_df:
        grid_df["PPCW"] = np.nan

    if "SWATINIT" in grid_df:
        grid_df["QC_FLAG"] = qc_flag(grid_df)

    # Above the gas-oil contact, the computed capillary pressure will
    # be p_gas - p_water, but at cells truncated by SWL, the code
    # will give p_oil - p_water. Delete these inconsistent capillary
    # pressures by ignoring PC scaling whenever SWL has been truncated:
    if "QC_FLAG" in grid_df:
        grid_df.loc[grid_df["QC_FLAG"] == __SWL_TRUNC__, "PC_SCALING"] = np.nan

    if "PC_SCALING" in grid_df:
        grid_df["PC"] = compute_pc(grid_df, satfunc_df)

    return grid_df


def qc_flag(qc_frame: pd.DataFrame) -> pd.DataFrame:
    """Compute a series categorizing the QC type of the cell, determining
    how SWATINIT behaved in that cell

    This function is the core of check_swatinit.

    Args:
        qc_frame (pd.DataFrame)

    Returns:
        pd.DataFrame (with an additional column QC_FLAG)
    """

    qc_col = pd.Series(index=qc_frame.index, dtype=str)

    contact = "OWC" if "OWC" in qc_frame else "GWC"

    # Eclipse and libecl does not calculate cell centres to the same decimals.
    # Add some tolerance when testing towards fluid contacts.
    contacttolerance = 1e-4

    # SWATINIT ignored, water is lost if pc > 0, lost and/or gained if oil-wet pc-curve
    qc_col[
        (qc_frame["SWATINIT"] < 1)
        & (qc_frame["Z"] > qc_frame[contact] - contacttolerance)
    ] = __HC_BELOW_FWL__

    # SWATINIT accepted and PC is scaled.
    qc_col[
        np.isclose(qc_frame["SWAT"], qc_frame["SWATINIT"], atol=1e-6)
        & (qc_frame["SWATINIT"] < 1)
    ] = __PC_SCALED__

    if "PC_SCALING" in qc_frame:
        # If SWATINIT == SWL and capillary pressure warrants SWL, then PPCW
        # matches PCOW_MAX and PC_SCALING is 1. We denote this as __PC_SCALED__
        # because it is "scaled" by 1.
        qc_col[
            np.isclose(qc_frame["SWAT"], qc_frame["SWATINIT"], atol=1e-6)
            & np.isclose(qc_frame["PC_SCALING"], 1)
        ] = __PC_SCALED__

    # Below a nonzero capillary entry pressure but above the contact,
    # SWAT and SWATINIT should be 1.
    if "PPCW" in qc_frame:
        qc_col[np.isclose(qc_frame["SWAT"], 1) & np.isclose(qc_frame["PPCW"], 0)] = (
            __PC_SCALED__
        )

    # PC is scaled (including "scaling" using PC_SCALING=1), but
    # SWAT!=SWATINIT, this must be due to EQUIL item 9 being nonzero.
    if "OIP_INIT" in qc_frame and "PC_SCALING" in qc_frame:
        qc_col[
            (~np.isclose(qc_frame["OIP_INIT"], 0))
            & (~np.isclose(qc_frame["SWAT"], qc_frame["SWATINIT"], atol=1e-6))
            & (~pd.isnull(qc_frame["PC_SCALING"]))
        ] = __FINE_EQUIL__

    # SWATINIT=1 above contact:
    qc_col[
        np.isclose(qc_frame["SWATINIT"], 1)
        & (qc_frame["Z"] < qc_frame[contact] + contacttolerance)
    ] = __SWATINIT_1__

    # If SWU is less than 1, SWATINIT is ignored whenever it is equal or larger
    # than SWU. Behaviour is the same as SWATINIT=1; SWATINIT is ignored, and thus
    # the same flag is reused:
    if "SWU" in qc_frame:
        qc_col[
            (qc_frame["SWU"] < 1)
            & ~np.isclose(qc_frame["SWATINIT"], qc_frame["SWAT"])
            & (qc_frame["SWATINIT"] >= qc_frame["SWU"])
        ] = __SWATINIT_1__

    # SWATINIT=1 below contact but with SWAT < 1, can happen with OIP_INIT:
    if "OIP_INIT" in qc_frame:
        qc_col[
            (~np.isclose(qc_frame["OIP_INIT"], 0))
            & (qc_frame["Z"] > qc_frame[contact] - contacttolerance)
            & (np.isclose(qc_frame["SWATINIT"], 1))
            & (~np.isclose(qc_frame["SWATINIT"], qc_frame["SWAT"]))
        ] = __SWATINIT_1__

    # SWAT limited by PPCWMAX:
    if "PPCWMAX" in qc_frame and "PPCW" in qc_frame:
        qc_col[
            np.isclose(qc_frame["PPCW"], qc_frame["PPCWMAX"])
            & (qc_frame["SWAT"] < qc_frame["SWATINIT"])
        ] = __PPCWMAX__

    # When everything is good below contact:
    qc_col[
        np.isclose(qc_frame["SWATINIT"], 1)
        & np.isclose(qc_frame["SWAT"], 1)
        & (qc_frame["Z"] > qc_frame[contact])
    ] = __WATER__

    qc_col[
        np.isclose(qc_frame["SWAT"], qc_frame["SWL"])
        & (qc_frame["SWL"] > qc_frame["SWATINIT"])
    ] = __SWL_TRUNC__

    if "SWLPC" in qc_frame:
        # SWLPC is not supported by OPM-flow, therefore we also check
        # that SWAT == SWLPC before assigning this:
        qc_col[
            np.isclose(qc_frame["SWAT"], qc_frame["SWLPC"])
            & (qc_frame["SWLPC"] > qc_frame["SWATINIT"])
        ] = __SWL_TRUNC__

    # Tag the remainder with "unknown", when/if this happens, it is a bug or a
    # feature request:
    qc_col.fillna(__UNKNOWN__, inplace=True)

    return qc_col


def qc_volumes(qc_frame: pd.DataFrame) -> Dict[str, float]:
    """Compute numbers relevant for QC of saturation initialization of a
    reservoir model.

    Different volume numbers are typically related to the different QC_FLAG

    Args:
        qc_frame (pd.DataFrame): Cell-based dataframe from which volumes are
            computed.

    Returns:
        dict: Summed water and hydrocarbon reservoir volumes for different cell
        groupings.
    """
    watergains: Dict[str, float]
    watergains = {}

    if "QC_FLAG" in qc_frame:
        # Ensure all categories are represented:
        for qc_cat in QC_FLAGS:
            watergains[qc_cat] = 0.0

        # Overwrite dict values with correct figures:
        for qc_cat, qc_subframe in qc_frame.groupby("QC_FLAG"):
            watergains[qc_cat] = (
                (qc_subframe["SWAT"] - qc_subframe["SWATINIT"]) * qc_subframe["PORV"]
            ).sum()

    # Extra figures:
    watergains["PORV"] = float(qc_frame["PORV"].sum())
    if "VOLUME" in qc_frame:
        watergains["VOLUME"] = qc_frame["VOLUME"].sum()
    if "SWATINIT" in qc_frame:
        watergains["SWATINIT_WVOL"] = (qc_frame["SWATINIT"] * qc_frame["PORV"]).sum()
        watergains["SWATINIT_HCVOL"] = float(
            watergains["PORV"] - watergains["SWATINIT_WVOL"]
        )
    watergains["SWAT_WVOL"] = (qc_frame["SWAT"] * qc_frame["PORV"]).sum()
    watergains["SWAT_HCVOL"] = watergains["PORV"] - watergains["SWAT_WVOL"]

    return watergains


def _evaluate_pc(
    swats: List[float],
    scale_vert: List[float],
    swls: List[float],
    swus: List[float],
    satfunc: pd.DataFrame,
    sat_name: str = "SW",
    pc_name: str = "PCOW",
) -> List[Any]:
    """Evaluate pc as a function of saturation on a scaled Pc-curve

    Args:
        swats: floats with water saturation values
        scale_vert: floats with vertical scalers for pc
        swls: List of SWL values for horizontal scaling.
            If the model is using SWLPC, supply those values instead.
        swus: List of SWU values for horizontal scaling.
        satfunc: Dataframe representing un-scaled
            capillary pressure curve
        sat_name: Column name for the column in the dataframe with the
            water saturation values
        pc_name: Column name for the column with capillary pressure
            values.

    Returns:
        Computed capillary pressure values.
    """
    p_cap = []
    sw_min = satfunc[sat_name].min()
    sw_max = satfunc[sat_name].max()
    if swls is None:
        swls = [sw_min] * len(swats)
    if swus is None:
        swus = [sw_max] * len(swats)
    for swat, pc_scaling, swl, swu in zip(swats, scale_vert, swls, swus):
        p_cap.append(
            np.interp(
                swat,
                swl
                + (satfunc[sat_name].values - sw_min) / (sw_max - sw_min) * (swu - swl),
                satfunc[pc_name].values * pc_scaling,
            )
        )
    return p_cap


def compute_pc(qc_frame: pd.DataFrame, satfunc_df: pd.DataFrame) -> pd.Series:
    """Compute the capillary pressure in every cell, inferring backwards from
    SWAT at time zero and a scaled capillary pressure curve.

    Note that the computed Pc is truncated at PPCW = pc(SWL) when we
    back-calculate it like this.

    Likewise, we are not getting arbitrarily negative Pc values below contact
    for the same reason, only slightly negative for an oil-wet curve.

    Note: If SWLPC is present in the dataframe, it will be used instead
    of SWL. As OPM-flow outputs SWLPC in the INIT files but otherwise
    ignores SWLPC, this will result in an incorrect PC estimate for OPM-flow
    when SWLPC is in use.

    Args:
        qc_frame
        satfunc_df

    Returns:
        pd.Series, with capillary pressure values in bars (given Eclipse unit
        is METRIC)
    """
    p_cap = pd.Series(index=qc_frame.index, dtype=np.float64)
    p_cap[:] = np.nan

    if "SATNUM" not in qc_frame or "PC_SCALING" not in qc_frame:
        return p_cap

    for satnum, satnum_frame in qc_frame.groupby("SATNUM"):
        if "SWLPC" in satnum_frame:
            swls = satnum_frame["SWLPC"].values
        elif "SWL" in satnum_frame:
            swls = satnum_frame["SWL"].values
        else:
            swls = None
        swus = satnum_frame["SWU"].values if "SWU" in satnum_frame else None
        p_cap[satnum_frame.index] = _evaluate_pc(
            satnum_frame["SWAT"].values,
            satnum_frame["PC_SCALING"].values,
            swls,
            swus,
            satfunc_df[satfunc_df["SATNUM"] == satnum],
        )
    # Fix needed for OPM-flow above contact:
    contact = "OWC" if "OWC" in qc_frame else "GWC"

    # When SWATINIT=SWL=SWAT, PPCW as reported by Eclipse is the
    # same as PCOW_MAX, and we cannot use it to compute PC, remove it:
    if "SWL" in qc_frame:
        p_cap[
            np.isclose(qc_frame["SWAT"], qc_frame["SWL"])
            & np.isclose(qc_frame["PC_SCALING"], 1)
        ] = np.nan

    if "QC_FLAG" in qc_frame:
        p_cap[
            (qc_frame["QC_FLAG"] == __SWATINIT_1__)
            & (p_cap == 0)
            & (qc_frame["Z"] < qc_frame[contact])
        ] = np.nan
    return p_cap


def ppcwmax_gridvector(eclfiles: res2df.ResdataFiles) -> pd.Series:
    """Generate a vector of PPCWMAX data pr cell

    PPCWMAX is pr. SATNUM in the input deck

    Args:
        eclfiles

    Returns:
        pd.Series, indexed according to res2df.grid.df(eclfiles)
    """

    satnum_df = res2df.grid.df(eclfiles, vectors="SATNUM")
    deck = eclfiles.get_deck()
    for satnum in satnum_df["SATNUM"].unique():
        ppcwmax = deck["PPCWMAX"][satnum - 1][0].get_raw_data_list()[0]
        satnum_df.loc[satnum_df["SATNUM"] == satnum, "PPCWMAX"] = ppcwmax
    return satnum_df["PPCWMAX"]


def merge_equil(grid_df: pd.DataFrame, equil_df: pd.DataFrame) -> pd.DataFrame:
    """Merge z, datum_pressure, contact information and oip_init settting from
    an EQUIL dataframe into the grid dataframe"""
    assert "EQLNUM" in grid_df, "Grid dataframe must have the EQLNUM column"
    assert not equil_df.empty, "EQUIL dataframe is empty"
    assert "Z" in equil_df
    assert "PRESSURE" in equil_df

    # Be compatible with future change in res2df:
    equil_df.rename({"ACCURACY": "OIP_INIT"}, axis="columns", inplace=True)

    contacts = list({"OWC", "GOC", "GWC"}.intersection(set(equil_df.columns)))
    # Rename and slice the equil dataframe:
    equil_df = equil_df.rename(
        {"Z": "Z_DATUM", "PRESSURE": "PRESSURE_DATUM"}, axis="columns"
    )
    if "KEYWORD" in equil_df:
        equil_df = equil_df[equil_df["KEYWORD"] == "EQUIL"]
    equil_df = equil_df[["Z_DATUM", "PRESSURE_DATUM", "EQLNUM", "OIP_INIT"] + contacts]
    equil_df["EQLNUM"] = equil_df["EQLNUM"].astype(int)
    assert (
        not pd.isnull(equil_df).any().any()
    ), f"BUG: NaNs in equil dataframe:\n{equil_df}"
    return grid_df.merge(equil_df, on="EQLNUM", how="left")


def merge_pc_max(
    grid_df: pd.DataFrame, satfunc_df: pd.DataFrame, pc_name: str = "PCOW"
) -> pd.DataFrame:
    """Extract the maximum capillary pressure function in input
    saturation tables (SWOF/SWFN) pr. SATNUM and merges that
    into a grid dataframe (pr cell)

    Returns:
        pd.Dataframe: One row pr cell with an extra column PCOW_NAX
    """
    if pc_name not in satfunc_df:
        raise ValueError(f"{pc_name} not found in saturation function dataframe")
    if satfunc_df.empty:
        raise ValueError("Saturation function dataframe is empty")
    max_pc = satfunc_df.groupby("SATNUM")[pc_name].max()
    max_pc.name = pc_name + "_MAX"
    return grid_df.merge(max_pc.reset_index(), on="SATNUM")


def augment_grid_frame_qc_vectors(grid_df: pd.DataFrame) -> pd.DataFrame:
    """Add extra columns to a dataframe with simple calculations from
    data already in the dataframe"""
    grid_df["EQLNUM"] = grid_df["EQLNUM"].astype(int)
    grid_df["FIPNUM"] = grid_df["FIPNUM"].astype(int)
    grid_df["SATNUM"] = grid_df["SATNUM"].astype(int)

    grid_df["PORV"] = grid_df["VOLUME"] * grid_df["NTG"] * grid_df["PORO"]

    if "PPCW" in grid_df:
        grid_df["PC_SCALING"] = grid_df["PPCW"] / grid_df["PCOW_MAX"]
    else:
        logger.warning("PPCW not found in grid dataframe")

    if "SWATINIT" in grid_df:
        grid_df["SWATINIT_SWAT"] = grid_df["SWATINIT"] - grid_df["SWAT"]
        grid_df["SWATINIT_SWAT_WVOL"] = grid_df["SWATINIT_SWAT"] * grid_df["PORV"]

    return grid_df


def get_parser() -> argparse.ArgumentParser:
    """Construct a command line argument parser"""
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "DATAFILE",
        help=(
            "Eclipse DATA-file for a finished run with restart data. "
            "It is also possible to provide a CSV file that has earlier "
            "been exported by this tool, which will trigger a rerun of "
            "the volumetric report and plotting."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help="Output filename for CSV that can be used for QC in other tools",
    )
    parser.add_argument(
        "--volplot",
        action="store_true",
        help=(
            "Display a waterfall chart with the water "
            "saturation volumes from SWATINIT to SWAT"
        ),
    )
    parser.add_argument(
        "--volplotfile",
        type=str,
        help="PNG filename for where to dump a waterfall chart.",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help=(
            "Show scatter QC plots with one dot pr. reservoir cell in a given EQLNUM "
            "region, use together with the --eqlnum option"
        ),
    )
    parser.add_argument(
        "--plotfile", type=str, help="PNG filename for where to dump a QC plot."
    )
    parser.add_argument(
        "--eqlnum",
        type=int,
        default=1,
        help=(
            "Which EQLNUM to plot for in scatter plots. Defaults to 1. "
            "Does not affect CSV output"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + subscript.__version__ + ")",
    )
    return parser


if __name__ == "__main__":
    main()
