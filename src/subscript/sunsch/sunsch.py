#!/usr/bin/env python
"""
Tool for generating Eclipse Schedule files

This script was originally based on a library named sunbeam,
hence the name. Later, this library has been merged into opm-common
"""

import argparse
import datetime
import logging
import sys
import tempfile
import textwrap
import warnings
from pathlib import Path
from typing import List, Union

import configsuite  # lgtm [py/import-and-import-from]
import dateutil.parser
import yaml
from configsuite import MetaKeys as MK  # lgtm [py/import-and-import-from]
from configsuite import types  # lgtm [py/import-and-import-from]

from subscript import __version__, getLogger
from subscript.sunsch.time_vector import TimeVector  # type: ignore

# from opm.tools import TimeVector  # type: ignore


logger = getLogger(__name__)

__MAGIC_STDOUT__ = "-"  # When used as a filename on the command line

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
def _is_valid_dategrid(dategrid_str: str):
    return dategrid_str in SUPPORTED_DATEGRIDS


@configsuite.validator_msg("Is filename an existing file")
def _is_existing_file(filename: str):
    return Path(filename).exists()


@configsuite.transformation_msg("Defaults handling")
def _defaults_handling(config: dict):
    """Handle defaults with dates."""
    return _shuffle_start_refdate(config)


@configsuite.transformation_msg("Convert to string")
def _to_string(element):
    """Convert anything to a string"""
    return str(element)


@configsuite.transformation_msg("Shuffle startdate vs refdate")
def _shuffle_start_refdate(config: dict) -> dict:
    """
    Ensure that:
    * startdate is always defined, if not given, it is picked
      from starttime or refdate. If neither of these, then default
      value 1900-01-01 is chosen.
    * starttime is always defined, use clocktime if defined
      explicit
    * refdate is always defined, set to startdate if not excplicit.
    """
    if "startdate" not in config:
        if "starttime" in config:
            config["startdate"] = config["starttime"]
        elif "refdate" in config:
            config["startdate"] = config["refdate"]
        else:
            config["startdate"] = datetime.date(1900, 1, 1)

    if "starttime" not in config:
        config["starttime"] = datetime_from_date(config["startdate"])

    if "refdate" not in config:
        config["refdate"] = config["startdate"]

    return config


CONFIG_SCHEMA_V2 = {
    MK.Type: types.NamedDict,
    MK.Transformation: _defaults_handling,
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


def get_schema() -> dict:
    """Return the ConfigSuite schema"""
    return CONFIG_SCHEMA_V2


def datetime_from_date(
    date: Union[str, datetime.datetime, datetime.date]
) -> datetime.datetime:
    """Set time to 00:00:00 in a date, keep time info if given a datetime object"""
    if isinstance(date, datetime.datetime):
        return date
    if isinstance(date, str):
        raise ValueError(f"Is the string {date} a date?")
    return datetime.datetime.combine(date, datetime.datetime.min.time())


def process_sch_config(conf) -> TimeVector:
    """Process a Schedule configuration into a opm.tools TimeVector

    Recognized keys in the configuration dict: files, startdate, startime,
    refdate, enddate, dategrid, insert

    Args:
        conf: Configuration dictionary for the schedule
            merges and inserts

    Returns:
        opm.io.TimeVector
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
                f"ERROR: enddate {conf.enddate} not in ISO-8601 format, "
                "must be YYYY-MM-DD"
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
        for _date in dates:
            schedule.add_keywords(datetime_from_date(_date), [""])

    return schedule


def load_timevector_from_file(
    filename: str, startdate: datetime.date, file_starts_with_dates: bool
) -> TimeVector:
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


def sch_file_nonempty(filename: str) -> bool:
    """Determine if a file (to be included) has any Eclipse
    keywords at all (excluding comments)

    Args:
        filename

    Returns:
        bool: False if the file is empty or has only comments.
    """
    # Implementation is by trial and error:
    try:
        tmpschedule = TimeVector(datetime.date(1900, 1, 1))
        tmpschedule.load(filename)
    except IndexError as err:
        if (
            "vector::_M_range_check: __n (which is 0) >= this->size() (which is 0)"
            in str(err)
        ):
            # This is what we get from opm>=2022.04 for empty files.
            return False

        if "Keyword index 0 is out of range" in str(err):
            # This is what we get from opm<2022.04 for empty files.
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


def sch_file_starts_with_dates_keyword(filename: str) -> bool:
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


def substitute(insert_statement) -> str:
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

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as resultfile:
        resultfilename = resultfile.name
        templatelines = (
            Path(insert_statement.template).read_text(encoding="utf8").splitlines()
        )

        # Parse substitution list:
        substdict = insert_statement.substitute
        # Perform substitution and put into a tmp file
        for line in templatelines:
            for key, value in substdict:
                if "<" + key + ">" in line:
                    line = line.replace("<" + key + ">", str(value))
            resultfile.write(line + "\n")
    return resultfilename


def wrap_long_lines(string: str, maxchars: int = 128, warn: bool = True) -> str:
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


def dategrid(
    startdate: datetime.date, enddate: datetime.date, interval: str
) -> List[datetime.date]:
    """Return a list of dates at given interval

    Args:
        startdate: First date in range
        enddate: Last date in range
        interval: Must be among: 'monthly', 'yearly', 'weekly',
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

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + __version__ + ")",
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
    yaml_config = yaml.safe_load(Path(args.config).read_text(encoding="utf8"))

    # Command line configuration:
    cli_config = {}
    if args.output:
        cli_config["output"] = args.output
    if args.startdate:
        cli_config["startdate"] = dateutil.parser.isoparse(args.startdate).date()
    if args.enddate:
        cli_config["enddate"] = dateutil.parser.isoparse(args.enddate).date()
    if args.refdate:
        cli_config["refdate"] = dateutil.parser.isoparse(args.refdate).date()
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
        logger.error("Your configuration is invalid. Exiting.")
        sys.exit(1)

    if args.verbose and config.snapshot.output != __MAGIC_STDOUT__:
        logger.setLevel(logging.INFO)
    if args.debug and config.snapshot.output != __MAGIC_STDOUT__:
        logger.setLevel(logging.DEBUG)

    # Generate the schedule section, as a string:
    schedule = wrap_long_lines(
        str(process_sch_config(config.snapshot)), maxchars=128, warn=True
    )

    if config.snapshot.output == __MAGIC_STDOUT__:
        print(schedule)
    else:
        logger.info("Writing Eclipse deck to %s", str(config.snapshot.output))
        dirname = Path(config.snapshot.output).parent
        if dirname and not dirname.exists():
            warnings.warn(
                f"Implicit mkdir of directory {str(dirname)} is deprecated and "
                f"will be removed later. Please ensure {str(dirname)} exists before "
                "calling sunsch.",
                FutureWarning,
            )
            dirname.mkdir()
        Path(config.snapshot.output).write_text(schedule, encoding="utf8")


if __name__ == "__main__":
    main()
