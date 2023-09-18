from typing import Dict, Optional

import numpy as np
import pandas as pd
import seaborn
from matplotlib import pyplot

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

SNS_PAL = seaborn.color_palette("tab10")
QC_PALETTE = {
    __FINE_EQUIL__: SNS_PAL[8],
    __HC_BELOW_FWL__: SNS_PAL[5],
    __PC_SCALED__: SNS_PAL[2],
    __PPCWMAX__: SNS_PAL[9],
    __SWATINIT_1__: SNS_PAL[6],
    __SWL_TRUNC__: SNS_PAL[3],
    __UNKNOWN__: SNS_PAL[1],
    __WATER__: SNS_PAL[0],
}


def plot_qc_panels(
    qc_frame: pd.DataFrame, eqlnum: Optional[int] = None, show: bool = False
) -> None:
    """Make a plotting panel (multiple plots) on cell-based dataframe.

    It only makes sense to view one eqlnum at a time.

    Args:
        qc_frame (pd.Dataframe): Dataframe constructed by check_swatinit
        eqlnum (int): Restrict plotting to this EQLNUM. If None, the qc_frame must have
            only one unique value for EQLNUM
    Returns:
        pyplot handle
    """

    if eqlnum is not None:
        qc_frame = qc_frame[qc_frame["EQLNUM"] == eqlnum]

    assert (
        len(qc_frame["EQLNUM"].unique()) == 1
    ), "Can only plot for one EQLNUM at a time"
    pyplot.style.use("seaborn-v0_8-darkgrid")
    seaborn.color_palette("tab10")

    pyplot.figure(figsize=(16, 8))
    pyplot.subplot(2, 2, 1)
    swatinit_depth(qc_frame)
    pyplot.subplot(2, 2, 2)
    swat_depth(qc_frame)
    pyplot.subplot(2, 2, 3)
    pressure_depth(qc_frame)
    pyplot.subplot(2, 2, 4)
    pc_depth(qc_frame)

    oip_init = qc_frame["OIP_INIT"].values[0]
    eqlnum = qc_frame["EQLNUM"].values[0]
    pyplot.suptitle(f"EQLNUM: {eqlnum}, OIP_INIT: {oip_init}")
    if show:
        pyplot.show()


def visual_depth(qc_frame: pd.DataFrame) -> float:
    """Suggest a deep depth limit for what to plot, in order to avoid
    showing too much of a less interesting water zone"""
    assert (
        len(qc_frame["EQLNUM"].unique()) == 1
    ), "Can only plot for one EQLNUM at a time"
    lowest_hc = qc_frame[qc_frame["SWATINIT"] < 1]["Z"].max()
    hc_height = lowest_hc - qc_frame["Z"].min()

    if hc_height > 0:
        # Suggest to visualize a water height of 10% of the hc zone:
        return lowest_hc + 0.2 * hc_height

    # Plot everything when there is only water in the model
    return qc_frame["Z"].max()


def swat_depth(
    qc_frame: pd.DataFrame, axis: Optional[pyplot.Axes] = None, hue: str = "QC_FLAG"
) -> None:
    """Make a SWAT vs depth plot on current axis"""
    if axis is None:
        axis = pyplot.gca()
    seaborn.scatterplot(
        x="SWAT", y="Z", data=qc_frame, hue=hue, palette=QC_PALETTE, alpha=0.5
    )
    bottom, _ = pyplot.ylim()
    pyplot.ylim(bottom, visual_depth(qc_frame))
    axis.invert_yaxis()
    add_contacts_to_plot(qc_frame, axis)


def swatinit_depth(
    qc_frame: pd.DataFrame, axis: Optional[pyplot.Axes] = None, hue: str = "QC_FLAG"
) -> None:
    """Make a swatinit vs depth plot on current axis"""
    if axis is None:
        axis = pyplot.gca()
    seaborn.scatterplot(
        x="SWATINIT", y="Z", data=qc_frame, hue=hue, palette=QC_PALETTE, alpha=0.5
    )
    bottom, _ = pyplot.ylim()
    pyplot.ylim(bottom, visual_depth(qc_frame))
    axis.invert_yaxis()
    add_contacts_to_plot(qc_frame, axis)


def pressure_depth(
    qc_frame: pd.DataFrame, axis: Optional[pyplot.Axes] = None, hue: str = "QC_FLAG"
) -> None:
    """Make a pressure vs. depth plot on current axis"""
    if axis is None:
        axis = pyplot.gca()
    seaborn.scatterplot(
        x="PRESSURE", y="Z", data=qc_frame, hue=hue, palette=QC_PALETTE, alpha=0.5
    )
    bottom, _ = pyplot.ylim()
    pyplot.ylim(bottom, visual_depth(qc_frame))
    axis.invert_yaxis()
    add_contacts_to_plot(qc_frame, axis)


def pc_depth(
    qc_frame: pd.DataFrame, axis: Optional[pyplot.Axes] = None, hue: str = "QC_FLAG"
) -> None:
    """Make a pc vs depth plot on current axis"""
    if axis is None:
        axis = pyplot.gca()
    seaborn.scatterplot(
        x="PC", y="Z", data=qc_frame, hue=hue, palette=QC_PALETTE, alpha=0.5
    )
    bottom, _ = pyplot.ylim()
    pyplot.ylim(bottom, visual_depth(qc_frame))
    axis.invert_yaxis()
    add_contacts_to_plot(qc_frame, axis)


def add_contacts_to_plot(qc_frame: pd.DataFrame, axis: pyplot.Axes) -> None:
    """Annotate axes with named horizontal lines for contacts."""
    if "OWC" in qc_frame:
        owc = qc_frame["OWC"].values[0]  # OWC is assumed constant in the dataframe
        axis.axhline(owc, color="black", linestyle="--", linewidth=1)
        axis.annotate(f"OWC={owc:g}", (0, owc))
    if "GOC" in qc_frame:
        goc = qc_frame["GOC"].values[0]
        axis.axhline(goc, color="black", linestyle="--", linewidth=1)
        axis.annotate(f"GOC={goc:g}", (0, goc))
    if "GWC" in qc_frame:
        gwc = qc_frame["GWC"].values[0]
        axis.axhline(gwc, color="black", linestyle="--", linewidth=1)
        axis.annotate(f"GWC={gwc:g}", (0, gwc))


def wvol_waterfall(qc_vols: Dict[str, float]) -> None:
    """Make a waterfall chart of the computed volumes

    Plots on current axis.

    Based on:

    https://pbpython.com/waterfall-chart.html

    Args:
        qc_vols (dict)
    """
    index = [
        # Ensure fixed order of plot elements:
        "SWATINIT_WVOL",
        __SWL_TRUNC__,
        __PPCWMAX__,
        __FINE_EQUIL__,
        __HC_BELOW_FWL__,
        __SWATINIT_1__,
    ]
    swatinit_hcvol = qc_vols["PORV"] - qc_vols["SWATINIT_WVOL"]
    swat_hcvol = qc_vols["PORV"] - qc_vols["SWAT_WVOL"]
    values = {"volume": [qc_vols[key] for key in index]}
    trans = pd.DataFrame(data=values, index=index)

    # "Transparent" bars (blanks):
    blank = trans["volume"].cumsum().shift(1).fillna(0)
    total = trans["volume"].sum()
    trans.loc["SWAT_WVOL"] = total
    blank.loc["SWAT_WVOL"] = total
    step = blank.reset_index(drop=True).repeat(3).shift(-1)
    step[1::3] = np.nan
    blank.loc["SWAT_WVOL"] = 0

    fig = trans.plot(kind="bar", alpha=0.7, stacked=True, legend=None, bottom=blank)
    fig.plot(step.index, step.values, "k")
    pyplot.gcf().subplots_adjust(bottom=0.25)

    blanktrans = blank.values + trans["volume"].values
    span = blank.max() - blanktrans[1:-1].min()

    if np.isclose(span, 0.0):
        span = blank.max()

    # Calculate percent changed relative to SWATINIT_WVOL
    for number, qc_flag in enumerate(index[1:]):
        change = qc_vols[qc_flag] / qc_vols["SWATINIT_WVOL"]
        pyplot.gca().annotate(
            f"{change*100:3.2f}%",
            (
                number + 1,
                blanktrans[number] + max(0, qc_vols[qc_flag]) + span / 20,
            ),
            horizontalalignment="center",
            color="C0",
        )
        hc_change = -qc_vols[qc_flag] / swatinit_hcvol
        pyplot.gca().annotate(
            f"{hc_change*100:3.2f}%",
            (number + 1, blanktrans[number] + max(0, qc_vols[qc_flag]) + 4 * span / 20),
            horizontalalignment="center",
            color="C2",
        )
    final_change = (qc_vols["SWAT_WVOL"] - qc_vols["SWATINIT_WVOL"]) / qc_vols[
        "SWATINIT_WVOL"
    ]
    pyplot.gca().annotate(
        f"{final_change*100:>3.2f}%",
        (6, total + span / 20),
        horizontalalignment="center",
        color="C0",
    )
    final_hc_change = (swat_hcvol - swatinit_hcvol) / swatinit_hcvol
    pyplot.gca().annotate(
        f"{final_hc_change*100:>3.2f}%",
        (6, total + 4 * span / 20),
        horizontalalignment="center",
        color="C2",
    )

    pyplot.ylim((max(0.0, blank[1:-1].min() - span), blank.max() + span))
    pyplot.xticks(rotation=45)
