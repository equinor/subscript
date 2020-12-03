
CSV_STACK
=========

.. argparse::
   :module: subscript.csv_stack.csv_stack
   :func: get_parser
   :prog: csv_stack

Example
-------

If a CSV file contains::

  REALIZATION, DATE, poro, WOPT:A1, WOPT:A2, RPR:1, RPR:2
  1,     2015-01-01,  6,    1,        2,       3,    4
  1,     2015-02-01,  7,    2,        3,       4,    5
  1,     2015-02-03,  8,    3,        4,       5,    6
  2,     2015-01-01,  9,    4,        5,       6,    7
  2,     2015-02-01, 10,    5,        6,       7,    8
  2,     2015-03-01,  4,    3,        2,       4,    5
  2,     2015-04-01, 11,    6,        7,       8,    9

If you then want to plot ``WOPT`` for all wells, you might want to
colour by the name of the well. Then you can stack your dataset into
a layout more favourable for that purpose::

  WELL, DATE,   RPR:1, RPR:2, REALIZATION, WOPT, poro
  A1, 2015-01-01, 3.0, 4.0,    1.0,        1.0,  6.0
  A2, 2015-01-01, 3.0, 4.0,    1.0,        2.0,  6.0
  A1, 2015-02-01, 4.0, 5.0,    1.0,        2.0,  7.0
  A2, 2015-02-01, 4.0, 5.0,    1.0,        3.0,  7.0
  A1, 2015-02-03, 5.0, 6.0,    1.0,        3.0,  8.0
  A2, 2015-02-03, 5.0, 6.0,    1.0,        4.0,  8.0
  A1, 2015-01-01, 6.0, 7.0,    2.0,        4.0,  9.0
  A2, 2015-01-01, 6.0, 7.0,    2.0,        5.0,  9.0
  A1, 2015-02-01, 7.0, 8.0,    2.0,        5.0, 10.0
  A2, 2015-02-01, 7.0, 8.0,    2.0,        6.0, 10.0
  A1, 2015-03-01, 4.0, 5.0,    2.0,        3.0,  4.0
  A2, 2015-03-01, 4.0, 5.0,    2.0,        2.0,  4.0
  A1, 2015-04-01, 8.0, 9.0,    2.0,        6.0, 11.0
  A2, 2015-04-01, 8.0, 9.0,    2.0,        7.0, 11.0

where the columns ``WOPT:A1`` and ``WOPT:A2`` has been condensed into only one
column called ``WOPT``, but the name of the well now occurs as a column value
(in the column called ``WELL``).

Note that you might also want to stack on the region pressures instead, ``RPR:*``.
This can be accomplished by an option, see below. You may also stack on
well parameters and region parameters at the same time.

Be careful stacking large datasets (gigabytes), the memory usage during
stacking and filesize can blow up.
