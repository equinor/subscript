# -*- coding: utf-8 -*-

from __future__ import division, print_function, absolute_import

import argparse
import sys
import os.path
import yaml
import pprint
import copy
import datetime

from xtgeo.common import XTGeoDialog
from xtgeoapp_grd3dmaps.avghc._loader import YamlXLoader, ConstructorError

xtg = XTGeoDialog()

logger = xtg.functionlogger(__name__)


def parse_args(args, appname, appdescr):

    if args is None:
        args = sys.argv[1:]
    else:
        args = args

    usetxt = appname + " --config some.yaml ... "

    parser = argparse.ArgumentParser(description=appdescr, usage=usetxt)

    parser.add_argument(
        "-c",
        "--config",
        dest="config",
        type=str,
        required=True,
        help="Config file on YAML format (required)",
    )

    parser.add_argument(
        "-f",
        "--folderroot",
        dest="folderroot",
        type=str,
        help="Folder root name for inputdata",
    )

    parser.add_argument(
        "-e",
        "--eclroot",
        dest="eclroot",
        type=str,
        help="Eclipse root name (includes case name)",
    )

    parser.add_argument(
        "--mapfolder", dest="mapfolder", type=str, help="Name of map output root"
    )

    parser.add_argument(
        "--plotfolder",
        dest="plotfolder",
        type=str,
        default=None,
        help="Name of plot output root",
    )

    parser.add_argument(
        "--zfile", dest="zfile", type=str, help="Explicit file (YAML) for zonation"
    )

    parser.add_argument(
        "--dump",
        dest="dumpfile",
        type=str,
        help="Dump the parsed config to a file (for qc)",
    )

    parser.add_argument(
        "--legacydateformat",
        dest="legacydateformat",
        action="store_true",
        help="Flag for legacy dateformat in output file "
        "names, such as 1991_01_01 instead of 19910101",
    )

    if appname == "grid3d_hc_thickness":

        parser.add_argument(
            "-d",
            "--dates",
            dest="dates",
            nargs="+",
            type=int,
            default=None,
            help="A list of dates on YYYYMMDD format",
        )

        parser.add_argument(
            "-m", "--mode", dest="mode", type=str, default=None, help="oil, gas or comb"
        )

    if len(args) < 2:
        parser.print_help()
        print("QUIT")
        raise SystemExit

    args = parser.parse_args(args)

    logger.debug("Command line args: ")
    for arg in vars(args):
        logger.debug("{}  {}".format(arg, getattr(args, arg)))

    return args


# =============================================================================
# YAML config
# =============================================================================


def yconfig(inputfile, tmp=False, standard=False):
    """Read from YAML file, returns a dictionary."""

    if not os.path.isfile(inputfile):
        logger.critical("STOP! No such config file exists: {}".format(inputfile))
        raise SystemExit

    with open(inputfile, "r") as stream:
        if standard:
            config = yaml.load(stream)
        else:
            try:
                config = yaml.load(stream, Loader=YamlXLoader)
            except ConstructorError as errmsg:
                xtg.error(errmsg)
                raise SystemExit

    xtg.say("Input config YAML file <{}> is read...".format(inputfile))

    pp = pprint.PrettyPrinter(indent=4)

    out = pp.pformat(config)
    logger.info("\n%s", out)

    logger.info("CONFIG:\n {}".format(config))

    # if the file is a temporary file, delete:
    if tmp:
        os.remove(inputfile)

    return config


def yconfigdump(cfg, outfile):
    """Write a dictionary (config) to YAML file."""

    with open(outfile, "w") as stream:
        yaml.dump(cfg, stream, default_flow_style=False)


def dateformatting(config):
    """Special processing of dates.

    The issue is to treat dates both flexible and backward compatible.

    Example on the 'implemented' format:
        dates:
          - 19991201
          - 20010101-19991201

    The 'alternative' format; implicit the case if include from master YAML:
        dates:
          - 1999-02-01  # as datetime.date object!
        diffdates:
          - [2001-01-01, 1999-02-01]  # as list with 2 datetime.date objects!

    The 'alternative' form will be converted to the 'implemented' form here.

    """

    newconfig = copy.deepcopy(config)

    if "input" not in config:
        return newconfig

    newdates = list()
    update = False

    if "dates" in config["input"]:
        update = True
        for entry in config["input"]["dates"]:
            if isinstance(entry, datetime.date):
                newdates.append(entry.strftime("%Y%m%d"))
            else:
                newdates.append(entry)

        del newconfig["input"]["dates"]

    if "diffdates" in config["input"]:
        update = True
        for entry in config["input"]["diffdates"]:
            if isinstance(entry, list) and len(entry) == 2:
                dd1, dd2 = entry
                if isinstance(dd1, datetime.date):
                    dd1 = dd1.strftime("%Y%m%d")
                if isinstance(dd2, datetime.date):
                    dd2 = dd2.strftime("%Y%m%d")
                newdates.append(dd1 + "-" + dd2)
        del newconfig["input"]["diffdates"]

    if update:
        newconfig["input"]["dates"] = []
        newconfig["input"]["dates"].extend(newdates)

    return newconfig


def propformatting(config):
    """Special processing of 'properties' list if present in input.

    This applies to the average script.

    Example on the 'implemented' format::

       PORO: $eclroot.INIT
       PRESSURE--19991201: $eclroot.UNRST
       PRESSURE--20030101-19991201: $eclroot.UNRST

    The 'alternative' format; implicit the case if include from master YAML::

       properties:
         -
           name: PORO
           source: $eclroot.INIT
         -
           name: PRESSURE
           source: $eclroot.UNRST
           dates: !include_from global_config3a.yml::global.DATES
           diffdates: !include_from global_config3a.yml::global.DIFFDATES

    The 'alternative' form will be converted to the 'implemented' form here.

    """

    newconfig = copy.deepcopy(config)

    if "input" not in config or "properties" not in config["input"]:
        return newconfig

    for prop in config["input"]["properties"]:
        if "name" not in prop:
            raise KeyError('The "name" key is required in "properties"')
        if "source" not in prop:
            raise KeyError('The "source" key is required in "properties"')

        newdates = list()
        if "dates" in prop:
            for entry in prop["dates"]:
                if isinstance(entry, datetime.date):
                    newdates.append(entry.strftime("%Y%m%d"))
                else:
                    newdates.append(entry)

        if "diffdates" in prop:
            for entry in prop["diffdates"]:
                if isinstance(entry, list) and len(entry) == 2:
                    dd1, dd2 = entry
                    if isinstance(dd1, datetime.date):
                        dd1 = dd1.strftime("%Y%m%d")
                    if isinstance(dd2, datetime.date):
                        dd2 = dd2.strftime("%Y%m%d")
                    newdates.append(dd1 + "-" + dd2)

        if newdates:
            for mydate in newdates:
                newkey = prop["name"] + "--" + mydate
                newconfig["input"][newkey] = prop["source"]
        else:
            newconfig["input"][prop["name"]] = prop["source"]

    del newconfig["input"]["properties"]

    return newconfig


def yconfig_override(config, args, appname):
    """Override the YAML config with command line options"""

    newconfig = copy.deepcopy(config)

    if args.eclroot:
        newconfig["input"]["eclroot"] = args.eclroot
        xtg.say(
            "YAML config overruled... eclroot is now: <{}>".format(
                newconfig["input"]["eclroot"]
            )
        )

    if args.folderroot:
        newconfig["input"]["folderroot"] = args.folderroot
        xtg.say(
            "YAML config overruled... folderroot is now: <{}>".format(
                newconfig["input"]["folderroot"]
            )
        )

    if args.zfile:
        newconfig["zonation"]["yamlfile"] = args.zfile
        xtg.say(
            "YAML config overruled... zfile (yaml) is now: <{}>".format(
                newconfig["zonation"]["yamlfile"]
            )
        )

    if args.mapfolder:
        newconfig["output"]["mapfolder"] = args.mapfolder
        xtg.say(
            "YAML config overruled... output:mapfolder is now: <{}>".format(
                newconfig["output"]["mapfolder"]
            )
        )

    if args.plotfolder:
        newconfig["output"]["plotfolder"] = args.plotfolder
        xtg.say(
            "YAML config overruled... output:plotfolder is now: <{}>".format(
                newconfig["output"]["plotfolder"]
            )
        )

    if args.legacydateformat:
        newconfig["output"]["legacydateformat"] = args.legacydateformat

    if appname == "grid3d_hc_thickness":

        if args.dates:
            newconfig["input"]["dates"] = args.dates
            logger.debug(
                "YAML config overruled by cmd line: dates are now {}".format(
                    newconfig["eclinput"]["dates"]
                )
            )

    pp = pprint.PrettyPrinter(indent=4)
    out = pp.pformat(newconfig)
    logger.debug("After override: \n{}".format(out))

    return newconfig


def yconfig_set_defaults(config, appname):
    """Override the YAML config with defaults where missing input."""

    newconfig = copy.deepcopy(config)

    # some defaults if data is missing...
    if "title" not in newconfig:
        newconfig["title"] = "SomeField"

    if "computesettings" not in newconfig:
        newconfig["computesettings"] = dict()

    if "plotsettings" not in newconfig:
        newconfig["plotsettings"] = dict()

    if "zonation" not in newconfig:
        newconfig["zonation"] = dict()

    if "mapsettings" not in newconfig:
        newconfig["mapsettings"] = None

    if "mapfile" not in newconfig["output"]:
        newconfig["output"]["mapfile"] = "hc_thickness"

    if "plotfile" not in newconfig["output"]:
        newconfig["output"]["plotfile"] = None

    if "legacydateformat" not in newconfig["output"]:
        newconfig["output"]["legacydateformat"] = False

    if "tuning" not in newconfig["computesettings"]:
        newconfig["computesettings"]["tuning"] = dict()

    if "mask_zeros" not in newconfig["computesettings"]:
        newconfig["computesettings"]["mask_zeros"] = False

    if "mapfolder" not in newconfig["output"]:
        newconfig["output"]["mapfolder"] = "/tmp"

    if "plotfolder" not in newconfig["output"]:
        newconfig["output"]["plotfolder"] = None

    if "tag" not in newconfig["output"]:
        newconfig["output"]["tag"] = None

    if "prefix" not in newconfig["output"]:
        newconfig["output"]["prefix"] = None

    if "lowercase" not in newconfig["output"]:
        newconfig["output"]["lowercase"] = True

    if "zname" not in newconfig["zonation"]:
        newconfig["zonation"]["zname"] = "all"

    if "yamlfile" not in newconfig["zonation"]:
        newconfig["zonation"]["yamlfile"] = None

    if "zonefile" not in newconfig["zonation"]:
        newconfig["zonation"]["zonefile"] = None

    if "zone_avg" not in newconfig["computesettings"]["tuning"]:
        newconfig["computesettings"]["tuning"]["zone_avg"] = False

    if "coarsen" not in newconfig["computesettings"]["tuning"]:
        newconfig["computesettings"]["tuning"]["coarsen"] = 1

    if appname == "grid3d_hc_thickness":

        if "dates" not in newconfig["input"]:
            if newconfig["computesettings"]["mode"] in ("rock"):
                xtg.say('No date give, probably OK since "rock" mode)')
            else:
                xtg.warn('Warning: No date given, set date to "unknowndate")')

            newconfig["input"]["dates"] = ["unknowndate"]

        if "mode" not in newconfig["computesettings"]:
            newconfig["computesettings"]["mode"] = "oil"

        if "method" not in newconfig["computesettings"]:
            newconfig["computesettings"]["method"] = "use_poro"

        if "mask_outside" not in newconfig["computesettings"]:
            newconfig["computesettings"]["mask_outside"] = False

        if "shc_interval" not in newconfig["computesettings"]:
            newconfig["computesettings"]["shc_interval"] = [0.0001, 1.0]

        if "critmode" not in newconfig["computesettings"]:
            newconfig["computesettings"]["critmode"] = None

        if newconfig["computesettings"]["critmode"] is False:
            newconfig["computesettings"]["critmode"] = None

        if "zone" not in newconfig["computesettings"]:
            newconfig["computesettings"]["zone"] = False

        if "all" not in newconfig["computesettings"]:
            newconfig["computesettings"]["all"] = True

        # be generic if direct calculation is applied
        xlist = set(["stooip", "goip", "hcpv", "stoiip", "giip"])
        for xword in xlist:
            if xword in newconfig["input"]:
                newconfig["input"]["xhcpv"] = newconfig["input"][xword]
                break

    # treat dates as strings, not ints
    if "dates" in config["input"]:
        dlist = []
        for date in config["input"]["dates"]:
            dlist.append(str(date))

        newconfig["input"]["dates"] = dlist

    pp = pprint.PrettyPrinter(indent=4)
    out = pp.pformat(newconfig)
    logger.debug("After setting defaults: \n{}".format(out))

    return newconfig


def yconfig_addons(config, appname):
    """Addons e.g. YAML import spesified in the top config."""

    newconfig = copy.deepcopy(config)

    if config["zonation"]["yamlfile"] is not None:

        # re-use yconfig:
        zconfig = yconfig(config["zonation"]["yamlfile"])
        if "zranges" in zconfig:
            newconfig["zonation"]["zranges"] = zconfig["zranges"]
        if "superranges" in zconfig:
            newconfig["zonation"]["superranges"] = zconfig["superranges"]

    return newconfig
