DESCRIPTION = """Convert between Eclipse binary EGRID output to ROFF grid format.

This forward model uses the script ``convert_grid_format`` from subscript.

Destination directory must exist.

The file extension ``.roff`` will be added to the OUTPUTNAME argument.
"""

CATEGORY = "utility.eclipse"

EXAMPLES = "FORWARD_MODEL ECLGRID2ROFF(<INPUTNAME>=<ECLBASE>, <OUTPUTNAME>=share/results/grids/eclgrid)"  # noqa
