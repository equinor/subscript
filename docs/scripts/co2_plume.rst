
CO2_PLUME - PLUME AREA
======================

.. argparse::
   :module: subscript.co2_plume.plume_area
   :func: get_parser
   :prog: plume_area

Calculates the area of the CO\ :sub:`2` plume for each formation and time step, for both SGAS and AMFG (Pflotran) / YMF2 (Eclipse).

Output is a table on CSV format.


CSV file example - plume area
-----------------------------
Example of how the plume area output CSV file is structured:

.. list-table:: CSV file of CO2 plume area (m^2)
   :widths: 25 25 25 25 25 25 25
   :header-rows: 1

   * - DATE
     - toptherys_SGAS
     - topvolantis_SGAS
     - topvolon_SGAS
     - toptherys_AMFG
     - topvolantis_AMFG
     - topvolon_AMFG
   * - 2020-01-01
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
   * - 2060-01-01
     - 1200000.0
     - 300000.0
     - 100000.0
     - 1600000.0
     - 320000.0
     - 105000.0
   * - 2100-01-01
     - 2100000.0
     - 400000.0
     - 300000.0
     - 2900000.0
     - 510000.0
     - 360000.0


CO2_PLUME - PLUME EXTENT
========================

.. argparse::
   :module: subscript.co2_plume.plume_extent
   :func: get_parser
   :prog: plume_extent

Calculates the maximum lateral distance of the CO\ :sub:`2` plume from a given location, for instance an injection point. The distance is calculated for each time step, for both SGAS and AMFG (Pflotran) / YMF2 (Eclipse).

Output is a table on CSV format.

CSV file example - plume extent
-------------------------------
Example of how the plume extent output CSV file is structured:

.. list-table:: CSV file of CO2 plume extent (m)
   :widths: 25 25 25
   :header-rows: 1

   * - DATE
     - MAX_DISTANCE_SGAS
     - MAX_DISTANCE_AMFG
   * - 2020-01-01
     - 0.0
     - 0.0
   * - 2060-01-01
     - 703.4
     - 761.5
   * - 2100-01-01
     - 1305.2
     - 1521.0
