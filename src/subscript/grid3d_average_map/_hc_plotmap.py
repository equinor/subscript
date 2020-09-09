# -*- coding: utf-8 -*-
"""Private module for HC thickness functions."""

from __future__ import division, print_function, absolute_import

import getpass
from time import localtime, strftime
import numpy as np
from collections import OrderedDict

from xtgeo.common import XTGeoDialog
from xtgeo.surface import RegularSurface
from xtgeo.xyz import Polygons

xtg = XTGeoDialog()

logger = xtg.functionlogger(__name__)


def do_hc_mapping(config, initd, hcpfzd, zonation, zoned, hcmode):
    """Do the actual map gridding, for zones and groups of zones"""

    mapzd = OrderedDict()

    if "templatefile" in config["mapsettings"]:
        basemap = RegularSurface(config["mapsettings"]["templatefile"])
        basemap.values = 0.0
    else:
        ncol = config["mapsettings"].get("ncol")
        nrow = config["mapsettings"].get("nrow")

        basemap = RegularSurface(
            xori=config["mapsettings"].get("xori"),
            yori=config["mapsettings"].get("yori"),
            ncol=config["mapsettings"].get("ncol"),
            nrow=config["mapsettings"].get("nrow"),
            xinc=config["mapsettings"].get("xinc"),
            yinc=config["mapsettings"].get("yinc"),
            values=np.zeros((ncol, nrow)),
        )

    mycoarsen = config["computesettings"]["tuning"]["coarsen"]
    myavgzon = config["computesettings"]["tuning"]["zone_avg"]
    mymaskoutside = config["computesettings"]["mask_outside"]

    for zname, zrange in zoned.items():

        usezonation = zonation.copy()
        usezrange = zrange

        # in case of super zones:
        if isinstance(zrange, list):
            usezonation = zonation.copy()
            usezonation[:, :, :] = 0
            logger.debug(usezonation)
            for zr in zrange:
                logger.debug("ZR is {}".format(zr))
                usezonation[zonation == zr] = 888

            usezrange = 888

        if zname == "all":
            usezonation = zonation.copy()
            usezonation[:, :, :] = 999
            usezrange = 999

            if config["computesettings"]["all"] is not True:
                logger.info("Skip <{}> (cf. computesettings: all)".format(zname))
                continue
        else:
            if config["computesettings"]["zone"] is not True:
                logger.info("Skip <{}> (cf. computesettings: zone)".format(zname))
                continue

        mapd = dict()

        for date, hcpfz in hcpfzd.items():
            logger.info("Mapping <{}> for date <{}> ...".format(zname, date))
            xmap = basemap.copy()

            xmap.hc_thickness_from_3dprops(
                xprop=initd["xc"],
                yprop=initd["yc"],
                hcpfzprop=hcpfz,
                zoneprop=usezonation,
                zone_minmax=(usezrange, usezrange),
                coarsen=mycoarsen,
                dzprop=initd["dz"],
                zone_avg=myavgzon,
                mask_outside=mymaskoutside,
            )

            filename = _hc_filesettings(config, zname, date, hcmode)
            xtg.say("Map file to {}".format(filename))
            xmap.to_file(filename)

            mapd[date] = xmap

        mapzd[zname] = mapd

    # return the map dictionary: {zname: {date1: map_object1, ...}}

    logger.debug("The map objects: {}".format(mapzd))

    return mapzd


def do_hc_plotting(config, mapzd, hcmode, filtermean=None):
    """Do plotting via matplotlib to PNG (etc) (if requested)"""

    xtg.say("Plotting ...")

    for zname, mapd in mapzd.items():

        for date, xmap in mapd.items():

            plotfile = _hc_filesettings(config, zname, date, hcmode, mode="plot")

            pcfg = _hc_plotsettings(config, zname, date, hcmode, filtermean)

            xtg.say("Plot to {}".format(plotfile))

            usevrange = pcfg["valuerange"]
            if len(date) > 10:
                usevrange = pcfg["diffvaluerange"]

            faults = None
            if pcfg["faultpolygons"] is not None:
                try:
                    fau = Polygons(pcfg["faultpolygons"], fformat="guess")
                    faults = {"faults": fau}
                except Exception as e:
                    xtg.say(e)
                    faults = None

            xmap.quickplot(
                filename=plotfile,
                title=pcfg["title"],
                subtitle=pcfg["subtitle"],
                infotext=pcfg["infotext"],
                xlabelrotation=pcfg["xlabelrotation"],
                minmax=usevrange,
                colormap=pcfg["colortable"],
                faults=faults,
            )


def _hc_filesettings(config, zname, date, hcmode, mode="map"):
    """Local function for map or plot file name"""

    delim = "--"

    if config["output"]["lowercase"]:
        zname = zname.lower()

    date = date.replace("unknowndate", "")

    if config["output"]["legacydateformat"]:
        date = _dates_oldformat(date)

    phase = hcmode

    if phase == "comb":
        phase = "hc"

    tag = ""
    if config["output"]["tag"]:
        tag = config["output"]["tag"] + "_"

    prefix = zname
    if prefix == "all" and config["output"]["prefix"]:
        prefix = config["output"]["prefix"]

    date = date.replace("-", "_")

    path = config["output"]["mapfolder"] + "/"
    if not date:
        xfil = prefix + delim + tag + phase + "thickness" + ".gri"
    else:
        xfil = prefix + delim + tag + phase + "thickness" + delim + str(date) + ".gri"

    if mode == "plot":
        path = config["output"]["plotfolder"] + "/"
        xfil = xfil.replace("gri", "png")

    return path + xfil


def _dates_oldformat(date):
    """Get dates on legacy format with underscore, 19910101 --> 1991_01_01."""

    if not date:  # empty string or None
        return ""

    date = str(date)
    newdate = date

    if len(date) == 8:
        year, month, day = (date[0:4], date[4:6], date[6:8])
        newdate = year + "_" + month + "_" + day
    elif len(date) == 17:
        year1, month1, day1, year2, month2, day2 = (
            date[0:4],
            date[4:6],
            date[6:8],
            date[9:13],
            date[13:15],
            date[15:17],
        )

        newdate = (
            year1 + "_" + month1 + "_" + day1 + "_" + year2 + "_" + month2 + "_" + day2
        )
    else:
        raise ValueError('Could not convert date to "old format"')

    return newdate


def _hc_plotsettings(config, zname, date, hcmode, filtermean):
    """Local function for plot additional info."""

    phase = config["computesettings"]["mode"]

    if phase == "comb":
        phase = "oil + gas"

    rock = "net"
    modecfg = config["computesettings"]["mode"]
    if modecfg == "dz_only" or modecfg == "rock":
        rock = "bulk"

    title = phase.capitalize() + " " + rock + " thickness for " + zname
    if date and date != "unknowndate":
        title = title + " " + date

    showtime = strftime("%Y-%m-%d %H:%M:%S", localtime())
    infotext = config["title"] + " - "
    infotext += " " + getpass.getuser() + " " + showtime
    if config["output"]["tag"]:
        infotext += " (tag: " + config["output"]["tag"] + ")"

    subtitle = None
    if filtermean < 1.0:
        subtitle = "Property filter: " + config["_filterinfo"]

    xlabelrotation = None
    valuerange = (None, None)
    diffvaluerange = (None, None)
    colortable = "rainbow"
    xlabelrotation = 0
    fpolyfile = None

    if "xlabelrotation" in config["plotsettings"]:
        xlabelrotation = config["plotsettings"]["xlabelrotation"]

    if "valuerange" in config["plotsettings"]:
        valuerange = tuple(config["plotsettings"]["valuerange"])

    if "diffvaluerange" in config["plotsettings"]:
        diffvaluerange = tuple(config["plotsettings"]["diffvaluerange"])

    if "faultpolygons" in config["plotsettings"]:
        fpolyfile = config["plotsettings"]["faultpolygons"]

    if "colortable" in config["plotsettings"]:
        colortable = config["plotsettings"]["colortable"]

    # there may be individual plotsettings for zname
    if zname is not None and zname in config["plotsettings"]:

        zfg = config["plotsettings"][zname]

        if "valuerange" in zfg:
            valuerange = tuple(zfg["valuerange"])

        if "diffvaluerange" in zfg:
            diffvaluerange = tuple(zfg["diffvaluerange"])

        if "xlabelrotation" in zfg:
            xlabelrotation = zfg["xlabelrotation"]

        if "colortable" in zfg:
            colortable = zfg["colortable"]

        if "faultpolygons" in zfg:
            fpolyfile = zfg["faultpolygons"]

    # assing settings to a dictionary which is returned
    plotcfg = {}
    plotcfg["title"] = title
    plotcfg["subtitle"] = subtitle
    plotcfg["infotext"] = infotext
    plotcfg["valuerange"] = valuerange
    plotcfg["diffvaluerange"] = diffvaluerange
    plotcfg["xlabelrotation"] = xlabelrotation
    plotcfg["colortable"] = colortable
    plotcfg["faultpolygons"] = fpolyfile

    return plotcfg
