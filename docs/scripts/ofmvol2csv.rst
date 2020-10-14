
OFMVOL2CSV
==========

.. argparse::
   :module: subscript.ofmvol2csv.ofmvol2csv
   :func: get_parser
   :prog: ofmvol2csv

Example
-------

If you have a ``vol``-file with this data:

.. code-block:: console

  *METRIC
  *DAILY
  *HRS_IN_DAYS
  *DATE *OIL *GAS *WATER *GINJ *DAYS
  *Name  Well_A
  21.08.2003        0.00        0.00        0.00    115346.18    24.0
  22.08.2003        0.00        0.00        0.00    115239.26    24.0
  23.08.2003        0.00        0.00        0.00    115344.04    24.0
  24.08.2003        0.00        0.00        0.00    115237.16    24.0
  25.08.2003        0.00        0.00        0.00    115341.91    24.0
  26.08.2003        0.00        0.00        0.00    115235.07    24.0
  27.08.2003        0.00        0.00        0.00    115339.77    24.0

you can call

.. code-block:: console

  $ ofmvol2csv --verbose myvolfile.vol --output proddata.csv

and the file ``proddata.csv`` will then contain:

.. code-block:: console

  WELL,DATE,OIL,GAS,WATER,GINJ,DAYS
  WELL_A,2003-08-21,0.0,0.0,0.0,115346.18,24.0
  WELL_A,2003-08-22,0.0,0.0,0.0,115239.26,24.0
  WELL_A,2003-08-23,0.0,0.0,0.0,115344.04,24.0
  WELL_A,2003-08-24,0.0,0.0,0.0,115237.16,24.0
  WELL_A,2003-08-25,0.0,0.0,0.0,115341.91,24.0
  WELL_A,2003-08-26,0.0,0.0,0.0,115235.07,24.0
  WELL_A,2003-08-27,0.0,0.0,0.0,115339.77,24.0


Modifying production data
-------------------------

The reason for converting *vol*-files to CSV is to be able
to utilize Pandas or other tools that reads CSV to for example
modify production data.

Examples:

.. code-block:: python

  import pandas as pd

  proddata = pd.read_csv("proddata.csv")
  # Scale up all water production by 5 percent:
  proddata["WATER"] = proddata["WATER"] * 1.05
  proddata.to_csv("proddata-scaled.csv", index=False)

  # Only include wells with non-zero oil production:
  oildata = proddata.groupby("WELL").filter(lambda x: x["OIL"].sum() > 0)
  oildata.to_csv("oilproducers.csv", index=False)

From CSV to vol again
---------------------

See the subscript utility ``csv2ofmvol`` to convert your modified CSV file
back to a vol-file again, for import into RMS for example.
