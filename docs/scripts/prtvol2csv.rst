
PRTVOL2CSV
==========

.. argparse::
   :module: subscript.prtvol2csv.prtvol2csv
   :func: get_parser
   :prog: prtvol2csv


Eclipse PRT volumetric data
---------------------------

The script will read numbers from the line with ``CURRENTLY IN PLACE`` in Eclipse PRT files:


.. code-block:: none

                                                 =================================
                                                 : FIPNUM  REPORT REGION    1    :
                                                 :     PAV =        305.89  BARSA:
                                                 :     PORV=     78815548.   RM3 :
                            :--------------- OIL    SM3  ---------------:-- WAT    SM3  -:--------------- GAS    SM3  ---------------:
                            :     LIQUID         VAPOUR         TOTAL   :       TOTAL    :       FREE      DISSOLVED         TOTAL   :
  :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
  :CURRENTLY IN PLACE       :     10656981.                    10656981.:      59957809. :            0.   1960884420.    1960884420.:
  :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
  :OUTFLOW TO OTHER REGIONS :            0.                           0.:             0. :            0.            0.             0.:
  :OUTFLOW THROUGH WELLS    :                                         0.:             0. :                                         0.:
  :MATERIAL BALANCE ERROR.  :                                         0.:             0. :                                         0.:
  :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
  :ORIGINALLY IN PLACE      :     10656981.                    10656981.:      59957809. :            0.   1960884420.    1960884420.:
  :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
  ====================================================================================================================================


Additionally, if the Eclipse DATA file includes::

  RPTSOL
    FIP=2 'FIPRESV' /

the PRT-file will also contain a table with pore volumes pr. phase and pr.
FIPNUM, which will be added to the exported table.

.. code-block:: none

                                                      ===================================
                                                      :  RESERVOIR VOLUMES      RM3     :
  :---------:---------------:---------------:---------------:---------------:---------------:
  : REGION  :  TOTAL PORE   :  PORE VOLUME  :  PORE VOLUME  : PORE VOLUME   :  PORE VOLUME  :
  :         :   VOLUME      :  CONTAINING   :  CONTAINING   : CONTAINING    :  CONTAINING   :
  :         :               :     OIL       :    WATER      :    GAS        :  HYDRO-CARBON :
  :---------:---------------:---------------:---------------:---------------:---------------:
  :   FIELD :     399202846.:      45224669.:     353978177.:             0.:      45224669.:
  :       1 :      78802733.:      17000359.:      61802374.:             0.:      17000359.:
  :       2 :      79481140.:             0.:      79481140.:             0.:             0.:
  ===========================================================================================



Region and zone support
-----------------------

Each row in the exported CSV can be augmented with the corresponding Region and
Zone the particular FIPNUM belongs to. This is accomplished by supplying a YAML
file which defines the map between regions and/or zones to FIPNUM.

The YAML file for the mapping between FIPNUM and regions can be
structured like in this example:

.. code-block:: yaml

  region2fipnum:
    RegionA: [1, 2, 3]
    RegionB: [4, 5, 6]
  zone2fipnum:
    Upper: [1, 4]
    Mid: [2, 5]
    Lower: [3, 6]

It is possible to supply inverse maps instead (they will be inverted if needed):

.. code-block:: yaml

  fipnum2region:
    1: RegionA
    2: RegionA
    3: RegionA
    4: RegionB
    5: RegionB
    6: RegionB
  fipnum2zone:
    1: Upper
    2: Mid
    3: Lower
    4: Upper
    5: Mid
    6: Lower

The keys ``region2fipnum`` etc. can be at the root level of the yaml file, or
inside the ``global`` section. It is possible to reuse the fmu-config generated
yaml file.

You may also use the same YAML file as used for the ``webviz-subsurface`` plugin
"ReservoirSimulationTimeSeriesRegional", the same configuration as above would then look
like

.. code-block:: yaml

   FIPNUM:
     groups:
       REGION:
         RegionA: [1, 2, 3]
         RegionB: [4, 5, 6]
       ZONE:
         Upper: [1, 4]
         Mid: [2, 5]
         Lower: [3, 6]

Example output
--------------

This example table is from a case where pore volumes are included, and a yaml
file has been supplied defining the map from zones and regions to FIPNUM:

.. csv-table:: Example output CSV from prtvol2csv
   :file: prtvol2csv.csv
   :header-rows: 1

See also
--------

* https://equinor.github.io/res2df/usage/fipreports.html can be used to extract
  more information from  the PRT files.
