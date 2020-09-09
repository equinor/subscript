# -*- coding: utf-8 -*-

from __future__ import division, print_function, absolute_import

import getpass
from time import localtime, strftime
import numpy as np
import numpy.ma as ma
from collections import OrderedDict

from xtgeo.common import XTGeoDialog
from xtgeo.surface import RegularSurface
from xtgeo.xyz import Polygons

xtg = XTGeoDialog()
logger = xtg.functionlogger(__name__)


def get_avg(config, specd, propd, dates, zonation, zoned, filterarray):
    """Compute a dictionary with average numpy per date

    It will return a dictionary per parameter and eventually dates"""

    avgd = OrderedDict()

    myavgzon = config["computesettings"]["tuning"]["zone_avg"]
    mycoarsen = config["computesettings"]["tuning"]["coarsen"]

    if "templatefile" in config["mapsettings"]:
        xmap = RegularSurface(config["mapsettings"]["templatefile"])
        xmap.values = 0.0
    else:
        ncol = config["mapsettings"].get("ncol")
        nrow = config["mapsettings"].get("nrow")

        xmap = RegularSurface(
            xori=config["mapsettings"].get("xori"),
            yori=config["mapsettings"].get("yori"),
            ncol=ncol,
            nrow=nrow,
            xinc=config["mapsettings"].get("xinc"),
            yinc=config["mapsettings"].get("yinc"),
            values=np.zeros((ncol, nrow)),
        )

    logger.debug("Flags of xmap is {}".format(xmap.values.flags))
    xtg.say("Mapping ...")
    if len(propd) == 0 or len(zoned) == 0:
        raise RuntimeError("The dictionary <propd> or <zoned> is zero. Stop")

    for zname, zrange in zoned.items():

        logger.info("ZNAME and ZRANGE are {}:  {}".format(zname, zrange))
        usezonation = zonation
        usezrange = zrange

        # in case of super zones:
        if isinstance(zrange, list):
            usezonation = zonation.copy()
            usezonation[:, :, :] = 0
            logger.debug(usezonation)
            for zr in zrange:
                logger.info("ZR is {}".format(zr))
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

        for propname, pvalues in propd.items():

            # filters get into effect by multyplying with DZ weight
            usedz = specd["idz"] * filterarray

            xmap.avg_from_3dprop(
                xprop=specd["ixc"],
                yprop=specd["iyc"],
                mprop=pvalues,
                dzprop=usedz,
                zoneprop=usezonation,
                zone_minmax=[usezrange, usezrange],
                zone_avg=myavgzon,
                coarsen=mycoarsen,
            )

            filename = _avg_filesettings(config, zname, propname, mode="map")
            usename = (zname, propname)

            if config["computesettings"]["mask_zeros"]:
                xmap.values = ma.masked_inside(xmap.values, -1e-30, 1e-30)

            logger.debug("XMAP updated after mask: \n{}\n".format(xmap.values))
            logger.debug("XMAP flags {}".format(xmap.values.flags))

            avgd[usename] = xmap.copy()

            logger.debug("Saved as copy...\n{}\n".format(avgd[usename].values))

            xtg.say("Map file to {}".format(filename))
            avgd[usename].to_file(filename)

    return avgd


def do_avg_plotting(config, avgd):
    """Do plotting via matplotlib to PNG (etc) (if requested)"""

    xtg.say("Plotting ...")

    for names, xmap in avgd.items():

        # 'names' is a tuple as (zname, pname)
        zname = names[0]
        pname = names[1]

        plotfile = _avg_filesettings(config, zname, pname, mode="plot")

        pcfg = _avg_plotsettings(config, zname, pname)

        xtg.say("Plot to {}".format(plotfile))

        usevrange = pcfg["valuerange"]

        faults = None
        if pcfg["faultpolygons"] is not None:
            xtg.say("Try: {}".format(pcfg["faultpolygons"]))
            try:
                fau = Polygons(pcfg["faultpolygons"], fformat="guess")
                faults = {"faults": fau}
                xtg.say("Use fault polygons")
            except Exception as e:
                xtg.say(e)
                faults = None
                xtg.say("No fault polygons")

        xmap.quickplot(
            filename=plotfile,
            title=pcfg["title"],
            subtitle=pcfg["subtitle"],
            infotext=pcfg["infotext"],
            xlabelrotation=pcfg["xlabelrotation"],
            minmax=usevrange,
            colortable=pcfg["colortable"],
            faults=faults,
        )


def _avg_filesettings(config, zname, pname, mode="root"):
    """Local function for map or plot file root name"""

    delim = "--"

    if config["output"]["lowercase"]:
        zname = zname.lower()
        pname = pname.lower()

    # pname may have a single '-' if it contains a date; replace with '_'
    # need to trick a bit by first replacing '--' (if delim = '--')
    # with '~~', then back again...
    pname = pname.replace(delim, "~~").replace("-", "_").replace("~~", delim)

    tag = ""
    if config["output"]["tag"]:
        tag = config["output"]["tag"] + "_"

    prefix = zname
    if prefix == "all" and config["output"]["prefix"]:
        prefix = config["output"]["prefix"]

    xfil = prefix + delim + tag + "average" + "_" + pname

    if mode == "root":
        return xfil

    elif mode == "map":
        path = config["output"]["mapfolder"] + "/"
        xfil = xfil + ".gri"

    elif mode == "plot":
        path = config["output"]["plotfolder"] + "/"
        xfil = xfil + ".png"

    return path + xfil


def _avg_plotsettings(config, zname, pname):
    """Local function for plot additional info for AVG maps."""

    title = "Weighted average for " + pname + ", zone " + zname

    showtime = strftime("%Y-%m-%d %H:%M:%S", localtime())
    infotext = config["title"] + " - "
    infotext += getpass.getuser() + " " + showtime
    if config["output"]["tag"]:
        infotext += " (tag: " + config["output"]["tag"] + ")"

    xlabelrotation = None
    valuerange = (None, None)
    diffvaluerange = (None, None)
    colortable = "rainbow"
    xlabelrotation = 0
    fpolyfile = None

    if "xlabelrotation" in config["plotsettings"]:
        xlabelrotation = config["plotsettings"]["xlabelrotation"]

    # better perhaps:
    # xlabelrotation = config['plotsettings'].get('xlabelrotation', None)

    if "valuerange" in config["plotsettings"]:
        valuerange = tuple(config["plotsettings"]["valuerange"])

    if "diffvaluerange" in config["plotsettings"]:
        diffvaluerange = tuple(config["plotsettings"]["diffvaluerange"])

    if "faultpolygons" in config["plotsettings"]:
        fpolyfile = config["plotsettings"]["faultpolygons"]

    # there may be individual plotsettings per property per zone...
    if pname is not None and pname in config["plotsettings"]:

        pfg = config["plotsettings"][pname]

        if "valuerange" in pfg:
            valuerange = tuple(pfg["valuerange"])

        if "diffvaluerange" in pfg:
            diffvaluerange = tuple(pfg["diffvaluerange"])

        if "xlabelrotation" in pfg:
            xlabelrotation = pfg["xlabelrotation"]

        if "colortable" in pfg:
            colortable = pfg["colortable"]

        if "faultpolygons" in pfg:
            fpolyfile = pfg["faultpolygons"]

        if zname is not None and zname in config["plotsettings"][pname]:

            zfg = config["plotsettings"][pname][zname]

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

    subtitle = None
    if "_filterinfo" in config and config["_filterinfo"]:
        subtitle = config["_filterinfo"]

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
