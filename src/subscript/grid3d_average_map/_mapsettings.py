# -*- coding: utf-8 -*-

from __future__ import division, print_function, absolute_import

import copy
import xtgeo

xtg = xtgeo.common.XTGeoDialog()

logger = xtg.functionlogger(__name__)


def check_mapsettings(config, grd):
    """Check if given map settings looks sane compared with actual grid

    It returns a 'pscore' which is a measure of problems. Everything
    greater than 0 is a problem, and > 0 is critical
    """

    ggeom = grd.get_geometrics(return_dict=True, cellcenter=False)

    # Compute the geometrics values from the mapsettings:
    cfmp = config["mapsettings"]

    if "templatefile" in cfmp:
        mymap = xtgeo.surface.RegularSurface(cfmp["templatefile"])
        xmin = mymap.xmin
        xmax = mymap.xmax
        ymin = mymap.ymin
        ymax = mymap.ymax
    else:
        xmin = cfmp["xori"]  # since unrotated map
        xmax = xmin + (cfmp["ncol"] - 1) * cfmp["xinc"]
        ymin = cfmp["yori"]  # since unrotated map
        ymax = ymin + (cfmp["nrow"] - 1) * cfmp["yinc"]

    # problems score pscore is 0 if all is OK
    pscore = 0
    if xmax < ggeom["xmin"] or xmin > ggeom["xmax"]:
        pscore += 10

    if ymax < ggeom["ymin"] or ymin > ggeom["ymax"]:
        pscore += 10

    return pscore


def estimate_mapsettings(config, grd):
    """Guess map settings if they are missing."""

    newconfig = copy.deepcopy(config)

    newconfig["mapsettings"] = dict()

    ggeom = grd.get_geometrics(return_dict=True, cellcenter=False)

    xmin = ggeom["xmin"]
    xmax = ggeom["xmax"]
    ymin = ggeom["ymin"]
    ymax = ggeom["ymax"]

    xlen = xmax - xmin
    ylen = ymax - ymin

    xmin = xmin - 0.05 * xlen
    xmax = xmax + 0.05 * xlen
    ymin = ymin - 0.05 * ylen
    ymax = ymax + 0.05 * ylen

    avgdxy = 0.5 * (ggeom["avg_dx"] + ggeom["avg_dy"])

    xinc = 0.5 * avgdxy
    yinc = 0.5 * avgdxy

    ncol = int(1.1 * xlen / xinc)
    nrow = int(1.1 * ylen / yinc)

    newconfig["mapsettings"]["ncol"] = ncol
    newconfig["mapsettings"]["nrow"] = nrow
    newconfig["mapsettings"]["xinc"] = xinc
    newconfig["mapsettings"]["yinc"] = yinc
    newconfig["mapsettings"]["xori"] = xmin
    newconfig["mapsettings"]["yori"] = ymin

    logger.debug(newconfig)

    return newconfig
