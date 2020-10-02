
PRESENTVALUE
============

.. argparse::
   :module: subscript.presentvalue.presentvalue
   :func: get_parser
   :prog: presentvalue


Example
-------

The simplest usage if you have a finished simulation named ``MYSIMULATION.DATA``
is the following statement::

  $ presentvalue MYSIMULATION.DATA
  {'Presentvalue': 11433.1}

where the presentvalue is expressed in MNOK for the year you
are discounting to (current year by default).

Economic input
--------------

Price parameters can be given as constant values (check the current default by
typing presentvalue --help), or if you need something more fancy, as a yearly
table. If you give a yearly table, it must be a CSV (comma separated values)
file with exact column names. You may also add a cost column if you need to
deduct some costs occuring in specific years (in MNOK). You do not need to
include all columns, only for the data where you want to deviate from defaults.

Example text file::

  year, oilprice, gasprice, usdtonok, costs
  2018, 50, 1.6, 7.1, 0
  2019, 55, 1.7, 7.0, 100
  2020, 53, 1.9, 7.5, 0
  2021, 60, 1.95, 7.3, 0

if this table is saved in the file ``econtable.csv``, you may run the script
as::

  $ presentvalue --econtable econtable.csv MYSIMULATION.DATA

Difference profiles
-------------------

The script can be used to produce yearly difference profiles for the chosen oil
and gas vectors and including discounted values. This is accomplished by
combining the ``--basedatafiles`` and ``--verbose``. The table output you get
from the script can be copied into Excel or anywhere else.
