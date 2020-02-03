import os


def replace_NNC(file_list, replace_value=0):

    for FILENAME in file_list:

        # Check if the FILENAME can be found
        # This can be both relative or absolute, do check!
        if not os.path.exists(FILENAME):
            print("EDIT file does not exist!", " ")
            return completions, well_list

        f = open(FILENAME, "r")
        f_new = open(FILENAME + "_mod", "w")

        new_lines = []

        # Read through all lines of text
        for line in f:

            # Progress updates
            print(line)

            new_line = line
            line_strip = line.strip()

            # Remove comments if required
            # line_strip = removecomments(clearcomments,line_strip)
            # line = removecomments(clearcomments,line)
            if "EDITNNC" in line_strip[0:7]:
                # EDITNNC keyword found!
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
                            line_base = line_strip.split("/")[0]
                            editnnc_elements = line_base.split()

                            if editnnc_elements[6] == "0":
                                new_line = new_line.replace(
                                    " " + editnnc_elements[6] + " ",
                                    " " + str(replace_value) + " ",
                                    1,
                                )

                            new_lines.append(new_line)
                            f_new.write(new_line)

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


def shift_NNC_down(file_list, shift_x=0, shift_y=0, shift_z=0):

    for FILENAME in file_list:

        # Check if the FILENAME can be found
        # This can be both relative or absolute, do check!
        if not os.path.exists(FILENAME):
            print("EDIT file does not exist!", " ")
            return completions, well_list

        f = open(FILENAME, "r")
        f_new = open(FILENAME + "_shifted", "w")

        new_lines = []

        # Read through all lines of text
        for line in f:

            # Progress updates
            print(line)

            new_line = line
            line_strip = line.strip()

            # Remove comments if required
            # line_strip = removecomments(clearcomments,line_strip)
            # line = removecomments(clearcomments,line)
            if "EDITNNC" in line_strip[0:7]:
                # EDITNNC keyword found!
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
                            line_base = line_strip.split("/")[0]
                            editnnc_elements = line_base.split()

                            new_editnnc_element = int(editnnc_elements[0]) + shift_x
                            editnnc_elements[0] = str(new_editnnc_element)
                            new_editnnc_element = int(editnnc_elements[1]) + shift_y
                            editnnc_elements[1] = str(new_editnnc_element)
                            new_editnnc_element = int(editnnc_elements[2]) + shift_z
                            editnnc_elements[2] = str(new_editnnc_element)
                            new_editnnc_element = int(editnnc_elements[3]) + shift_x
                            editnnc_elements[3] = str(new_editnnc_element)
                            new_editnnc_element = int(editnnc_elements[4]) + shift_y
                            editnnc_elements[4] = str(new_editnnc_element)
                            new_editnnc_element = int(editnnc_elements[5]) + shift_z
                            editnnc_elements[5] = str(new_editnnc_element)

                            new_line = "  "

                            for element in editnnc_elements:
                                new_line = new_line + "     " + element

                            new_line = new_line + "     /\n"

                            new_lines.append(new_line)
                            f_new.write(new_line)

                        else:
                            new_lines.append(new_line)
                            f_new.write(new_line)

                    else:
                        new_lines.append(new_line)
                        f_new.write(new_line)

            if "MULTIPLY" in line_strip[0:8]:
                # MULTIPLY keyword found!
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
                            line_base = line_strip.split("/")[0]
                            mult_elements = line_base.split()

                            new_mult_element = int(mult_elements[2]) + shift_x
                            mult_elements[2] = str(new_mult_element)
                            new_mult_element = int(mult_elements[3]) + shift_x
                            mult_elements[3] = str(new_mult_element)
                            new_mult_element = int(mult_elements[4]) + shift_y
                            mult_elements[4] = str(new_mult_element)
                            new_mult_element = int(mult_elements[5]) + shift_y
                            mult_elements[5] = str(new_mult_element)
                            new_mult_element = int(mult_elements[6]) + shift_z
                            mult_elements[6] = str(new_mult_element)
                            new_mult_element = int(mult_elements[7]) + shift_z
                            mult_elements[7] = str(new_mult_element)

                            new_line = "  "

                            for element in mult_elements:
                                new_line = new_line + "     " + element

                            new_line = new_line + "     /\n"

                            new_lines.append(new_line)
                            f_new.write(new_line)

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


def find_NNC(file_list):

    NNC_list = []
    for FILENAME in file_list:

        # Check if the FILENAME can be found
        # This can be both relative or absolute, do check!
        if not os.path.exists(FILENAME):
            print("EDIT file does not exist!", " ")

        f = open(FILENAME, "r")

        # Read through all lines of text
        for line in f:

            # Progress updates
            print(line)

            line_strip = line.strip()

            # Remove comments if required
            # line_strip = removecomments(clearcomments,line_strip)
            # line = removecomments(clearcomments,line)
            if "EDITNNC" in line_strip[0:7]:
                # EDITNNC keyword found!
                # new_data_file = new_data_file + line

                for line in f:
                    print(line)
                    line_strip = line.strip()

                    # Breaks on /
                    if "/" in line_strip[0]:
                        break

                    if not len(line.strip()) == 0:

                        if "--" not in line_strip[0:2] and not len(line_strip) == 0:

                            # Start reading completions
                            line_base = line_strip.split("/")[0]
                            editnnc_elements = line_base.split()

                            ijk1 = (
                                int(editnnc_elements[0]),
                                int(editnnc_elements[1]),
                                int(editnnc_elements[2]),
                            )

                            ijk2 = (
                                int(editnnc_elements[3]),
                                int(editnnc_elements[4]),
                                int(editnnc_elements[5]),
                            )

                            # if ijk1 not in NNC_list:
                            NNC_list.append(ijk1)

                            # if ijk2 not in NNC_list:
                            NNC_list.append(ijk2)

            if "MULTIPLY" in line_strip[0:8]:
                # EDITNNC keyword found!
                # new_data_file = new_data_file + line

                for line in f:
                    print(line)
                    line_strip = line.strip()

                    # Breaks on /
                    if "/" in line_strip[0]:
                        break

                    if not len(line.strip()) == 0:

                        if "--" not in line_strip[0:2] and not len(line_strip) == 0:

                            # Start reading completions
                            line_base = line_strip.split("/")[0]
                            editnnc_elements = line_base.split()

                            ijk1 = (
                                int(editnnc_elements[2]),
                                int(editnnc_elements[4]),
                                int(editnnc_elements[6]),
                            )

                            # if ijk1 not in NNC_list:
                            # NNC_list.append(ijk1)

        f.close()

    return NNC_list


def deact_fault_connections(grid, init, NNC_list, filename_path):

    f_new = open(filename_path, "w")

    fluxnum_kw = init.iget_named_kw("FLUXNUM", 0)
    #    actnum_kw = init.iget_named_kw("ACTNUM", 0)

    f_new.write("EQUALS\n")

    for pos in NNC_list:
        new_pos = (pos[0] - 1, pos[1] - 1, pos[2] - 1)
        activeIndex = grid.get_active_index(ijk=new_pos)

        if activeIndex > -1 and fluxnum_kw[activeIndex] == 0:
            f_new.write(
                "ACTNUM"
                + "    "
                + "0"
                + "     "
                + str(pos[0])
                + "  "
                + str(pos[0])
                + "  "
                + str(pos[1])
                + "  "
                + str(pos[1])
                + "  "
                + str(pos[2])
                + "  "
                + str(pos[2])
                + "  /"
            )
            f_new.write("\n")

            print(
                (
                    "ACTNUM"
                    + "  "
                    + "0"
                    + "  "
                    + str(pos[0])
                    + "  "
                    + str(pos[0])
                    + "  "
                    + str(pos[1])
                    + "  "
                    + str(pos[1])
                    + "  "
                    + str(pos[2])
                    + "  "
                    + str(pos[2])
                    + "  /"
                )
            )

    f_new.write("/\n")
    f_new.close()
