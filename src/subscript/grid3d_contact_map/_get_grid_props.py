# -*- coding: utf-8 -*-

from __future__ import division, print_function, absolute_import

import pprint
from collections import defaultdict
import numpy as np
import numpy.ma as ma

import xtgeo
from xtgeo.common.exceptions import DateNotFoundError
from xtgeo.common.exceptions import KeywordFoundNoDateError

# from xtgeo.common.exceptions import KeywordNotFoundError
from xtgeo.common import XTGeoDialog
from xtgeo.grid3d import GridProperties
from xtgeo.grid3d import GridProperty

xtg = XTGeoDialog()

logger = xtg.functionlogger(__name__)


def files_to_import(config, appname):
    """Get a list of files to import, based on config"""

    eclroot = None
    if "eclroot" in config["input"]:
        if config["input"]["eclroot"] is not None:
            eclroot = config["input"]["eclroot"]

    gfile = ""
    initlist = dict()
    restartlist = dict()
    dates = []

    if eclroot:
        gfile = eclroot + ".EGRID"

    if "grid" in config["input"]:
        gfile = config["input"]["grid"]

    else:
        initlist["PORO"] = eclroot + ".INIT"
        initlist["NTG"] = eclroot + ".INIT"
        initlist["PORV"] = eclroot + ".INIT"

        restartlist["SWAT"] = eclroot + ".UNRST"
        restartlist["SGAS"] = eclroot + ".UNRST"

        for date in config["input"]["dates"]:
            logger.debug("DATE {}".format(date))
            if len(date) == 8:
                dates.append(date)
            elif len(date) > 12:
                dates.append(date.split("-")[0])
                dates.append(date.split("-")[1])

    dates = list(sorted(set(dates)))  # to get a list with unique dates

    ppinit = pprint.PrettyPrinter(indent=4)
    pprestart = pprint.PrettyPrinter(indent=4)
    ppdates = pprint.PrettyPrinter(indent=4)

    logger.debug("Grid from {}".format(gfile))
    logger.debug("{}".format(ppinit.pformat(initlist)))
    logger.debug("{}".format(pprestart.pformat(restartlist)))
    logger.debug("{}".format(ppdates.pformat(dates)))

    return gfile, initlist, restartlist, dates


def import_data(config, appname, gfile, initlist, restartlist, dates):
    """Get the grid and the props data.
    Well get the grid and the propsdata for data to be plotted,
    zonation (if required), filters (if required)

    Will return data on appropriate format...

    Args:
        config(dict): Th configuration dictionary
        appname(str): Name of application

    """

    logger.info("Import data for {}".format(appname))

    # get the grid data + some geometrics
    grd = xtgeo.grid3d.Grid(gfile, fformat="guess")

    logger.info("Grid is now imported for {}".format(appname))

    # collect data per initfile etc: make a dict on the form:
    # {initfilename: [[prop1, lookfor1], [prop2, lookfor2], ...]} the
    # trick is defaultdict!
    #
    # The initfile itself may be a file or dictionary itself, e.g. either
    # SOME.INIT or {Name: somefile.roff}. In the latter, we should look for
    # Name in the file while doing the import.

    initdict = defaultdict(list)
    for ipar, ifile in initlist.items():
        logger.info("Parameter INIT: {} \t file is {}".format(ipar, ifile))
        if isinstance(ifile, dict):
            lookfor, usefile = list(ifile.keys()), list(ifile.values())
            initdict[usefile[0]].append([ipar, lookfor[0]])
        else:
            lookfor = ipar

            # if just a name: file.roff, than the name here and name in
            # the file may not match. So here it is assumed that "lookfor"
            # shall be 'unknown'

            if ifile.endswith(".roff"):
                lookfor = "unknown"

            initdict[ifile].append([ipar, lookfor])

    ppinitdict = pprint.PrettyPrinter(indent=4)
    logger.debug("\n{}".format(ppinitdict.pformat(initdict)))

    restdict = defaultdict(list)
    for rpar, rfile in restartlist.items():
        logger.info("Parameter RESTART: {} \t file is {}".format(rpar, rfile))
        restdict[rfile].append(rpar)

    pprestdict = pprint.PrettyPrinter(indent=4)
    logger.debug("\n{}".format(pprestdict.pformat(restdict)))

    initobjects = []
    for inifile, iniprops in initdict.items():
        if len(iniprops) > 1:
            tmp = GridProperties()
            lookfornames = []
            usenames = []
            for iniprop in iniprops:
                usename, lookforname = iniprop
                lookfornames.append(lookforname)
                usenames.append(usename)

            xtg.say("Import <{}> from <{}> ...".format(lookfornames, inifile))
            tmp.from_file(inifile, names=lookfornames, fformat="init", grid=grd)
            for i, name in enumerate(lookfornames):
                prop = tmp.get_prop_by_name(name)
                prop.name = usenames[i]  # rename if different
                initobjects.append(prop)

        else:
            # single properties, typically ROFF stuff
            tmp = GridProperty()
            usename, lookforname = iniprops[0]

            xtg.say("Import <{}> from <{}> ...".format(lookforname, inifile))
            tmp.from_file(inifile, name=lookforname, fformat="guess", grid=grd)
            tmp.name = usename
            initobjects.append(tmp)

    logger.info("Init type data is now imported for {}".format(appname))

    # restarts; will issue an warning if one or more dates are not found
    # assume that this is Eclipse stuff .UNRST
    restobjects = []
    for restfile, restprops in restdict.items():
        tmp = GridProperties()
        try:
            logger.info("Reading--")
            tmp.from_file(
                restfile, names=restprops, fformat="unrst", grid=grd, dates=dates
            )

        except DateNotFoundError:
            logger.info("Got warning...")
            for prop in tmp.props:
                logger.info("Append prop: {}".format(prop))
                restobjects.append(prop)
        except KeywordFoundNoDateError as rwarn:
            logger.info("Keyword found but not for this date {}".format(rwarn))
            raise SystemExit("STOP")
        except Exception as message:
            raise SystemExit(message)
        else:
            logger.info("Works further...")
            for prop in tmp.props:
                logger.info("Append prop: {}".format(prop))
                restobjects.append(prop)

    logger.info("Restart type data is now imported for {}".format(appname))

    newdateslist = []
    for rest in restobjects:
        newdateslist.append(rest.date)

    newdateslist = list(set(newdateslist))
    logger.info("Actual dates to use: {}".format(newdateslist))

    for obj in initobjects:
        logger.info("Init object for <{}> is <{}> ".format(obj.name, obj))

    for obj in restobjects:
        logger.info("Restart object for <{}> is <{}> ".format(obj.name, obj))

    logger.info("Routine at end")

    return grd, initobjects, restobjects, newdateslist


def get_numpies_contact(config, grd, initobjects, restobjects, dates):
    """Process for contact script; to get the needed numpies"""

    logger.info("Getting numpies...")

    logger.info("Getting actnum...")
    actnum = grd.get_actnum().values3d
    logger.info("Got actnum...")
    actnum = ma.filled(actnum)
    logger.info("Ran ma.filled for actnum")
    # mask is False  to get values for all cells, also inactive

    logger.info("Getting xc, yc, zc...")
    xc, yc, zc = grd.get_xyz(mask=False)
    xc = ma.filled(xc.values3d)
    yc = ma.filled(yc.values3d)
    zc = ma.filled(zc.values3d)

    logger.info("Getting dz...")
    dz = ma.filled(grd.get_dz(mask=False).values3d)
    logger.info("Getting dz as ma.filled...")
    dz[actnum == 0] = 0.0
    logger.info("dz = 0 of actnum is 0 ...")

    logger.info("Getting dx dy...")
    dx, dy = grd.get_dxdy()
    dx = ma.filled(dx.values3d)
    dy = ma.filled(dy.values3d)
    logger.info("ma.filled for dx dy done")

    initd = {
        "iactnum": actnum,
        "xc": xc,
        "yc": yc,
        "zc": zc,
        "dx": dx,
        "dy": dy,
        "dz": dz,
    }

    logger.info("Got {}".format(initd.keys()))

    for prop in initobjects:
        if prop.name == "PORO":
            poro = ma.filled(prop.values3d, fill_value=0.0)
        if prop.name == "NTG":
            ntg = ma.filled(prop.values3d, fill_value=0.0)
        if prop.name == "PORV":
            porv = ma.filled(prop.values3d, fill_value=0.0)
        if prop.name == "DX":
            dx = ma.filled(prop.values3d, fill_value=0.0)
        if prop.name == "DY":
            dy = ma.filled(prop.values3d, fill_value=0.0)
        if prop.name == "DZ":
            dz = ma.filled(prop.values3d, fill_value=0.0)

    porv[actnum == 0] = 0.0
    poro[actnum == 0] = 0.0
    ntg[actnum == 0] = 0.0
    dz[actnum == 0] = 0.0

    initd.update({"porv": porv, "poro": poro, "ntg": ntg, "dx": dx, "dy": dy, "dz": dz})

    xtg.say("Got relevant INIT numpies, OK ...")

    # restart data, they have alos a date component:

    restartd = {}

    sgas = dict()
    swat = dict()
    soil = dict()

    for date in dates:
        nsoil = 0
        for prop in restobjects:
            pname = "SWAT" + "_" + str(date)
            if prop.name == pname:
                swat[date] = ma.filled(prop.values3d, fill_value=1)
                nsoil += 1

            pname = "SGAS" + "_" + str(date)
            if prop.name == pname:
                sgas[date] = ma.filled(prop.values3d, fill_value=1)
                nsoil += 1

            if nsoil == 2:
                soil[date] = np.ones(sgas[date].shape, dtype=sgas[date].dtype)
                soil[date] = soil[date] - swat[date] - sgas[date]

        logger.debug("Date is {} and  SWAT is {}".format(date, swat))
        logger.debug("Date is {} and  SGAS is {}".format(date, sgas))
        logger.debug("Date is {} and  SOIL is {}".format(date, soil))

        # numpy operations on the saturations
        for anp in [soil[date], sgas[date]]:
            anp[anp > 1.0] = 1.0
            anp[anp < 0.0] = 0.0
            anp[actnum == 0] = 0.0

        restartd["sgas_" + str(date)] = sgas[date]
        restartd["swat_" + str(date)] = swat[date]
        restartd["soil_" + str(date)] = soil[date]

    for key in initd:
        logger.debug("INITS: Key and object {} {}".format(key, type(initd[key])))

    for key in restartd:
        logger.debug("RESTARTS: Key and object {} {}".format(key, type(restartd[key])))

    return initd, restartd
