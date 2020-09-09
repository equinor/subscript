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

# Heavy need for reprogramming...:
# pylint: disable=logging-format-interpolation
# pylint: disable=too-many-statements
# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
# pylint: disable=too-many-nested-blocks


def files_to_import(config, appname):
    """Get a list of files to import, based on config"""

    folderroot = None
    if "folderroot" in config["input"]:
        if config["input"]["folderroot"] is not None:
            folderroot = config["input"]["folderroot"]

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

    if appname == "grid3d_hc_thickness":

        if config["computesettings"]["mode"] == "rock":
            return gfile, initlist, restartlist, dates

        if "xhcpv" in config["input"]:
            initlist["xhcpv"] = config["input"]["xhcpv"]

        else:
            initlist["PORO"] = eclroot + ".INIT"
            initlist["NTG"] = eclroot + ".INIT"
            initlist["PORV"] = eclroot + ".INIT"
            initlist["DX"] = eclroot + ".INIT"
            initlist["DY"] = eclroot + ".INIT"
            initlist["DZ"] = eclroot + ".INIT"
            if config["computesettings"]["critmode"]:
                crname = config["computesettings"]["critmode"].upper()
                initlist[crname] = eclroot + ".INIT"

            restartlist["SWAT"] = eclroot + ".UNRST"
            restartlist["SGAS"] = eclroot + ".UNRST"

            for date in config["input"]["dates"]:
                if len(date) == 8:
                    dates.append(date)
                elif len(date) > 12:
                    dates.append(date.split("-")[0])
                    dates.append(date.split("-")[1])

    if appname == "grid3d_average_map":

        # Put things in initlist or restart list. Only Eclipse
        # UNRST comes in the restartlist, all other in the initlist.
        # For instance, a ROFF parameter PRESSURE_20110101 will
        # technically be an initlist parameter here

        logger.debug(config["input"])

        for item in config["input"]:
            if item == "folderroot":
                continue
            if item == "eclroot":
                continue
            elif item == "grid":
                gfile = config["input"]["grid"]
                if "$folderroot" in gfile:
                    gfile = gfile.replace("$folderroot", folderroot)
                if "$eclroot" in gfile:
                    gfile = gfile.replace("$eclroot", eclroot)
            else:
                if "UNRST" in config["input"][item]:
                    if "--" in item:
                        param = item.split("--")[0]
                        date = item.split("--")[1]

                    rfile = config["input"][item]
                    if "$folderroot" in rfile:
                        rfile = rfile.replace("$folderroot", folderroot)
                    if "$eclroot" in rfile:
                        rfile = rfile.replace("$eclroot", eclroot)
                    restartlist[param] = rfile
                    # dates:
                    if len(date) > 10:
                        dates.append(date.split("-")[0])
                        dates.append(date.split("-")[1])
                    else:
                        dates.append(date)

                else:
                    ifile = config["input"][item]
                    if "$folderroot" in ifile:
                        ifile = ifile.replace("$folderroot", folderroot)
                    if "$eclroot" in ifile:
                        ifile = ifile.replace("$eclroot", eclroot)
                    initlist[item] = ifile

        logger.debug(dates)

    dates = list(sorted(set(dates)))  # to get a list with unique dates

    ppinit = pprint.PrettyPrinter(indent=4)
    pprestart = pprint.PrettyPrinter(indent=4)
    ppdates = pprint.PrettyPrinter(indent=4)

    logger.debug("Grid from %s", gfile)
    logger.debug("%s", ppinit.pformat(initlist))
    logger.debug("%s", pprestart.pformat(restartlist))
    logger.debug("%s", ppdates.pformat(dates))

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

    logger.info("Import data for %s", appname)
    logger.debug("Config is %s", config)

    # get the grid data + some geometrics
    grd = xtgeo.grid3d.Grid(gfile, fformat="guess")

    # For rock thickness only model, the initlist and restartlist will be
    # empty dicts, and just return at this point

    if not initlist and not restartlist:
        return grd, None, None, None

    # collect data per initfile etc: make a dict on the form:
    # {initfilename: [[prop1, lookfor1], [prop2, lookfor2], ...]} the
    # trick is defaultdict!
    #
    # The initfile itself may be a file or dictionary itself, e.g. either
    # SOME.INIT or {Name: somefile.roff}. In the latter, we should look for
    # Name in the file while doing the import.

    initdict = defaultdict(list)
    for ipar, ifile in initlist.items():

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
    logger.debug("\n%s", ppinitdict.pformat(initdict))

    restdict = defaultdict(list)
    for rpar, rfile in restartlist.items():
        logger.info("Parameter RESTART: %s \t file is %s", rpar, rfile)
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

        except DateNotFoundError as rwarn:
            logger.info("Got warning... %s", rwarn)
            for prop in tmp.props:
                logger.info("Append prop: {}".format(prop))
                restobjects.append(prop)
        except KeywordFoundNoDateError as rwarn:
            logger.info("Keyword found but not for this date %s", rwarn)
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

    logger.debug("The initiobjects and restobjects: %s %s", initobjects, restobjects)

    return grd, initobjects, restobjects, newdateslist


def import_filters(config, appname, grd):
    """Get the filterdata, and process them, return a filterarray

    If no filters are active, the filterarray will be 1 for all cells.

    Args:
        config(dict): Th configuration dictionary
        appname(str): Name of application
        grd (Grid): The XTGeo Grid obejct

    Returns:
        filterarray (ndarray): A 3D numpy array with 0 and 1 to be used as
            a multiplier.

    """

    eclroot = config["input"].get("eclroot")

    logger.info("Import filter data for %s", appname)

    filterarray = np.ones(grd.dimensions, dtype="int")

    filterinfo = ""

    if "filters" not in config or not isinstance(config["filters"], list):
        config["_filterinfo"] = filterinfo  # perhaps not best practice...
        return filterarray

    for flist in config["filters"]:

        if "name" in flist:
            name = flist["name"]
            logger.info("Filter name: %s", name)
            source = flist["source"]
            drange = flist.get("discrange", None)

            # drange may either be a list or a dict (or None):
            if isinstance(drange, dict):
                drangetxt = list(drange.values())
                drange = list(drange.keys())
            elif isinstance(drange, list):
                drangetxt = [val for val in drange]

            irange = flist.get("intvrange", None)
            discrete = flist.get("discrete", False)
            filterinfo = filterinfo + "  " + name

            if "$eclroot" in source:
                source = source.replace("$eclroot", eclroot)
            gprop = GridProperty(source, grid=grd, name=name)
            pval = gprop.values
            xtg.say("Filter, import <{}> from <{}> ...".format(name, source))

            if not discrete:
                filterarray[(pval < irange[0]) | (pval > irange[1])] = 0
                filterinfo = filterinfo + ":" + str(irange)
            else:
                # discrete variables can both be a range and discrete choice
                # i.e. intvrange vs discrange
                invarray = np.zeros(grd.dimensions, dtype="int")
                if drange and irange is None:
                    filterinfo = filterinfo + ":" + str(drangetxt)
                    for ival in drange:
                        if ival not in gprop.codes.keys():
                            xtg.warn(
                                "Filter codevalue {} is not present in "
                                "discrete property {}".format(ival, gprop.name)
                            )

                        invarray[pval == ival] = 1
                elif drange is None and irange:
                    filterinfo = filterinfo + ":" + str(irange)
                    invarray[(pval >= irange[0]) & (pval <= irange[1])] = 1
                else:
                    raise ValueError(
                        'Either "discrange" OR "intvrange" must ',
                        "be defined in input (not both)",
                    )

                filterarray[invarray == 0] = 0

        if "tvdrange" in flist:
            tvdrange = flist["tvdrange"]
            _xc, _yc, zc = grd.get_xyz(asmasked=False)
            filterinfo = filterinfo + "  " + "tvdrange: {}".format(tvdrange)

            filterarray[zc.values < tvdrange[0]] = 0
            filterarray[zc.values > tvdrange[1]] = 0
            xtg.say(
                "Filter on tdvrange {} (rough; based on cell center)".format(tvdrange)
            )

    config["_filterinfo"] = filterinfo  # perhaps not best practice...

    return filterarray


def get_numpies_hc_thickness(config, grd, initobjects, restobjects, dates):
    """Process for HC thickness map; to get the needed numpies"""

    logger.info("Getting numpies...")

    logger.info("Getting actnum...")
    actnum = grd.get_actnum().values3d
    logger.info("Got actnum...")
    actnum = ma.filled(actnum)
    logger.info("Ran ma.filled for actnum")
    # mask is False  to get values for all cells, also inactive

    logger.info("Getting xc, yc, zc...")
    xc, yc, zc = grd.get_xyz(asmasked=False)
    xc = ma.filled(xc.values3d)
    yc = ma.filled(yc.values3d)
    zc = ma.filled(zc.values3d)

    logger.info("Getting dz...")
    dz = ma.filled(grd.get_dz(asmasked=False).values3d)
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

    if config["computesettings"]["critmode"]:
        crname = config["computesettings"]["critmode"].upper()
    else:
        crname = None

    xmode = config["computesettings"]["mode"]
    xmethod = config["computesettings"]["method"]
    xinput = config["input"]

    if "rock" in xmode:
        return initd, None

    if "xhcpv" in xinput:
        xhcpv = ma.filled(initobjects[0].values3d, fill_value=0.0)
        xhcpv[actnum == 0] = 0.0
        initd.update({"xhcpv": xhcpv})

    else:

        if xmethod == "use_poro" or xmethod == "use_porv":
            # initobjects is a list of GridProperty objects (single)
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
                if crname is not None and prop.name == crname:
                    soxcr = ma.filled(prop.values3d, fill_value=0.0)

            porv[actnum == 0] = 0.0
            poro[actnum == 0] = 0.0
            ntg[actnum == 0] = 0.0
            dz[actnum == 0] = 0.0

            initd.update(
                {"porv": porv, "poro": poro, "ntg": ntg, "dx": dx, "dy": dy, "dz": dz}
            )

            if crname is not None:
                initd["soxcr"] = soxcr
            else:
                initd["soxcr"] = None

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

                if crname is not None:
                    soil[date] = soil[date] - soxcr

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


def get_numpies_avgprops(config, grd, initobjects, restobjects, dates):
    """Process for average map; to get the needed numpies"""

    actnum = grd.get_actnum().get_npvalues3d(fill_value=0)
    # mask is False  to get values for all cells, also inactive
    xc, yc, zc = grd.get_xyz(asmasked=False)
    xc = xc.get_npvalues3d()
    yc = yc.get_npvalues3d()
    zc = zc.get_npvalues3d()
    dz = grd.get_dz(asmasked=False).get_npvalues3d()

    dz[actnum == 0] = 0.0

    # store these in a dict for special data (specd):
    specd = {"idz": dz, "ixc": xc, "iyc": yc, "izc": zc, "iactnum": actnum}

    if initobjects is not None:
        for prop in initobjects:
            logger.debug("INIT PROP name {}".format(prop.name))

    if restobjects is not None:
        for prop in restobjects:
            logger.debug("REST PROP name {}".format(prop.name))

    if initobjects is not None and restobjects is not None:
        groupobjects = initobjects + restobjects
    elif initobjects is None and restobjects is not None:
        groupobjects = restobjects
    elif initobjects is not None and restobjects is None:
        groupobjects = initobjects
    else:
        raise ValueError("Both initiobjects and restobjects are None")

    propd = {}

    for pname in config["input"]:
        usepname = pname
        if pname in set(["folderroot", "eclroot", "grid"]):
            continue

        # initdata may also contain date if ROFF is input!
        if "--" in pname:
            name = pname.split("--")[0]
            date = pname.split("--")[1]

            # treating difference values
            if "-" in date:
                date1 = date.split("-")[0]
                date2 = date.split("-")[1]

                usepname1 = name + "_" + date1
                usepname2 = name + "_" + date2

                ok1 = False
                ok2 = False

                for prop in groupobjects:
                    if usepname1 == prop.name:
                        ptmp1 = prop.get_npvalues3d()
                        ok1 = True
                    if usepname2 == prop.name:
                        ptmp2 = prop.get_npvalues3d()
                        ok2 = True

                    if ok1 and ok2:
                        ptmp = ptmp1 - ptmp2
                        propd[pname] = ptmp
                        logger.debug("DIFF were made: {}".format(pname))

            # only one date
            else:
                for prop in groupobjects:
                    usepname = pname.replace("--", "_")
                    if usepname == prop.name:
                        ptmp = prop.get_npvalues3d()
                        propd[pname] = ptmp

        # no dates
        else:
            for prop in groupobjects:
                if usepname == prop.name:
                    ptmp = prop.get_npvalues3d()
                    propd[pname] = ptmp

    logger.info("Return specd from {} is {}".format(__name__, specd.keys()))
    logger.info("Return propd from {} is {}".format(__name__, propd.keys()))
    return specd, propd
