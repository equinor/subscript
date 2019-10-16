"""
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

 Eclipse Summary plotter is based on ERT-Python
  http://sib-docs.equinor.com/docs/ecl/index.html

 The source code is a part of the subscript repository:
  https://github.com/equinor/subscript

"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import ert.ecl as ecl
import matplotlib.pyplot
import numpy as np
import sys
import os
import re
import difflib
import argparse
from multiprocessing import Process

# Get rid of FutureWarning from pandas/plotting.py
from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()

DESCRIPTION = """Syntax:

summaryplot [<options>] <vectorstoplot> <datafilestoread>

vectorstoplot is a list of vectors to be plotted in the syntax
<vector>[:<wellname>]

For more vector possibilities, issue 'summary.x --list ECLFILE.DATA'
datafilestoread is a list of Eclipse *.DATA files to be read

Command line arguments are assumed to be Eclipse DATA-files as long
as the command line argument is an existing file. If not, it is assumed
to be a vector to plot. Thus, vectors and datafiles can be mixed.

Options:
 -hi (--hist) Include historical vector
 -nl No label; to avoid the plot to be filled with labels
 -s Single plot, all vectors are put into the same plot.
    Axes will not be adjusted.
 -n Normalize each vector to maximum 1.
 -e Ensemble mode: Colour by vector instead of by DATA-file, and adapt legend
 -d Dump images to files instead of displaying on screen
 -c PARAMNAME colour curves based on the value associated to PARAMNAME as found
   in a textfile called parameters.txt alongside the Eclipse runs.
"""

EPILOG = ""


def get_parser():
    """Setup mock parser to be improved at later stage"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=DESCRIPTION,
        epilog=EPILOG,
    )
    parser.add_argument(
        "-hi", "--hist", help="Plot historical vector", action="store_true"
    )
    return parser


# Entire functionality is wrapped in a function
# to allow running the plotter in a subprocess.
# (again needed in order to support ctrl-c)
def summaryplotter(*args):
    vectors = []  # strings
    datafiles = []  # strings
    summaryfiles = []  # EclSum objects
    rstfiles = []  # EclRst objects
    gridfiles = []  # EclGrid objects
    parameterfiles = []  # Vector of parameterfiles, from ERT or Basra
    includehistory = False  # default behaviour
    nolabel = False  # default behaviour
    singleplot = False  # default behaviour
    ensemblemode = False  # default behaviour
    normalize = False
    dumpimages = False
    maxlegends = 10  # Do not show more than the first 10 simulations in the legend
    parametercolouring = False
    logparametercolouring = False
    takeparamname = False
    paramnameforcolouring = ""
    parametervalues = []  # Vector of values pr. realization for colouring

    for arg in args:
        if takeparamname:  #
            paramnameforcolouring = arg
            takeparamname = False
            continue
        if arg == "-hist":
            includehistory = True
            continue
        if arg == "-n":
            normalize = True
            continue
        if arg == "-nl":
            nolabel = True
            continue
        if arg == "-s":
            singleplot = True
            continue
        if arg == "-e":
            ensemblemode = True
            continue
        if arg == "-l":
            maxlegends = 99999  # Don't truncate legend before this number is reached
            continue
        if arg == "-d":
            dumpimages = True
            continue
        if arg == "-c":
            takeparamname = (
                True
            )  # Process the parameter name for coloruing in next loop.
            parametercolouring = True
            logparametercolouring = False
            nolabel = True
            continue
        if arg == "-cl":
            takeparamname = True
            logparametercolouring = True
            parametercolouring = False
            nolabel = True
            continue

        # Try to parse command line arg as a summary file,
        # try as a vector if not.
        try:
            sumfn = ecl.EclSum(arg)
            datafiles.append(arg)

            summaryfiles.append(sumfn)

            # Try to load a corresponding parameter-file for colouring data
            parameterfileERT = (
                os.path.dirname(os.path.realpath(arg)) + "/../../parameters.txt"
            )  # ERT files
            parameterfileBasra = (
                os.path.dirname(os.path.realpath(arg)) + "/ParameterValues"
            )  # Basra files
            if os.path.isfile(parameterfileERT):
                parameterfiles.append(parameterfileERT)
            elif os.path.isfile(parameterfileBasra):
                parameterfiles.append(parameterfileBasra)
            else:
                parameterfiles.append("")
            # (we don't care yet if it exists or not)

        except Exception:
            vectors.append(arg)

    if (parametercolouring or logparametercolouring) and nolabel is False:
        print("Hint: Use -nl to skip legend")

    if (parametercolouring or logparametercolouring) and len(summaryfiles) < 2:
        parametercolouring = False
        logparametercolouring = False
        print("Info: Not colouring by parameter when only one DATA file is loaded")

    minvalue = 0.0
    maxvalue = 0.0
    parameternames = []
    if parametercolouring or logparametercolouring:
        # Try to load parameters.txt for each datafile,
        # and put the associated values in a vector
        for parameterfile in parameterfiles:
            valuefound = False
            if os.path.isfile(parameterfile):
                file = open(parameterfile)
                for line in file:
                    linecontents = line.split()
                    parameternames.append(linecontents[0])
                    if linecontents[0] == paramnameforcolouring:
                        parametervalues.append(float(linecontents[1]))
                        valuefound = True
                        break
            if not valuefound:
                print(
                    "Warning: "
                    + paramnameforcolouring
                    + " was not found in parameter-file "
                    + parameterfile
                )
                parametervalues.append(0.0)
        # print parametervalues

        # Normalize parametervalues to [0,1]:
        minvalue = np.min(parametervalues)
        maxvalue = np.max(parametervalues)
        if (maxvalue - minvalue) < 0.000001:
            print(
                "Warning: No data found to colour by, are you sure you typed "
                + paramnameforcolouring
                + " correctly?"
            )
            suggestion = difflib.get_close_matches(
                paramnameforcolouring, parameternames, 1
            )
            if len(suggestion) > 0:
                print("         Maybe you meant " + suggestion[0])
            logparametercolouring = False
            parametercolouring = False
        else:
            normalizedparametervalues = (parametervalues - minvalue) / (
                maxvalue - minvalue
            )

        if logparametercolouring:
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
                parametercolouring = True
                logparametercolouring = False

        # print normalizedparametervalues

        # Build a colour map from all the values, from min to max.

    if normalize and includehistory:
        print("Warning: Historical data is not "
              "normalized equal to simulated data")

    if len(summaryfiles) == 0:
        print("Error: No summary files found")
        sys.exit(1)

    # We support wildcards in summary vectors. The wildcards will be matched against
    # the existing vectors in the first Eclipse deck mentioned on the command
    # line
    matchedsummaryvectors = []
    restartvectors = []
    for v in vectors:
        if not summaryfiles[0].keys(v):
            # Check if it is a restart vector with syntax
            # <vector>:<i>,<j>,<k> aka SOIL:40,31,33
            if re.match(r"^[A-Z]+:[0-9]+,[0-9]+,[0-9]+$", v):
                print("Found restart vector " + v)
                restartvectors.append(v)
            else:
                print("Warning: No summary or restart vectors matched " + v)
        matchedsummaryvectors.extend(summaryfiles[0].keys(v))

    # If we have any restart vectors defined, we must also load the restart files
    if restartvectors:
        for datafile in datafiles:
            rstfile = datafile.replace(".DATA", "")
            rstfile = rstfile + ".UNRST"
            gridfile = datafile.replace(".DATA", "")
            gridfile = gridfile + ".EGRID"  # What about .GRID??
            print("Loading grid and restart file " + rstfile)
            # TODO: Allow some of the rstfiles to be missing
            # TODO: Handle missing rstfiles gracefully
            rst = ecl.EclFile(rstfile)
            grid = ecl.EclGrid(gridfile)
            rstfiles.append(rst)
            gridfiles.append(grid)
            print("done")

    if (len(matchedsummaryvectors) + len(restartvectors)) == 0:
        print("Error: No vectors to plot")
        sys.exit(1)

    # Now it is time to prepare vectors from restart-data, quite time-consuming!!
    # Remember that SOIL should also be supported, but must be calculated on
    # demand from SWAT and SGAS
    restartvectordata = {}
    restartvectordates = {}
    for v in restartvectors:
        print("Getting data for " + v + "...")
        match = re.match(r"^([A-Z]+):([0-9]+),([0-9]+),([0-9]+)$", v)
        dataname = match.group(1)  # aka SWAT, PRESSURE, SGAS etc..
        (ijk) = (int(match.group(2)), int(match.group(3)), int(match.group(4)))
        # Remember that these indices start on 1, not on zero!

        restartvectordata[v] = {}
        restartvectordates[v] = {}
        for datafile_idx in range(0, len(datafiles)):
            active_index = gridfiles[datafile_idx].get_active_index(ijk=ijk)
            restartvectordata[v][datafiles[datafile_idx]] = []
            restartvectordates[v][datafiles[datafile_idx]] = []

            # Loop over all restart steps
            last_step = range(rstfiles[datafile_idx].num_named_kw("SWAT"))[-1]
            for report_step in range(0, last_step + 1):
                restartvectordates[v][datafiles[datafile_idx]].append(
                    rstfiles[datafile_idx].iget_restart_sim_time(report_step)
                )
                if dataname != "SOIL":
                    restartvectordata[v][datafiles[datafile_idx]].append(
                        rstfiles[datafile_idx].iget_named_kw(dataname, report_step)[
                            active_index
                        ]
                    )
                else:
                    swatvalue = rstfiles[datafile_idx].iget_named_kw(
                        "SWAT", report_step
                    )[active_index]
                    sgasvalue = rstfiles[datafile_idx].iget_named_kw(
                        "SGAS", report_step
                    )[active_index]
                    restartvectordata[v][datafiles[datafile_idx]].append(
                        1 - swatvalue - sgasvalue
                    )

            # print restartvectordata[v][datafiles[datafile_idx]]
            # print restartvectordates[v][datafiles[datafile_idx]]
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

    if parametercolouring or logparametercolouring:
        colourmap = matplotlib.colors.LinearSegmentedColormap.from_list(
            "GreenBlackRed", [(0, 0.6, 0), (0, 0, 0), (0.8, 0, 0)]
        )
        matplotlib.cm.register_cmap(name="GreenBlackRedMap", cmap=colourmap)
        colours = list(
            map(tuple, pyplot.get_cmap("GreenBlackRedMap")(normalizedparametervalues))
        )

    if parametercolouring or logparametercolouring:
        # Using contourf to provide my colorbar info, then clearing the figure
        Z = [[0, 0], [0, 0]]
        step = (maxvalue - minvalue) / 100
        levels = np.arange(minvalue, maxvalue + step, step)
        invisiblecontourplot = pyplot.contourf(Z, levels, cmap="GreenBlackRedMap")
        pyplot.clf()
        pyplot.close()

    for v_idx in range(0, len(matchedsummaryvectors)):
        v = matchedsummaryvectors[v_idx]

        if (not singleplot) or v == matchedsummaryvectors[0]:
            fig = pyplot.figure()
            if parametercolouring or logparametercolouring:
                pyplot.colorbar(invisiblecontourplot)
            pyplot.xlabel("Date")

        # Set background colour outside plot area to white:
        fig.patch.set_facecolor("white")

        # Add grey major gridlines:
        pyplot.grid(b=True, which="both", color="0.65", linestyle="-")

        if not singleplot:
            if parametercolouring:
                pyplot.title(v + ", colouring: " + paramnameforcolouring)
            elif logparametercolouring:
                pyplot.title(v + ", colouring: Log10(" + paramnameforcolouring + ")")
            else:
                pyplot.title(v)
        else:
            pyplot.title("")

        # Look for historic vectors in first summaryfile
        if includehistory:
            s = summaryfiles[0]
            toks = v.split(":", 1)
            histvec = toks[0] + "H"
            if len(toks) > 1:
                histvec = histvec + ":" + toks[1]
            if histvec in s.keys():
                values = s.numpy_vector(histvec)
                sumlabel = "_nolegend_"
                if normalize:
                    maxvalue = values.max()
                    values = [i * 1 / maxvalue for i in values]
                    sumlabel = histvec + " " + str(maxvalue)

                pyplot.plot_date(s.dates, values, "k.", label=sumlabel)
                fig.autofmt_xdate()

        for s_idx in range(0, len(summaryfiles)):
            s = summaryfiles[s_idx]
            if v in s.keys():
                if s_idx >= maxlegends:  # Truncate legend if too many
                    sumlabel = "_nolegend_"
                else:
                    if singleplot:
                        sumlabel = v + " " + s.case.lower()
                    else:
                        sumlabel = s.case.lower()

                values = s.numpy_vector(v)

                if ensemblemode:
                    cycledcolor = colours[v_idx]
                    if s_idx == 0:
                        sumlabel = v
                    else:
                        sumlabel = "_nolegend_"
                elif singleplot:
                    cycledcolor = colours[v_idx]
                else:
                    cycledcolor = colours[s_idx]

                if normalize:
                    maxvalue = values.max()
                    values = [i * 1 / maxvalue for i in values]
                    sumlabel = sumlabel + " " + str(maxvalue)

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

        if not nolabel:
            pyplot.legend(loc="best", fancybox=True, framealpha=0.5)
    for v in restartvectors:

        if not singleplot or (
            v == restartvectors[0] and len(matchedsummaryvectors) == 0
        ):
            fig = pyplot.figure()
            if parametercolouring or logparametercolouring:
                pyplot.colorbar(invisiblecontourplot)
            pyplot.xlabel("Date")

        if not singleplot:
            if parametercolouring:
                pyplot.title(v + ", colouring: " + paramnameforcolouring)
            elif logparametercolouring:
                pyplot.title(v + ", colouring: Log10(" + paramnameforcolouring + ")")
            else:
                pyplot.title(v)
        else:
            pyplot.title("")

        # Set background colour outside plot area to white:
        fig.patch.set_facecolor("white")

        # Add grey major gridlines:
        pyplot.grid(b=True, which="both", color="0.65", linestyle="-")

        for datafile_idx in range(0, len(datafiles)):

            if singleplot:
                rstlabel = v + " " + datafiles[datafile_idx].lower()
            else:
                rstlabel = datafiles[datafile_idx].lower()

            if ensemblemode:
                cycledcolor = colours[len(matchedsummaryvectors) + v_idx]
                if datafile_idx == 0:
                    rstlabel = v
                else:
                    rstlabel = "_nolegend_"
            else:
                cycledcolor = colours[datafile_idx]

            values = np.array(restartvectordata[v][datafiles[datafile_idx]])
            if normalize:
                maxvalue = values.max()
                values = [i * 1 / maxvalue for i in values]
                rstlabel = rstlabel + " " + str(maxvalue)

            pyplot.plot_date(
                restartvectordates[v][datafiles[datafile_idx]],
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

        if not nolabel:
            pyplot.legend(loc="best")

    if dumpimages:
        pyplot.savefig("summaryplotdump.png", bbox_inches="tight")
        pyplot.savefig("summaryplotdump.pdf", bbox_inches="tight")

    if not dumpimages:
        pyplot.show()


def main():

    parser = get_parser()
    parsed_args, args = parser.parse_known_args()

    # we are mocking argparse so, this will need to be fixed at some point
    if parsed_args.hist:
        args.append("-hist")

    plotprocess = Process(target=summaryplotter, args=args)
    plotprocess.start()

    # If user only wants to dump image to file, then do only that:
    for arg in args:
        if arg == "-d":
            print("Dumping plot to summaryplotdump.png and summaryplotdump.pdf")
            plotprocess.join()
            plotprocess.terminate()
            sys.exit(0)

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
                    print(
                        "Reloading plot...\r"
                    )  # Must use \r instead of \n since we have messed up terminal
                    plotprocess.terminate()
                    plotprocess = Process(target=summaryplotter, args=args)
                    plotprocess.start()
        except KeyboardInterrupt:
            pass
        # We have messed up the terminal, remember to fix:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

        # Close plot windows (running in a subprocess)
        plotprocess.terminate()


if __name__ == "__main__":
    main()
