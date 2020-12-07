DESCRIPTION = """Convert between Eclipse binary EGRID output to ROFF grid format.

This forward model uses the script ``convert_grid_format`` from subscript.

Destination directory must exist.

The file extension ``.roff`` will be added to the OUTPUT argument.
"""

CATEGORY = "utility.eclipse"

EXAMPLES = """
..  code-block:: console

   FORWARD_MODEL ECLGRID2ROFF(<ECLROOT>=<ECLBASE>, <OUTPUT>=share/results/grids/eclgrid)

where ``ECLBASE`` is already defined in your ERT config, pointing to the Eclipse
basename relative to ``RUNPATH``.
"""  # noqa
