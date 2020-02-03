import sys
import os
import shutil
from cwrap import open as copen
import io

## Find completions from COMDAT


def get_well_list(schedule_file_list):
    well_list = []

    return well_list


def remove_GASLIFTOPT(schedule_file_list):

    for FILENAME in schedule_file_list:

        # Check if the FILENAME can be found
        # This can be both relative or absolute, do check!
        if not os.path.exists(FILENAME):
            print("Schedule file does not exist!", " ")

        f = open(FILENAME, "r")

        # pre-check for LIFTOPT
        contains_LIFTOPT = False
        for line in f:
            line_strip = line.strip()
            new_line = line
            if "LIFTOPT" in line_strip[0:7]:
                contains_LIFTOPT = True

        f.close()

        if contains_LIFTOPT:

            f = open(FILENAME, "r")
            f_new = open(FILENAME + "_NO_LIFTOPT", "w")

            # Read through all lines of text
            for line in f:
                line_strip = line.strip()
                new_line = line
                if "LIFTOPT" in line_strip[0:7]:
                    f_new.write("-- " + new_line)
                    f_new.write("-- **************************************** --\n")
                    f_new.write("-- Removed for USEFLUX applications\n")
                    f_new.write("-- **************************************** --\n")

                    for line in f:
                        line_strip = line.strip()
                        new_line = line
                        f_new.write("-- " + new_line)
                        line_elements = line_strip.split()
                        if "/" in line_elements:
                            break

                elif "GLIFTOPT" in line_strip[0:8]:
                    f_new.write("-- " + new_line)

                    for line in f:
                        line_strip = line.strip()
                        new_line = line
                        f_new.write("-- " + new_line)
                        line_elements = line_strip.split()

                        if "/" in line_elements[0]:
                            break

                elif "WLIFTOPT" in line_strip[0:8]:
                    f_new.write("-- " + new_line)

                    for line in f:
                        line_strip = line.strip()
                        new_line = line
                        f_new.write("-- " + new_line)
                        line_elements = line_strip.split()

                        if "/" in line_elements[0]:
                            break

                else:
                    f_new.write(new_line)

            f_new.close()
            f.close()


def find_completions(schedule_file_list, clearcomments=False):

    # Array of completion triplets
    completions = []
    well_list = []

    for FILENAME in schedule_file_list:

        # Check if the FILENAME can be found
        # This can be both relative or absolute, do check!
        if not os.path.exists(FILENAME):
            print("Schedule file does not exist!", " ")
            return completions, well_list

        # Try to open the file, if fail: show message to user
        f = io.open(FILENAME, "r", encoding="latin_1")

        # Read through all lines of text
        for line in f:

            line_strip = line.strip()

            # Remove comments if required
            # line_strip = removecomments(clearcomments,line_strip)
            # line = removecomments(clearcomments,line)
            if "COMPDAT" in line_strip[0:7]:
                # COMPDAT keyword found!
                # new_data_file = new_data_file + line

                for line in f:
                    line_strip = line.strip()

                    # Remove comments if required
                    # line_strip = removecomments(clearcomments,line_strip)
                    # line = removecomments(clearcomments,line)

                    if not len(line.strip()) == 0:
                        # Breaks on /
                        if "/" in line_strip[0]:
                            break

                        if not "--" in line_strip[0:3] and not len(line_strip) == 0:

                            if not " /" in line_strip:
                                print(
                                    "ERROR: COMPDAT line not completed with /! Check formating ..."
                                )
                                sys.exit(1)

                            # Start reading completions
                            line_base = line_strip.split(" /")[0]
                            compdat_elements = line_base.split()

                            wellname_strip = compdat_elements[0].strip("'")

                            # print well name
                            # print wellname_strip, " "

                            # Chack if well is not in the well_list
                            if wellname_strip not in well_list:

                                # Adds to well list
                                well_list.append(wellname_strip)
                                # Creates a list
                                completions.append([])

                                for k in range(
                                    int(compdat_elements[3]),
                                    int(compdat_elements[4]) + 1,
                                ):
                                    comp_ijk = (
                                        int(compdat_elements[1]) - 1,
                                        int(compdat_elements[2]) - 1,
                                        k - 1,
                                    )

                                    if not comp_ijk in completions[-1]:
                                        completions[-1].append(comp_ijk)

                            elif wellname_strip in well_list:
                                ind = well_list.index(wellname_strip)

                                for k in range(
                                    int(compdat_elements[3]),
                                    int(compdat_elements[4]) + 1,
                                ):
                                    comp_ijk = (
                                        int(compdat_elements[1]) - 1,
                                        int(compdat_elements[2]) - 1,
                                        k - 1,
                                    )

                                    if not comp_ijk in completions[ind]:
                                        completions[ind].append(comp_ijk)

        # close file in schedule_file_list
        f.close()

    # Return completions in the schedule file list
    return completions, well_list


def replace_completions(
    schedule_file_list,
    scale_i=1,
    scale_j=1,
    shift_i=0,
    shift_j=0,
    max_i=100000,
    max_j=100000,
):

    for FILENAME in schedule_file_list:

        # Check if the FILENAME can be found
        # This can be both relative or absolute, do check!
        if not os.path.exists(FILENAME):
            print("Schedule file does not exist!", " ")
            return completions, well_list

        f = open(FILENAME, "r")
        f_new = open(FILENAME + "_new", "w")

        new_lines = []

        # Read through all lines of text
        for line in f:

            ## Progress updates
            # print line

            new_line = line
            line_strip = line.strip()

            # Remove comments if required
            # line_strip = removecomments(clearcomments,line_strip)
            # line = removecomments(clearcomments,line)
            if "COMPDAT" in line_strip[0:7]:
                # COMPDAT keyword found!
                # new_data_file = new_data_file + line

                new_lines.append(new_line)
                f_new.write(new_line)

                for line in f:

                    new_line = line
                    line_strip = line.strip()

                    # Breaks on /
                    if "/" in line_strip[0]:
                        new_lines.append(new_line)
                        f_new.write(new_line)
                        break

                    if not len(line.strip()) == 0:

                        if not "--" in line_strip[0:2] and not len(line_strip) == 0:

                            # Start reading completions
                            line_base = line_strip.split(" /")[0]
                            compdat_elements = line_base.split()

                            # ECL coordinates !
                            new_compdat_element_i = (
                                int(compdat_elements[1]) - shift_i
                            ) * scale_i - (scale_i - 1)
                            new_compdat_element_j = (
                                int(compdat_elements[2]) - shift_j
                            ) * scale_j - (scale_j - 1)

                            if new_compdat_element_i < 1:
                                new_compdat_element_i = 1

                            if new_compdat_element_i > max_i:
                                new_compdat_element_i = max_i

                            if new_compdat_element_j < 1:
                                new_compdat_element_j = 1

                            if new_compdat_element_j > max_j:
                                new_compdat_element_j = max_j

                            compdat_elements[1] = str(new_compdat_element_i)
                            compdat_elements[2] = str(new_compdat_element_j)

                            ##                            new_line = "  ".join(compdat_elements)

                            new_line = "  "

                            for element in compdat_elements:
                                new_line = new_line + "     " + element

                            new_line = new_line + "     /\n"

                            new_lines.append(new_line)
                            f_new.write(new_line)

                            wellname_strip = compdat_elements[0].strip("'")

                            # print well name
                            print(wellname_strip, " ")

                        else:
                            new_lines.append(new_line)
                            f_new.write(new_line)

                    else:
                        new_lines.append(new_line)
                        f_new.write(new_line)

            elif "WPIMULT" in line_strip[0:7]:

                new_lines.append(new_line)
                f_new.write(new_line)

                for line in f:

                    new_line = line
                    line_strip = line.strip()

                    # Breaks on /
                    if "/" in line_strip[0]:
                        new_lines.append(new_line)
                        f_new.write(new_line)
                        break

                    if not len(line.strip()) == 0:

                        if not "--" in line_strip[0:2] and not len(line_strip) == 0:

                            # Start reading completions
                            line_base = line_strip.split(" /")[0]
                            compdat_elements = line_base.split()

                            if (
                                len(compdat_elements) > 4
                                and "*" not in compdat_elements[2]
                                and "*" not in compdat_elements[3]
                            ):

                                # ECL coordinates !
                                new_compdat_element_i = (
                                    int(compdat_elements[2]) - shift_i
                                ) * scale_i - (scale_i - 1)
                                new_compdat_element_j = (
                                    int(compdat_elements[3]) - shift_j
                                ) * scale_j - (scale_j - 1)

                                if new_compdat_element_i < 1:
                                    new_compdat_element_i = 1

                                if new_compdat_element_i > max_i:
                                    new_compdat_element_i = max_i

                                if new_compdat_element_j < 1:
                                    new_compdat_element_j = 1

                                if new_compdat_element_j > max_j:
                                    new_compdat_element_j = max_j

                                compdat_elements[2] = str(new_compdat_element_i)
                                compdat_elements[3] = str(new_compdat_element_j)

                                ##                                new_line = "  ".join(compdat_elements)

                                new_line = "  "

                                for element in compdat_elements:
                                    new_line = new_line + "     " + element

                                new_line = new_line + "     /\n"

                                new_lines.append(new_line)
                                f_new.write(new_line)

                                wellname_strip = compdat_elements[0].strip("'")

                                # print well name
                                # print wellname_strip, " "

                            else:
                                new_lines.append(new_line)
                                f_new.write(new_line)

                        else:
                            new_lines.append(new_line)
                            f_new.write(new_line)

                    else:
                        new_lines.append(new_line)
                        f_new.write(new_line)

            elif "WELSPECS" in line_strip[0:8]:
                # WELSPECS keyword found!
                # new_data_file = new_data_file + line

                new_lines.append(new_line)
                f_new.write(new_line)

                for line in f:

                    new_line = line
                    line_strip = line.strip()

                    # Breaks on /
                    if "/" in line_strip[0]:
                        new_lines.append(new_line)
                        f_new.write(new_line)
                        break

                    if not len(line.strip()) == 0:

                        if not "--" in line_strip[0:2] and not len(line_strip) == 0:

                            # Start reading completions
                            line_base = line_strip.split(" /")[0]
                            compdat_elements = line_base.split()

                            # ECL coordinates !
                            new_compdat_element_i = (
                                int(compdat_elements[2]) - shift_i
                            ) * scale_i - (scale_i - 1)
                            new_compdat_element_j = (
                                int(compdat_elements[3]) - shift_j
                            ) * scale_j - (scale_j - 1)

                            if new_compdat_element_i < 1:
                                new_compdat_element_i = 1

                            if new_compdat_element_i > max_i:
                                new_compdat_element_i = max_i

                            if new_compdat_element_j < 1:
                                new_compdat_element_j = 1

                            if new_compdat_element_j > max_j:
                                new_compdat_element_j = max_j

                            compdat_elements[2] = str(new_compdat_element_i)
                            compdat_elements[3] = str(new_compdat_element_j)

                            new_line = "  "

                            for element in compdat_elements:
                                new_line = new_line + "     " + element

                            new_line = new_line + "     /\n"

                            new_lines.append(new_line)
                            f_new.write(new_line)

                            wellname_strip = compdat_elements[0].strip("'")

                            # print well name
                            print(wellname_strip, " ")

                        else:
                            new_lines.append(new_line)
                            f_new.write(new_line)

                    else:
                        new_lines.append(new_line)
                        f_new.write(new_line)

            else:
                new_lines.append(new_line)
                f_new.write(new_line)

        f.close()
        f_new.close()


def replace_completions_down(schedule_file_list, shift_x=0, shift_y=0, shift_z=0):

    for FILENAME in schedule_file_list:

        # Check if the FILENAME can be found
        # This can be both relative or absolute, do check!
        if not os.path.exists(FILENAME):
            print("Schedule file does not exist!", " ")
            return completions, well_list

        f = open(FILENAME, "r")
        f_new = open(FILENAME + "_shifted", "w")

        new_lines = []

        # Read through all lines of text
        for line in f:

            ## Progress updates
            # print line

            new_line = line
            line_strip = line.strip()

            # Remove comments if required
            # line_strip = removecomments(clearcomments,line_strip)
            # line = removecomments(clearcomments,line)
            if "COMPDAT" in line_strip[0:7]:
                # COMPDAT keyword found!
                # new_data_file = new_data_file + line

                new_lines.append(new_line)
                f_new.write(new_line)

                for line in f:

                    new_line = line
                    line_strip = line.strip()

                    # Breaks on /
                    if "/" in line_strip[0]:
                        new_lines.append(new_line)
                        f_new.write(new_line)
                        break

                    if not len(line.strip()) == 0:

                        if not "--" in line_strip[0:2] and not len(line_strip) == 0:

                            # Start reading completions
                            line_base = line_strip.split(" /")[0]
                            compdat_elements = line_base.split()

                            # ECL coordinates !
                            new_compdat_element_i = int(compdat_elements[1]) + shift_x
                            new_compdat_element_j = int(compdat_elements[2]) + shift_y
                            new_compdat_element_k = int(compdat_elements[3]) + shift_z
                            new_compdat_element_k_2 = int(compdat_elements[4]) + shift_z

                            compdat_elements[1] = str(new_compdat_element_i)
                            compdat_elements[2] = str(new_compdat_element_j)
                            compdat_elements[3] = str(new_compdat_element_k)
                            compdat_elements[4] = str(new_compdat_element_k_2)

                            ##                            new_line = "  ".join(compdat_elements)

                            new_line = "  "

                            for element in compdat_elements:
                                new_line = new_line + "     " + element

                            new_line = new_line + "     /\n"

                            new_lines.append(new_line)
                            f_new.write(new_line)

                            wellname_strip = compdat_elements[0].strip("'")

                            # print well name
                            # print wellname_strip, " "

                        else:
                            new_lines.append(new_line)
                            f_new.write(new_line)

                    else:
                        new_lines.append(new_line)
                        f_new.write(new_line)

            elif "WPIMULT" in line_strip[0:7]:

                new_lines.append(new_line)
                f_new.write(new_line)

                for line in f:

                    new_line = line
                    line_strip = line.strip()

                    # Breaks on /
                    if "/" in line_strip[0]:
                        new_lines.append(new_line)
                        f_new.write(new_line)
                        break

                    if not len(line.strip()) == 0:

                        if not "--" in line_strip[0:2] and not len(line_strip) == 0:

                            # Start reading completions
                            line_base = line_strip.split(" /")[0]
                            compdat_elements = line_base.split()

                            if (
                                len(compdat_elements) > 4
                                and "*" not in compdat_elements[2]
                                and "*" not in compdat_elements[3]
                            ):

                                # ECL coordinates !
                                new_compdat_element_i = (
                                    int(compdat_elements[2]) + shift_x
                                )
                                new_compdat_element_j = (
                                    int(compdat_elements[3]) + shift_y
                                )
                                new_compdat_element_k = (
                                    int(compdat_elements[4]) + shift_z
                                )

                                compdat_elements[2] = str(new_compdat_element_i)
                                compdat_elements[3] = str(new_compdat_element_j)
                                compdat_elements[4] = str(new_compdat_element_k)

                                ##                                new_line = "  ".join(compdat_elements)

                                new_line = "  "

                                for element in compdat_elements:
                                    new_line = new_line + "     " + element

                                new_line = new_line + "     /\n"

                                new_lines.append(new_line)
                                f_new.write(new_line)

                                wellname_strip = compdat_elements[0].strip("'")

                                # print well name
                                # print wellname_strip, " "

                            else:
                                new_lines.append(new_line)
                                f_new.write(new_line)

                        else:
                            new_lines.append(new_line)
                            f_new.write(new_line)

                    else:
                        new_lines.append(new_line)
                        f_new.write(new_line)

            elif "WELSPECS" in line_strip[0:8]:
                # WELSPECS keyword found!
                # new_data_file = new_data_file + line

                new_lines.append(new_line)
                f_new.write(new_line)

                for line in f:

                    new_line = line
                    line_strip = line.strip()

                    # Breaks on /
                    if "/" in line_strip[0]:
                        new_lines.append(new_line)
                        f_new.write(new_line)
                        break

                    if not len(line.strip()) == 0:

                        if not "--" in line_strip[0:2] and not len(line_strip) == 0:

                            # Start reading completions
                            line_base = line_strip.split(" /")[0]
                            compdat_elements = line_base.split()

                            # ECL coordinates !
                            new_compdat_element_i = int(compdat_elements[2]) + shift_x
                            new_compdat_element_j = int(compdat_elements[3]) + shift_y

                            compdat_elements[2] = str(new_compdat_element_i)
                            compdat_elements[3] = str(new_compdat_element_j)

                            new_line = "  "

                            for element in compdat_elements:
                                new_line = new_line + "     " + element

                            new_line = new_line + "     /\n"

                            new_lines.append(new_line)
                            f_new.write(new_line)

                            wellname_strip = compdat_elements[0].strip("'")

                            # print well name
                            print(wellname_strip, " ")

                        else:
                            new_lines.append(new_line)
                            f_new.write(new_line)

                    else:
                        new_lines.append(new_line)
                        f_new.write(new_line)

            else:
                new_lines.append(new_line)
                f_new.write(new_line)

        f.close()
        f_new.close()


def find_schedule_files(DATAFile, clearcomments=False):

    file_list = []

    fin = open(DATAFile, "r")
    DATAFile_dir = os.path.dirname(os.path.abspath(DATAFile))

    file_list.append(DATAFile)

    for line in fin:

        line_strip = line.strip()

        if "SCHEDULE" in line_strip[0:8]:

            for line in fin:
                line_strip = line.strip()

                if "INCLUDE" in line_strip[0:7]:

                    for line in fin:

                        line_strip = line.strip()

                        if "/" in line_strip[0]:
                            break

                        if not len(line_strip) == 0:
                            if not "--" in line_strip[0:2]:
                                # Striping down filename string, but keeping "/" in path name
                                line_base = line_strip.rsplit("'", 1)[0]
                                line_base = line_base + "'"
                                line_base_strip = line_base.strip().strip("'").strip()

                                file_path = line_base_strip

                                if not os.path.isfile(file_path):
                                    file_path = DATAFile_dir + "/" + line_base_strip

                                    # print file_path

                                    if not os.path.isfile(file_path):
                                        print(
                                            "ERROR: Not able to find path for INCLUDE file"
                                        )
                                        print(file_path)
                                        sys.exit(1)

                                    # Creates storage dir for include files
                                    if not os.path.isdir("./include"):
                                        os.makedirs("./include")

                                    new_file_path = "./include/" + os.path.basename(
                                        file_path
                                    )
                                    shutil.copy2(file_path, new_file_path)

                                    file_list.append(new_file_path)
                                    break

                                file_list.append(file_path)
                                break

    fin.close()

    return file_list


def find_non_completed_wells(
    schedule_file_list, well_alias_list=(), clearcomments=False
):

    # Array of completion triplets
    well_list_temp = []
    well_list = []

    for FILENAME in schedule_file_list:

        # Check if the FILENAME can be found
        # This can be both relative or absolute, do check!
        if not os.path.exists(FILENAME):
            print("Schedule file does not exist!", " ")
            return well_list

        # Try to open the file, if fail: show message to user
        f = open(FILENAME, "r")

        # Read through all lines of text
        for line in f:

            line_strip = line.strip()

            # Remove comments if required
            # line_strip = removecomments(clearcomments,line_strip)
            # line = removecomments(clearcomments,line)
            if (
                "has no trajectory" in line_strip
                or "has flow but no grid connection" in line_strip
            ):
                # print line_strip
                # new_data_file = new_data_file + line
                line_elements = line_strip.split()
                wellname_strip = line_elements[2]

                if wellname_strip not in well_list_temp:
                    well_list_temp.append(wellname_strip)

        # close file in schedule_file_list
        f.close()

        well_list = well_list_temp
        for element in well_list_temp:
            for alias_line in well_alias_list:
                if (
                    element in alias_line.split()[0]
                    and alias_line.split()[1].strip("'") not in well_list
                ):
                    well_list.append(alias_line.split()[1].strip("'"))
                elif (
                    element in alias_line.split()[1]
                    and alias_line.split()[0].strip("'") not in well_list
                ):
                    well_list.append(alias_line.split()[0].strip("'"))

    # Return completions in the schedule file list
    return well_list


def find_alias_wells(file_list, clearcomments=False):

    # Array of completion triplets
    well_alias_list = []

    for FILENAME in file_list:

        # Check if the FILENAME can be found
        # This can be both relative or absolute, do check!
        if not os.path.exists(FILENAME):
            print("Alias file does not exist!", " ")
            return well_alias_list

        # Try to open the file, if fail: show message to user
        f = open(FILENAME, "r")

        # Read through all lines of text
        for line in f:

            line_strip = line.strip()

            if len(line_strip) > 0 and "--" not in line_strip:

                # print line_strip
                # new_data_file = new_data_file + line
                line_elements = line_strip.split()

                well_alias_list.append(line_strip)
                # well_alias_list.append(line_elements[1].strip("'"))

        # close file in schedule_file_list
        f.close()

    # Return completions in the schedule file list
    return well_alias_list


def remove_wells(schedule_file_list, well_list):

    for FILENAME in schedule_file_list:

        # Check if the FILENAME can be found
        # This can be both relative or absolute, do check!
        if not os.path.exists(FILENAME):
            print("Schedule file does not exist!", " ")
            return well_list

        f = open(FILENAME, "r")
        f_new = open(FILENAME + "_updated_wells", "w")

        # Read through all lines of text
        for line in f:

            ## Progress updates
            # print line

            new_line = line
            line_strip = line.strip()
            line_elements = line_strip.split()

            # Remove comments if required
            # line_strip = removecomments(clearcomments,line_strip)
            # line = removecomments(clearcomments,line)
            if not len(line_strip) == 0 and line_elements[0].strip("'") in well_list:
                new_line = "--    " + new_line
            else:
                f_new.write(new_line)

        f.close()
        f_new.close()


def replace_completions_lgr(
    schedule_file_list, dummy_lgr_cells, dummy_lgr_wells, dummy_lgr_names
):

    for FILENAME in schedule_file_list:

        # Check if the FILENAME can be found
        # This can be both relative or absolute, do check!
        if not os.path.exists(FILENAME):
            print("Schedule file does not exist!", " ")
            return completions, well_list

        f = open(FILENAME, "r")
        f_out = open(FILENAME + "_Dummy_lgr", "w")

        lgr_lines = ""
        temp_lines = ""
        is_lgr = False
        in_COMPDAT = False
        in_WELSPECS = False
        in_COMPLUMP = False
        in_WPIMULT = False
        in_WELOPEN = False

        # Read through all lines of text
        for line in f:

            ## Progress updates
            # print line

            line_strip = line.strip()
            # Remove comments if required
            # line_strip = removecomments(clearcomments,line_strip)
            # line = removecomments(clearcomments,line)

            if "COMPDAT" in line_strip[0:7] or in_COMPDAT == True:
                # COMPDAT keyword found!
                in_COMPDAT = False
                is_lgr = False
                has_COMPDATL = False
                temp_lines += line

                for line in f:
                    # temp_lines+=(line)
                    line_strip = line.strip()

                    # Breaks on /
                    if "/" in line_strip[0]:
                        temp_lines += line
                        in_COMPDAT = False
                        break

                    if not len(line.strip()) == 0:

                        if not "--" in line_strip[0:2] and not len(line_strip) == 0:

                            # Start reading completions
                            line_base = line_strip.split(" /")[0]
                            compdat_elements = line_base.split()

                            if compdat_elements[0].strip("'") in dummy_lgr_wells:
                                temp_lines += "-- " + line
                                is_lgr = True
                                if not has_COMPDATL:
                                    lgr_lines += "COMPDATL\n"
                                    has_COMPDATL = True

                                I = int(compdat_elements[1])
                                J = int(compdat_elements[2])
                                K1 = int(compdat_elements[3])
                                K2 = int(compdat_elements[4])

                                for K in range(K2 - K1 + 1):
                                    if (
                                        I - 1,
                                        J - 1,
                                        K1 + K - 1,
                                    ) not in dummy_lgr_cells:
                                        lgr_lines += "  " + compdat_elements[0]
                                        lgr_lines += "  " + "LGRMAIN"
                                        lgr_lines += "  " + "1"
                                        lgr_lines += "  " + "1"
                                        lgr_lines += "  " + "1"
                                        lgr_lines += "  " + "1"
                                        for index2 in range(5, len(compdat_elements)):
                                            lgr_lines += "  " + compdat_elements[index2]

                                        lgr_lines += " /\n"
                                    else:

                                        for index1 in range(len(dummy_lgr_cells)):
                                            if (
                                                (I - 1, J - 1, K1 + K - 1)
                                                == dummy_lgr_cells[index1]
                                                and compdat_elements[0].strip("'")
                                                == dummy_lgr_wells[index1]
                                            ):

                                                lgr_lines += (
                                                    "  "
                                                    + "'"
                                                    + dummy_lgr_wells[index1]
                                                    + "'"
                                                )
                                                lgr_lines += (
                                                    "  " + dummy_lgr_names[index1]
                                                )
                                                lgr_lines += "  " + "1"
                                                lgr_lines += "  " + "1"
                                                lgr_lines += "  " + "1"
                                                lgr_lines += "  " + "1"
                                                for index2 in range(
                                                    5, len(compdat_elements)
                                                ):
                                                    lgr_lines += (
                                                        "  " + compdat_elements[index2]
                                                    )

                                                lgr_lines += " /\n"

                            else:
                                temp_lines += line

                        else:
                            temp_lines += line

                    else:
                        temp_lines += line

                if is_lgr:
                    f_out.write(lgr_lines)
                    f_out.write("/\n\n")

                lgr_lines = ""
                f_out.write(temp_lines)
                temp_lines = ""

            elif "WELSPECS" in line_strip[0:8] or in_WELSPECS == True:
                # WELSPECS keyword found!
                in_WELSPECS = False
                has_WELSPECL = False
                is_lgr = False
                temp_lines += line

                for line in f:
                    # temp_lines+=(line)
                    line_strip = line.strip()

                    if not len(line.strip()) == 0:

                        # Breaks on /
                        if "/" in line_strip[0]:
                            temp_lines += line
                            in_WELSPECS = False
                            break

                        if not "--" in line_strip[0:2] and not len(line_strip) == 0:

                            # Start reading
                            line_base = line_strip.split(" /")[0]
                            compdat_elements = line_base.split()

                            if compdat_elements[0].strip("'") in dummy_lgr_wells:
                                is_lgr = True
                                temp_lines += "-- " + line
                                if not has_WELSPECL:
                                    lgr_lines += "WELSPECL\n"
                                    has_WELSPECL = True

                                # Finds index of first occurance of well name
                                index = dummy_lgr_wells.index(
                                    compdat_elements[0].strip("'")
                                )
                                lgr_lines += "  " + "'" + dummy_lgr_wells[index] + "'"
                                lgr_lines += "  " + compdat_elements[1]
                                lgr_lines += "  " + dummy_lgr_names[index]
                                lgr_lines += "  " + "1"
                                lgr_lines += "  " + "1"
                                for index2 in range(4, len(compdat_elements)):
                                    lgr_lines += "  " + compdat_elements[index2]

                                lgr_lines += " /\n"
                            else:
                                temp_lines += line

                        else:
                            temp_lines += line

                    else:
                        temp_lines += line

                if is_lgr:
                    f_out.write(lgr_lines)
                    f_out.write("/\n\n")

                lgr_lines = ""
                f_out.write(temp_lines)
                temp_lines = ""

            elif "COMPLUMP" in line_strip[0:8] or in_COMPLUMP == True:
                # COMPLUMP keyword found!
                in_COMPLUMP = False
                has_COMPLMPL = False
                is_lgr = False
                temp_lines += line

                for line in f:
                    # temp_lines+=(line)
                    line_strip = line.strip()

                    # Breaks on /
                    if "/" in line_strip[0]:
                        temp_lines += line
                        in_COMPLUMP = False
                        break

                    if not len(line.strip()) == 0:

                        if not "--" in line_strip[0:2] and not len(line_strip) == 0:

                            # Start reading completions
                            line_base = line_strip.split(" /")[0]
                            compdat_elements = line_base.split()

                            if compdat_elements[0].strip("'") in dummy_lgr_wells:
                                temp_lines += "-- " + line
                                is_lgr = True
                                if not has_COMPLMPL:
                                    lgr_lines += "COMPLMPL\n"
                                    has_COMPLMPL = True

                                I = int(compdat_elements[1])
                                J = int(compdat_elements[2])
                                K1 = int(compdat_elements[3])
                                K2 = int(compdat_elements[4])

                                for K in range(K2 - K1 + 1):

                                    if (
                                        I - 1,
                                        J - 1,
                                        K1 + K - 1,
                                    ) not in dummy_lgr_cells:
                                        lgr_lines += (
                                            "  " + "'" + compdat_elements[0] + "'"
                                        )
                                        lgr_lines += "  " + "LGRMAIN"
                                        lgr_lines += "  " + "1"
                                        lgr_lines += "  " + "1"
                                        lgr_lines += "  " + "1"
                                        lgr_lines += "  " + "1"
                                        for index2 in range(5, len(compdat_elements)):
                                            lgr_lines += "  " + compdat_elements[index2]

                                        lgr_lines += " /\n"
                                    else:

                                        for index1 in range(len(dummy_lgr_cells)):
                                            if (
                                                (I - 1, J - 1, K1 + K - 1)
                                                == dummy_lgr_cells[index1]
                                                and compdat_elements[0].strip("'")
                                                == dummy_lgr_wells[index1]
                                            ):

                                                lgr_lines += (
                                                    "  "
                                                    + "'"
                                                    + dummy_lgr_wells[index1]
                                                    + "'"
                                                )
                                                lgr_lines += (
                                                    "  " + dummy_lgr_names[index1]
                                                )
                                                lgr_lines += "  " + "1"
                                                lgr_lines += "  " + "1"
                                                lgr_lines += "  " + "1"
                                                lgr_lines += "  " + "1"
                                                for index2 in range(
                                                    5, len(compdat_elements)
                                                ):
                                                    lgr_lines += (
                                                        "  " + compdat_elements[index2]
                                                    )

                                                lgr_lines += " /\n"

                            else:
                                temp_lines += line

                        else:
                            temp_lines += line

                    else:
                        temp_lines += line

                if is_lgr:
                    f_out.write(lgr_lines)
                    f_out.write("/\n\n")

                lgr_lines = ""
                f_out.write(temp_lines)
                temp_lines = ""

            elif "WPIMULT" in line_strip[0:7] or in_WPIMULT == True:
                # WPIMULT keyword found!
                in_WPIMULT = False
                has_WPIMULTL = False
                is_lgr = False

                temp_lines += line

                for line in f:
                    # temp_lines+=(line)
                    line_strip = line.strip()

                    # Breaks on /
                    if "/" in line_strip[0]:
                        temp_lines += line
                        in_WPIMULT = False
                        break

                    if not len(line.strip()) == 0:

                        if not "--" in line_strip[0:2] and not len(line_strip) == 0:

                            # Start reading completions
                            line_base = line_strip.split(" /")[0]
                            compdat_elements = line_base.split()

                            if compdat_elements[0].strip("'") in dummy_lgr_wells:
                                temp_lines += "-- " + line
                                is_lgr = True
                                if not has_WPIMULTL:
                                    lgr_lines += "WPIMULTL\n"
                                    has_WPIMULTL = True

                                if len(compdat_elements) < 4:
                                    print(
                                        "ERROR: Worng format of line in WPIMULT ...",
                                        " ",
                                    )
                                    print(line)
                                    sys.exit(1)

                                K1 = int(compdat_elements[3])
                                K2 = int(compdat_elements[4])

                                for K in range(K2 - K1 + 1):

                                    for index1 in range(len(dummy_lgr_cells)):
                                        (i, j, k) = dummy_lgr_cells[index1]
                                        if (K1 + K - 1) == k and compdat_elements[
                                            0
                                        ].strip("'") == dummy_lgr_wells[index1]:

                                            lgr_lines += (
                                                "  "
                                                + "'"
                                                + dummy_lgr_wells[index1]
                                                + "'"
                                            )
                                            lgr_lines += "  " + compdat_elements[1]
                                            lgr_lines += "  " + dummy_lgr_names[index1]
                                            lgr_lines += "  " + "3*"
                                            for index2 in range(
                                                3, len(compdat_elements)
                                            ):
                                                lgr_lines += (
                                                    "  " + compdat_elements[index2]
                                                )

                                            lgr_lines += " /\n"

                            else:
                                temp_lines += line

                        else:
                            temp_lines += line

                    else:
                        temp_lines += line

                if is_lgr:
                    f_out.write(lgr_lines)
                    f_out.write("/\n\n")

                lgr_lines = ""
                f_out.write(temp_lines)
                temp_lines = ""

            elif "WELOPEN" in line_strip[0:7] or in_WELOPEN == True:
                # WPIMULT keyword found!
                in_WELOPNE = False
                has_WELOPENL = False
                is_lgr = False

                temp_lines += line

                for line in f:
                    # temp_lines+=(line)
                    line_strip = line.strip()

                    # Breaks on /
                    if "/" in line_strip[0]:
                        temp_lines += line
                        in_WELOPEN = False
                        break

                    if not len(line.strip()) == 0:

                        if not "--" in line_strip[0:2] and not len(line_strip) == 0:

                            # Start reading completions
                            line_base = line_strip.split(" /")[0]
                            compdat_elements = line_base.split()

                            if compdat_elements[0].strip("'") in dummy_lgr_wells:
                                temp_lines += "-- " + line
                                is_lgr = True
                                if not has_WPIMULTL:
                                    lgr_lines += "WELOPENL\n"
                                    has_WELOPENL = True

                                # Finds index of first occurance of well name
                                index = dummy_lgr_wells.index(
                                    compdat_elements[0].strip("'")
                                )
                                lgr_lines += "  " + "'" + dummy_lgr_wells[index] + "'"
                                lgr_lines += "  " + dummy_lgr_names[index]
                                for index2 in range(1, len(compdat_elements)):
                                    lgr_lines += "  " + compdat_elements[index2]

                                lgr_lines += " /\n"

                            else:
                                temp_lines += line

                        else:
                            temp_lines += line

                    else:
                        temp_lines += line

                if is_lgr:
                    f_out.write(lgr_lines)
                    f_out.write("/\n\n")

                lgr_lines = ""
                f_out.write(temp_lines)
                temp_lines = ""

            else:
                f_out.write(line)

        f.close()
        f_out.close()
