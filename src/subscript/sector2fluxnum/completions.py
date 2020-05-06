import sys
import os
import shutil
from ecl2df import compdat, EclFiles


def generate_compdat_dataframe(ECL_DATA_file_name):
    """
    Create a datafram of unrolled well completions

    Args:
       Input DATA file name

    Returns:
       dataFrame with the following header:

    """
    ECL_file = EclFiles(ECL_DATA_file_name)
    compdat_df = compdat.df(ECL_file)
    compdat_df = compdat.unrolldf(compdat_df)

    return compdat_df


def get_completion_list(dframe):
    """
    Create a datafram of unrolled well completions

    Args:
       Pandas data frame with completions

    Returns:
       List of unique well names
       List of completions associated to well names

    """
    # Convert from ECL index
    dframe[['I', 'J', 'K1', 'K2']] = dframe[['I', 'J', 'K1', 'K2']] - 1

    # Create tuples
    dframe['IJK'] = dframe[['I', 'J', 'K1']].apply(tuple, axis=1)

    well_list = dframe['WELL'].unique().tolist()
    completion_list = []
    for well in well_list:
        completion_list.append(dframe['IJK'].loc[dframe['WELL'] == well].to_list())

    return completion_list, well_list


def replace_completions(
    schedule_file_list,
    scale_i=1,
    scale_j=1,
    shift_i=0,
    shift_j=0,
    max_i=100000,
    max_j=100000,
):

    completions = []
    well_list = []

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

            # Progress updates
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

                        if "--" not in line_strip[0:2] and not len(line_strip) == 0:

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

                            # new_line = "  ".join(compdat_elements)

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

                        if "--" not in line_strip[0:2] and not len(line_strip) == 0:

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

                                # new_line = "  ".join(compdat_elements)

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

                        if "--" not in line_strip[0:2] and not len(line_strip) == 0:

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

    completions = []
    well_list = []

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

            # Progress updates
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

                        if "--" not in line_strip[0:2] and not len(line_strip) == 0:

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

                            # new_line = "  ".join(compdat_elements)

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

                        if "--" not in line_strip[0:2] and not len(line_strip) == 0:

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

                                # new_line = "  ".join(compdat_elements)

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

                        if "--" not in line_strip[0:2] and not len(line_strip) == 0:

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
                            if "--" not in line_strip[0:2]:
                                # Striping down filename string,
                                # but keeping "/" in path name
                                line_base = line_strip.rsplit("'", 1)[0]
                                line_base = line_base + "'"
                                line_base_strip = line_base.strip().strip("'").strip()

                                file_path = line_base_strip

                                if not os.path.isfile(file_path):
                                    file_path = DATAFile_dir + "/" + line_base_strip

                                    # print file_path

                                    if not os.path.isfile(file_path):
                                        print("ERROR: Not able to find INCLUDE file...")
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
                # line_elements = line_strip.split()

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

            # Progress updates
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
