import argparse
import hashlib
import logging
import shlex
import sys
import time
from io import StringIO
from pathlib import Path
from shutil import copy
from typing import Dict, List, Optional, TextIO, Union

from subscript import __version__, getLogger
from subscript.eclcompress.eclcompress import file_is_binary

logger = getLogger(__name__)

DESCRIPTION = """The script pack_sim will read trough a data file and copy all
include files to one include directory in the so-called packing
directory. It will also generate a new DATA file in the packing
directory with relative include paths. This way a simulation model can
be quickly packed to be, for example, distributed to a partner
company.  The script also works with include files in include files.
"""

EOL_UNIX = r"\n"
EOL_WINDOWS = r"\r\n"
EOL_MAC = r"\r"


def _read_lines(filename: Path) -> List[str]:
    try:
        with open(filename, encoding="utf-8") as fin:
            lines = fin.readlines()
    except UnicodeDecodeError:
        try:
            with open(filename, encoding="iso-8859-1") as fin:
                lines = fin.readlines()
        except ValueError as e:
            raise ValueError(
                f"Unsupported character encoding in file {filename}"
            ) from e
    return lines


def _normalize_line_endings(lines: str, line_ending: str = "unix"):
    """Normalize line endings to unix (\n), windows (\r\n) or mac (\r).
    Acceptable values are 'unix' (default), 'windows' and 'mac'.

    Args:
        lines: The lines to normalize as one long (multiline) string.
        line_ending: The line ending format.

    Returns:
        Multiline string with endings normalized.

    """
    lines = lines.replace(EOL_WINDOWS, EOL_UNIX).replace(EOL_MAC, EOL_UNIX)
    if line_ending == "windows":
        lines = lines.replace(EOL_UNIX, EOL_WINDOWS)
    elif line_ending == "mac":
        lines = lines.replace(EOL_UNIX, EOL_MAC)
    return lines


def _remove_comments(clear_comments: bool, tmp_in: str):
    """Remove comments, when needed, in the tmp_in string.
    In-line comments will not be removed.

    Args:
        clear_comments: Boolean describing whether to remove comments.
        tmp_in: text to remove Eclipse comments.

    Returns:
        tmp_in or tmp_in without comments depending on clear_comments
    """
    if clear_comments and "--" in tmp_in:
        return tmp_in.split("--")[0] + "\n"
    return tmp_in


def _expand_filename(filename: Path, org_sim_loc: Path) -> Path:
    """Check whether the supplied filename can be found either directly,
    or as a relative path

    Args:
        filename: filename of the file
        org_sim_loc: Original simulation path

    Returns:
        absolute path of an existing file

    Raises:
        IOError when file is not found or readable
    """
    if filename.exists():
        return filename
    if (org_sim_loc / filename).exists():
        return org_sim_loc / filename
    raise IOError(f"Could not open '{str(filename)}'. Make sure you have read access.")


def _md5checksum(
    filepath: Optional[Union[str, Path]] = None, data: Optional[str] = None
) -> Optional[str]:
    """Perform an MD5 checksum on a file or a string

    Checksums are made independent of line endings (win/unix), by removing
    all line-endings to unix style before sending to checksum algorithm.

    Args:
        filepath: Path to a file to perform a checksum on
        data:  Text to perform a checksum on

    Returns:
        str: MD5 checksum
    """

    def _md5_on_fhandle(fhandle: TextIO) -> str:
        md5hash = hashlib.md5()
        wholefile = str(fhandle.read())
        md5hash.update("".join(wholefile.splitlines()).encode("utf-8"))
        return md5hash.hexdigest()

    if data is not None and filepath is not None:
        raise ValueError(
            "Cannot get both a file path and a data string; what should I checksum?"
        )
    if data is not None:
        return _md5_on_fhandle(StringIO(data))
    if filepath is not None:
        with open(filepath, "r", encoding="utf8") as fhandle:
            return _md5_on_fhandle(fhandle)
    raise ValueError(
        "Either a file path or data string need to be supplied. Nothing to checksum."
    )


def _get_paths(filename: Path, org_sim_loc: Path) -> Dict[str, Path]:
    """Method to scan for a PATHS keyword in the datafile
    Multiple paths can be defined in the keyword

    Args:
        filename: File to scan for PATHS keyword,
            can both be absolute or base filename
        org_sim_loc: Original simulation location

    Returns:
        dictionary with PATHS

    """
    paths = {}

    # Check if the filename can be found
    filename = _expand_filename(filename, org_sim_loc)
    lines = _read_lines(filename)

    # Read through all lines of text
    for line in lines:
        line_strip = line.strip()

        if line_strip.startswith("PATHS"):
            logger.info("Found Eclipse PATHS keyword, creating a dictionary.")

            # In the keyword, find the path definitions and ignore comments
            for innerline in lines:
                line_strip = innerline.strip()
                if line_strip.startswith("--"):
                    continue

                if innerline.split("--")[0].strip() == "/":
                    # Finished reading the data for the PATHS keyword
                    break

                # Assume we have found a PATHS definition line
                try:
                    path_info = innerline.split("--")[0].strip().split("'")
                    paths[path_info[1]] = Path(path_info[3])
                except IndexError:
                    logger.warning(
                        "Could not parse %s as a PATHS definition, skipping",
                        line_strip,
                    )
    logger.debug("Dictionary created: %s", str(paths))
    return paths


def _replace_paths(text: Union[str, Path], paths: Dict[str, Path]) -> Path:
    """Helper method to replace PATHS keys

    Args:
        text: String to replace path keys in
        paths: Paths dictionary

    Returns:
        String with replaced keys

    """
    if "$" in str(text):
        for key in paths:
            text = str(text).replace("$" + key, str(paths[key]))
    return Path(text)


def inspect_file(
    filename: Path,
    org_sim_loc: Path,
    packing_path: Path,
    eclipse_paths: Dict[str, Path],
    indent: str = "",
    clear_comments: bool = False,
    fmu: bool = False,
    section: str = "",
) -> str:
    """Method that inspects a file for includes and copies the
    results to include folder. This can be both the main DATA file
    or it can be called recursively in order to inspect files
    that are included by the DATA file and below.

    Args:
        filename: filename to inspect
        org_sim_loc: original simulation path
        packing_path: path to pack simulation in
        eclipse_paths: PATHS dictionary
        indent: indent for output printing
        clear_comments: comments or not.
        fmu: flag for FMU directory layout
        section: currently active Eclipse section.

    Returns:
        Modified text of inspected file.

    """
    filename = _expand_filename(filename, org_sim_loc)

    # Modified text will be stored in new_data_file
    new_data_file = ""

    lines = iter(_read_lines(filename))
    for line in lines:
        line = _normalize_line_endings(line)
        line_strip = line.strip()

        # Remove comments if required
        line_strip = _remove_comments(clear_comments, line_strip)
        line_strip_no_comment = _remove_comments(True, line_strip).strip()
        line = _remove_comments(clear_comments, line)

        if line.upper().startswith(("INCLUDE", "GDFILE", "IMPORT")):
            # Include keyword found!
            logger.info("%s%s", indent, "FOUND INCLUDE FILE ==>")
            new_data_file += line

            # In the INCLUDE or GDFILE keyword, find the include path and
            # ignore comments, continuing iterating the same file handle
            # as in the outer loop:
            while True:
                try:
                    include_line = next(lines)
                except StopIteration:
                    break
                line_strip = include_line.strip()

                # Remove comments if required
                line_strip = _remove_comments(clear_comments, line_strip)
                include_line = _remove_comments(clear_comments, include_line)

                if len(include_line.strip()) != 0:
                    if "--" not in line_strip[0:3] and len(line_strip) != 0:
                        # This is the include file!
                        include_full = line_strip.split("--")[0]
                        include_stripped = Path(shlex.split(include_full)[0])

                        # Sometimes paths are entered in a Windows style, using \
                        # instead of /. Although this should not be done,
                        # Eclipse allows it.
                        include_stripped_in_file = include_stripped
                        include_stripped = Path(
                            str(include_stripped).replace("\\", "/")
                        )

                        # Inspect an INCLUDE file one layer deeper, return a
                        # modified INCLUDE file
                        logger.info("%sInspecting %s...", indent, include_stripped)

                        # check if use has been made of eclipse paths
                        include_stripped = _replace_paths(
                            include_stripped, eclipse_paths
                        )

                        new_include = (
                            packing_path / "include" / section / include_stripped.name
                        )

                        include_filename = _expand_filename(
                            include_stripped, org_sim_loc
                        )
                        if file_is_binary(include_filename):
                            logger.info(
                                "%sThe file %s seems to be binary; we'll simply copy "
                                "this file and skip scanning its contents.",
                                indent,
                                include_stripped,
                            )
                            copy(include_filename, new_include)
                        else:
                            file_text = inspect_file(
                                include_stripped,
                                org_sim_loc,
                                packing_path,
                                eclipse_paths,
                                indent + "      ",
                                clear_comments,
                                section=section,
                                fmu=fmu,
                            )
                            logger.info(
                                "%sFinished inspecting %s", indent, include_stripped
                            )

                            # Write the results of the inspect to the include folder
                            logger.info(
                                "%sWriting include file %s...", indent, new_include
                            )

                            # Check if file already exists
                            if new_include.exists():
                                # Calculate MD5 hashes for the files with equal file
                                # names to be able to compare the contents
                                md5a = _md5checksum(filepath=Path(new_include))
                                md5b = _md5checksum(data=file_text)

                                if md5a == md5b:
                                    # Files are equal, skip
                                    logger.info(
                                        "%sIdentical files in packing folder, "
                                        "skipping %s",
                                        indent,
                                        new_include,
                                    )

                                else:
                                    # Add timestamp to the filename to make it unique
                                    tstamp = int(time.time())
                                    new_include = Path(str(new_include) + str(tstamp))

                                    try:
                                        Path(new_include).write_text(
                                            file_text, encoding="utf8"
                                        )
                                        logger.info(
                                            "%sfilename made unique "
                                            "with a timestamp (%s).",
                                            indent,
                                            tstamp,
                                        )
                                        logger.info(
                                            "%sFinished writing include file %s",
                                            indent,
                                            new_include,
                                        )
                                    except IOError as orig_exc:
                                        raise IOError(
                                            "Script stopped: Could not write to "
                                            f"'{new_include}'. "
                                            "Make sure you have write access for "
                                            "this file."
                                        ) from orig_exc
                            else:
                                Path(new_include).write_text(file_text, encoding="utf8")
                                logger.info(
                                    "%sFinished writing include file %s",
                                    indent,
                                    new_include,
                                )
                        fmu_include = "../" if fmu else ""

                        # Change the include path in the current file being inspected
                        if "'" in include_full or '"' in include_full:
                            new_data_file += include_line.replace(
                                str(include_stripped_in_file),
                                f"{fmu_include}include/{section}{new_include.name}",
                            )
                        else:
                            new_data_file += include_line.replace(
                                str(include_stripped_in_file),
                                f"'{fmu_include}include/{section}{new_include.name}'",
                            )

                        # Ignore comments after the include statement
                        break
                    new_data_file += include_line
        elif line_strip_no_comment == "RUNSPEC" and fmu:
            section = "runspec/"
            (packing_path / "include" / section).mkdir(exist_ok=True)
            new_data_file += line
        elif line_strip_no_comment == "GRID" and fmu:
            section = "grid/"
            (packing_path / "include" / section).mkdir(exist_ok=True)
            new_data_file += line
        elif line_strip_no_comment == "EDIT" and fmu:
            section = "edit/"
            (packing_path / "include" / section).mkdir(exist_ok=True)
            new_data_file += line
        elif line_strip_no_comment == "PROPS" and fmu:
            section = "props/"
            (packing_path / "include" / section).mkdir(exist_ok=True)
            new_data_file += line
        elif line_strip_no_comment == "REGIONS" and fmu:
            section = "regions/"
            (packing_path / "include" / section).mkdir(exist_ok=True)
            new_data_file += line
        elif line_strip_no_comment == "SOLUTION" and fmu:
            section = "solution/"
            (packing_path / "include" / section).mkdir(exist_ok=True)
            new_data_file += line
        elif line_strip_no_comment == "SUMMARY" and fmu:
            section = "summary/"
            (packing_path / "include" / section).mkdir(exist_ok=True)
            new_data_file += line
        elif line_strip_no_comment == "SCHEDULE" and fmu:
            section = "schedule/"
            (packing_path / "include" / section).mkdir(exist_ok=True)
            new_data_file += line
        elif line_strip_no_comment == "OPTIMIZE" and fmu:
            section = "optimize/"
            (packing_path / "include" / section).mkdir(exist_ok=True)
            new_data_file += line
        elif line_strip_no_comment == "RESTART":
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
            new_data_file += line
        elif line_strip.startswith("IMPFILE"):
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
            new_data_file += line
        elif line_strip.startswith("USEFLUX"):
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
                "******************************************"
                "****************************"
            )
            new_data_file += line
        else:
            if not (clear_comments and len(line.strip()) == 0):
                # This line represents anything else: just copy the info.
                new_data_file += line

    # Return modified text of inspected file
    return new_data_file


def pack_simulation(
    ecl_case: Path, packing_path: Path, clear_comments: bool, fmu: bool
) -> None:
    """Method that will pack an Eclipse simulation DATA file.

    Args:
        ecl_case: Path to Eclipse simulation DATA file
        packing_path: Path to packing location (directory)
        clear_comments: clear or not to clear comments
        fmu: use fmu packing style or not

    """
    if ecl_case == "":
        raise ValueError("Script stopped: please supply a non-empty Eclipse DATA-file")

    if packing_path == "":
        raise ValueError("Script stopped: please supply a non-empty packing path")

    # This can raise IOError
    packing_path = packing_path.absolute()

    if clear_comments:
        logger.info("You requested to clear all comments during the packing process.")
        logger.warning("NB: In-line comments behind slashes will NOT be removed.")

    if fmu:
        logger.info("You requested FMU path style saving.")

    # Increase maximum include depth to unrealistic high values
    sys.setrecursionlimit(10000)

    # Get the original directory of the simulation
    org_sim_loc = ecl_case.parent

    # Create include folder in packing location
    (packing_path / "include").mkdir(parents=True, exist_ok=True)

    if fmu:
        (packing_path / "model").mkdir(parents=True, exist_ok=True)

    # Get paths from Eclipse PATHS keyword
    eclipse_paths = _get_paths(ecl_case, org_sim_loc)

    # Inspect the DATA file, return a modified DATA file
    data_file = inspect_file(
        ecl_case, org_sim_loc, packing_path, eclipse_paths, "", clear_comments, fmu=fmu
    )
    if not data_file:
        raise ValueError("Script stopped: no text was found in the DATA deck.")

    data_file_name = Path(ecl_case).name

    if fmu:
        path_new_data_file = packing_path / "model" / data_file_name
    else:
        path_new_data_file = packing_path / data_file_name

    # Write out DATA file if not already exists
    if path_new_data_file.exists():
        raise ValueError(
            f"DATA file {str(path_new_data_file)} exists already, will not overwrite."
        )

    path_new_data_file.write_text(data_file)

    # Print output to screen
    logger.info(
        "Written modificated %s to packing folder %s",
        str(data_file_name),
        str(packing_path),
    )


def get_parser() -> argparse.ArgumentParser:
    """Function to create the argument parser that is going to be served to the user.

    Returns:
        argparse.ArgumentParser: The argument parser to be served

    """
    parser = argparse.ArgumentParser(prog="pack_sim.py", description=DESCRIPTION)
    parser.add_argument(
        "ECLIPSE_CASE", type=str, help="Name of the Eclipse case to be packed "
    )
    parser.add_argument(
        "PACKING_PATH",
        type=str,
        help="Path towards the directory where the packed simulation model "
        "should end up.",
    )
    parser.add_argument(
        "-c",
        "--clearcomments",
        action="store_true",
        help="Set this switch (only -c, no further input required) to clear all "
        "comments during packing.",
    )
    parser.add_argument(
        "-fmu",
        "--fmu",
        default=False,
        action="store_true",
        help="Set this switch (only -fmu, no further input required) to save the the "
        "Eclipse model in standard fmu file structure (model/ and include/grid, "
        "include/props, etc folders)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + __version__ + ")",
    )
    return parser


def main() -> None:
    """Parse command line arguments and run"""
    parser = get_parser()
    args = parser.parse_args()
    logger.setLevel(logging.INFO)
    pack_simulation(
        Path(args.ECLIPSE_CASE), Path(args.PACKING_PATH), args.clearcomments, args.fmu
    )


if __name__ == "__main__":
    main()
