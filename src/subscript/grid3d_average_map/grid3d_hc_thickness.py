# -*- coding: utf-8 -*-

"""Script to make HC thickness maps directly from 3D grids.

A typical scenario is to create HC thickness maps directly from Eclipse
simulation files (or eventually other similators).

"""

from __future__ import division, print_function, absolute_import

import sys

from xtgeo.common import XTGeoDialog

from . import _configparser
from . import _get_grid_props
from . import _get_zonation_filters
from . import _compute_hcpfz
from . import _hc_plotmap
from . import _mapsettings

try:
    from ..theversion import version as __version__
except ImportError:
    __version__ = "0.0.0"

APPNAME = "grid3d_hc_thickness"

APPDESCR = (
    "Make HC thickness maps directly from 3D grids. Docs:\n"
    + "https://fmu-docs.equinor.com/docs/xtgeoapp-grd3dmaps/"
)

xtg = XTGeoDialog()

logger = xtg.basiclogger(__name__)


def do_parse_args(args):

    args = _configparser.parse_args(args, APPNAME, APPDESCR)

    return args


def yamlconfig(inputfile, args):
    """Read from YAML file and modify/override"""
    config = _configparser.yconfig(inputfile)
    config = _configparser.dateformatting(config)

    # override with command line args
    config = _configparser.yconfig_override(config, args, APPNAME)

    config = _configparser.yconfig_set_defaults(config, APPNAME)

    # in case of YAML input (e.g. zonation from file)
    config = _configparser.yconfig_addons(config, APPNAME)

    if args.dumpfile:
        _configparser.yconfigdump(config, args.dumpfile)

    return config


def get_grid_props_data(config):
    """Collect the relevant Grid and props data (but not do the import)."""

    gfile, initlist, restartlist, dates = _get_grid_props.files_to_import(
        config, APPNAME
    )

    xtg.say("Grid file is {}".format(gfile))

    if initlist:
        xtg.say("Getting INITIAL file data (as INIT or ROFF)")

        for initpar, initfile in initlist.items():
            logger.info("%s file is %s", initpar, initfile)

    if restartlist:
        xtg.say("Getting RESTART file data")
        for restpar, restfile in restartlist.items():
            logger.info("%s file is %s", restpar, restfile)

    xtg.say("Getting dates")
    for date in dates:
        logger.info("Date is %s", date)

    return gfile, initlist, restartlist, dates


def import_pdata(config, gfile, initlist, restartlist, dates):
    """Import the data, and represent datas as numpies"""

    grd, initobjects, restobjects, dates = _get_grid_props.import_data(
        config, APPNAME, gfile, initlist, restartlist, dates
    )
    # get the numpies
    initd, restartd = _get_grid_props.get_numpies_hc_thickness(
        config, grd, initobjects, restobjects, dates
    )

    # returns also dates since dates list may be updated after import

    return grd, initd, restartd, dates


def import_filters(config, grd):
    """Import the filter data properties, process and return a filter mask"""

    filter_mask = _get_grid_props.import_filters(config, APPNAME, grd)

    return filter_mask


def get_zranges(config, grd):
    """Get the zonation names and ranges based on the config file.

    The zonation input has several variants; this is processed
    here. The config['zonation']['zranges'] is a list like

        - Tarbert: [1, 10]
        - Ness: [11,13]

    Args:
        config (dict): The configuration dictionary
        grd (Grid): The XTGeo grid object

    Returns:
        A numpy zonation 3D array
    """
    zonation, zoned = _get_zonation_filters.zonation(config, grd)

    return zonation, zoned


def compute_hcpfz(config, initd, restartd, dates, hcmode, filterarray):

    hcpfzd = _compute_hcpfz.get_hcpfz(
        config, initd, restartd, dates, hcmode, filterarray
    )

    return hcpfzd


def plotmap(config, grd, initd, hcpfzd, zonation, zoned, hcmode, filtermean=None):
    """Do checks, mapping and plotting"""

    # check if values looks OK. Status flag:
    # 0: Seems

    if config["mapsettings"] is None:
        config = _mapsettings.estimate_mapsettings(config, grd)
    else:
        xtg.say("Check map settings vs grid...")
        status = _mapsettings.check_mapsettings(config, grd)
        if status >= 10:
            xtg.critical("STOP! Mapsettings defined is outside the 3D grid!")

    mapzd = _hc_plotmap.do_hc_mapping(config, initd, hcpfzd, zonation, zoned, hcmode)

    if config["output"]["plotfolder"] is not None:
        _hc_plotmap.do_hc_plotting(config, mapzd, hcmode, filtermean=filtermean)


def main(args=None):

    XTGeoDialog.print_xtgeo_header(APPNAME, __version__)

    xtg.say("Parse command line")
    args = do_parse_args(args)

    config = None
    if not args.config:
        xtg.error("Config file is missing")
        sys.exit(1)

    logger.debug("--config option is applied, reading YAML ...")

    # get the configurations
    xtg.say("Parse YAML file")
    config = yamlconfig(args.config, args)

    # get the files
    xtg.say("Collect files...")
    gfile, initlist, restartlist, dates = get_grid_props_data(config)

    # import data from files and return relevant numpies
    xtg.say("Import files...")
    grd, initd, restartd, dates = import_pdata(
        config, gfile, initlist, restartlist, dates
    )

    # get the filter array
    filterarray = import_filters(config, grd)
    logger.info("Filter mean value: %s", filterarray.mean())
    if filterarray.mean() < 1.0:
        xtg.say("Property filters are active")

    # Get the zonations
    xtg.say("Get zonation info")

    zonation, zoned = get_zranges(config, grd)

    if config["computesettings"]["mode"] == "both":
        hcmodelist = ["oil", "gas"]
    else:
        hcmodelist = [config["computesettings"]["mode"]]

    for hcmode in hcmodelist:

        xtg.say("Compute HCPFZ property for {}".format(hcmode))
        hcpfzd = compute_hcpfz(config, initd, restartd, dates, hcmode, filterarray)

        xtg.say("Do mapping...")
        plotmap(
            config,
            grd,
            initd,
            hcpfzd,
            zonation,
            zoned,
            hcmode,
            filtermean=filterarray.mean(),
        )


if __name__ == "__main__":
    main()
