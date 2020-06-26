#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#     Eclipse Summary plotter is based on ERT-Python
#      http://fmu-docs.equinor.com/docs/ecl/index.html
#
#     The source code is a part of the subscript repository:
#      https://github.com/equinor/subscript

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import sys
import os
import re
import difflib
import logging
import argparse
from multiprocessing import Process

import matplotlib.pyplot
import numpy as np

# Get rid of FutureWarning from pandas/plotting.py
from pandas.plotting import register_matplotlib_converters

from ecl.summary import EclSum
from ecl.eclfile import EclFile
from ecl.grid import EclGrid

register_matplotlib_converters()

DESCRIPTION = """
Summaryplot will plot summary vectors from your Eclipse output files.

To list summary vectors for a specific Eclipse output set, try
 > summary.x --list ECLFILE.DATA

Command line argument VECTORSDATAFILES are assumed to be Eclipse DATA-files as long
as the command line argument is an existing file. If not, it is assumed
to be a vector to plot. Thus, vectors and datafiles can be mixed.
"""

EPILOG = ""


def get_parser():
    """Setup parser for command line options"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=DESCRIPTION,
        epilog=EPILOG,
    )
    parser.add_argument(
        "-H", "--hist", help="Add historical vectors", action="store_true"
    )
    parser.add_argument(
        "-n",
        "--normalize",
        help="Normalize the values pr. vector to (0,1)",
        action="store_true",
    )
    parser.add_argument(
        "--nolegend", "--nolabels", help="Drop legend", action="store_true"
    )
    parser.add_argument(
        "--maxlabels", type=int, help="Max number of vector names in legend", default=5
    )
    parser.add_argument(
        "-e",
        "--ensemblemode",
        help="Colour by vector instead of by DATA-file",
        action="store_true",
    )
    parser.add_argument(
        "-d",
        "--dumpimages",
        help="Dump images to files instead of displaying on screen",
        action="store_true",
    )
    parser.add_argument(
        "-c",
        "--colourby",
        type=str,
        help="Colourize curves by the a value found in parameters.txt",
    )
    parser.add_argument(
        "--logcolourby",
        type=str,
        help="Colourize curves by the logarithm of a value found in parameters.txt",
    )
    parser.add_argument(
        "--singleplot",
        "-s",
        action="store_true",
        help="All vectors are put into one single plot",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    parser.add_argument(
        "VECTORSDATAFILES",
        nargs="+",
        type=str,
        help="List of vectors to plot and/or DATA-files to include",
    )
    return parser


def summaryplotter(
    summaryfiles=None,
    datafiles=None,
    vectors=None,
    parameterfiles=None,
    histvectors=False,
    normalize=False,
    singleplot=False,
    nolegend=False,
    maxlabels=5,
    ensemblemode=False,
    dumpimages=False,
    colourby="",
    logcolourby="",
):
    """
    Will plot Eclipse summary vectors to screen or dump to file based on kwargs.

    Args:
        eclsums (list of EclSum)
        vectors (list of str)
        histvectors (bool),
        normalize (bool)
        singleplot (bool)
        nolegend (bool)
        maxlabels (int)
        ensemblemode (bool)
        dumpimages (bool)
        colourby (str):
        logcolourby (str):
    """
    rstfiles = []  # EclRst objects
    gridfiles = []  # EclGrid objects
    parametervalues = []  # Vector of values pr. realization for colouring

    if datafiles and not summaryfiles:
        logging.info("Reloading summary files from disk")
        summaryfiles = [EclSum(datafile) for datafile in datafiles]

    if maxlabels == 0:
        nolegend = True

    if colourby and logcolourby:
        logging.error("Can't colour non-log and log at the same time")
        sys.exit(1)

    if (colourby or logcolourby) and ensemblemode:
        logging.error("Can't colour by ensemble and by parameter at the same time")
        sys.exit(1)

    if (colourby or logcolourby) and not nolegend:
        print("Hint: Use --nolegend to skip legend")

    if (colourby or logcolourby) and len(summaryfiles) < 2:
        colourby = False
        logcolourby = False
        logging.warning("Not colouring by parameter when only one DATA file is loaded")

    minvalue = 0.0
    maxvalue = 0.0
    parameternames = []
    if colourby or logcolourby:
        if colourby:
            colourbyparametername = colourby
            logging.info("Colouring by parameter %s", colourby)
        if logcolourby:
            colourbyparametername = logcolourby
            logging.info("Colouring logarithmically by parameter %s", logcolourby)
        # Try to load parameters.txt for each datafile,
        # and put the associated values in a vector
        for parameterfile in parameterfiles:
            valuefound = False
            if os.path.isfile(parameterfile):
                filename = open(parameterfile)
                for line in filename:
                    linecontents = line.split()
                    parameternames.append(linecontents[0])
                    if linecontents[0] == colourbyparametername:
                        parametervalues.append(float(linecontents[1]))
                        valuefound = True
                        break
            if not valuefound:
                logging.warning(
                    str(colourbyparametername)
                    + " was not found in parameter-file "
                    + parameterfile
                )
                parametervalues.append(0.0)
        # print parametervalues

        # Normalize parametervalues to [0,1]:
        minvalue = np.min(parametervalues)
        maxvalue = np.max(parametervalues)
        if (maxvalue - minvalue) < 0.000001:
            logging.warning(
                "No data found to colour by, are you sure you typed "
                + colourbyparametername
                + " correctly?"
            )
            suggestion = difflib.get_close_matches(
                colourbyparametername, parameternames, 1
            )
            if suggestion:
                print("         Maybe you meant " + suggestion[0])
            colourby = False
            logcolourby = False
        else:
            normalizedparametervalues = (parametervalues - minvalue) / (
                maxvalue - minvalue
            )

        if logcolourby:
            minvalue = np.min(np.log10(parametervalues))
            maxvalue = np.max(np.log10(parametervalues))
            if maxvalue - minvalue > 0:
                normalizedparametervalues = (np.log10(parametervalues) - minvalue) / (
                    maxvalue - minvalue
                )
            else:
                print(
                    "Warning: Log(zero) encountered, "
                    "reverting to non-logarithmic values"
                )
                minvalue = np.min(parametervalues)
                maxvalue = np.max(parametervalues)
                normalizedparametervalues = (parametervalues - minvalue) / (
                    maxvalue - minvalue
                )
                colourby = None
                logcolourby = None

        # print normalizedparametervalues

        # Build a colour map from all the values, from min to max.

    if normalize and histvectors:
        logging.warning("Historical data is not normalized equally to simulated data")

    if not summaryfiles:
        print("Error: No summary files found")
        sys.exit(1)

    # We support wildcards in summary vectors. The wildcards will be matched against
    # the existing vectors in the first Eclipse deck mentioned on the command
    # line
    matchedsummaryvectors = []
    restartvectors = []
    wildcard_in_use = False
    for vector in vectors:
        matchingvectors = summaryfiles[0].keys(vector)
        if len(matchingvectors) > 1:
            wildcard_in_use = True
        if not matchingvectors:
            # Check if it is a restart vector with syntax
            # <vector>:<i>,<j>,<k> aka SOIL:40,31,33
            if re.match(r"^[A-Z]+:[0-9]+,[0-9]+,[0-9]+$", vector):
                logging.info("Found restart vector %s", vector)
                restartvectors.append(vector)
            else:
                logging.warning("No summary or restart vectors matched %s", vector)
        matchedsummaryvectors.extend(summaryfiles[0].keys(vector))
    if wildcard_in_use:
        logging.info(
            "Summary vectors after wildcard expansion: %s", str(matchedsummaryvectors)
        )

    # If we have any restart vectors defined, we must also load the restart files
    if restartvectors:
        for datafile in datafiles:
            rstfile = datafile.replace(".DATA", "")
            rstfile = rstfile + ".UNRST"
            gridfile = datafile.replace(".DATA", "")
            gridfile = gridfile + ".EGRID"  # What about .GRID??
            logging.info("Loading grid and restart file %s", rstfile)
            # TODO: Allow some of the rstfiles to be missing
            # TODO: Handle missing rstfiles gracefully
            rst = EclFile(rstfile)
            grid = EclGrid(gridfile)
            rstfiles.append(rst)
            gridfiles.append(grid)
            logging.info("RST loading done")

    if (len(matchedsummaryvectors) + len(restartvectors)) == 0:
        logging.error("Error: No vectors to plot")
        sys.exit(1)

    # Now it is time to prepare vectors from restart-data, quite time-consuming!!
    # Remember that SOIL should also be supported, but must be calculated on
    # demand from SWAT and SGAS (if present)
    restartvectordata = {}
    restartvectordates = {}
    for rstvec in restartvectors:
        logging.info("Getting data for %s...", rstvec)
        match = re.match(r"^([A-Z]+):([0-9]+),([0-9]+),([0-9]+)$", rstvec)
        dataname = match.group(1)  # aka SWAT, PRESSURE, SGAS etc..
        (ijk) = (
            int(match.group(2)) - 1,
            int(match.group(3)) - 1,
            int(match.group(4)) - 1,
        )
        # Remember that these indices start on 1, not on zero!

        restartvectordata[rstvec] = {}
        restartvectordates[rstvec] = {}
        for datafile_idx in range(0, len(datafiles)):
            active_index = gridfiles[datafile_idx].get_active_index(ijk=ijk)
            restartvectordata[rstvec][datafiles[datafile_idx]] = []
            restartvectordates[rstvec][datafiles[datafile_idx]] = []

            # Loop over all restart steps
            last_step = range(rstfiles[datafile_idx].num_named_kw("SWAT"))[-1]
            for report_step in range(0, last_step + 1):
                restartvectordates[rstvec][datafiles[datafile_idx]].append(
                    rstfiles[datafile_idx].iget_restart_sim_time(report_step)
                )
                if dataname != "SOIL":
                    restartvectordata[rstvec][datafiles[datafile_idx]].append(
                        rstfiles[datafile_idx].iget_named_kw(dataname, report_step)[
                            active_index
                        ]
                    )
                else:
                    swatvalue = rstfiles[datafile_idx].iget_named_kw(
                        "SWAT", report_step
                    )[active_index]
                    if "SGAS" in rstfiles[datafile_idx]:
                        sgasvalue = rstfiles[datafile_idx].iget_named_kw(
                            "SGAS", report_step
                        )[active_index]
                        restartvectordata[rstvec][datafiles[datafile_idx]].append(
                            1 - swatvalue - sgasvalue
                        )
                    else:
                        restartvectordata[rstvec][datafiles[datafile_idx]].append(
                            1 - swatvalue
                        )
    # Data structure examples
    # restartvectordata["SOIL:1,1,1"]["datafile"] = [0.89, 0.70, 0.60, 0.55, 0.54]
    # restartvectortimes["SOIL:1,1,1"]["datafile"] = ["1 Jan 2011", "1 Jan 2012"]
    # (NB dates are in format "datetime")
    # TODO: Fill restartvectordata with NaN's if restart data is missing

    # Make the plots
    pyplot = matplotlib.pyplot

    numberofcolours = len(summaryfiles)
    alpha = 0.7  # default
    if ensemblemode:
        numberofcolours = len(matchedsummaryvectors) + len(restartvectors)
        if len(summaryfiles) > 50:
            alpha = 0.4
        if len(summaryfiles) > 5 and len(summaryfiles) < 51:
            # Linear transparency in number of summaryfiles between 5 and 50:
            alpha = 0.7 - (float((len(summaryfiles)) - 5.0)) / 45.0 * 0.3
    if singleplot:
        numberofcolours = len(matchedsummaryvectors)

    colours = list(
        map(tuple, pyplot.get_cmap("jet")(np.linspace(0, 1.0, numberofcolours)))
    )

    if colourby or logcolourby:
        colourmap = matplotlib.colors.LinearSegmentedColormap.from_list(
            "GreenBlackRed", [(0, 0.6, 0), (0, 0, 0), (0.8, 0, 0)]
        )
        matplotlib.cm.register_cmap(name="GreenBlackRedMap", cmap=colourmap)
        colours = list(
            map(tuple, pyplot.get_cmap("GreenBlackRedMap")(normalizedparametervalues))
        )

    if colourby or logcolourby:
        # Using contourf to provide the colorbar info, then clearing the figure
        Z = [[0, 0], [0, 0]]
        step = (maxvalue - minvalue) / 100
        levels = np.arange(minvalue, maxvalue + step, step)
        invisiblecontourplot = pyplot.contourf(Z, levels, cmap="GreenBlackRedMap")
        pyplot.clf()
        pyplot.close()

    for vector_idx, vector in enumerate(matchedsummaryvectors):

        if (not singleplot) or vector == matchedsummaryvectors[0]:
            fig = pyplot.figure()
            if colourby or logcolourby:
                pyplot.colorbar(invisiblecontourplot)
            pyplot.xlabel("Date")

        # Set background colour outside plot area to white:
        fig.patch.set_facecolor("white")

        # Add grey major gridlines:
        pyplot.grid(b=True, which="both", color="0.65", linestyle="-")

        if not singleplot:
            if colourby:
                pyplot.title(vector + ", colouring: " + colourby)
            elif logcolourby:
                pyplot.title(vector + ", colouring: Log10(" + logcolourby + ")")
            else:
                pyplot.title(vector)
        else:
            pyplot.title("")

        # Look for historic vectors in first summaryfile
        if histvectors:
            s = summaryfiles[0]
            toks = vector.split(":", 1)
            histvec = toks[0] + "H"
            if len(toks) > 1:
                histvec = histvec + ":" + toks[1]
            if histvec in s.keys():
                values = s.numpy_vector(histvec)
                sumlabel = "_nolegend_"
                if normalize:
                    maxvalue = values.max()
                    if abs(maxvalue) > 0.0:
                        values = [i * 1 / maxvalue for i in values]
                        sumlabel = histvec + " " + str(maxvalue)
                    else:
                        logging.warn(
                            "Could not normalize %s, maxvalue is %g", histvec, maxvalue
                        )

                pyplot.plot_date(s.dates, values, "k.", label=sumlabel)
                fig.autofmt_xdate()

        for s_idx in range(0, len(summaryfiles)):
            s = summaryfiles[s_idx]
            if vector in s.keys():
                if s_idx >= maxlabels:  # Truncate legend if too many
                    sumlabel = "_nolegend_"
                else:
                    if singleplot:
                        sumlabel = vector + " " + s.case.lower()
                    else:
                        sumlabel = s.case.lower()

                values = s.numpy_vector(vector)

                if ensemblemode:
                    cycledcolor = colours[vector_idx]
                    if s_idx == 0:
                        sumlabel = vector
                    else:
                        sumlabel = "_nolegend_"
                elif singleplot:
                    cycledcolor = colours[vector_idx]
                else:
                    cycledcolor = colours[s_idx]

                if normalize:
                    maxvalue = values.max()
                    if abs(maxvalue) > 0.0:
                        values = [i * 1 / maxvalue for i in values]
                        sumlabel = sumlabel + " " + str(maxvalue)
                    else:
                        logging.warn(
                            "Could not normalize %s, maxvalue is %g", vector, maxvalue
                        )

                pyplot.plot_date(
                    s.dates,
                    values,
                    xdate=True,
                    ydate=False,
                    ls="-",
                    marker="None",
                    color=cycledcolor,
                    label=sumlabel,
                    linewidth=1.5,
                    alpha=alpha,
                )
                fig.autofmt_xdate()

        if not nolegend:
            pyplot.legend(loc="best", fancybox=True, framealpha=0.5)
    for rstvec_idx, rstvec in enumerate(restartvectors):

        if not singleplot or (
            rstvec == restartvectors[0] and not matchedsummaryvectors
        ):
            fig = pyplot.figure()
            if colourby or logcolourby:
                pyplot.colorbar(invisiblecontourplot)
            pyplot.xlabel("Date")

        if not singleplot:
            if colourby:
                pyplot.title(rstvec + ", colouring: " + colourby)
            elif logcolourby:
                pyplot.title(rstvec + ", colouring: Log10(" + logcolourby + ")")
            else:
                pyplot.title(rstvec)
        else:
            pyplot.title("")

        # Set background colour outside plot area to white:
        fig.patch.set_facecolor("white")

        # Add grey major gridlines:
        pyplot.grid(b=True, which="both", color="0.65", linestyle="-")

        for datafile_idx, _ in enumerate(datafiles):

            if singleplot:
                rstlabel = rstvec + " " + datafiles[datafile_idx].lower()
            else:
                rstlabel = datafiles[datafile_idx].lower()

            if ensemblemode:
                cycledcolor = colours[len(matchedsummaryvectors) + rstvec_idx]
                if datafile_idx == 0:
                    rstlabel = rstvec
                else:
                    rstlabel = "_nolegend_"
            else:
                cycledcolor = colours[datafile_idx]

            values = np.array(restartvectordata[rstvec][datafiles[datafile_idx]])
            if normalize:
                maxvalue = values.max()
                values = [i * 1 / maxvalue for i in values]
                rstlabel = rstlabel + " " + str(maxvalue)

            pyplot.plot_date(
                restartvectordates[rstvec][datafiles[datafile_idx]],
                values,
                xdate=True,
                ydate=False,
                ls="-",
                marker="None",
                color=cycledcolor,
                label=rstlabel,
                linewidth=1.5,
                alpha=alpha,
            )

        if not nolegend:
            pyplot.legend(loc="best")

    if dumpimages:
        pyplot.savefig("summaryplotdump.png", bbox_inches="tight")
        pyplot.savefig("summaryplotdump.pdf", bbox_inches="tight")
    else:
        pyplot.show()


def split_vectorsdatafiles(vectorsdatafiles):
    """
    Takes a list of strings and determines which of the arguments are Eclipse runs
    (by attempting to construct an EclSum object), and which are summary
    vector names/wildcards (that is, those that are not openable as EclSum)

    Args:
        vectorsdatafiles (list of str)

    Returns:
        4-tuple of lists, with EclSum-filenames,  datafilename-strings,
            vector-strings, parameterfilename-strings
    """
    summaryfiles = []  # Eclsum instances corresponding to datafiles
    datafiles = []  # strings
    vectors = []  # strings
    parameterfiles = []  # strings

    for vecdata in vectorsdatafiles:
        try:
            sumfn = EclSum(vecdata)
            datafiles.append(vecdata)

            summaryfiles.append(sumfn)

            # Try to load a corresponding parameter-file for colouring data
            parameterfile = (
                os.path.dirname(os.path.realpath(vecdata)) + "/../../parameters.txt"
            )
            if os.path.isfile(parameterfile):
                parameterfiles.append(parameterfile)
            else:
                parameterfiles.append("")
            # (we don't care yet if it exists or not)

        except IOError:
            vectors.append(vecdata)
    return (summaryfiles, datafiles, vectors, parameterfiles)


def main():
    """Parse command line, and control user interface."""

    parser = get_parser()

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    (summaryfiles, datafiles, vectors, parameterfiles) = split_vectorsdatafiles(
        args.VECTORSDATAFILES
    )
    logging.info("Summaryfiles: %s", str(summaryfiles))
    logging.info("Vectors: %s", str(vectors))

    plotprocess = Process(
        target=summaryplotter,
        kwargs=dict(
            summaryfiles=summaryfiles,
            datafiles=datafiles,
            vectors=vectors,
            colourby=args.colourby,
            maxlabels=args.maxlabels,
            logcolourby=args.logcolourby,
            parameterfiles=parameterfiles,
            histvectors=args.hist,
            normalize=args.normalize,
            singleplot=args.singleplot,
            nolegend=args.nolegend,
            dumpimages=args.dumpimages,
            ensemblemode=args.ensemblemode,
        ),
    )
    plotprocess.start()

    # If user only wants to dump image to file, then do only that:
    if args.dumpimages:
        print("Dumping plot to summaryplotdump.png and summaryplotdump.pdf")
        plotprocess.join()
        plotprocess.terminate()
        return

    # Give out a "menu" (text-based) only if we are running in foreground:
    if os.getpgrp() == os.tcgetpgrp(sys.stdout.fileno()):
        import tty
        import termios

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        print("Menu: 'q' = quit, 'r' = reload plots")
        try:
            # change terminal settings to allow keyboard
            # input without user pressing 'enter'
            tty.setcbreak(sys.stdin.fileno())
            ch = ""
            while ch != "q" and plotprocess.is_alive():
                ch = sys.stdin.read(1)
                if ch == "r":
                    plotprocess.terminate()
                    plotprocess = Process(
                        target=summaryplotter,
                        kwargs=dict(
                            summaryfiles=None,  # forces reload
                            datafiles=datafiles,
                            vectors=vectors,
                            colourby=args.colourby,
                            maxlabels=args.maxlabels,
                            logcolourby=args.logcolourby,
                            parameterfiles=parameterfiles,
                            histvectors=args.hist,
                            normalize=args.normalize,
                            singleplot=args.singleplot,
                            nolegend=args.nolegend,
                            dumpimages=args.dumpimages,
                            ensemblemode=args.ensemblemode,
                        ),
                    )
                    plotprocess.start()
        except KeyboardInterrupt:
            pass
        # We have messed up the terminal, remember to fix:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

        # Close plot windows (running in a subprocess)
        plotprocess.terminate()


if __name__ == "__main__":
    main()
