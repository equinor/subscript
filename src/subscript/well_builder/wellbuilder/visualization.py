# -*- coding: utf-8 -*-
"""
Created on Fri Aug 23 12:57:31 2019

@author: iari
"""
from matplotlib import rcParams
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.backends.backend_pdf import PdfPages


def update_fonts(family="DejaVu Serif", size=12):
    """This procedure updates the plot fonts

    Args:
        family (str) : font family name
        size (float) : font sizes
    """
    rcParams["font.family"] = family
    rcParams.update({"font.size": size})


def format_axis(subplot, title, xlabel, ylabel, categorical=False):
    """Format axis of the subplot

    Args:
        subplot (plt subplot) : plt subplot
        title (str) : title of the subplot
        xlabel (str) : name of the x axis
        ylabel (str) : name of the y axis
        categorical (bol) : if the x axis is not int or float set to True, otherwise False
    """
    min_val, max_val = subplot.get_ylim()
    subplot.set_xlabel(xlabel)
    subplot.set_ylabel(ylabel)
    if categorical:
        subplot.minorticks_on()
        subplot.tick_params(
            axis="both", which="major", direction="in", length=6, width=1.0
        )
        subplot.tick_params(
            axis="both", which="minor", direction="in", length=3, width=1.0
        )
        major = (max_val - min_val) / 5.0
        if major < 1.0:
            major = round(major, 1)
            if abs(major - 1.0) < abs(major - 0.5):
                major = 1.0
            else:
                if abs(major - 0.5) < abs(major - 0.25):
                    major = 0.5
                else:
                    major = 0.25
        else:
            major = round(major, 0)
        subplot.yaxis.set_major_locator(ticker.MultipleLocator(major))
        subplot.minorticks_off()
    else:
        subplot.minorticks_on()
        subplot.tick_params(
            axis="both", which="major", direction="in", length=6, width=1.0
        )
        subplot.tick_params(
            axis="both", which="minor", direction="in", length=3, width=1.0
        )
    subplot.yaxis.set_ticks_position("both")
    subplot.xaxis.set_ticks_position("both")
    subplot.grid(which="both", linestyle="-", linewidth=0.1, color="grey", alpha=0.1)
    subplot.set_title(title)
    return subplot


def format_scale(subplot, xscale="linear", yscale="linear", xlim=None, ylim=None):
    """Format axis scale

    Args:
        subplot (matplotlib subplot) : matplotlib subplot
        xscale (str) : scale type for x axis. permitted value log/linear
        yscale (str) : scale type for y axis. permitted value log/linear
        xlim (list) : [min, max] limit of the x axis. default=None.
        ylim (list) : [min, max] limit of the y axis. default=None.

    Returns:
        matplotlib subplot : reformatted subplot
    """
    subplot.set_xscale(xscale)
    subplot.set_yscale(yscale)
    if not xlim is None:
        subplot.set_xlim(xlim)
    if not ylim is None:
        subplot.set_ylim(ylim)
    return subplot


def format_legend(subplot, legend=True, location="right"):
    """Format legend of subplot

    Args:
        subplot (matplotlib subplot) : matplotlib subplot
        legend (bol) : True for on and False for off
        location (str) : legend location

    Returns:
        matplotlib subplot : reformatted subplot
    """
    if legend:
        if location == "top":
            subplot.legend(
                numpoints=1,
                bbox_to_anchor=(0.0, 1.02, 1.0, 0.102),
                loc=3,
                ncol=2,
                mode="expand",
                borderaxespad=0,
                framealpha=0.2,
            )
        elif location == "right":
            subplot.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    return subplot


def subplot_position(nplots):
    """Return the row and index of subplot position

    Args:
        nplots (int) : number of subplots in the figure

    Returns:
        tupple : row, column
    """
    list_rows = [1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 5]
    list_cols = [1, 2, 3, 2, 3, 3, 4, 4, 3, 4, 5]
    return list_rows[nplots - 1], list_cols[nplots - 1]


def create_pdfpages(filename):
    """Create a pdf file

    Args:
        filename (str) : full name of the file without extension .pdf

    Returns:
        str : pdfpages class
    """
    return PdfPages(filename + ".pdf")


def create_figure(figsize=(18, 12)):
    """Create a matplotlib pplt figure

    Args:
        figsize (list) : [widht, height]

    Returns:
        matplotlib figure
    """
    if figsize is None:
        return plt.figure()
    return plt.figure(figsize=figsize)


def close_figure():
    """Close matplotlib figure

    Args:
        fig (plt figure) : matplotlib figure
    """
    plt.close("all")
