import argparse
from pathlib import Path
import os
import tempfile
import fnmatch
import shutil
import xml.dom.minidom
import re
import logging
import sys
import inspect
from importlib import reload
from typing import Optional, Tuple, List, Set
from types import ModuleType
from subscript import getLogger, __version__
import grpc

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import rips  # noqa: E402

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
    <MSW>="A2;A4;'R*'")

 FORWARD_MODEL RI_WELLMOD(
    <RI_PROJECT>=<CONFIG_PATH>/../../resinsight/input/well_modelling/wells.rsp,
    <ECLBASE>=<ECLBASE>,
    <OUTPUTFILE>=<RUNPATH>/eclipse/include/schedule/well_def.sch,
    <MSW>="A4",
    <XARG0>="--lgr",
    <XARG1>="A4:3;3;1")


.. warning:: Remember to remove line breaks in argument list when copying the
   examples into your own ERT config.


.. note:: More examples and options may be seen in the subscript docs for the script
   ``ri_wellmod``, just replace ',' by ';' and note that spaces cannot be part of
   argument strings, so you may need to use <XARGn> for the individual parts.

"""


logger = getLogger(__name__)

RI_HOME = "/prog/ResInsight"
WRAPPER_TEMPLATE = """
#!/bin/bash
unset LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/prog/ResInsight/6.14-3_odb_api/lib
"""


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """
    Multiple inheritance used for argparse to get both
    defaults and raw description formatter
    """

    # pylint: disable=unnecessary-pass
    pass


def get_resinsight_exe() -> Optional[str]:
    """
    Return the path to a ResInsight executable (or wrapper script), None if not found.
    """
    ri_exe = shutil.which("ResInsight")
    if ri_exe is not None:
        return ri_exe

    ri_exe = shutil.which("resinsight")
    if ri_exe is not None:
        return ri_exe

    return None


def get_rips_version_triplet() -> Tuple[int, int, str]:
    """
    Get the rips (client-side) version, without instanciating/launching ResInsight
    """
    major = rips.instance.RiaVersionInfo.RESINSIGHT_MAJOR_VERSION
    minor = rips.instance.RiaVersionInfo.RESINSIGHT_MINOR_VERSION
    patch = rips.instance.RiaVersionInfo.RESINSIGHT_PATCH_VERSION
    return (major, minor, patch)


def find_and_wrap_resinsight_version(
    version_triplet: Tuple[int, int, str]
) -> Optional[str]:
    """
    Find a ResInsight executable matching at least the major.minor version
    of the version triplet, and create a temporary wrapper that may be used to
    launch this particular version.

    NB! The caller is responsible for deleting the temporary wrapper

    :param version_triplet: (major, minor, patch)

    :return: Path to temporary wrapper or None if not found
    """
    (major, minor, patch) = version_triplet  # pylint: disable=unused-variable
    ri_home_path = Path(RI_HOME)

    def _find_ri_exe(pattern: str) -> Optional[Path]:
        """
        Utility function to search for the ResInsight executable
        """
        cand_dirs = [x for x in ri_home_path.glob(pattern) if x.is_dir()]
        for cand_dir in cand_dirs:
            logger.debug("Checking for valid ResInsight version in %s", cand_dir)
            resinsight_exe = cand_dir / Path("ResInsight")
            if resinsight_exe.exists():
                return resinsight_exe

        return None

    # First, search for full match, including patch version
    resinsight_exe = _find_ri_exe(f"*{major}.{minor}.{patch}*")
    if not resinsight_exe:
        # Then try to find a matching major.minor
        resinsight_exe = _find_ri_exe(f"*{major}.{minor}*")

    if not resinsight_exe:
        return None

    logger.info("Found ResInsight version: %s", resinsight_exe)

    wrapper_file = tempfile.NamedTemporaryFile(delete=False)
    with open(wrapper_file.name, "w") as fhandle:
        print(WRAPPER_TEMPLATE, file=fhandle)
        print(f'{resinsight_exe} "$@"', file=fhandle)
        fhandle.flush()
    os.chmod(wrapper_file.name, 0o770)
    wrapper_file.close()
    logger.debug("Created ResInsight wrapper file: %s", wrapper_file.name)

    return wrapper_file.name


def launch_resinsight(console_mode: bool, command_line_parameters: List[str]):
    """
    Try to launch a version of ResInsight matching the client version

    :return: A resinsight instance, or False if launch was not successfull
    """
    cmajor, cminor, cpatch = get_rips_version_triplet()
    logger.debug(
        "Client-side library (rips) version is: %s.%s.%s", cmajor, cminor, cpatch
    )

    # Start with trying to find standard install, then search RI_HOME
    resinsight_exe = get_resinsight_exe()
    wrapper = False
    if not resinsight_exe:
        # Get rips version
        rips_version_triplet = get_rips_version_triplet()
        resinsight_exe = find_and_wrap_resinsight_version(rips_version_triplet)
        if not resinsight_exe:
            return False
        wrapper = True

    # First launch attempt (always try twice, occationally times out on busy nodes)
    try:
        resinsight = rips.Instance.launch(
            resinsight_executable=resinsight_exe,
            console=console_mode,
            command_line_parameters=command_line_parameters,
        )
    except Exception as any_exception:  # pylint: disable=broad-except
        if (
            len(any_exception.args) > 3
            and any_exception.args[0].find("Wrong Version") >= 0
        ):
            server_version_triplet = any_exception.args[2].split(".")
            smajor, sminor, spatch = server_version_triplet
            logger.error(
                "Wrong ResInsight version - found (%s.%s.%s), requires (%s.%s.*)",
                smajor,
                sminor,
                spatch,
                cmajor,
                cminor,
            )
            if (
                wrapper
            ):  # If already tried via wrapper, no need to search, just try again
                logger.debug(
                    "Trying to launch ResInsight wrapper again: %s", resinsight_exe
                )
                try:  # Second launch attempt via wrapper
                    resinsight = rips.Instance.launch(
                        resinsight_executable=resinsight_exe,
                        console=console_mode,
                        command_line_parameters=command_line_parameters,
                    )
                except Exception as any_exception:  # pylint: disable=broad-except
                    Path(resinsight_exe).unlink()  # Delete wrapper
                    logger.error(str(any_exception))
                    return False
            else:  # Not via wrapper - try to find a valid install and wrap it
                resinsight_exe = find_and_wrap_resinsight_version(
                    get_rips_version_triplet()
                )
                if not resinsight_exe:
                    return False
                wrapper = True
                try:  # First launch attempt via wrapper
                    resinsight = rips.Instance.launch(
                        resinsight_executable=resinsight_exe,
                        console=console_mode,
                        command_line_parameters=command_line_parameters,
                    )
                except Exception as any_exception:  # pylint: disable=broad-except
                    logger.error(str(any_exception))
                    try:  # Second launch attempt via wrapper
                        resinsight = rips.Instance.launch(
                            resinsight_executable=resinsight_exe,
                            console=console_mode,
                            command_line_parameters=command_line_parameters,
                        )
                    except Exception as any_exception:  # pylint: disable=broad-except
                        Path(resinsight_exe).unlink()
                        logger.error(str(any_exception))
                        return False
        else:  # Not a version error, just try a second time
            try:
                resinsight = rips.Instance.launch(
                    resinsight_executable=resinsight_exe,
                    console=console_mode,
                    command_line_parameters=command_line_parameters,
                )
            except Exception as any_exception:  # pylint: disable=broad-except
                logger.error(str(any_exception))
                return False

    if wrapper:
        Path(resinsight_exe).unlink()

    return resinsight


def find_candidate_modules(top_path: Path) -> Set[str]:
    """
    Find candidate python modules below a specified top path (which must
    be a member of sys.path)

    (candidate modules are here simply defined as directories or .py files)

    :return: set of importable names, empty set if top_path not in sys.path
    """
    mod_names: Set[str] = set()
    if str(top_path) not in sys.path:
        return mod_names

    for root, dirs, files in os.walk(top_path):
        for dname in dirs:
            mod_names.add(dname)
        for fname in files:
            pyfile_name = Path(fname)
            if pyfile_name.suffix == ".py":
                mod_names.add(pyfile_name.stem)

    return mod_names


def deep_reload(
    module: ModuleType, top_path: Path, loaded: Set = set(), ok_names: Set[str] = None
):
    """
    Deep module reload constrained to names possibly found in a given folder
    """
    if not ok_names:
        ok_names = find_candidate_modules(top_path)

    logger.debug(
        "Trying to reload module %s (previously in %s)", module.__name__, module
    )
    mod_name = module.__name__.rsplit(".")[-1]
    if inspect.ismodule(module):
        if mod_name not in ok_names:
            logger.debug("Module %s not found below top path specified")
            return
        reload(module)

    for name in dir(module):
        member = getattr(module, name)
        if inspect.ismodule(member) and member not in loaded:
            loaded.add(module)
            if name in ok_names:
                logger.debug("Recursively reloading module %s", name)
                deep_reload(member, top_path, loaded, ok_names)


def launch_resinsight_dev(
    resinsightdev: str, console_mode: bool, command_line_parameters: List[str]
):
    """
    Launch development version of ResInsight
    """
    ripath = Path(resinsightdev)
    if not ripath.exists():
        logger.error(
            "Specified development version of ResInsight does not exist: %s",
            resinsightdev,
        )
        return 1
    ridir = ripath.parent
    pypath = ridir / Path("Python")
    if pypath.exists():  # Use development rips, if present
        sys.path.insert(0, str(ridir))
        sys.path.insert(0, str(pypath))
        deep_reload(rips, pypath)
        sys.path.pop(0)
    try:
        resinsight = rips.Instance.launch(
            resinsight_executable=resinsightdev,
            console=console_mode,
            command_line_parameters=command_line_parameters,
        )
    except Exception as any_exception:  # pylint: disable=broad-except
        logger.error("Unable to launch development version of ResInsight")
        logger.error("  (Exception was: %s)", str(any_exception))
        resinsight = None

    return resinsight


def get_parser() -> argparse.ArgumentParser:
    """
    Utility function to build the cmdline argument parser using argparse
    (https://docs.python.org/3/library/argparse.html)
    """

    description = (
        "Utility script for creating Eclipse well definitions using ResInsight."
    )
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
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
        default="resinsight/ri_completions",
        help="Output folder (default=resinsight/ri_completions)",
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
        "--msw",
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
        default="well_lgr_defs.inc",
        help="Well LGR output file (default=well_lgr_defs.sch)",
    )
    parser.add_argument(
        "--with-resinsight-dev",
        help="Use specified development version of ResInsight (full path to binary)",
    )
    parser.add_argument(
        "--time_step",
        "-t",
        default=0,
        help="Optional selection of time step to use for completion export (default=0)",
    )
    parser.add_argument(
        "--dummy",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + __version__ + ")",
    )
    return parser


def select_matching_strings(
    pattern_list: List[str], string_list: List[str]
) -> List[str]:
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


def is_init_case(ecl_case: Path) -> bool:
    """
    Check if input Eclipse case name corresponds to an initialized Eclipse run.

    :param ecl_case: Run name (or path) to check (file name with suffix ok)
    """
    ecl_path = Path(ecl_case)
    has_grid = (
        ecl_path.with_suffix(".EGRID").exists()
        or ecl_path.with_suffix(".GRID").exists()
    )
    has_init = ecl_path.with_suffix(".INIT").exists()
    return has_grid and has_init


def has_restart_file(ecl_case: Path) -> bool:
    """
    Check if ecl_case has a restart file
    (Currently required for LGR creation, to be fixed in next ResInsight release )
    """
    ecl_path = Path(ecl_case)
    return (
        ecl_path.with_suffix(".UNRST").exists()
        or ecl_path.with_suffix(".X0000").exists()
    )


def rsp_extract_export_names(well_project: str, well_path_names: List[str]):
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


def decode_lgr_spec(spec: str) -> Optional[Tuple[str, int, int, int]]:
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


def split_arg_string(arg_string: str) -> list:
    """
    Split an arg string of formats 'str1,str2,str3' or 'str1|str2|str3'
    """
    return [tok.strip() for tok in re.split(r",|;", arg_string.strip())]


def main() -> int:
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
    resinsightdev = args.with_resinsight_dev
    wells = args.wells
    msw_wells = args.msw
    lgr_specs = args.lgr

    time_step = args.time_step

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

    # Until fix in next ResInsight release for LGR cases, exit if:
    #  * No X display (unable to start with GUI)
    #  * No .UNRST
    if lgr_specs is not None and len(lgr_specs) > 0:
        has_display = "DISPLAY" in os.environ and os.environ["DISPLAY"]
        if not has_display and not resinsightdev:
            logger.error("Currently LGR creation requires an X display (GUI mode).")
            return 1
        if not (init_case and has_restart_file(ecl_path)):
            logger.error(
                "Can currently only create LGRs for init cases with restart file."
            )
            return 1

        console_mode = resinsightdev is not None

    # Input cases must be loaded by a cmdline workaround
    if not init_case:
        command_line_parameters += ["--project", well_project]
        command_line_parameters += ["--case", ecl_case]
        command_line_parameters += input_property_files
        logger.debug("Command line parameters are: %s", command_line_parameters)

    # Launch ResInsight
    if resinsightdev:  # Use development version
        resinsight = launch_resinsight_dev(
            resinsightdev, console_mode, command_line_parameters
        )
    else:  # Launch standard version
        resinsight = launch_resinsight(console_mode, command_line_parameters)
    if not resinsight:
        logger.error(
            "Could not launch ResInsight - run with debug flag and examine output."
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

    def get_exported_perf_filename(well_name: str, ri_case_name: str) -> Path:
        """
        Get file name of exported perforation completion file
        """
        perf_fn = well_name + "_UnifiedCompletions_" + ri_case_name
        perf_fn = perf_fn.replace("/", "_")
        perf_fn = perf_fn.replace(" ", "_")
        return Path(tmp_output_folder) / perf_fn

    def get_exported_msw_filename(well_name: str, ri_case_name: str) -> Path:
        """
        Get file name of exported msw completion file
        """
        perf_fn = well_name + "_UnifiedCompletions_MSW_" + ri_case_name
        perf_fn = perf_fn.replace("/", "_")
        perf_fn = perf_fn.replace(" ", "_")
        return Path(tmp_output_folder) / perf_fn

    def get_lgr_spec_filename(lgr_well_path: str) -> Path:
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
