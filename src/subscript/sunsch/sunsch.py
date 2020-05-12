"""
Tool for generating Eclipse Schedule files

This script was originally based on a library named sunbeam,
hence the name. Later, this library has been merged into opm-common
"""

import os
import datetime
import tempfile
import argparse
import yaml
import logging
import six

from opm.tools import TimeVector

import configsuite
from configsuite import types
from configsuite import MetaKeys as MK

logger = logging.getLogger(__name__)
logging.basicConfig()

SUPPORTED_DATEGRIDS = ["monthly", "yearly", "weekly", "biweekly", "bimonthly"]


@configsuite.validator_msg("Is dategrid a supported frequency")
def _is_valid_dategrid(dategrid):
    return dategrid in SUPPORTED_DATEGRIDS


@configsuite.validator_msg("Is filename an existing file")
def _is_existing_file(filename):
    return os.path.exists(filename)


@configsuite.transformation_msg("Convert V1 sunsch format to V2")
def _V1_content_to_V2(v1_config):
    """
    Process an incoming dictionary with sunsch configuration.

    If sunsch V1 format is detected, then transform to V2. If V2 format
    nothing happens.

    Validation (and convertion from mutable dict to immutable named_dict)
    happens later

    Beware: Exceptions in this function as a transformation service will
    be caught by ConfigSuite.

    Args:
        config (dict)

    Returns
        dict
    """
    v2_config = {}

    if "insert" in v1_config:
        v2_config["insert"] = []
        for insertstatement in v1_config["insert"]:
            if len(insertstatement) == 1:
                v2_config["insert"] += [remap_v1_insert_to_v2(insertstatement)]
            else:
                v2_config["insert"] += [insertstatement]
    v2_config["files"] = []
    if "init" in v1_config:
        v2_config["files"] += [v1_config["init"]]
    if "merge" in v1_config:
        # In V1, this can be both a list and a string
        if isinstance(v1_config["merge"], six.string_types):
            v2_config["files"] += [v1_config["merge"]]
        else:
            v2_config["files"] += v1_config["merge"]
    if "output" in v1_config:
        v2_config["output"] = v1_config["output"]
    if "startdate" in v1_config:
        v2_config["startdate"] = v1_config["startdate"]
    if "enddate" in v1_config:
        v2_config["enddate"] = v1_config["enddate"]
    if "refdate" in v1_config:
        v2_config["refdate"] = v1_config["refdate"]
    if "dategrid" in v1_config:
        v2_config["dategrid"] = v1_config["dategrid"]
    return v2_config


CONFIG_SCHEMA_V2 = {
    MK.Type: types.NamedDict,
    MK.Transformation: _V1_content_to_V2,
    MK.Content: {
        "files": {
            MK.Type: types.List,
            MK.Required: False,
            MK.Content: {
                MK.Item: {
                    MK.Type: types.String,
                    MK.ElementValidators: (_is_existing_file,),
                }
            },
        },
        "output": {MK.Type: types.String, MK.Required: False},
        "startdate": {MK.Type: types.Date, MK.Required: False},
        "refdate": {MK.Type: types.Date, MK.Required: False},
        "enddate": {MK.Type: types.Date, MK.Required: False},
        "dategrid": {
            MK.Type: types.String,
            MK.Required: False,
            MK.ElementValidators: (_is_valid_dategrid,),
        },
        "insert": {
            MK.Type: types.List,
            MK.Required: False,
            MK.Content: {
                MK.Item: {
                    MK.Type: types.NamedDict,
                    MK.Content: {
                        "date": {MK.Type: types.Date, MK.Required: False},
                        "filename": {
                            MK.Type: types.String,
                            MK.Required: False,
                            MK.ElementValidators: (_is_existing_file,),
                        },
                        "template": {
                            MK.Type: types.String,
                            MK.Required: False,
                            MK.ElementValidators: (_is_existing_file,),
                        },
                        "days": {MK.Type: types.Integer, MK.Required: False},
                        "string": {MK.Type: types.String, MK.Required: False},
                        "substitute": {
                            MK.Type: types.Dict,
                            MK.Required: False,
                            MK.Content: {
                                MK.Key: {MK.Type: types.String},
                                MK.Value: {MK.Type: types.Integer},
                            },
                        },
                    },
                }
            },
        },
    },
}

# This schema will be deprecated some day in the future.
# CONFIG_SCHEMA_V1 = {
#     MK.Type: types.NamedDict,
#     MK.Content: {
#         "init": {
#             MK.Type: types.String,
#             MK.ElementValidators: (_is_existing_file,),
#             MK.Required: False,
#         },
#         "output": {MK.Type: types.String, MK.Required: False},
#         "startdate": {MK.Type: types.Date, MK.Required: False},
#         "refdate": {MK.Type: types.Date, MK.Required: False},
#         "enddate": {MK.Type: types.Date, MK.Required: False},
#         "dategrid": {
#             MK.Type: types.String,
#             MK.Required: False,
#             MK.ElementValidators: (_is_valid_dategrid,),
#         },
#         "merge": {
#             # Code allows this to be of type string as well
#             # but that is not possible in configsuite.
#             MK.Type: types.List,
#             MK.Required: False,
#             MK.Content: {
#                 MK.Item: {
#                     MK.Type: types.String,
#                     MK.ElementValidators: (os.path.exists,),
#                 }
#             },
#         },
#         "insert": {
#             MK.Type: types.List,
#             MK.Required: False,
#             MK.Content: {
#                 MK.Item: {
#                     MK.Type: types.Dict,
#                     # In v1 config, this dict always has only one element, random key
#                     MK.Content: {
#                         MK.Key: {MK.Type: types.String},
#                         MK.Value: {
#                             MK.Type: types.NamedDict,
#                             MK.Content: {
#                                 "date": {MK.Type: types.Date, MK.Required: False},
#                                 "filename": {
#                                     MK.Type: types.String,
#                                     MK.Required: False,
#                                     MK.ElementValidators: (_is_existing_file,),
#                                 },
#                                 "days": {MK.Type: types.Integer, MK.Required: False},
#                                 "string": {MK.Type: types.String, MK.Required: False},
#                                 "substitute": {
#                                     MK.Type: types.Dict,
#                                     MK.Required: False,
#                                     MK.Content: {
#                                         MK.Key: {MK.Type: types.String},
#                                         MK.Value: {MK.Type: types.Integer},
#                                     },
#                                 },
#                             },
#                         },
#                     },
#                 }
#             },
#         },
#     },
# }


def datetime_from_date(date):
    """Set time to 00:00:00 in a date"""
    if isinstance(date, six.string_types):
        raise ValueError("Is the string {} a date?".format(str(date)))
    return datetime.datetime.combine(date, datetime.datetime.min.time())


def process_sch_config(conf):
    """Process a Schedule configuration into a opm.tools TimeVector

    Assumes the configuration is valid, but this function will tolerate
    more than the configsuite configuration restricts the input to.

    Args:
        conf (dict or named_dict): Configuration dictionary for the schedule
            merges and inserts
    """

    # At least test code is calling this function with a dictionary with
    # config - convert it to a configsuite snapshot:
    if isinstance(conf, dict):
        conf = configsuite.ConfigSuite(conf, CONFIG_SCHEMA_V2).snapshot

    if conf.startdate is None:
        if conf.refdate:
            startdate = conf.refdate
        else:
            startdate = datetime.date(1900, 1, 1)
    else:
        startdate = conf.startdate

    if "starttime" not in conf:
        starttime = datetime_from_date(startdate)
    else:
        starttime = conf.starttime

    if "refdate" not in conf:
        refdate = conf.startdate
    else:
        refdate = conf.refdate

    # Initialize the opm.tools.TimeVector class, which needs
    # a date to anchor to:
    schedule = TimeVector(starttime)

    if conf.files is not None:
        for filename in conf.files:
            logger.info("Loading %s", filename)
            file_starts_with_dates = sch_file_starts_with_dates_keyword(filename)
            timevector = load_timevector_from_file(
                filename, startdate, file_starts_with_dates
            )
            if file_starts_with_dates:
                schedule.load_string(str(timevector))
            else:
                schedule.load_string(str(timevector), starttime)

    if conf.insert is not None:
        logger.info("Processing %s insert statements", str(len(conf.insert)))
        for insert_statement in conf.insert:
            logger.debug(str(insert_statement))

            if insert_statement.substitute and insert_statement.template:
                filename = substitute(insert_statement)
                logger.debug("Produced file: %s", str(filename))
            elif insert_statement.filename:
                filename = insert_statement.filename
            elif not insert_statement.string:
                logger.error("Invalid insert statement: %s", str(insert_statement))

            # Which date to use for insertion?
            if insert_statement.date:
                date = datetime_from_date(insert_statement.date)
            elif insert_statement.days:
                date = datetime_from_date(refdate) + datetime.timedelta(
                    days=insert_statement.days
                )
            else:
                logger.error("Could not determine date for insertion")
                logger.error("From data: %s", str(insert_statement))
                continue

            # Do the insertion:
            if date >= starttime:
                if insert_statement.string is None:
                    schedule.load(filename, date=date)
                else:
                    schedule.add_keywords(
                        datetime_from_date(date), [insert_statement.string]
                    )
            else:
                logger.warning("Ignoring inserts before startdate")

    if conf.enddate is None:
        enddate = schedule.dates[-1].date()
    else:
        enddate = conf.enddate  # datetime.date
        if not isinstance(enddate, datetime.date):
            raise TypeError(
                "ERROR: enddate {} not in ISO-8601 format, must be YYYY-MM-DD".format(
                    conf.enddate
                )
            )

    # Clip anything that is beyond the enddate
    for date in schedule.dates:
        if date.date() > enddate:
            schedule.delete(date)

    # Ensure that the end-date is actually mentioned in the Schedule
    # so that we know Eclipse will actually simulate until this date
    if enddate not in [x.date() for x in schedule.dates]:
        schedule.add_keywords(datetime_from_date(enddate), [""])

    # Dategrid is added at the end, in order to support
    # an implicit end-date
    if conf.dategrid:
        dates = dategrid(startdate, enddate, conf.dategrid)
        for date in dates:
            schedule.add_keywords(datetime_from_date(date), [""])

    return schedule


def load_timevector_from_file(filename, startdate, file_starts_with_dates):
    """
    Load a timevector from a file, and clip dates that are  earlier than startdate.

    When the file does not start with a DATES keyword, we will never
    delete whatever comes before the first DATES. But if the first DATES
    predates startdate, then we delete it.

    Returns:
        opm.tools.TimeVector
    """
    tmpschedule = TimeVector(datetime.date(1900, 1, 1))
    if file_starts_with_dates:
        tmpschedule.load(filename)
        early_dates = [date for date in tmpschedule.dates if date.date() < startdate]
        if len(early_dates) > 1:
            logger.info("Clipping away dates: " + str(early_dates[1:]))
            for date in early_dates:
                tmpschedule.delete(date)
    else:
        tmpschedule.load(filename, datetime_from_date(datetime.date(1900, 1, 1)))

        early_dates = [date for date in tmpschedule.dates if date.date() < startdate]
        if len(early_dates) > 1:
            logger.info("Clipping away dates: " + str(early_dates[1:]))
            for date in early_dates:
                tmpschedule.delete(date)
    return tmpschedule


def sch_file_starts_with_dates_keyword(filename):
    """Determine if a file (to be included) has
    DATES as its first keyword, or something else.

    We depend on knowing this in order to initialize
    the opm.tools.TimeVector object, and to be able
    to carefully handle whatever is in front of that DATES
    keyword (it is tricky, because we can't know for sure
    which date to anchor that to)

    Args:
        filename (string): Filename which will be opened and read.
    Returns:
        bool, true if first keyword is DATES
    """
    file_starts_with_dates = True

    # Implementation is by trial and error:
    try:
        # Test if it has DATES
        tmpschedule = TimeVector(datetime.date(1900, 1, 1))
        tmpschedule.load(filename)
    except ValueError:
        file_starts_with_dates = False
    return file_starts_with_dates


def substitute(insert_statement):
    """
    Perform key-value substitutions and generate the result
    as a file on disk.

    It is more natural to return a string, but this is to be used
    in opm.tools.TimeVector which initializes with a filename.

    Template parameters for which there are no values provided will
    be left untouched.

    Args:
        insert_statement (named_dict): Required keys are "template", which is
            a filename with parameters to be replaced, and "substitute"
            which is a named_dict with values parameter-value mappings
            to be used.

    Returns:
        filename (string): Filename on temporary location for immediate use
    """

    if len([key for key in list(insert_statement) if key is not None]) > 3:
        # (there should be also 'days' or 'date' in the dict)
        logger.warning(
            "Too many (?) configuration elements in %s", str(insert_statement)
        )

    resultfile = tempfile.NamedTemporaryFile(mode="w", delete=False)
    resultfilename = resultfile.name
    templatelines = open(insert_statement.template, "r").readlines()

    # Parse substitution list:
    substdict = insert_statement.substitute
    # Perform substitution and put into a tmp file
    for line in templatelines:
        for (key, value) in substdict:
            if "<" + key + ">" in line:
                line = line.replace("<" + key + ">", str(value))
        resultfile.write(line)
    resultfile.close()
    return resultfilename


def remap_v1_insert_to_v2(insert_statement):
    """
    Remap a config v1 insert section to how it should look like
    in the v2 config.

    Args:
        insert_statement (dict): A dictionary with only one key, which is either
            dummy or a filename. The key refers to a dictionary of configuration
            elements
    Returns:
        dict: The dictionary value being the first key in the input dict, with
            the key 'filename' added.
    """
    fileid = list(insert_statement.keys())[0]

    if len(insert_statement) > 1:
        logger.warning(
            "This does not look like v1 insert config element %s", str(insert_statement)
        )

    filedata = list(insert_statement[fileid].keys())

    # v1 config property:
    assert isinstance(insert_statement[fileid], dict)

    v2_insert_statement = {}

    if "string" in filedata:
        v2_insert_statement = {}
    else:
        if "filename" not in filedata:
            filename = fileid
        else:
            filename = insert_statement[fileid]["filename"]
        v2_insert_statement.update({"filename": filename})

    if "substitute" in insert_statement[fileid]:
        v2_insert_statement.update({"template": filename})
        if "filename" in v2_insert_statement:
            v2_insert_statement.pop("filename")
    if "filename" in insert_statement[fileid]:
        insert_statement[fileid].pop("filename")
    v2_insert_statement.update(insert_statement[fileid])
    return v2_insert_statement


def dategrid(startdate, enddate, interval):
    """Return a list of datetimes at given interval

    Args:
        startdate (datetime.date): First date in range
        enddate (datetime.date): Last date in range
        interval (str): Must be among: 'monthly', 'yearly', 'weekly',
            'biweekly', 'bimonthly'

    Return:
        list of datetime.date. Always includes start-date, might not include end-date
    """

    if interval not in SUPPORTED_DATEGRIDS:
        raise ValueError(
            'Unsupported dategrid interval "'
            + interval
            + '". Pick among '
            + ", ".join(SUPPORTED_DATEGRIDS)
        )
    dates = [startdate]
    date = startdate + datetime.timedelta(days=1)
    startdateweekday = startdate.weekday()

    # Brute force implementation by looping over all possible
    # days. This is robust with respect to all possible date oddities,
    # but makes it difficult to support more interval types.
    while date <= enddate:
        if interval == "monthly":
            if date.day == 1:
                dates.append(date)
        elif interval == "bimonthly":
            if date.day == 1 and date.month % 2 == 1:
                dates.append(date)
        elif interval == "weekly":
            if date.weekday() == startdateweekday:
                dates.append(date)
        elif interval == "biweekly":
            weeknumber = date.isocalendar()[1]
            if date.weekday() == startdateweekday and weeknumber % 2 == 1:
                dates.append(date)
        elif interval == "yearly":
            if date.day == 1 and date.month == 1:
                dates.append(date)
        elif interval == "daily":
            dates.append(date)
        date += datetime.timedelta(days=1)
    return dates


def file_startswith_dates(filename):
    """Check if a sch file starts with DATES

    This information is sometimes needed to determine how to send
    calls off to opm.io.tools.TimeVector

    Args:
        filename (str): Filename to check

    Returns:
        True if the first statement/keyword is DATES
    """
    tmpschedule = TimeVector(datetime.date(1900, 1, 1))
    try:
        # Since the date is provided in the second arg here, this will fail if the
        # file starts with DATES
        tmpschedule.load(filename, datetime_from_date(datetime.date(1900, 1, 1)))
        return False
    except ValueError:
        return True


def get_parser():
    """Set up parser for command line utility"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""Generate Eclipse Schedule file from merges and insertions.

Reads a YAML-file specifying how a Eclipse Schedule section is to be
produced given certain input files.

Command line options override configuration in YAML.

Output will not be generated unless the produced data is valid in
Eclipse, checking provided by OPM.""",
        epilog="""YAML-file components:

 startdate - YYYY-MM-DD for the initial date of the simulation (START keyword)

 files - list of filenames to be merged. Optional

 output - filename for output. stdout if omitted

 refdate - if supplied, will work as a reference date for relative
           inserts. If not supplied, startdate will be used.

 enddate - YYYY-MM-DD. DATES after this date will be removed.

 dategrid - a string being either 'weekly', 'biweekly', 'monthly',
            'bimonthly' stating how often a DATES keyword is wanted
            (independent of inserts/merges).  '(bi)monthly' and
            'yearly' will be rounded to first in every month.

 insert - list of components to be inserted into the final Schedule
          file. Each list element can contain the elements:

        date - Fixed date for the insertion

        days - relative date for insertion relative to refdate/startdate

        filename - filename to override the yaml-component element name.

        string - instead of filename, you can write the contents inline

        template - filename if substitution is to take place

        substitute - key-value pairs that will subsitute <key> in
                     incoming files (or inline string) with
                     associated values.
""",
    )
    parser.add_argument(
        "config", help="Config file in YAML format for Schedule merging"
    )
    parser.add_argument(
        "-o", "--output", type=str, default="", help="Output filename to write to"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Set logging level to info."
    )
    parser.add_argument(
        "--debug", action="store_true", help="Set logging level to debug."
    )
    parser.add_argument(
        "--startdate", type=str, help="Start date (START keyword), YYYY-MM-DD."
    )
    parser.add_argument(
        "--enddate",
        type=str,
        help="End date, delete keywords after this date, YYYY-MM-DD.",
    )
    parser.add_argument(
        "--refdate",
        type=str,
        help="Reference date to use for relative inserts, YYYY-MM-DD.",
    )
    parser.add_argument(
        "--dategrid", type=str, help="Interval for extra DATES to be inserted."
    )

    # Deprecated argument, keep to avoid old scripts failing. The setting is not used.
    parser.add_argument("-q", "--quiet", action="store_true", help=argparse.SUPPRESS)

    return parser


def main():
    """Entry point from command line"""
    parser = get_parser()
    args = parser.parse_args()

    # Application defaults configuration:
    defaults_config = {"output": "-", "startdate": "1900-01-01"}

    # Users YAML configuration:
    yaml_config = yaml.safe_load(open(args.config))

    # Command line configuration:
    cli_config = {}
    if args.output:
        cli_config["output"] = args.output
    if args.startdate:
        cli_config["startdate"] = args.startdate
    if args.enddate:
        cli_config["enddate"] = args.enddate
    if args.enddate:
        cli_config["refdate"] = args.refdate
    if args.dategrid:
        cli_config["dategrid"] = args.dategrid

    # Merge defaults-, yaml- and command line options, and then validate:
    config = configsuite.ConfigSuite(
        {}, CONFIG_SCHEMA_V2, layers=(defaults_config, yaml_config, cli_config)
    )
    if not config.valid:
        logger.error(config.errors)
        logger.warning(
            "Failed validating your input, will continue, but expect errors.."
        )

    else:
        # Check if yaml had outdated V1 syntax, check that by removing the transformation
        # from configsuite:
        transformation_key = list(CONFIG_SCHEMA_V2.keys())[1]  # slightly ugly
        config_schema_v2_pure = CONFIG_SCHEMA_V2.copy()
        del config_schema_v2_pure[transformation_key]
        config_pure = configsuite.ConfigSuite(
            {}, config_schema_v2_pure, layers=(defaults_config, yaml_config, cli_config)
        )
        if not config_pure.valid:
            logger.warning(
                "Your configuration uses a DEPRECATED format. Please switch,"
            )
            logger.warning(
                "The keys 'init' and 'merge' are now merged into a key called 'files'"
            )
            logger.warning(
                "and the insert statements all start with a single dash on a line."
            )

    if args.verbose:
        logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    schedule = process_sch_config(config.snapshot)

    if config.snapshot.output == "-":
        print(str(schedule))
    else:
        logger.info("Writing Eclipse deck to " + config.snapshot.output)
        open(config.snapshot.output, "w").write(str(schedule))


if __name__ == "__main__":
    main()
