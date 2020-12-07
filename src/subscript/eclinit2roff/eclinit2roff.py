DESCRIPTION = """Convert Eclipse INIT file to ROFF grid format.

This forward model uses the script ``convert_grid_format`` from subscript.

Destination directory must exist.

One file will be written for each of the requested parameters, the example
given below will produce the files::

    share/results/grids/eclgrid--poro.roff
    share/results/grids/eclgrid--permx.roff
"""

CATEGORY = "utility.eclipse"

EXAMPLES = """
.. code-block:: console

  FORWARD_MODEL ECLINIT2ROFF(<ECLROOT>=<ECLBASE>, <OUTPUT>=share/results/grids/eclgrid, <PROP>=PORO:PERMX)

where ``ECLBASE`` is already defined in your ERT config, pointing to the Eclipse
basename relative to ``RUNPATH``.
"""  # noqa
