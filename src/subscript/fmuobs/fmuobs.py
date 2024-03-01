"""fmuobs is a converter tool for observation files used in assisted
history matching"""

import argparse
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Optional, Tuple, Union

import pandas as pd
import yaml
from ert.config import ErtScript
from ert.shared.plugins.plugin_manager import hook_implementation  # type: ignore

from subscript import __version__, getLogger
from subscript.fmuobs.parsers import (
    compute_date_from_days,
    ertobs2df,
    obsdict2df,
    resinsight_df2df,
)
from subscript.fmuobs.writers import (
    CLASS_SHORTNAME,
    df2ertobs,
    df2obsdict,
    df2resinsight_df,
)

logger = getLogger(__name__)

DESCRIPTION = """Converter for assisted history match observation files.

Supported file formats:
    * ERT observation files
    * YAML observation files (Webviz)
    * ResInsight observation files (semi-colon separated values)

Any of these formats can be parsed and outputted to any of the other formats,
for the subset of observations types supported by each format. Internally the
script holds a tabular format that supports all formats, and this can be
exported and imported as CSV.

ERT observation file syntax:
https://fmu-docs.equinor.com/docs/ert/reference/configuration/observations.html

ResInsight format:
https://resinsight.org/import/observeddata/
"""

CATEGORY = "observations.transformation"

EXAMPLES = """
Add a file named e.g. ``ert/bin/workflows/wf_fmuobs`` with the contents:

.. code-block:: none

  FMUOBS "--verbose" observations.txt "--yaml" observations.yml "--resinsight" observations-ri.csv

You probably need to use the variables ``<CONFIG_PATH>`` and ``<CASEDIR>`` to
build fully qualified pathnames.

Add to your ert config::

    LOAD_WORKFLOW ../bin/workflows/wf_fmuobs
    HOOK_WORKFLOW wf_fmuobs PRE_SIMULATION

"""  # noqa

__MAGIC_STDOUT__ = "-"


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """Multiple inheritance used for argparse to get both defaults
    and raw description formatter"""

    # pylint: disable=unnecessary-pass


def get_parser() -> argparse.ArgumentParser:
    """Return a parser for the command line client, and for
    generating help text. The description, defaults and help-text for
    each argument is shared with the parser for the ERT workflow"""

    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter, description=DESCRIPTION
    )

    parser.add_argument(
        "inputfile",
        help="Input file, in any of the supported observation formats",
        type=str,
    )
    parser.add_argument(
        "--ertobs",
        "--ert",
        type=str,
        help="Name of ERT observation file. Use '-' to write to stdout.",
    )
    parser.add_argument(
        "-o",
        "--yml",
        "--yaml",
        type=str,
        help="YAML output-file. Use '-' to write to stdout.",
    )
    parser.add_argument(
        "--resinsight",
        "--ri",
        type=str,
        help="ResInsight observations output CSV-file. Use '-' to write to stdout.",
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="Name of output CSV file. Use '-' to write to stdout.",
    )
    parser.add_argument(
        "--starttime",
        "--startdate",
        type=str,
        default=None,
        help="Starttime or startdate to be used for converting DAYS to date(time)s",
    )
    parser.add_argument(
        "--includedir",
        type=str,
        help=(
            "Path to directory to be used for resolving include filenames "
            "when parsing ERT observation files. "
            "This path should be set to the directory of the ERT config file, "
            "and the include file statements must be relative to this."
        ),
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    parser.add_argument("--debug", action="store_true", help="Print debugging messages")
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + __version__ + ")",
    )
    return parser


def validate_internal_dframe(obs_df: pd.DataFrame) -> bool:
    """Validate the internal dataframe format for observations.

    Will log warnings and/or errors if anything found.

    Args:
        obs_df: Dataframe to validate

    Returns:
        True if everything is ok (or empty)
    """
    failed = False
    if obs_df.empty:
        logger.warning("Observation dataframe empty")
        return True
    if "CLASS" not in obs_df:
        logger.error("CLASS is not in dataframe - not valid")
        failed = True
    if "LABEL" not in obs_df:
        logger.error("LABEL is not in dataframe - not valid")
        failed = True
    non_supported_classes = set(obs_df["CLASS"]) - set(CLASS_SHORTNAME.keys())
    if non_supported_classes:
        logger.error("Unsupported observation classes: %s", str(non_supported_classes))
        failed = True

    index = {"CLASS", "LABEL", "OBS", "SEGMENT"}.intersection(set(obs_df.columns))
    repeated_rows = obs_df[obs_df.set_index(list(index)).index.duplicated(keep=False)]
    if not repeated_rows.empty:
        logger.error("Non-unique observation classes and labels")
        logger.error("\n%s", str(repeated_rows.dropna(axis="columns", how="all")))
        failed = True

    # Possibilities for further validation:
    #  * Check that segment has start and end if not default.
    #  * SUMMARY_OBSERVATION requires four arguments (also for resinsight?)
    #  * BLOCK_OBSERVATIONk requires two global, and j, k, value, error for
    #    each subunit.
    #  * block requires label
    #  * general requires data, restart, obs_file. index_list, index_file,
    #  * error_covariance is optional.

    logger.info("Observation dataframe validated")
    return not failed


def autoparse_file(filename: str) -> Tuple[Optional[str], Union[pd.DataFrame, dict]]:
    """Detects the observation file format for a given filename. This
    is done by attempting to parse its content and giving up on
    exceptions.

    NB: In case of ERT file formats, the include statements are
    interpreted relative to current working directory. Thus it
    is recommended to reparse with correct cwd after detecting ERT file
    format. The correct cwd for include-statement is the path of the
    ERT config file, which is outside the context of fmuobs.

    Args:
        filename

    Returns:
        tuple: First element is a string in [resinsight, csv, yaml, ert], second
        element is a dataframe or a dict (if input was yaml).
    """
    # Pylint exceptions as this code is made to catch these errors and act on them.
    # pylint: disable=unsubscriptable-object, no-member
    # pylint: disable=unsupported-assignment-operation
    try:
        dframe = pd.read_csv(filename, sep=";")
        if {"DATE", "VECTOR", "VALUE", "ERROR"}.issubset(
            set(dframe.columns)
        ) and not dframe.empty:
            logger.info("Parsed %s as a ResInsight observation file", filename)
            return ("resinsight", resinsight_df2df(dframe))
    except ValueError:
        pass

    try:
        dframe = pd.read_csv(filename, sep=",")
        if {"CLASS", "LABEL"}.issubset(dframe.columns) and not dframe.empty:
            logger.info(
                "Parsed %s as a CSV (internal dataframe format for ertobs) file",
                filename,
            )
            if "DATE" in dframe:
                dframe["DATE"] = pd.to_datetime(dframe["DATE"])
            return ("csv", dframe)
    except ValueError:
        pass

    try:
        obsdict = yaml.safe_load(Path(filename).read_text(encoding="utf8"))
        if isinstance(obsdict, dict) and (
            obsdict.get("smry", None) or obsdict.get("rft", None)
        ):
            logger.info("Parsed %s as a YAML file with observations", filename)
            return ("yaml", obsdict2df(obsdict))
    except yaml.scanner.ScannerError as exception:
        # This occurs if there are tabs in the file, which is not
        # allowed in a YAML file (but it can be present in ERT observation files)
        logger.debug("ScannerError while attempting yaml-parsing")
        logger.debug(str(exception))
    except ValueError:
        pass

    try:
        with open(filename, encoding="utf8") as f_handle:
            # This function does not have information on include file paths.
            # Accept a FileNotFoundError while parsing, if we encounter that
            # it is most likely an ert file, but which needs additional hints
            # on where include files are located.
            try:
                dframe = ertobs2df(f_handle.read())
            except FileNotFoundError:
                logger.info(
                    "Parsed %s as an ERT observation file, with include statements",
                    filename,
                )
                return ("ert", pd.DataFrame())
        if (
            {"CLASS", "LABEL"}.issubset(dframe.columns)
            and not dframe.empty
            and set(dframe["CLASS"]).intersection(set(CLASS_SHORTNAME.keys()))
        ):
            logger.info("Parsed %s as an ERT observation file", filename)
            return ("ert", dframe)
    except ValueError:
        pass

    logger.error(
        "Unable to parse %s as any supported observation file format", filename
    )
    return (None, pd.DataFrame)


def main() -> None:
    """Command line client, parse command line arguments and execute the tool."""
    parser = get_parser()
    args = parser.parse_args()
    fmuobs(
        args.inputfile,
        ertobs=args.ertobs,
        yml=args.yml,
        resinsight=args.resinsight,
        csv=args.csv,
        verbose=args.verbose,
        debug=args.debug,
        starttime=args.starttime,
        includedir=args.includedir,
    )


def fmuobs(
    inputfile: str,
    ertobs: Optional[str] = None,
    yml: Optional[str] = None,
    resinsight: Optional[str] = None,
    csv: Optional[str] = None,
    verbose: bool = False,
    debug: bool = False,
    starttime: Optional[str] = None,
    includedir: Optional[bool] = None,
):
    # pylint: disable=too-many-arguments
    """Alternative to main() with named arguments"""
    if verbose or debug:
        if __MAGIC_STDOUT__ in (csv, yml, ertobs):
            raise SystemExit("Don't use verbose/debug when writing to stdout")
        loglevel = logging.INFO
        if debug:
            loglevel = logging.DEBUG
        logger.setLevel(loglevel)
        getLogger("subscript.fmuobs.parsers").setLevel(loglevel)
        getLogger("subscript.fmuobs.writers").setLevel(loglevel)
        getLogger("subscript.fmuobs.util").setLevel(loglevel)

    (filetype, dframe) = autoparse_file(inputfile)

    # For ERT files, there is the problem of include-file-path. If not-found
    # include filepaths are present, the filetype is ert, but dframe is empty.
    if filetype == "ert" and pd.DataFrame.empty:
        input_str = Path(inputfile).read_text(encoding="utf8")
        if not includedir:
            # Try and error for the location of include files, first in current
            # dir, then in the directory of the input file. The proper default
            # for cwd is the location of the ert config file, which is not
            # available in this parser, and must be supplied on command line.
            try:
                dframe = ertobs2df(input_str, cwd=".", starttime=starttime)
            except FileNotFoundError:
                dframe = ertobs2df(
                    input_str,
                    cwd=os.path.dirname(inputfile),
                    starttime=starttime,
                )
        else:
            dframe = ertobs2df(input_str, cwd=includedir)

    if starttime:
        dframe = compute_date_from_days(dframe)

    if not validate_internal_dframe(dframe):
        logger.error("Observation dataframe is invalid!")

    # Trigger warning if user specify ERROR_MODE != ABS
    # in BLOCK_OBSERVATION and SUMMARY_OBSERVATION
    if isinstance(dframe, pd.DataFrame) and "ERROR_MODE" in dframe.columns:
        error_mode = list(
            dframe[
                (dframe["CLASS"].isin(["BLOCK_OBSERVATION", "SUMMARY_OBSERVATION"]))
                & (dframe["ERROR_MODE"] != "ABS")
            ]["ERROR_MODE"]
            .dropna()
            .unique()
        )
        if len(error_mode) > 0:
            logger.warn(
                f"Unsupported ERROR_MODE : {', '.join(error_mode)}. "
                "Please verify the output file"
            )

    dump_results(dframe, csv, yml, resinsight, ertobs)


def dump_results(
    dframe: pd.DataFrame,
    csvfile: Optional[str] = None,
    yamlfile: Optional[str] = None,
    resinsightfile: Optional[str] = None,
    ertfile: Optional[str] = None,
) -> None:
    """Dump dataframe with ERT observations to CSV and/or YML
    format to disk. Writes to stdout if filenames are "-". Skips
    export if filenames are empty or None.

    Args:
        dframe
        csvfile: Filename
        yamlfile: Filename
        resinsightfile: Filename
        ertfile: Filename
    """

    if not (csvfile or yamlfile or resinsightfile or ertfile):
        logger.warning("No output filenames provided")
    if csvfile:
        if csvfile != __MAGIC_STDOUT__:
            logger.info("Writing observations as CSV to %s", csvfile)
            dframe.to_csv(csvfile, index=False)
        else:
            # Ignore pipe errors when writing to stdout:
            signal.signal(signal.SIGPIPE, signal.SIG_DFL)
            dframe.to_csv(sys.stdout, index=False)

    if yamlfile:
        obs_dict_for_yaml = df2obsdict(dframe)
        if not obs_dict_for_yaml and not dframe.empty:
            logger.error("None of your observations are supported in YAML")
        yaml_str = yaml.safe_dump(obs_dict_for_yaml)

        if yamlfile != __MAGIC_STDOUT__:
            logger.info(
                "Writing observations in YAML (webviz) format to file: %s", yamlfile
            )
            Path(yamlfile).write_text(yaml_str, encoding="utf8")
        else:
            print(yaml_str)

    if resinsightfile:
        ri_dframe = df2resinsight_df(dframe)
        if resinsightfile != __MAGIC_STDOUT__:
            logger.info(
                "Writing observations in ResInsight format to CSV-file: %s",
                resinsightfile,
            )
            ri_dframe.to_csv(resinsightfile, index=False, sep=";")
        else:
            # Ignore pipe errors when writing to stdout:
            signal.signal(signal.SIGPIPE, signal.SIG_DFL)
            ri_dframe.to_csv(sys.stdout, index=False, sep=";")

    if ertfile:
        ertobs_str = df2ertobs(dframe)
        if ertfile != __MAGIC_STDOUT__:
            logger.info("Writing ERT observation format to %s", ertfile)
            Path(ertfile).write_text(ertobs_str, encoding="utf8")
        else:
            print(ertobs_str)


class FmuObs(ErtScript):
    """This class defines the ERT workflow hook.

    It is constructed to work identical to the command line except

      * fmuobs is upper-cased to FMUOBS
      * All option names with double-dash must be enclosed in "" to avoid
        interference with the ERT comment characters "--".
    """

    # pylint: disable=too-few-public-methods
    def run(self, *args):
        # pylint: disable=no-self-use
        """Pass the ERT workflow arguments on to the same parser as the command
        line."""
        parser = get_parser()
        parsed_args = parser.parse_args(args)
        fmuobs(**vars(parsed_args))


@hook_implementation
def legacy_ertscript_workflow(config):
    """A hook for usage of this script in an ERT workflow,
    using the legacy hook format."""
    workflow = config.add_workflow(FmuObs, "FMUOBS")
    workflow.parser = get_parser
    workflow.description = DESCRIPTION
    workflow.examples = EXAMPLES
    workflow.category = CATEGORY


if __name__ == "__main__":
    main()
