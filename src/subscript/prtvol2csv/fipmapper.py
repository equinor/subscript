"""
This class has been moved to fmu-tools.
"""
import warnings

import fmu.tools.fipmapper.fipmapper


def FipMapper(*args, **kwargs):
    warnings.warn(
        "Use fipmapper from fmu.tools instead, this will be deleted", FutureWarning
    )
    return fmu.tools.fipmapper.fipmapper.FipMapper(*args, **kwargs)


def webviz_to_prtvol2csv(webvizdict: dict):
    """Convert a dict representation of a region/zone map in the Webviz format
    to the prtvol2csv format"""
    warnings.warn("Use fipmapper from fmu.tools", FutureWarning)
    return fmu.tools.fipmapper.fipmapper.webviz_to_prtvol2csv(webvizdict)


def invert_map(*args, **kwargs):
    warnings.warn("Use fipmapper from fmu.tools", FutureWarning)
    return fmu.tools.fipmapper.fipmapper.invert_map(*args, **kwargs)
