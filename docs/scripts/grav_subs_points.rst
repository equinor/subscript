GRAV_SUBS_POINTS
================

.. argparse::
   :module: subscript.grav_subs_points.grav_subs_points
   :func: get_parser
   :prog: grav_subs_points

	  
Include dates
-------------

Instead of specifying the modelling dates directly in the yaml config file
it is possible to include them from another yaml file:

.. code-block:: text

  input:
    diffdates: !include_from global_variables.yml::global.dates.GRAVITY_DIFFDATES

This is an advantage if the dates in the global config is used also for other jobs. In this example the included file looks like this:

.. code-block:: yaml

  # example global config file with dates
  global:
    dates:
      GRAVITY_DIFFDATES:
      - - 2020-07-01
        - 2018-01-01


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

- one column text files of modelled gravity change/subsidence GEN_DATA files that can be used with ert GENERAL_OBSERVATION
  
- x,y,z text file that can be used for visualisation.

The ordering of points in these two files will be the same as given in the station coordinates file used as input. It can therefore be a good idea to order the benchmark stations in the station coordinates file in the order you would like to see them in e.g. line plots, for instance sorted by area.

In some cases where the reservoir model covers several structures or fields it can be beneficial to split the modelling for different structures into several files. E.g. for testing in assisted history matching what effect it has if only observations for one of the structures is used as observations compared to both. To facilitate this usage the option to add a prefix to the GEN_DATA file to separate them, using the prefix_gendata option. There is also a possibility to use a different report step and extension than the default ".txt" by using the extension_gendata option. The default is now without any report step, since this is now longer needed in ert. But if defining a report step is needed, an extension like e.g. "_10.txt" could be given. 
  

  
