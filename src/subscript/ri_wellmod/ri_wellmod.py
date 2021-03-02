#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
"""
 ri_wellmod.py


"""
import sys
import argparse
import os.path
import fnmatch
import shutil
import xml.dom.minidom

import rips

RI_HOME = '/prog/ResInsight'
DEFAULT_VERSION='2020.10.1'
RI_EXE = lambda version: RI_HOME+'/resinsight_'+version+'_RHEL7/ResInsight'


def _build_argument_parser():
    """
    Utility function to build the cmdline argument parser using argparse
    (https://docs.python.org/3/library/argparse.html)
    """

    description = """
  Script description.
"""
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument(
        '--verbose',
        '-vb',
        action='store_true',
        help='Verbose output'
        )
    parser.add_argument(
        '--silent',
        '-s',
        action='store_true',
        help='Silence non-critical messages'
        )
    parser.add_argument(
        '--debug',
        '-d',
        action='store_true',
        help='Debug mode'
        )
    parser.add_argument(
            'well_project',
            help='Path to project with well paths and completions defined.'
    )
    parser.add_argument(
            'ecl_case',
            help='Path to initialized Eclipse case.'
    )
    parser.add_argument(
        '--property_files',
        nargs='*',
        help='Additional input property files for PERM/NTG (GRDECL format)'
    )
    parser.add_argument(
        '--output_file',
        '-o',
        default='welldefs.sch',
        help='Ouptput file (default=welldefs.sch)'
    )
    parser.add_argument(
        '--tmpfolder',
        '-tmp',
        default='ri_completions',
        help='Output folder (default=tmp_ri_completions)'
    )
    parser.add_argument(
        '--wells',
        '-w',
        default=None,
        help='Optional comma-separated list of wells (wildcards allowed) to generate completions \
            for (default=all wells in project)'
    )
    parser.add_argument(
        '--msw_wells',
        '-msw',
        default=None,
        help='Optional comma-separated list of wells (wildcards allowed) to generate msw \
            well definitions for (default=none)'
    )
    parser.add_argument(
        '--time_step',
        '-t',
        default=0,
        help='Optional selection of time step to use for completion export (default=0)'
    )
    parser.add_argument(
        '--version',
        '-v',
        default=DEFAULT_VERSION,
        help='Optional ResInsight version to use (default='+DEFAULT_VERSION+')'
    )

    return parser

def select_matching_strings(pattern_list, string_list):
    """
    Utility function to select mathching strings (fnmath wildcard style)

    :param pattern_list: List of fnmatch-style patterns
    :param string_list: List of strings to check for match

    :return: List of unique strings from string_list matching any pattern in pattern_list
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

    :param ecl_case: Run name to check (file name with suffix ok)

    :return: True/False
    """
    ecl_name = os.path.splitext(ecl_case)[0]
    has_grid = os.path.exists(ecl_name + ".EGRID") or os.path.exists(ecl_name + ".GRID")
    has_init = os.path.exists(ecl_name + ".INIT")
    return has_grid and has_init

def rsp_extract_export_names(well_project, well_path_names):
    """
    Extract export well names from ResInsight project 

    :param well_project: ResInsight project (rsp) file
    :param well_path_names: List of well names (as returned by the RI instance)

    :return: Dict export_name[well_path_name] = export_name
    """
    doc = xml.dom.minidom.parse(well_project)
    name_nodes = doc.getElementsByTagName('WellNameForExport')
    export_names = [node.childNodes[0].nodeValue for node in name_nodes]
    if len(export_names) != len(well_path_names):
        print("ERROR: Could not find export names for all wells - returning empty dict")
        return {}

    return dict(zip(export_names, well_path_names))


def main():
    """
    Main function
    """
    parser = _build_argument_parser()
    args = parser.parse_args()

    debug = args.debug
    verbose = args.verbose
    silent = args.silent
    well_project = args.well_project
    ecl_case = args.ecl_case
    input_property_files = args.property_files
    tmp_output_folder = args.tmpfolder
    output_file = args.output_file
    wells = args.wells
    msw_wells = args.msw_wells
    time_step = args.time_step
    version = args.version

    ecl_case_name = os.path.splitext(ecl_case)[0]
    command_line_parameters = []
    init_case = is_init_case(ecl_case_name)
    if not init_case:
        command_line_parameters += ['--project', well_project]
        command_line_parameters += ['--case', ecl_case]
        command_line_parameters += input_property_files
        if debug:
            print("INFO: Command line parameters are: ", command_line_parameters)

    # @TODO Detect if this is an initialized case (GRID/EGRID + INIT), otherwise assumed input case

    if verbose or debug:
        print("Launching ResInsight: {}".format(RI_EXE(version)))

    resinsight = rips.Instance.launch(resinsight_executable=RI_EXE(version), console=True,
      command_line_parameters=command_line_parameters)

    if resinsight is None:
        print("ERROR: Could not launch ResInsight - \
            please check the executable {}.".format(RI_EXE(version)))
        return 1

    try:
        resinsight.set_export_folder("COMPLETIONS", tmp_output_folder)

        if init_case:
            proj = resinsight.project.open(well_project)            
            case = proj.load_case(ecl_case_name + ".EGRID")
        else:
            proj = resinsight.project
            case = proj.cases()[0]

        ri_case_name = proj.cases()[0].name
        #case.export_well_path_completions(time_step, well_path_names, file_split="UNIFIED_FILE")
        #case.name = "ECLIPSE" # NO EFFECT, UNFORTUNATELY...

        all_well_path_names = [w.name for w in proj.well_paths()]
        exportname2wellpathname = rsp_extract_export_names(well_project, all_well_path_names)
        export_well_names = exportname2wellpathname.keys()

        if wells is not None:
            well_patterns = [x.strip() for x in wells.split(sep=',')]
            export_well_names = select_matching_strings(well_patterns, export_well_names)
            well_path_names = [exportname2wellpathname[well] for well in export_well_names]


        case.export_well_path_completions(time_step, well_path_names, file_split="SPLIT_ON_WELL")

        if debug:
            print("Completion files for case {} exported \
                to folder {}.".format(ecl_case_name, tmp_output_folder))

        resinsight.exit()

    except Exception as any_exception:  # pylint: disable=broad-except
        resinsight.exit()
        print("ERROR: Unknown exception trying to run ResInsight - check logs..: {}".format(
            any_exception))
        return 1

    # Gather ResInsight-generated output files in a single output file


    msw_well_names = []
    if msw_wells is not None:
        msw_well_patterns = [x.strip() for x in msw_wells.split(sep=',')]
        if debug:
            print("DEBUG: Looking for the following MSW wells: {}".format(msw_well_patterns))
        msw_well_exportnames = select_matching_strings(msw_well_patterns, export_well_names)
        msw_well_names = [exportname2wellpathname[msw] for msw in msw_well_exportnames]
        if debug:
            print("DEBUG: Found the following MSW wells: {}".format(msw_well_names))

    
    def get_exported_perf_filename(well_name, ri_case_name):
        """
        Get file name of exported perforation completion file
        """
        perf_fn = well_name + "_UnifiedCompletions_" + ri_case_name
        return os.path.join(tmp_output_folder, perf_fn)

    def get_exported_msw_filename(well_name, ri_case_name):
        """
        Get file name of exported msw completion file
        """
        perf_fn = well_name + "_UnifiedCompletions_MSW_" + ri_case_name
        return os.path.join(tmp_output_folder, perf_fn)

    ri_case_name = ri_case_name.replace('.','_')
    with open(output_file, 'w') as out_fd:
        for well in well_path_names:
            perf_fn = get_exported_perf_filename(well, ri_case_name)
            if os.path.exists(perf_fn):            
                with open(perf_fn, 'r') as perf_fd:
                    shutil.copyfileobj(perf_fd, out_fd)
            elif debug:
                print("WARNING: No completion file found for well {}".format(well))
                print("         Expected file: {}".format(perf_fn))

            if well in msw_well_names:
                msw_fn = get_exported_msw_filename(well, ri_case_name)
                if os.path.exists(msw_fn):
                    with open(msw_fn, 'r') as msw_fd:
                        shutil.copyfileobj(msw_fd, out_fd)
                elif debug:
                    print("WARNING: No msw completion file found for well {}".format(well))
                    print("         Expected file: {}".format(msw_fn))

    if not silent:
        print("INFO: Completions exported to {}".format(output_file))

    return 0


if __name__ == '__main__':
    sys.exit(main())
