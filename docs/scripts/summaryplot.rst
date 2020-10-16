
SUMMARYPLOT
===========

``summaryplot`` is a command line utility to generate plots from Eclipse
simulations, based on `libecl <http://github.com/equinor/libecl>`_
for processing Eclipse output files and
`matplotlib <http://matplotlib.sourceforge.net>`_ for plotting.

.. figure:: images/Summaryplot-ert.png
   :width: 50%

   Example plot produced by summaryplot, lines coloured by an ERT input parameter,
   ``summaryplot -nl -cl REGTRANS:GNUS_GNVUS BPR:12,16,2 realization-*/iter-1/*DATA``

Syntax
------

.. argparse::
   :module: subscript.summaryplot.summaryplot
   :func: get_parser
   :prog: summaryplot

The script is forgiving for incomplete filenames, if you want to read
PERFECTMATCH.DATA it is sufficient to write "PERFECTMATCH" OR "PERFECTMATCH."
(this feature is there to save time when you tab yourself to filename
completion).

Vectors can be written with wildcards. For a list of possible vectors, issue
``summary.x --list <eclipsedatafile>``. If using the c-shell (``csh``), you
need to enclose each vector wildcard in quotes.

.. figure:: images/Summaryplot-normalizeexample.png
   :width: 40%

   Example with normalize option,
   ``summaryplot -n -s FWIR FGIR WPR FVPR MYSIMULATION.DATA``

.. figure:: images/Summaryplot-ensemble.png
   :width: 40%

   Example with ensemble mode,
   ``summaryplot -e -H -s FOPR FWPT realization*/*DATA`` was used to produce
   this example. Transparency is adjusted according to number of models plotted.

Plotting cell values
--------------------

Cell values (f.ex. ``SWAT``, ``SOIL``, ``PRESSURE``) can be plotted by giving
vector names like ``keyword:i,j,k``, f.ex::

  $ summaryplot SOIL:14,32,1 FILENAME.DATA

This requires the relevant information to be available in a unified restart file.
