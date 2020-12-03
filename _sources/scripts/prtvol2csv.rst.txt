
PRTVOL2CSV
==========

.. argparse::
   :module: subscript.prtvol2csv.prtvol2csv
   :func: get_parser
   :prog: prtvol2csv


Region-support
--------------

The script supports aggregating volumes from the FIPNUMs in Eclipse
to a "region" definition in use by e.g. RMS. The FIPNUM is assumed
to be at a finer or equal scale as REGION - thus FIPNUM to REGION
can be a many-to-one mapping.

The YAML file for the mapping between FIPNUM and regions must be
structured like in this example:

.. code-block:: yaml

  region2fipnum:
    RegionA:
    - 1
    - 4
    - 6
    RegionB:
    - 2
    - 5


When is provided, a column named ``REGION`` will appear
in the output CSV file (from the argument ``--regionoutputfilename``), and
with volumes summed over included FIPNUMs (if more than one).

The FIPNUM column will then contain a space-separated list of FIPNUM values
that were included in the REGION.

The FIPNUM indexed table (the standard output from this script) will be augmented
by an extra REGION column with space-separated regions pointing to each
individual FIPNUM.

Regions can be overlapping, so for also gettiing out Totals (or subset of totals)
you can achieve that using custom region names. Here shown also with a more
condensed yaml syntax:

.. code-block:: yaml

  region2fipnum:
    RegionA: [1, 4, 6]
    RegionB: [2, 5]
    FormationA: [1, 2]
    Totals: [1, 2, 3, 4, 5, 6]

