# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
import sys
import os
import time
import hashlib

try:
    from StringIO import StringIO  # Python 2 import
except ImportError:
    from io import StringIO  # Python 3 import

EOL_UNIX = "\n"
EOL_WINDOWS = "\r\n"
EOL_MAC = "\r"


def _normalize_line_endings(lines, line_ending="unix"):
    """Normalize line endings to unix (\n), windows (\r\n) or mac (\r).
    Acceptable values are 'unix' (default), 'windows' and 'mac'.

    Args:
        lines: The lines to normalize.
        line_ending: The line ending format.

    Returns:
        Line endings normalized.

    """
    lines = lines.replace(EOL_WINDOWS, EOL_UNIX).replace(EOL_MAC, EOL_UNIX)
    if line_ending == "windows":
        lines = lines.replace(EOL_UNIX, EOL_WINDOWS)
    elif line_ending == "mac":
        lines = lines.replace(EOL_UNIX, EOL_MAC)
    return lines


def _remove_comments(clear_comments, tmp_in):
    """Remove comments, when needed, in the tmp_in string.
    In-line comments will not be removed.

    Args:
        clear_comments (bool): Boolean describing whether to remove comments.
        tmp_in (str): text to remove Eclipse comments.

    Returns:
        str: tmp_in or tmp_in without comments depending on clear_comments
    """
    tmp_out = tmp_in
    if clear_comments:
        if "--" in tmp_out:
            tmp_out = "%s\n" % tmp_out.split("--")[0]
    return tmp_out


def _check_filename_found(filename, org_sim_loc):
    """Check whether the supplied filename can be found either rdirectly,
    or as a relative path

    Args:
        filename (str): filename of the file
        org_sim_loc (str: Original simulation path

    Returns:
        str: converted file when successfull or,
        bool: False on failure

    """
    if not os.path.exists(filename):
        if os.path.exists(org_sim_loc + filename):
            filename = org_sim_loc + filename
            return filename
        else:
            sys.exit(
                "Script stopped: Could not open '%s'. Make sure you have read access "
                "for this file." % filename
            )
    else:
        return filename


def _md5checksum(filepath=None, data=None):
    """Perform an MD5 checksum on a file or a string

    Args:
        filepath (str): Path to a file to perform a checksum on
        data (str):  Text to perform a checksum on

    Returns:
        str: MD5 checksum

    """
    if data:
        fh = StringIO(data)
    elif filepath:
        fh = open(filepath, "rb")
    elif data and filepath:
        raise ValueError(
            "Cannot get both a file path and a data string; what should I checksum?"
        )
    else:
        raise ValueError(
            "Either a file path or data string need to be supplied. "
            "Nothing to checksum."
        )

    m = hashlib.md5()
    while True:
        data = fh.read(8192)
        data = _normalize_line_endings(data)
        if not data:
            break
        m.update(data)

    try:
        fh.close()
    except:
        pass

    return m.hexdigest()


def _get_paths(filename, org_sim_loc):
    """Method to scan for a PATHS keyword in the datafile
    Multiple paths can be defined in the keyword

    Args:
        filename (str): File to scan for PATHS keyword,
            can both be absolute or base filename
        org_sim_loc (str): Original simulation location

    Returns:
        dict: dictionary with PATHS

    """
    paths = {}

    # Check if the filename can be found
    filename = _check_filename_found(filename, org_sim_loc)

    # Try to open the file, if fail: show message to user
    try:
        f = open(filename, "r")
    except:
        print(
            "Script stopped: Could not open '%s'. Make sure you have read access "
            "for this file." % filename
        )
        return False

    # Read through all lines of text
    for line in f:
        line_strip = line.strip()

        if "PATHS" in line_strip[0:5]:
            print("Found Eclipse PATHS keyword, creating a dictionary.")

            # In the  keyword, find the path definitions and ignore comments
            for line in f:
                line_strip = line.strip()

                if line.split("--")[0].strip() == "/":
                    break

                if not len(line.strip()) == 0:
                    if "--" not in line_strip[0:3] and not len(line_strip) == 0:
                        # This should be a path definition :)

                        path_info = line.split("--")[0].strip().split("'")
                        paths[path_info[1]] = path_info[3]

    print("Dictionary created: ", end="")
    print(paths)

    f.close()

    return paths


def _replace_paths(text, paths):
    """Helper method to replace PATHS keys

    Args:
        text (str): String to replace path keys in
        paths (dict): Paths dictionary

    Returns:
        str: String with replaced keys

    """
    if "$" in text:
        for key in paths:
            text = text.replace("$" + key, paths[key])

    return text


def inspect_file(
    filename, org_sim_loc, packing_path, eclipse_paths, indent, clear_comments
):
    """Method that inspects a file for includes and copies the
    results to include folder

    Args:
        filename (str): filename to inspect
        org_sim_loc (str): original simulation path
        packing_path (str): path to pack simulation in
        eclipse_paths (str): PATHS dictionary
        indent (str): indent for output printing
        clear_comments (bool): comments or not.

    Returns:
        str: Modified text of include file.

    """
    global section
    global warnings
    global fmu_include

    # Check if the filename can be found
    filename = _check_filename_found(filename, org_sim_loc)

    # Try to open the file, if fail: show message to user
    try:
        f = open(filename, "r")
    except:
        print(
            "Script stopped: Could not open '%s'. Make sure you have read access for "
            "this file."
            % filename
        )
        return False

    # Modified text will be stored in new_data_file
    new_data_file = ""

    # Read through all lines of text
    for line in f:
        line = _normalize_line_endings(line)
        line_strip = line.strip()

        # Remove comments if required
        line_strip = _remove_comments(clear_comments, line_strip)
        line = _remove_comments(clear_comments, line)

        # if "INCLUDE" in line_strip[0:7].upper() or "GDFILE" in line_strip[0:6] or
        # "IMPORT" in line_strip[0:6]:
        if (
            line[0:7].upper() == "INCLUDE"
            or line[0:6] == "GDFILE"
            or line[0:6] == "IMPORT"
        ):
            # Include keyword found!
            print("%s%s" % (indent, "FOUND INCLUDE FILE ==>"))
            new_data_file += line

            # In the INCLUDE or GDFILE keyword, find the include path and
            # ignore comments
            for line in f:
                line_strip = line.strip()

                # Remove comments if required
                line_strip = _remove_comments(clear_comments, line_strip)
                line = _remove_comments(clear_comments, line)

                if not len(line.strip()) == 0:
                    if "--" not in line_strip[0:3] and not len(line_strip) == 0:
                        # This is the include file!
                        include_full = line_strip.split("--")[0]
                        if "'" in include_full or '"' in include_full:
                            include_stripped = include_full.split("'")[1].strip()
                        else:
                            include_stripped = include_full.split()[0].strip()

                        # Sometimes paths are entered in a Windows style, using \
                        # instead of /. Although this should not be done,
                        # Eclipse allows it.
                        include_stripped_in_file = include_stripped
                        include_stripped = include_stripped.replace("\\", "/")

                        # Inspect an INCLUDE file one layer deeper, return a
                        # modified INCLUDE file
                        print("%sInspecting %s..." % (indent, include_stripped))

                        # check if use has been made of eclipse paths
                        include_stripped = _replace_paths(
                            include_stripped, eclipse_paths
                        )

                        file_text = inspect_file(
                            include_stripped,
                            org_sim_loc,
                            packing_path,
                            eclipse_paths,
                            indent + "      ",
                            clear_comments,
                        )
                        try:
                            if file_text is False:
                                return False
                        except:
                            pass

                        print("%sFinished inspecting %s" % (indent, include_stripped))

                        new_include = "%s/include/%s%s" % (
                            packing_path,
                            section,
                            include_stripped.split("/")[-1],
                        )

                        # Write the results of the inspect to the include folder
                        print("%sWriting include file %s..." % (indent, new_include))

                        # Check if file already exists
                        if os.path.exists(new_include):

                            # Calculate MD5 hashes for the files with equal file names
                            # to be able to compare the contents
                            md5A = _md5checksum(filepath=new_include)
                            md5B = _md5checksum(data=file_text)

                            if md5A == md5B:
                                # Files are equal, skip
                                print(
                                    "%sIdentical files in packing folder, skipping %s"
                                    % (indent, new_include)
                                )

                            else:
                                # Add timestamp to the filename to make it unique
                                ts = int(time.time())
                                new_include += str(ts)

                                try:
                                    fw = open(new_include, "w")
                                    fw.write(file_text)
                                    fw.close()
                                    print(
                                        "%sfilename made unique with a timestamp (%s)."
                                        % (indent, ts)
                                    )
                                    print(
                                        "%sFinished writing include file %s"
                                        % (indent, new_include)
                                    )
                                except:
                                    print(
                                        "Script stopped: Could not write to '%s'. "
                                        "Make sure you have write access for "
                                        "this file." % new_include
                                    )
                                    return False
                        else:
                            try:
                                fw = open(new_include, "w")
                                fw.write(file_text)
                                fw.close()
                                print(
                                    "%sFinished writing include file %s"
                                    % (indent, new_include)
                                )
                            except:
                                print(
                                    "Script stopped: Could not write to '%s'. "
                                    "Make sure you have write access for "
                                    "this file." % new_include
                                )
                                return False

                        # Change the include path in the current file being inspected
                        if "'" in include_full or '"' in include_full:
                            new_data_file += line.replace(
                                include_stripped_in_file,
                                "%sinclude/%s%s"
                                % (fmu_include, section, new_include.split("/")[-1]),
                            )
                        else:

                            new_data_file += line.replace(
                                include_stripped_in_file,
                                "'%sinclude/%s%s'"
                                % (fmu_include, section, new_include.split("/")[-1]),
                            )

                        # Ignore comments after the include statement
                        break
                    else:
                        new_data_file += line
                        if "--" in line:
                            print(line)
        elif "RUNSPEC" == line_strip and fmu_include:
            section = "runspec/"
            if not os.path.exists("%s/include/%s" % (packing_path, section)):
                os.makedirs("%s/include/%s" % (packing_path, section))
            new_data_file += line
        elif "GRID" == line_strip and fmu_include:
            section = "grid/"
            if not os.path.exists("%s/include/%s" % (packing_path, section)):
                os.makedirs("%s/include/%s" % (packing_path, section))
            new_data_file += line
        elif "EDIT" == line_strip and fmu_include:
            section = "edit/"
            if not os.path.exists("%s/include/%s" % (packing_path, section)):
                os.makedirs("%s/include/%s" % (packing_path, section))
            new_data_file += line
        elif "PROPS" == line_strip and fmu_include:
            section = "props/"
            if not os.path.exists("%s/include/%s" % (packing_path, section)):
                os.makedirs("%s/include/%s" % (packing_path, section))
            new_data_file += line
        elif "REGIONS" == line_strip and fmu_include:
            section = "regions/"
            if not os.path.exists("%s/include/%s" % (packing_path, section)):
                os.makedirs("%s/include/%s" % (packing_path, section))
            new_data_file += line
        elif "SOLUTION" == line_strip and fmu_include:
            section = "solution/"
            if not os.path.exists("%s/include/%s" % (packing_path, section)):
                os.makedirs("%s/include/%s" % (packing_path, section))
            new_data_file += line
        elif "SUMMARY" == line_strip and fmu_include:
            section = "summary/"
            if not os.path.exists("%s/include/%s" % (packing_path, section)):
                os.makedirs("%s/include/%s" % (packing_path, section))
            new_data_file += line
        elif "SCHEDULE" == line_strip and fmu_include:
            section = "schedule/"
            if not os.path.exists("%s/include/%s" % (packing_path, section)):
                os.makedirs("%s/include/%s" % (packing_path, section))
            new_data_file += line
        elif "OPTIMIZE" == line_strip and fmu_include:
            section = "optimize/"
            if not os.path.exists("%s/include/%s" % (packing_path, section)):
                os.makedirs("%s/include/%s" % (packing_path, section))
            new_data_file += line
        elif "RESTART" in line_strip[0:7]:
            # This line defines a restart: raise a warning!
            print(
                "**********************************************************************"
            )
            print(
                "** WARNING: THE SIMULATION POSSIBLY DEPENDS ON A RESTART FILE!      **"
            )
            print(
                "** POSSIBLE CURES:                                                  **"
            )
            print(
                "** - MANUALLY COPY THE REQUIRED RESOURCES                           **"
            )
            print(
                "** - REMOVE THE RESTART DEPENDENCY                                  **"
            )
            print(
                "** - IGNORE IF WRONGLY DETECTED IN A RPTSOL KEYWORD                 **"
            )
            print(
                "**********************************************************************"
            )
            warnings += 1
            new_data_file += line
        elif "IMPFILE" in line_strip[0:6]:
            # This line defines a restart: raise a warning!
            print(
                "**********************************************************************"
            )
            print(
                "** WARNING: THE SIMULATION CONTAINS THE IMPFILE KEYWORD!            **"
            )
            print(
                "** POSSIBLE CURES:                                                  **"
            )
            print(
                "** - MANUALLY COPY THE REQUIRED RESOURCES AND MODIFY PATHS          **"
            )
            print(
                "** - REMOVE THE IMPFILE KEYWORD                                     **"
            )
            print(
                "**********************************************************************"
            )
            warnings += 1
            new_data_file += line
        elif "USEFLUX" in line_strip[0:6]:
            # This line defines a restart: raise a warning!
            print(
                "**********************************************************************"
            )
            print(
                "** WARNING: THE SIMULATION DEPENDS ON A USEFLUX FILE!               **"
            )
            print(
                "** POSSIBLE CURES:                                                  **"
            )
            print(
                "** - MANUALLY COPY THE REQUIRED RESOURCES AND MODIFY PATHS          **"
            )
            print(
                "** - REMOVE THE USEFLUX KEYWORD                                     **"
            )
            print(
                "**********************************************************************"
            )
            warnings += 1
            new_data_file += line
        else:
            if not (clear_comments and len(line.strip()) == 0):
                # This line represents anything else: just copy the info.
                new_data_file += line

    f.close()

    # Return modified text of inspected file
    return new_data_file


def pack_simulation(ecl_case, packing_path, clear_comments, fmu):
    """Method that will pack an Eclipse simulation DATA file.

    Args:
        ecl_case (str): Path to Eclipse simulation DATA file
        packing_path (str): Path to packing location
        clear_comments (bool): clear or not to clear comments
        fmu (bool): use fmu packing style or not

    Returns:
        bool: True is successful, False if failed.

    """
    global section
    global warnings
    global fmu_include

    section = ""
    warnings = 0
    fmu_include = ""

    if ecl_case == "":
        print("Script stopped: please supply a non-empty Eclipse DATA-file")
        return False

    if packing_path == "":
        print("Script stopped: please supply a non-empty packing path")
        return False
    try:
        packing_path = os.path.abspath(packing_path)
    except:
        print(
            "Script stopped: could not interpret the packing path '%s'" % packing_path
        )
        return False

    if clear_comments:
        print("You requested to clear all comments during the packing process.")
        print("NB: In-line comments behind slashes will NOT be removed.")

    if fmu:
        print("You requested FMU path style saving.")
        fmu_include = "../"

    # Increase maximum include depth to unrealistic high values
    sys.setrecursionlimit(10000)

    # Remove slash from packing path if needed
    if packing_path[-1] == "/":
        packing_path = packing_path[0:-1]

    # Get the original directory of the simulation
    org_sim_loc = os.path.dirname(ecl_case) + "/"

    # Create include folder in packing location
    if not os.path.exists("%s/include" % packing_path):
        os.makedirs("%s/include" % packing_path)

    fmu_data = ""
    if fmu:
        if not os.path.exists("%s/model" % packing_path):
            os.makedirs("%s/model" % packing_path)
        fmu_data = "model/"

    # Get paths from Eclipse PATHS keyword
    eclipse_paths = _get_paths(ecl_case, org_sim_loc)

    # Inspect the DATA file, return a modified DATA file
    data_file = inspect_file(
        ecl_case, org_sim_loc, packing_path, eclipse_paths, "", clear_comments
    )
    try:
        if data_file is False:
            return False
    except:
        pass

    data_file_name = ecl_case.split("/")[-1]
    path_new_data_file = "%s/%s%s" % (packing_path, fmu_data, data_file_name)

    # Write out DATA file if not already exists
    if os.path.exists(path_new_data_file):

        with open(path_new_data_file, "r") as f:
            content = f.read()

            if data_file == content:
                print("The DATA-file in place is identical. Did not re-save.")
            else:
                ts = int(time.time())
                path_new_data_file += str(ts)

                print("A unique number has been added in the name of the datafile.")
    try:
        # Do the actual writing of the output
        f = open("%s" % path_new_data_file, "w")
        f.write(data_file)
        f.close()
    except:
        print(
            "Script stopped: Could not write to '%s'. Make sure you have write access "
            "for this file."
            % path_new_data_file
        )

        return False

    # Print output to screen
    print("Modified %s and written output packing folder" % data_file_name)
    print("")
    print("*********************************************************************")
    if warnings == 0:
        print("SUCCESFULLY PACKED SIMULATION MODEL IN %s" % packing_path)
        return True
    else:
        print(
            "PACKED SIMULATION MODEL WITH %s WARNING(S) IN %s"
            % (warnings, packing_path)
        )
        print("PLEASE CHECK WARNING(S)!")
        return False


if __name__ == "__main__":
    pass
