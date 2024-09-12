
GRAV_SUBS_MAPS
==============

.. argparse::
   :module: subscript.grav_subs_maps.grav_subs_maps
   :func: get_parser
   :prog: grav_subs_maps
	
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
   
The output files
----------------

The output from this job are maps in irap binary format. For each difference date there will be one subsidence map and one or more gravity change maps (depending on which phases are specified to model).

The naming of the output files have been standardised to:

| all--subsidence--yyyymmdd_yyyymmdd.gri

| all--delta_gravity_gas--yyyymmdd_yyyymmdd.gri
| all--delta_gravity_oil--yyyymmdd_yyyymmdd.gri
| all--delta_gravity_water--yyyymmdd_yyyymmdd.gri
| all--delta_gravity_total--yyyymmdd_yyyymmdd.gri

The "all" prefix is indicating that the contributions from all zones is summed.    
