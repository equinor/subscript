# -*- coding: utf-8 -*-
"""
Tool for generating Eclipse Schedule files

This script was originally based on a library named sunbeam,
hence the name. Later, this library has been merged into opm-common
"""

import datetime
import tempfile
import argparse
import yaml
import logging

from opm.tools import TimeVector

logger = logging.getLogger(__name__)
logging.basicConfig()


def datetime_from_date(date):
    """Set time to 00:00:00 in a date"""
    return datetime.datetime.combine(date, datetime.datetime.min.time())


def process_sch_config(conf):
    """Process a Schedule configuration into a opm.tools TimeVector

    Assumes the configuration is valid.

    Args:
        conf (dict): Configuration dictionary for the schedule
            merges and inserts
    """

    if "startdate" not in conf:
        # startdate if mandatory for yaml files, but left optional here
        if "refdate" in conf:
            conf["startdate"] = conf["refdate"]
        else:
            conf["startdate"] = datetime.date(1900, 1, 1)

    if "starttime" not in conf:
        conf["starttime"] = datetime_from_date(conf["startdate"])

    if "refdate" not in conf:
        conf["refdate"] = conf["startdate"]

    # Initialize the opm.tools.TimeVector class, which needs
    # a date to anchor to:
    schedule = TimeVector(conf["starttime"])

    if "files" not in conf:
        conf["files"] = []

    if "init" in conf:
        logger.warning("init config entry is deprecated. Use 'files'.")
        conf["files"] += [conf["init"]]
        del conf["init"]

    if "merge" in conf:
        logger.warning("merge config entry is deprecated. Use 'files'.")
        if not isinstance(conf["merge"], list):
            conf["merge"] = [conf["merge"]]
        conf["files"] += conf["merge"]
        del conf["merge"]

    for filename in conf["files"]:
        logger.info("Loading %s", filename)
        file_starts_with_dates = sch_file_starts_with_dates_keyword(filename)
        timevector = load_timevector_from_file(
            filename, conf["startdate"], file_starts_with_dates
        )
        if file_starts_with_dates:
            schedule.load_string(str(timevector))
        else:
            schedule.load_string(str(timevector), conf["starttime"])

    if "insert" not in conf:
        conf["insert"] = []

    insert_deprecation_warning_emitted = False
    for insert_statement in conf["insert"]:
        # In v1 the list entries are dictionaries with key length 1,
        # in v2 there must be more than 1 key in the dictionaries in the list
        if len(insert_statement.keys()) == 1:
            if not insert_deprecation_warning_emitted:
                logger.warning(
                    "The configuration format you are using for inserts is deprecated"
                )
                insert_deprecation_warning_emitted = True
            insert_statement = remap_v1_insert_to_v2(insert_statement)
        logger.debug(str(insert_statement))
        if "substitute" in insert_statement:
            # Prepare a new file where substitutions have taken place:
            insert_statement["filename"] = substitute(insert_statement)

        # Which date to use for insertion?
        if "date" in insert_statement:
            date = datetime_from_date(insert_statement["date"])
        elif "days" in insert_statement:
            date = datetime_from_date(conf["refdate"]) + datetime.timedelta(
                days=insert_statement["days"]
            )
        else:
            logger.error("Could not determine date for insertion")
            logger.error("From data: %s", str(insert_statement))
            continue

        # Do the insertion:
        if date >= conf["starttime"]:
            if "filename" in insert_statement:
                schedule.load(insert_statement["filename"], date=date)
            else:
                schedule.add_keywords(
                    datetime_from_date(date), [insert_statement["string"]]
                )
        else:
            logger.warning("Ignoring inserts before startdate")

    if "enddate" not in conf:
        logger.info("Implicit end date. Any content at last date is ignored")
        # Whether we include it in the output does not matter, Eclipse will ignore it
        enddate = schedule.dates[-1].date()
    else:
        enddate = conf["enddate"]  # datetime.date
        if not isinstance(enddate, datetime.date):
            raise TypeError(
                "ERROR: enddate {} not in ISO-8601 format, must be YYYY-MM-DD".format(
                    conf["enddate"]
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
    if "dategrid" in conf:
        dates = dategrid(conf["startdate"], enddate, conf["dategrid"])
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
        insert_statement (dict): Required keys are "template", which is
            a filename with parameters to be replaced, and "substitute"
            which is a dictionary with values parameter-value mappings
            to be used.

    Returns:
        filename (string): Filename on temporary location for immediate use
    """
    assert "template" in insert_statement
    assert "substitute" in insert_statement

    if len(insert_statement.keys()) > 3:
        # (there should be also 'days' or 'date' in the dict)
        logger.warning(
            "Too many (?) configuration elements in %s", str(insert_statement)
        )

    resultfile = tempfile.NamedTemporaryFile(mode="w", delete=False)
    resultfilename = resultfile.name
    templatelines = open(insert_statement["template"], "r").readlines()

    # Parse substitution list:
    substdict = insert_statement["substitute"]
    assert isinstance(substdict, dict)
    # Perform substitution and put into a tmp file
    for line in templatelines:
        for key in substdict:
            if "<" + key + ">" in line:
                line = line.replace("<" + key + ">", str(substdict[key]))
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

    supportedintervals = ["monthly", "yearly", "weekly", "biweekly", "bimonthly"]
    if interval not in supportedintervals:
        raise ValueError(
            'Unsupported dategrid interval "'
            + interval
            + '". Pick among '
            + ", ".join(supportedintervals)
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
        "-o",
        "--output",
        type=str,
        default="",
        help="Override output in yaml config. Use - for stdout",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Set logging level to info"
    )

    # Deprecated argument, keep to avoid old scripts failing. The setting is not used.
    parser.add_argument("-q", "--quiet", action="store_true", help=argparse.SUPPRESS)

    return parser


def main():
    """Entry point from command line"""
    parser = get_parser()
    args = parser.parse_args()

    # Load YAML file:
    config = yaml.safe_load(open(args.config))

    # Overrides:
    if args.output != "":
        config["output"] = args.output

    if "output" not in config:
        config["output"] = "-"  # Write to stdout

    if args.verbose:
        logger.setLevel(logging.INFO)

    schedule = process_sch_config(config)

    if config["output"] == "-" or "output" not in config:
        print(str(schedule))
    else:
        logger.info("Writing Eclipse deck to " + config["output"])
        open(config["output"], "w").write(str(schedule))


if __name__ == "__main__":
    main()
