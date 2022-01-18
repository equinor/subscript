
RI_WELLMOD
===========

``ri_wellmod`` is a command line utility to generate Eclipse well model definitions
(WELSPECS/WELSPECL, COMPDAT/COMPDATL, WELSEGS, COMPSEGS) using ResInsight. The script
takes as input a ResInsight project with wells and completions defined, in addition to
an Eclipse case (either an initialized case or an input case with grid and PERMX|Y|Z
and NTG defined in the GRDECL format).

.. note:: Well names specified as command line arguments are assumed to refer to the
   Eclipse well names, i.e., the completion export names as defined in the ResInsight
   wells project.

Examples
--------

Example 1
^^^^^^^^^^^

To create well definitions in a file with the default name ``welldefs.sch``::

    > ri_wellmod wells.rsp DROGON-0


Here ``DROGON-0`` is an initialized Eclipse case (i.e., the files DROGON-0.INIT and
DROGON-0.EGRID/DROGON-0.GRID exist), and wells.rsp is a ResInsight project with wells
and completions defined:

.. figure:: images/resinsight_wells_project_example.png
   :figwidth: 85%
   :alt: Example wells project

   Example ResInsight project with wells for the Drogon case


Example 2
^^^^^^^^^

By default multi-segment well definitions are not created, but may be requested for
some or all wells using a command-line argument. E.g., to add MSW data for the well
``A44`` and any wells starting with ``C`` based on a NOSIM case::

    > ri_wellmod wells.rsp DROGON-0_NOSIM --msw A4,C*


Example 3
^^^^^^^^^

Instead of using an initialized Eclipse case an input GRDECL case may be used. To
create meaningful connection factors PERMX/PERMY/PERMZ and NTG (if non-unit) must
be specified, either in the GRDECL file or in separate files, as in this exapmle::

    > ri_wellmod wells.rsp ../include/grid/drogon.grid.grdecl \
      --property_files ../include/grid/drogon.perm.grdecl ../include/grid/drogon.ntg.grdecl

Example 4
^^^^^^^^^

ResInsight supports local grid refinement, and will automatically create WELSPECL/COMPDATL/COMPSEGL
when given an initialized Eclipse case with LGR(s)::

   > ri_wellmod wells.rsp DROGON-0_NOSIM_LGR --msw A4 -o wells_lgr.sch


Example 5
^^^^^^^^^

It is also possible to create local LGRs surrounding each well, and this may be specified on the
script command line. The following example adds a 3x3x2 refinement to the region of cells
perforated by the well A4 and a 1x1x3 refinement around A6::

   > ri_wellmod wells.rsp DROGON-0_NOSIM --lgr A4:3,3,2 A6:1,1,3 -msw A4 \
    --lgr_output_file lgr_definitions.inc

The corresponding CARFIN keywords are found in a separate file (here ``lgr_definitions.inc``), to
be included in the GRID section of the Eclipse .DATA file.

Syntax
------

.. argparse::
   :module: subscript.ri_wellmod.ri_wellmod
   :func: get_parser
   :prog: ri_wellmod
