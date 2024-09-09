GRAV_SUBS_POINTS
================

.. argparse::
   :module: subscript.grav_subs_points.grav_subs_points
   :func: get_parser
   :prog: grav_subs_points

Station coordinates
-------------------

The file with station coordinates should be on .csv format and contain headers
as specified in this example:

.. code-block:: text

  bm_id;utmx;utmy;depth;area
  1;462632.692871;5930050.419434;200.000000;WL
  2;464438.063965;5932652.277710;200.000000;CH
  3;462924.737793;5933448.764526;200.000000;CH
  4;459977.734863;5935121.387695;200.000000;NH
  5;462247.045000;5934298.281000;200.000000;CH
  6;461517.610352;5933448.764526;200.000000;CN
  7;463933.621582;5931643.393677;200.000000;CS
  8a;463429.180176;5935068.288086;200.000000;EL
  9b;460561.825684;5936608.163086;200.000000;CH
  10;460482.177246;5931723.042358;200.000000;WL

| **bm_id**:      Name of the bencmark location.
| **utmx**:       UTM X for the bencmark location [m]
| **utmy**:       UTM Y for the bencmark location [m]
| **depth**:      Seabed depth for benchmark location [m TVD MSL]
| **area**:       An area identifier that can be used for grouping or labeling in visualisations



The output files
----------------

There will be two types of output file from grav_subs_points.

- one column text files of modelled gravity change/subsidence that can be used with GEN_DATA observations
  
- x,y,z text file that can be used for visualisation.

The ordering of points in these two files will be the same as given in the station coordinates file used as input.
  

  
