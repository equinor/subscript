import argparse
from pathlib import Path
import tempfile
import fnmatch
import shutil
import xml.dom.minidom
import re
import logging

import rips
import grpc
from subscript import getLogger

DESCRIPTION = """
``ri_wellmod`` is a utility to generate Eclipse well model definitions
(WELSPECS/WELSPECL, COMPDAT/COMPDATL, WELSEGS, COMPSEGS) using ResInsight. The script
takes as input a ResInsight project with wells and completions defined, in addition to
an Eclipse case (either an initialized case or an input case with grid and PERMX|Y|Z
and NTG defined in the GRDECL format).

.. note:: Well names specified as command line arguments are assumed to refer to the
   Eclipse well names, i.e., the completion export names as defined in the ResInsight
   wells project.
"""

CATEGORY = "modelling.reservoir"

EXAMPLES = """
.. code-block:: console

 FORWARD_MODEL RI_WELLMOD(
    <RI_PROJECT>=<CONFIG_PATH>/../../resinsight/input/well_modelling/wells.rsp,
    <ECLBASE>=<ECLBASE>,
    <OUTPUTFILE>=<RUNPATH>/eclipse/include/schedule/well_def.sch)

 FORWARD_MODEL RI_WELLMOD(
    <RI_PROJECT>=<CONFIG_PATH>/../../resinsight/input/well_modelling/wells.rsp,
    <ECLBASE>=<ECLBASE>,
    <OUTPUTFILE>=<RUNPATH>/eclipse/include/schedule/well_def.sch,
    <MSW>="A2;A4;'R*')

 FORWARD_MODEL RI_WELLMOD(
    <RI_PROJECT>=<CONFIG_PATH>/../../resinsight/input/well_modelling/wells.rsp,
    <ECLBASE>=<ECLBASE>,
    <OUTPUTFILE>=<RUNPATH>/eclipse/include/schedule/well_def.sch,
    <MSW>="A4",
    <XARG0>="--lgr",
    <XARG1>="A4:3;3;1")


.. warning:: Remember to remove line breaks in argument list of copying the examples
   into your own ERT config.


.. note:: More examples and options may be seen in the subscript docs for the script
   ``ri_wellmod``, just replace ',' by ';' and note that spaces cannot be part of
   argument strings, so you may need to use <XARGn> for the individual parts.

"""


logger = getLogger(__name__)

RI_HOME = "/prog/ResInsight"
DEFAULT_VERSION = "2020.10.1"


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """
    Multiple inheritance used for argparse to get both
    defaults and raw description formatter
    """

    # pylint: disable=unnecessary-pass
    pass


def get_resinsight_exe(version=DEFAULT_VERSION):
    """
    Return the path to a valid ResInsight install, False if not found.
    """
    ri_exe = shutil.which("ResInsight")
    if ri_exe is not None:
        return ri_exe

    ri_exe = shutil.which("resinsight")
    if ri_exe is not None:
        return ri_exe

    ri_exe = Path(RI_HOME + "/resinsight_" + version + "_RHEL7/ResInsight")
    if ri_exe.exists():
        return ri_exe

    return False


def get_parser():
    """
    Utility function to build the cmdline argument parser using argparse
    (https://docs.python.org/3/library/argparse.html)
    """

    description = """
Utility script for creating Eclipse well definitions using ResInsight.
"""
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument("--verbose", "-vb", action="store_true", help="Verbose output")
    parser.add_argument(
        "--silent", "-s", action="store_true", help="Silence non-critical messages"
    )
    parser.add_argument("--debug", "-d", action="store_true", help="Debug mode")
    parser.add_argument(
        "well_project", help="Path to project with well paths and completions defined."
    )
    parser.add_argument("ecl_case", help="Path to initialized Eclipse case.")
    parser.add_argument(
        "--property_files",
        nargs="*",
        help="Additional input property files for PERM/NTG (GRDECL format)",
    )
    parser.add_argument(
        "--output_file",
        "-o",
        default="well_defs.sch",
        help="Output file (default=well_defs.sch)",
    )
    parser.add_argument(
        "--tmpfolder",
        "-tmp",
        default="resinsight/ri_completions",
        help="Output folder (default=tmp_ri_completions)",
    )
    parser.add_argument(
        "--wells",
        "-w",
        nargs="+",
        default=None,
        help="Optional comma-separated list of wells (wildcards allowed) to generate completions \
            for (default=all wells in project)",
    )
    parser.add_argument(
        "--msw_wells",
        "-msw",
        nargs="+",
        default=None,
        help="Optional comma-separated list of wells (wildcards allowed) to generate msw \
            well definitions for (default=none)",
    )
    parser.add_argument(
        "--lgr",
        "-l",
        nargs="*",
        help="Optional list of comma-separated LGR specs: WELLNAME:REF_I,REF_J,REF_K \
          (wildcards allowed in well names)",
    )
    parser.add_argument(
        "--lgr_output_file",
        "-lo",
        default="well_lgr_defs.inc",
        help="Well LGR output file (default=well_lgr_defs.sch)",
    )
    parser.add_argument(
        "--time_step",
        "-t",
        default=0,
        help="Optional selection of time step to use for completion export (default=0)",
    )
    parser.add_argument(
        "--resinsight_version",
        "-rv",
        default=DEFAULT_VERSION,
        help="Optional ResInsight version to use (default=" + DEFAULT_VERSION + ")",
    )
    parser.add_argument(
        "--dummy",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    return parser


def select_matching_strings(pattern_list, string_list):
    """
    Utility function to select mathching strings (fnmatch wildcard style)

    :param pattern_list: List of fnmatch-style patterns
    :param string_list: List of strings to check for match

    :return: List of unique strings string_list matching any element in pattern_list
    """
    all_matching = []
    for pattern in pattern_list:
        for cur_string in string_list:
            if fnmatch.fnmatchcase(cur_string, pattern):
                all_matching.append(cur_string)

    # Ensure unique elements
    matching_string_set = set(all_matching)

    return list(matching_string_set)


def is_init_case(ecl_case):
    """
    Check if input Eclipse case name corresponds to an initialized Eclipse run.

    :param ecl_case: Run name (or path) to check (file name with suffix ok)

    :return: True/False
    """
    ecl_path = Path(ecl_case)
    has_grid = (
        ecl_path.with_suffix(".EGRID").exists()
        or ecl_path.with_suffix(".GRID").exists()
    )
    has_init = ecl_path.with_suffix(".INIT").exists()
    return has_grid and has_init


def has_restart_file(ecl_case):
    """
    Check if ecl_case has a restart file
    (Currently required for LGR creation, to be fixed in next ResInsight release )
    """
    ecl_path = Path(ecl_case)
    return (
        ecl_path.with_suffix(".UNRST").exists()
        or ecl_path.with_suffix(".X0000").exists()
    )


def rsp_extract_export_names(well_project, well_path_names):
    """
    Extract export well names from ResInsight project

    :param well_project: ResInsight project (rsp) file
    :param well_path_names: List of well names (as returned by the RI instance)

    :return: Dict export_name[well_path_name] = export_name
    """
    doc = xml.dom.minidom.parse(well_project)
    name_nodes = doc.getElementsByTagName("WellNameForExport")
    export_names = [node.childNodes[0].nodeValue for node in name_nodes]
    if len(export_names) != len(well_path_names):
        logger.error("Could not find export names for all wells - returning empty dict")
        return {}

    return dict(zip(export_names, well_path_names))


def decode_lgr_spec(spec):
    """
    Decode LGR spec and return as parsed tuple. For ERT FM replace ',' by ';'.

    :param spec: LGR spec in the format 'wname:ref_i,ref_j,ref_k'

    :return: Tuple (str, int, int, int) if well-formed, None if not
    """
    tokens = re.split(",|:|;", spec.strip())
    if len(tokens) != 4:
        logger.warning("Malformed LGR spec string: %s", spec)
        return None
    wname = tokens[0]
    try:
        ref_i = int(tokens[1])
        ref_j = int(tokens[2])
        ref_k = int(tokens[3])
    except ValueError:
        logger.warning("Unable to integer valued refinements from LGR spec %s", spec)
        return None

    return (wname, ref_i, ref_j, ref_k)


def split_arg_string(arg_string):
    """
    Split an arg string of formats 'str1,str2,str3' or 'str1|str2|str3'
    """
    return [tok.strip() for tok in re.split(r",|;", arg_string.strip())]


def main():
    """
    Main function
    """
    parser = get_parser()
    args = parser.parse_args()

    debug = args.debug
    verbose = args.verbose
    silent = args.silent
    well_project = args.well_project
    ecl_case = args.ecl_case
    input_property_files = args.property_files
    tmp_output_folder = args.tmpfolder
    output_file = args.output_file
    lgr_output_file = args.lgr_output_file
    wells = args.wells
    msw_wells = args.msw_wells
    lgr_specs = args.lgr

    time_step = args.time_step
    version = args.resinsight_version

    # Use tempfile.mkdtemp to ensure unique output folders
    tmp_output_folder = Path(tmp_output_folder)
    tmp_output_folder.mkdir(parents=True, exist_ok=True)
    tmp_output_folder = tempfile.mkdtemp(dir=tmp_output_folder)

    if debug:
        logger.setLevel(logging.DEBUG)
    elif verbose:
        logger.setLevel(logging.INFO)
    elif silent:
        logger.setLevel(logging.CRITICAL)

    ecl_path = Path(ecl_case)
    command_line_parameters = []
    console_mode = True
    init_case = is_init_case(ecl_path)

    # Check that any input case has 'grdecl' extension for case and props
    if not init_case:
        input_files = [ecl_case]
        if input_property_files is not None:
            input_files.extend(input_property_files)
        for input_file in input_files:
            if Path(input_file).suffix.upper() != ".GRDECL":
                logger.error(
                    "Input files must have the extension '.grdecl' or '.GRDECL' for \
                        ResInsight to recognize it as an Eclipse input property file."
                )
                return 1

    # Until fix in next ResInsight release: Exit if requesting lgr without .UNRST
    # Also requires GUI versions
    if lgr_specs is not None and len(lgr_specs) > 0:
        if not (init_case and has_restart_file(ecl_path)):
            logger.error(
                "Can currently only create LGRs for init cases with restart file present \
            (to be fixed in April 2021 ResInsight release)"
            )
            return 1

        console_mode = False

    # Input cases must be loaded by a cmdline workaround
    if not init_case:
        command_line_parameters += ["--project", well_project]
        command_line_parameters += ["--case", ecl_case]
        command_line_parameters += input_property_files

        logger.debug("Command line parameters are: %s", command_line_parameters)
        logger.info("Launching ResInsight: %s", get_resinsight_exe(version))

    # Try twice - occationally times out on busy compute nodes
    try:
        resinsight = rips.Instance.launch(
            resinsight_executable=get_resinsight_exe(version),
            console=console_mode,
            command_line_parameters=command_line_parameters,
        )
    except Exception as any_exception:  # pylint: disable=broad-except
        logger.warning(
            "ResInsight cannot start - error %s - will try once more..", any_exception
        )
        resinsight = rips.Instance.launch(
            resinsight_executable=get_resinsight_exe(version),
            console=console_mode,
            command_line_parameters=command_line_parameters,
        )

    if resinsight is None:
        logger.error(
            "Could not launch ResInsight - \
            please check the executable %s.",
            get_resinsight_exe(version),
        )
        return 1

    try:
        resinsight.set_export_folder("COMPLETIONS", str(tmp_output_folder))

        if init_case:
            proj = resinsight.project.open(well_project)
            case = proj.load_case(str(ecl_path.with_suffix(".EGRID")))
        else:
            proj = resinsight.project
            case = proj.cases()[-1]

        ri_case_name = proj.cases()[-1].name
        logger.debug("Working on the case named %s...", ri_case_name)

        all_well_path_names = [w.name for w in proj.well_paths()]
        exportname2wellpathname = rsp_extract_export_names(
            well_project, all_well_path_names
        )
        export_well_names = exportname2wellpathname.keys()

        well_path_names = all_well_path_names
        if wells is not None:
            well_patterns = []
            for well_spec in wells:
                well_patterns.extend(split_arg_string(well_spec))

            export_well_names = select_matching_strings(
                well_patterns, export_well_names
            )
            well_path_names = [
                exportname2wellpathname[well] for well in export_well_names
            ]

        # Need to gather all wells with LGR and call 'create_lgr_for_completions' once,
        # else the previous LGRs will be deleted on the next call
        lgr_well_path_names = []
        if lgr_specs is not None and len(lgr_specs) > 0:
            for lgr_spec in lgr_specs:
                spec_tuple = decode_lgr_spec(lgr_spec)
                if spec_tuple is None:
                    logger.warning("Malformed LGR spec %s ignored", lgr_spec)
                    continue

                logger.info("Creating LGR from %s: ", lgr_spec)
                wname, ref_i, ref_j, ref_k = spec_tuple
                lgr_export_well_names = select_matching_strings(
                    [wname], export_well_names
                )
                lgr_well_path_names.extend(
                    [
                        exportname2wellpathname[ewname]
                        for ewname in lgr_export_well_names
                    ]
                )

            logger.debug(
                "Trying to create LGR at time step %d for the well paths %s",
                time_step,
                lgr_well_path_names,
            )
            case.create_lgr_for_completion(
                time_step,
                lgr_well_path_names,
                ref_i,
                ref_j,
                ref_k,
                split_type="LGR_PER_WELL",
            )

        case.export_well_path_completions(
            time_step, well_path_names, file_split="SPLIT_ON_WELL"
        )

        logger.debug(
            "Completion files for case %s exported \
                to folder %s.",
            (ecl_path.parent / ecl_path.stem),
            tmp_output_folder,
        )

        resinsight.exit()

    except grpc.RpcError as grpc_error:
        resinsight.exit()
        logger.error("Server exception while running ResInsight: %s", grpc_error)

    except Exception as any_exception:  # pylint: disable=broad-except
        resinsight.exit()
        logger.error(
            "Unknown exception trying to run ResInsight - check logs..: %s",
            any_exception,
        )

        return 1

    # Gather ResInsight-generated output files in a single output file
    msw_well_names = []
    if msw_wells is not None:
        msw_well_patterns = []
        for msw_pattern in msw_wells:
            msw_well_patterns.extend(split_arg_string(msw_pattern))

        logger.debug("Looking for the following MSW wells: %s", msw_well_patterns)

        msw_well_exportnames = select_matching_strings(
            msw_well_patterns, export_well_names
        )
        msw_well_names = [exportname2wellpathname[msw] for msw in msw_well_exportnames]

        logger.debug("Found the following MSW wells: %s", msw_well_names)

    def get_exported_perf_filename(well_name, ri_case_name):
        """
        Get file name of exported perforation completion file
        """
        perf_fn = well_name + "_UnifiedCompletions_" + ri_case_name
        perf_fn = perf_fn.replace("/", "_")
        perf_fn = perf_fn.replace(" ", "_")
        return Path(tmp_output_folder) / perf_fn

    def get_exported_msw_filename(well_name, ri_case_name):
        """
        Get file name of exported msw completion file
        """
        perf_fn = well_name + "_UnifiedCompletions_MSW_" + ri_case_name
        perf_fn = perf_fn.replace("/", "_")
        perf_fn = perf_fn.replace(" ", "_")
        return Path(tmp_output_folder) / perf_fn

    def get_lgr_spec_filename(lgr_well_path):
        """
        Get file name of exported LGR for a given well path
        """
        lgr_spec_fn = "LGR_" + lgr_well_path + ".dat"
        lgr_spec_fn = lgr_spec_fn.replace("/", "_")
        lgr_spec_fn = lgr_spec_fn.replace(" ", "_")
        return Path(tmp_output_folder) / lgr_spec_fn

    ri_case_name = ri_case_name.replace(".", "_")
    with open(output_file, "w") as out_fd:
        for well in well_path_names:
            perf_fn = get_exported_perf_filename(well, ri_case_name)

            # Need to check if LGR perfs exists, in case of non-LGR wells intersecting
            # well LGRs, or in case of LGRs present in the init case
            perf_fn_exists = False
            lgr_perf_fn = Path(str(perf_fn) + "_LGR")
            if Path(lgr_perf_fn).exists():
                perf_fn = lgr_perf_fn
                perf_fn_exists = True
                logger.debug("Found LGR completion file %s", lgr_perf_fn)

            if perf_fn_exists or Path(perf_fn).exists():
                with open(perf_fn, "r") as perf_fd:
                    shutil.copyfileobj(perf_fd, out_fd)
            else:
                logger.debug("No completion file found for well %s", well)
                logger.debug("   Expected file: %s", perf_fn)
                logger.debug(
                    "   (This could just mean no completions intersect the grid"
                )

            if well in msw_well_names:
                msw_fn = get_exported_msw_filename(well, ri_case_name)
                if Path(msw_fn).exists():
                    with open(msw_fn, "r") as msw_fd:
                        shutil.copyfileobj(msw_fd, out_fd)
                else:
                    logger.debug("No msw completion file found for well %s", well)
                    logger.debug("   Expected file: %s", msw_fn)
                    logger.debug(
                        "   (This could just mean no completions intersect the grid"
                    )

    logger.info("Completions exported to %s", output_file)
    if not silent:
        print(
            """
    Completions exported to {}

""".format(
                output_file
            )
        )

    # Finally, collect LGR files
    if lgr_specs is not None and len(lgr_specs) > 0:
        with open(lgr_output_file, "w") as out_fd:
            for lgr_well_path in lgr_well_path_names:
                lgr_spec_fn = get_lgr_spec_filename(lgr_well_path)
                if Path(lgr_spec_fn).exists():
                    with open(lgr_spec_fn, "r") as lgr_fd:
                        # shutil.copyfileobj(lgr_fd, out_fd)
                        # Ugly hack to get around 'multiple-wells-in-lgr'
                        # For now, assuming 5 wells in each LGR is sufficient..
                        txt = lgr_fd.read()
                        print(txt.replace(" /\n", "    5 /\n"), file=out_fd)
                else:
                    logger.debug(
                        "No LGR spec file found for well path %s", lgr_well_path
                    )

        logger.info("LGR specifications exported to %s", lgr_output_file)
        if not silent:
            print(
                """
    Well LGR definitions exported to {}
            """.format(
                    lgr_output_file
                )
            )

    return 0


if __name__ == "__main__":
    main()
