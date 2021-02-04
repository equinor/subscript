#!/usr/bin/env python
"""
Tool for generating Eclipse Schedule files

This script was originally based on a library named sunbeam,
hence the name. Later, this library has been merged into opm-common
"""

import os
import datetime
import tempfile
import argparse
import textwrap
import logging

import yaml

from opm.tools import TimeVector

import configsuite  # lgtm [py/import-and-import-from]
from configsuite import types  # lgtm [py/import-and-import-from]
from configsuite import MetaKeys as MK  # lgtm [py/import-and-import-from]

from subscript import getLogger

logger = getLogger(__name__)

SUPPORTED_DATEGRIDS = ["daily", "monthly", "yearly", "weekly", "biweekly", "bimonthly"]

DESCRIPTION = """Generate Eclipse Schedule file from merges and insertions.

Reads a YAML-file specifying how a Eclipse Schedule section is to be
produced given certain input files.

Command line options override configuration in YAML.

Output will not be generated unless the produced data is valid in
Eclipse, checking provided by OPM."""

CATEGORY = "modelling.production"

EXAMPLES = """
.. code-block:: console

  FORWARD_MODEL SUNSCH(<config>=sunsch_config.yml)
"""


@configsuite.validator_msg("Is dategrid a supported frequency")
def _is_valid_dategrid(dategrid_str):
    return dategrid_str in SUPPORTED_DATEGRIDS


@configsuite.validator_msg("Is filename an existing file")
def _is_existing_file(filename):
    return os.path.exists(filename)


@configsuite.transformation_msg("Defaults and v1-vs-v2 handling of config")
def _defaults_and_v1_format_handling(config):
    """Wrapper transformation function.

    Only one tranformation can be given to ConfigSuite.
    """
    return _v1_content_to_v2(_shuffle_start_refdate(config))


@configsuite.transformation_msg("Convert to string")
def _to_string(element):
    """Convert anything to a string"""
    return str(element)


@configsuite.transformation_msg("Shuffle startdate vs refdate")
def _shuffle_start_refdate(config):
    """
    Ensure that:
    * startdate is always defined, if not given, it is picked
      from starttime or refdate. If neither of these, then default
      value 1900-01-01 is chosen.
    * starttime is always defined, set to 00:00 of startdate if not
      explicit
    * refdate is always defined, set to startdate if not excplicit.
    """
    if "startdate" not in config:
        if "starttime" in config:
            config["startdate"] = config["starttime"].date()
        elif "refdate" in config:
            config["startdate"] = config["refdate"]
        else:
            config["startdate"] = datetime.date(1900, 1, 1)

    if "starttime" not in config:
        config["starttime"] = datetime_from_date(config["startdate"])

    if "refdate" not in config:
        config["refdate"] = config["startdate"]

    return config


@configsuite.transformation_msg("Convert v1 sunsch format to v2")
# pylint: disable=invalid-name
def _v1_content_to_v2(config):
    """
    Process an incoming dictionary with sunsch configuration.

    If sunsch v1 format is detected, then transform to v2. If v2 format
    nothing happens.

    Validation (and convertion from mutable dict to immutable named_dict)
    happens later.

    Args:
        config (dict)

    Returns
        dict
    """
    if "insert" in config:
        v2_insert = []
        for insertstatement in config["insert"]:
            # ConfigSuite 0.6.1 always provides the "substitute" key in the dict,
            # in order to detect v1 we must disregard an empty substitute:
            if "substitute" in insertstatement and not insertstatement["substitute"]:
                insertstatement_length = len(insertstatement) - 1
            else:
                insertstatement_length = len(insertstatement)
            if insertstatement_length == 1:
                v2_insert += [_remap_v1_insert_to_v2(insertstatement)]
            else:
                v2_insert += [insertstatement]
        config["insert"] = v2_insert

    if "init" in config or "merge" in config:
        v2_files = []
        if "files" in config:
            # This is a strange mix of v1 and v2 config..
            v2_files += config["files"]
        if "init" in config:
            v2_files += [config["init"]]
            del config["init"]
        if "merge" in config:
            # In v1, this can be both a list and a string
            if isinstance(config["merge"], str):
                v2_files += [config["merge"]]
            else:
                v2_files += config["merge"]
            del config["merge"]
        config["files"] = v2_files
    return config


CONFIG_SCHEMA_V2 = {
    MK.Type: types.NamedDict,
    MK.Transformation: _defaults_and_v1_format_handling,
    MK.Content: {
        "files": {
            MK.Type: types.List,
            MK.Description: "List of filenames to include in merge operation",
            MK.Content: {
                MK.Item: {
                    MK.Type: types.String,
                    MK.Description: "Filename to merge",
                    MK.ElementValidators: (_is_existing_file,),
                }
            },
        },
        "output": {
            MK.Description: "Output filename, '-' means stdout",
            MK.Type: types.String,
            MK.AllowNone: True,
            MK.Default: "-",
        },
        "startdate": {
            MK.Description: "The start date of the Eclipse run (START keyword).",
            MK.Type: types.Date,
            MK.AllowNone: True,
            # (a transformation will provide the default value here)
        },
        "starttime": {
            MK.Description: (
                "The start time, used for relative "
                "inserts if clock accuracy is needed"
            ),
            MK.Type: types.DateTime,
            MK.AllowNone: True,
            # (a transformation will provide/calculate a default value here)
        },
        "refdate": {
            MK.Description: (
                "Reference date for relative inserts. "
                "Only set if it should be different than startdate."
            ),
            MK.Type: types.Date,
            MK.AllowNone: True,
        },
        "enddate": {
            MK.Description: "An end date, events pass this date will be clipped",
            MK.Type: types.Date,
            MK.AllowNone: True,
        },
        "dategrid": {
            MK.Description: (
                "Set to yearly, monthly, etc to get a grid of dates included"
            ),
            MK.Type: types.String,
            MK.AllowNone: True,
            MK.ElementValidators: (_is_valid_dategrid,),
        },
        "insert": {
            MK.Description: (
                "List of insert statements to process into the Schedule file"
            ),
            MK.Type: types.List,
            MK.Content: {
                MK.Item: {
                    MK.Description: "Insert statement",
                    MK.Type: types.NamedDict,
                    MK.Content: {
                        "date": {
                            MK.Description: "Date at which to insert something",
                            MK.Type: types.Date,
                            MK.AllowNone: True,
                        },
                        "filename": {
                            MK.Description: "Filename with contents to insert",
                            MK.Type: types.String,
                            MK.AllowNone: True,
                            MK.ElementValidators: (_is_existing_file,),
                        },
                        "template": {
                            MK.Description: (
                                "Template file in which substitution will "
                                "take place before it is inserted"
                            ),
                            MK.Type: types.String,
                            MK.AllowNone: True,
                            MK.ElementValidators: (_is_existing_file,),
                        },
                        "days": {
                            MK.Description: (
                                "Days after refdate/startdate at which "
                                "insertion should take place"
                            ),
                            MK.Type: types.Number,
                            MK.AllowNone: True,
                        },
                        "string": {
                            MK.Description: ("A string to insert, instead of filename"),
                            MK.Type: types.String,
                            MK.AllowNone: True,
                        },
                        "substitute": {
                            MK.Description: (
                                "Key-value pairs for substitution in a template"
                            ),
                            MK.Type: types.Dict,
                            MK.Content: {
                                MK.Key: {
                                    MK.Description: "Template key name",
                                    MK.AllowNone: False,
                                    MK.Type: types.String,
                                },
                                MK.Value: {
                                    MK.AllowNone: "Value to insert in template",
                                    MK.AllowNone: False,
                                    # Since we allow both numbers and strings here,
                                    # it is converted to a string as configsuite
                                    # only allows one type.
                                    MK.Transformation: _to_string,
                                    MK.Type: types.String,
                                },
                            },
                        },
                    },
                }
            },
        },
    },
}


def get_schema():
    """Return the ConfigSuite schema"""
    return CONFIG_SCHEMA_V2


def datetime_from_date(date):
    """Set time to 00:00:00 in a date"""
    if isinstance(date, str):
        raise ValueError("Is the string {} a date?".format(str(date)))
    return datetime.datetime.combine(date, datetime.datetime.min.time())


def process_sch_config(conf):
    """Process a Schedule configuration into a opm.tools TimeVector

    Recognized keys in the configuration dict: files, startdate, startime,
    refdate, enddate, dategrid, insert

    Args:
        conf (dict or named_dict): Configuration dictionary for the schedule
            merges and inserts

    Returns:
        opm.io.TimeVector:
    """
    # At least test code is calling this function with a dict as
    # config - convert it to a configsuite snapshot:
    if isinstance(conf, dict):
        conf = configsuite.ConfigSuite(
            conf, CONFIG_SCHEMA_V2, deduce_required=True
        ).snapshot

    # Rerun this to ensure error is caught (already done in transformation)
    datetime_from_date(conf.startdate)

    # Initialize the opm.tools.TimeVector class, which needs
    # a date to anchor to:
    schedule = TimeVector(conf.starttime)

    if conf.files is not None:
        for filename in conf.files:
            if sch_file_nonempty(filename):
                logger.info("Loading %s", filename)
            else:
                logger.warning("No Eclipse statements in %s, skipping", filename)
                continue

            file_starts_with_dates = sch_file_starts_with_dates_keyword(filename)
            timevector = load_timevector_from_file(
                filename, conf.startdate, file_starts_with_dates
            )
            if file_starts_with_dates:
                schedule.load_string(str(timevector))
            else:
                schedule.load_string(str(timevector), conf.starttime)

    if conf.insert is not None:
        logger.info("Processing %s insert statements", str(len(conf.insert)))
        for insert_statement in conf.insert:
            logger.debug(str(insert_statement))

            if insert_statement.substitute and insert_statement.template:
                filename = substitute(insert_statement)
                logger.debug("Produced file: %s", str(filename))
            elif insert_statement.template and not insert_statement.substitute:
                logger.error(
                    "Missing subsitute for template %s", insert_statement.template
                )
                continue
            elif insert_statement.filename:
                filename = insert_statement.filename
            elif not insert_statement.string:
                logger.error("Invalid insert statement: %s", str(insert_statement))

            # Which date to use for insertion?
            if insert_statement.date:
                date = datetime_from_date(insert_statement.date)
            elif insert_statement.days:
                date = datetime_from_date(conf.refdate) + datetime.timedelta(
                    days=insert_statement.days
                )
            else:
                logger.error("Could not determine date for insertion")
                logger.error("From data: %s", str(insert_statement))
                continue

            # Do the insertion:
            if date >= conf.starttime:
                if insert_statement.string is None:
                    if sch_file_nonempty(filename):
                        schedule.load(filename, date=date)
                    else:
                        logger.warning(
                            "No Eclipse statements in %s, skipping", filename
                        )
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
        dates = dategrid(conf.startdate, enddate, conf.dategrid)
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
            logger.info("Clipping away dates: %s", str(early_dates[1:]))
            for date in early_dates:
                tmpschedule.delete(date)
    else:
        tmpschedule.load(filename, datetime_from_date(datetime.date(1900, 1, 1)))

        early_dates = [date for date in tmpschedule.dates if date.date() < startdate]
        if len(early_dates) > 1:
            logger.info("Clipping away dates: %s", str(early_dates[1:]))
            for date in early_dates:
                tmpschedule.delete(date)
    return tmpschedule


def sch_file_nonempty(filename):
    """Determine if a file (to be included) has any Eclipse
    keywords at all (excluding comments)

    Args:
        filename (str)

    Returns:
        bool: False if the file is empty or has only comments.
    """
    # Implementation is by trial and error:
    try:
        tmpschedule = TimeVector(datetime.date(1900, 1, 1))
        tmpschedule.load(filename)
    except IndexError as err:
        if "Keyword index 0 is out of range" in str(err):
            # This is what we get from opm for empty files.
            return False

        # Try to workaround a non-explanatory error from opm-common:
        if "map::at" in str(err):
            logger.error("Error happened while parsing %s", filename)
            logger.error(
                "You have potentially used PATHS variables in INCLUDE statements?"
            )
            logger.error("This is not supported")
            raise SystemExit from err

        # Unknown error condition
        logger.error("Could not parse %s", filename)
        logger.error(err)
        raise SystemExit from err

    except ValueError:
        # This is where we get for files not starting with DATES,
        # but that means it is nonempty
        return True
    return True


def sch_file_starts_with_dates_keyword(filename):
    """Determine if a file (to be included) has
    DATES as its first keyword, or something else.

    We depend on knowing this in order to initialize
    the opm.tools.TimeVector object, and to be able
    to carefully handle whatever is in front of that DATES
    keyword (it is tricky, because we can't know for sure
    which date to anchor that to)

    Args:
        filename (str): Filename which will be opened and read.
    Returns:
        bool: true if first keyword is DATES
    """
    # Implementation is by trial and error:
    try:
        # Test if it has DATES
        tmpschedule = TimeVector(datetime.date(1900, 1, 1))
        tmpschedule.load(filename)
    except ValueError:
        return False
    return True


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
        str: Filename on temporary location for immediate use
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


def wrap_long_lines(string, maxchars=128, warn=True):
    """Wrap long lines in a multiline string.

    Short enough lines are not touched.

    Args:
        string (str): Multiline string to be possibly wrapped
        maxchars (int): Maximal length of each line
        warn (bool): Whether to log a warning for each line
            of excessive length

    Returns:
        str: Multiline string with no lines more than maxchars
        in length. Trailing whitespace is always stripped.
    """
    wrappedstr = ""
    for line_idx, line in enumerate(string.splitlines()):
        commentsplit = line.partition("--")
        pre_comment = commentsplit[0]
        if len(pre_comment) > maxchars:
            # Trim all whitespace down to one space:
            pre_comment = " ".join(pre_comment.split())
            # (Comments are supported here even though they are always
            # stripped out by the current opm.io.TimeVector implementation)
            if warn:
                logger.warning("Line %d had length %d, wrapped", line_idx, len(line))
            wrappedstr += "\n".join(
                textwrap.wrap(
                    pre_comment,
                    width=maxchars,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
            ).strip()
            wrappedstr += commentsplit[1] + commentsplit[2] + "\n"
        else:
            wrappedstr += line + "\n"
    return wrappedstr.strip()


def _remap_v1_insert_to_v2(insert_statement):
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

    # ConfigSuite 0.6.1 always provides the "substitute" key in the dict,
    # delete it temporarily if it is present, and reinstate at the end.
    if "substitute" in insert_statement and not insert_statement["substitute"]:
        del insert_statement["substitute"]

    fileid = list(insert_statement.keys())[0]

    if len(insert_statement) > 1:
        logger.warning(
            "This does not look like v1 insert config element %s", str(insert_statement)
        )

    filedata = list(insert_statement[fileid].keys())
    # v1 config property:
    if not isinstance(insert_statement[fileid], dict):
        logger.error("BUG: The insert_statement: %s was not v1", str(insert_statement))
        return {}

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
    if "substitute" not in v2_insert_statement:
        v2_insert_statement["substitute"] = {}
    # Ensure the string transformation is applied
    for key in v2_insert_statement["substitute"]:
        v2_insert_statement["substitute"][key] = _to_string(
            v2_insert_statement["substitute"][key]
        )
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
        description=DESCRIPTION,
        epilog="""YAML-file components::

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
    defaults_config = {"output": "-", "startdate": datetime.date(1900, 1, 1)}

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
        {},
        get_schema(),
        layers=(defaults_config, yaml_config, cli_config),
        deduce_required=True,
    )
    if not config.valid:
        logger.error(config.errors)
        logger.warning(
            "Failed validating your input, will continue, but expect errors.."
        )
    else:
        config_schema_v2_pure = CONFIG_SCHEMA_V2.copy()
        # Check if yaml had outdated v1 syntax, check that by removing the
        # transformation key(s) in the top layer from configsuite:
        # pylint: disable=consider-iterating-dictionary
        trans_keys = [
            key
            for key in CONFIG_SCHEMA_V2.keys()
            if str(key) == "MetaKeys.Transformation"
        ]
        for deletekey in trans_keys:
            del config_schema_v2_pure[deletekey]

        try:
            config_pure = configsuite.ConfigSuite(
                {},
                config_schema_v2_pure,
                layers=(defaults_config, yaml_config, cli_config),
                deduce_required=True,
            )
            valid = config_pure.valid
        except KeyError:
            # Only Py2 gets here.
            valid = False
        if not valid:
            logger.warning(
                (
                    "Your configuration is DEPRECATED, "
                    "switch to new format.\n"
                    "The keys 'init' and 'merge' are "
                    "now merged into a key called 'files'\n"
                    "and the insert statements all start "
                    "with a single dash on a line.\n"
                    "The following auto-converted YAML "
                    "might be usable for you:\n"
                    "%s"
                    "\nEnd auto-converted YAML"
                ),
                yaml.dump(
                    _v1_content_to_v2(yaml_config)
                ).strip(),  # lgtm [py/call-to-non-callable]
            )

    if args.verbose:
        logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    # Generate the schedule section, as a string:
    schedule = wrap_long_lines(
        str(process_sch_config(config.snapshot)), maxchars=128, warn=True
    )

    if config.snapshot.output == "-":
        print(schedule)
    else:
        logger.info("Writing Eclipse deck to %s", str(config.snapshot.output))
        dirname = os.path.dirname(config.snapshot.output)
        if dirname and not os.path.exists(dirname):
            logger.debug("mkdir %s", dirname)
            os.makedirs(dirname)
        open(config.snapshot.output, "w").write(schedule)


if __name__ == "__main__":
    main()
