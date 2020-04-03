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
from opm.tools import TimeVector


def datetime_from_date(date):
    """Set time to 00:00:00 in a date"""
    return datetime.datetime.combine(date, datetime.datetime.min.time())


def process_sch_config(sunschconf, quiet=True):
    """Process a Schedule configuration into a opm.tools TimeVector

    :param sunschconf : configuration for the schedule merges and inserts
    :type sunschconf: dict
    :param quiet: Whether status messages should be printed during processing
    :type quiet: bool
    """
    if "startdate" in sunschconf:
        schedule = TimeVector(sunschconf["startdate"])
    elif "refdate" in sunschconf:
        schedule = TimeVector(sunschconf["refdate"])
    else:
        raise ValueError("No startdate or refdate given")

    if "refdate" not in sunschconf and "startdate" in sunschconf:
        sunschconf["refdate"] = sunschconf["startdate"]

    if "init" in sunschconf:
        starttime = datetime.datetime.combine(
            sunschconf["startdate"], datetime.datetime.min.time()
        )
        if not quiet:
            print(
                "Loading " + sunschconf["init"] + " at startdate: {}".format(starttime)
            )
        schedule.load(sunschconf["init"], starttime)

    if "merge" in sunschconf:
        for filename in sunschconf["merge"]:
            try:
                if not quiet:
                    print("Loading " + filename)
                tmpschedule = TimeVector(datetime.date(1900, 1, 1))
                tmpschedule.load(filename)
                # Clip dates prior to startdate
                for date in tmpschedule.dates:
                    if date.date() < sunschconf["startdate"]:
                        tmpschedule.delete(date)
                        # logging.info("removed at date...")
                schedule.load_string(str(tmpschedule))
            except ValueError as exception:
                raise ValueError("Error in " + filename + ": " + str(exception))

    if "insert" in sunschconf:  # inserts should be list of dicts of dicts
        for filedict in sunschconf["insert"]:
            # filedict is now a dict with only one key
            fileid = list(filedict.keys())[0]
            filedata = list(filedict[fileid].keys())

            # Figure out the correct filename, only needed when we
            # have a string.
            if "string" not in filedata:
                if "filename" not in filedata:
                    filename = fileid
                else:
                    filename = filedict[fileid]["filename"]

            resultfile = tempfile.NamedTemporaryFile(mode="w", delete=False)
            resultfilename = resultfile.name
            if "substitute" in filedata:
                templatelines = open(filename, "r").readlines()

                # Parse substitution list:
                substdict = filedict[fileid]["substitute"]
                # Perform substitution and put into a tmp file
                for line in templatelines:
                    for key in substdict:
                        if "<" + key + ">" in line:
                            line = line.replace("<" + key + ">", str(substdict[key]))
                    resultfile.write(line)
                resultfile.close()
                # Now we overwrite the filename coming from the yaml file!
                filename = resultfilename

            # Figure out the correct date:
            if "date" in filedict[fileid]:
                date = datetime.datetime.combine(
                    filedict[fileid]["date"], datetime.datetime.min.time()
                )
            if "days" in filedict[fileid]:
                if "refdate" not in sunschconf:
                    raise ValueError(
                        "ERROR: When using days in insert "
                        + "statements, you must provide refdate"
                    )
                date = datetime.datetime.combine(
                    sunschconf["refdate"], datetime.datetime.min.time()
                ) + datetime.timedelta(days=filedict[fileid]["days"])
            if date >= datetime.datetime.combine(
                sunschconf["startdate"], datetime.datetime.min.time()
            ):
                if "string" not in filedata:
                    schedule.load(filename, date=date)
                else:
                    schedule.add_keywords(
                        datetime_from_date(date), [filedict[fileid]["string"]]
                    )
            else:
                print("Ignoring inserts before startdate")

    if "enddate" not in sunschconf:
        if not quiet:
            print(
                ("Warning: Implicit end date. " + "Any content at last date is ignored")
            )
            # Whether we include it in the output does not matter,
            # Eclipse will ignore it
        enddate = schedule.dates[-1].date()
    else:
        enddate = sunschconf["enddate"]  # datetime.date
        if not isinstance(enddate, datetime.date):
            raise ValueError(
                "ERROR: end-date not in ISO-8601 format, must be YYYY-MM-DD"
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
    if "dategrid" in sunschconf:
        dates = dategrid(sunschconf["startdate"], enddate, sunschconf["dategrid"])
        for date in dates:
            schedule.add_keywords(datetime_from_date(date), [""])

    return schedule


def dategrid(startdate, enddate, interval):
    """Return a list of datetimes at given interval


    Parameters
    ----------
    startdate: datetime.date
               First date in range
    enddate: datetime.date
             Last date in range
    interval: str
              Must be among: 'monthly', 'yearly', 'weekly',
              'biweekly', 'bimonthly'
    Return
    ------
    list of datetime.date. Includes start-date, might not include end-date
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


# If we are called from command line:
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

 init - filename for the initial file. If omitted, defaults to an
        empty file. If you need something to happen between the
        Eclipse start date and the first DATES keyword, it must
        be present in this file.

 output - filename for output. stdout if omitted

 startdate - YYYY-MM-DD for the initial date in the simulation.

 refdate - if supplied, will work as a reference date for relative
           inserts. If not supplied, startdate will be used.

 enddate - YYYY-MM-DD. DATES after this date will be removed.

 dategrid - a string being either 'weekly', 'biweekly', 'monthly',
            'bimonthly' stating how often a DATES keyword is wanted
            (independent of inserts/merges).  '(bi)monthly' and
            'yearly' will be rounded to first in every month.

 merge - list of filenames to be merged in. DATES must be the first
         keyword in these files. Events prior to startdate will
         be removed.

 insert - list of components to be inserted into the final Schedule
          file. Each list elemen can contain the elemens:

            date - Fixed date for the insertion

            days - relative date for insertion relative to refdate/startdate

            filename - filename to override the yaml-component element name.

            string - instead of filename, you can write the contents inline

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
        "-q", "--quiet", action="store_true", help="Mute output from script"
    )
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

    if args.output == "-":
        args.quiet = True

    schedule = process_sch_config(config, args.quiet)

    if config["output"] == "-" or "output" not in config:
        print(str(schedule))
    else:
        if not args.quiet:
            print("Writing Eclipse deck to " + config["output"])
        open(config["output"], "w").write(str(schedule))


if __name__ == "__main__":
    main()
