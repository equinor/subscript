
FMUOBS
======

.. argparse::
   :module: subscript.fmuobs.fmuobs
   :func: get_parser
   :prog: fmuobs


Unsupported ERT observation keywords
------------------------------------

Newer ERT keywords such as ``RFT_OBSERVATION``, ``BREAKTHROUGH_OBSERVATION`` and ``SEISMIC_OBSERVATION``
are not supported, and are skipped with a warning. ``LOCALIZATION`` blocks inside
observations are ignored (also with a warning), while the rest of the observation is kept.
