
RMSECL_VOLUMETRICS
==================

.. warning::
    ``rmsecl_volumetrics`` is available for interactive testing only. Its
    name and command line arguments might change.

.. argparse::
   :module: subscript.rmsecl_volumetrics.rmsecl_volumetrics
   :func: get_parser
   :prog: rmsecl_volumetrics


Example
-------

Say you have a geomodel with 2 regions and 2 zones, for which you have exported
standard volumetrics. In the Eclipse model, you have set up a FIPNUM structure
which ignores the zone, and only takes the region into account. When comparing
the RMS volumetrics output, the volumes for both zones in each region must be
summed in order to be able to compare with the simulation model volumetrics,
typically extracted from the PRT file.

Assuming the PRT file and the volumetrics as exported from RMS are in their
standard locations on disk, you will only need to tell this script the mapping
between regions, zones and FIPNUMs. This mapping is quite general, and can be
supplied in multiple ways (either from FIPNUMs to regions/zones, or from
regions/zones to FIPNUMs).

If the region named "West" is modelled as FIPNUM 1, covering both the zones
named "Upper" and "Lower", the mapping could be specified as such:

.. code-block:: yaml

  region2fipnum:
    West: [1]
    East: [2]
  zone2fipnum:
    Upper: [1, 2]
    Lower: [1, 2]

An identical way of supplying this map would be to write up the inverse:

.. code-block:: yaml

  fipnum2region:
    1: West
    2: East
  fipnum2zone:
    1:
     - Upper
     - Lower
    2:
     - Upper
     - Lower

A third way of specifying this is to use the syntax also used by the
``webviz-subsurface`` plugin "ReservoirSimulationTimeSeriesRegional", where the
same map as above would be specified as:

.. code-block:: yaml

   FIPNUM:
     groups:
       REGION:
         West: [1]
         East: [2]
       ZONE:
         Upper: [1, 2]
         Lower: [1, 2]


The command line syntax would then typically look like:

.. code-block:: console

  $ rmsecl_volumetrics eclipse/model/MYMODEL.PRT share/results/volumes/geogrid fipmap.yml --sets sets.yml --output volcomp.csv

The code calculates two tables, both of which are printed to your terminal window, and
these tables can be separately exported to two different CSV files if wanted.

Volumes are compared over "sets" of collections of FIPNUMs, regions and zones.
The smallest comparable units are computed based on the provided mapping. The
first table tells which "sets" have been identified (and which regions/zones
and FIPNUMs are contained in each set), and the second table contains summed
volumes and differences in volumes for the identified sets.

The example above is simple in that each FIPNUM is a set, but complex arrangements
are possible. The sets are listed in the outputted file ``sets.yml``:

.. code-block:: yaml

  0:
    FIPNUM:
    - 2
    REGION:
    - East
    ZONE:
    - Lower
    - Upper
  1:
    FIPNUM:
    - 1
    REGION:
    - West
    ZONE:
    - Lower
    - Upper

Do not rely on the exact enumeration of sets, whichever FIPNUM-region-zone
combination comes first is arbitrary.  The compared volumes are in
``volcomp.csv``, from which an excerpt looks like:

.. list-table::
   :header-rows: 1

   * - SET
     - RMS_STOIIP_OIL
     - ECL_STOIIP_OIL
     - DIFF_STOIIP_OIL
   * - 0
     - 200.8
     - 200.0
     - -0.8
   * - 1
     - 100.8
     - 100.0
     - -0.8

which means that in both set 0 and 1, 0.8 m\ :sup:`3` of STOIIP was lost from the geomodel to the
dynamical model.
