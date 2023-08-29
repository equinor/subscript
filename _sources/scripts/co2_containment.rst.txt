
CO2_CONTAINMENT
===============

.. argparse::
   :module: subscript.co2_containment.co2_containment
   :func: get_parser
   :prog: co2_containment

Calculates the amount of CO\ :sub:`2` inside and outside a given perimeter, and separates the result per formation and phase (gas/dissolved). Output is a table on CSV format.

The most common use of the script is to calculate CO\ :sub:`2` mass. Options for calculation type input:

* "mass": CO\ :sub:`2` mass (kg), the default option
* "cell_volume": CO\ :sub:`2` volume (m\ :sup:`3`), a simple calculation finding the grid cells with some CO\ :sub:`2` and summing the volume of those cells
* "actual_volume": CO\ :sub:`2` volume (m\ :sup:`3`), an attempt to calculate a more precise representative volume of CO\ :sub:`2`

CSV file example
----------------------------
Example of how the output CSV file is structured:

.. list-table:: CSV file of CO2 mass (kg)
   :widths: 25 25 25 25 25 25 25 25 25 25
   :header-rows: 1

   * - date
     - total
     - total_contained
     - total_outside
     - total_hazardous
     - total_gas
     - total_aqueous
     - gas_contained
     - aqueous_contained
     - . . .
   * - 2020-01-01
     -
     -
     -
     -
     -
     -
     -
     -
     -
   * - 2060-01-01
     -
     -
     -
     -
     -
     -
     -
     -
     -
   * - 2100-01-01
     -
     -
     -
     -
     -
     -
     -
     -
     -

.. figure:: images/co2_containment_A.png
   :align: center
   :width: 40%

   Example plot of CO\ :sub:`2` mass made from a CO\ :sub:`2` containment output CSV file
