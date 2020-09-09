# -*- coding: utf-8 -*-

"""Script to estimate contact maps directly from 3D grids."""

from __future__ import division, print_function, absolute_import

import sys

from xtgeo.common import XTGeoDialog

from xtgeoapp_grd3dmaps.avghc import _configparser
from xtgeoapp_grd3dmaps.contact import _get_grid_props
from xtgeoapp_grd3dmaps.avghc import _get_zonation_filters

try:
    from ..theversion import version as __version__
except ImportError:
    __version__ = "0.0.0"


appname = "grid3d_get_contact"

appdescr = (
    "Estimate contact maps directly from 3D grids. Docs:\n"
    + "https://fmu-docs.equinor.com/docs/xtgeoapp-grd3dmaps/"
)

xtg = XTGeoDialog()

logger = xtg.basiclogger(__name__)


def do_parse_args(args):

    args = _configparser.parse_args(args, appname, appdescr)

    return args


def yamlconfig(inputfile, args):
    """Read from YAML file and modify/override"""
    config = _configparser.yconfig(inputfile)

    # override with command line args
    config = _configparser.yconfig_override(config, args, appname)

    config = _configparser.yconfig_set_defaults(config, appname)

    # in case of YAML input (e.g. zonation from file)
    config = _configparser.yconfig_addons(config, appname)

    logger.info("Updated config: {}".format(config))
    for name, val in config.items():
        logger.info("{}".format(name))
        logger.info("{}".format(val))

    return config


def get_grid_props_data(config, appname):
    """Collect the relevant Grid and props data (but not do the import)."""

    gfile, initlist, restartlist, dates = _get_grid_props.files_to_import(
        config, appname
    )

    xtg.say("Grid file is {}".format(gfile))

    if len(initlist) > 0:
        xtg.say("Getting INITIAL file data (as INIT or ROFF)")

        for initpar, initfile in initlist.items():
            logger.info("{} file is {}".format(initpar, initfile))

    if len(restartlist) > 0:
        xtg.say("Getting RESTART file data")
        for restpar, restfile in restartlist.items():
            logger.info("{} file is {}".format(restpar, restfile))

    xtg.say("Getting dates")
    for date in dates:
        logger.info("Date is {}".format(date))

    return gfile, initlist, restartlist, dates


def import_pdata(config, appname, gfile, initlist, restartlist, dates):
    """Import the data, and represent datas as numpies"""

    grd, initobjects, restobjects, dates = _get_grid_props.import_data(
        config, appname, gfile, initlist, restartlist, dates
    )
    # get the numpies
    initd, restartd = _get_grid_props.get_numpies_contact(
        config, grd, initobjects, restobjects, dates
    )

    # returns also dates since dates list may be updated after import
    logger.info("Returning numpy dates")
    return grd, initd, restartd, dates


def get_zranges(config, grd):
    """Get the zonation names and ranges based on the config file.

    The zonation input has several variants; this is processed
    here. The config['zonation']['zranges'] is a list like

        - Tarbert: [1, 10]
        - Ness: [11,13]

    Args:
        config: The configuration dictionary
        grd (Grid): grid instance

    Returns:
        A numpy zonation 3D array
    """
    zonation, zoned = _get_zonation_filters.zonation(config, grd)

    return zonation, zoned


def compute_contact(config, initd, restartd, dates):
    """The contact here is .... ready for gridding??"""
    compute_contact.gridmap_contact(config, initd, restartd, dates)


#    return contact


# def plotmap(config, grd, initd, hcpfzd, zonation, zoned, hcmode):
#     """Do checks, mapping and plotting"""

#     # check if values looks OK. Status flag:
#     # 0: Seems

#     if config['mapsettings'] is None:
#         config = _mapsettings.estimate_mapsettings(config, grd)
#     else:
#         xtg.say('Check map settings vs grid...')
#         status = _mapsettings.check_mapsettings(config, grd)
#         if status >= 10:
#             xtg.critical('STOP! Mapsettings defined is outside the 3D grid!')

#     mapzd = _hc_plotmap.do_hc_mapping(config, initd, hcpfzd, zonation,
#                                       zoned, hcmode)

#     if config['output']['plotfolder'] is not None:
#         _hc_plotmap.do_hc_plotting(config, mapzd, hcmode)


def main(args=None):

    XTGeoDialog.print_xtgeo_header(appname, __version__)

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
    gfile, initlist, restartlist, dates = get_grid_props_data(config, appname)

    # import data from files and return releavnt numpies
    xtg.say("Import files...")
    grd, initd, restartd, dates = import_pdata(
        config, appname, gfile, initlist, restartlist, dates
    )

    # Get the zonations
    zonation, zoned = get_zranges(config, grd)

    xtg.say("Grid contact map...")
    compute_contact(config, initd, restartd, dates)

    # for hcmode in hcmodelist:

    #     xtg.say('Do mapping...')
    #     plotmap(config, grd, initd, hcpfzd, zonation, zoned, hcmode)


if __name__ == "__main__":
    main()
