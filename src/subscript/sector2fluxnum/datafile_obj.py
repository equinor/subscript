#!/usr/bin/env python
import sys
import os
import subprocess
import shlex
import shutil


class Datafile:

    """
    Class containing parsers and write routines for
    DATA files and local executions of DATA files
    """

    def __init__(self, datafile_name):

        """
        Collects the name of the root datafile.
        """
        self.datafile_name = datafile_name
        self.datafile_shortname = os.path.basename(self.datafile_name)
        self.datafile_dirname = os.path.dirname(os.path.abspath(self.datafile_name))

        self.DUMPFLUX_name = "Empty"
        self.USEFLUX_name = "Empty"

    def check_DUMPFLUX_kw(self):

        fin = open(self.datafile_name, "r")
        hasDUMPFLUX = False

        for line in fin:

            line_strip = line.strip()

            if "DUMPFLUX" in line_strip[0:8]:
                hasDUMPFLUX = True

        fin.close()

        return hasDUMPFLUX

    def check_USEFLUX_kw(self):

        fin = open(self.datafile_name, "r")
        hasUSEFLUX = False

        for line in fin:

            line_strip = line.strip()

            if "USEFLUX" in line_strip[0:7]:
                hasUSEFLUX = True

        fin.close()

        return hasUSEFLUX

    def create_DUMPFLUX(self, fluxnumfile_name):
        """
        Writes a DATA file with DUMPFLUX keyword.

        Also includes NOSIM and OPTION entries for EOR functionality.

        @fluxnumfile_name : Name of the FLUXNUM kw file to be included
        """

        self.DUMPFLUX_name = "DUMPFLUX_" + self.datafile_shortname

        fin = open(self.datafile_name, "r")
        fout = open(self.DUMPFLUX_name, "w")

        for line in fin:

            new_line = line
            line_strip = line.strip()

            if "RUNSPEC" in line_strip[0:7]:
                fout.write("RUNSPEC\n\n")
                fout.write("NOSIM\n\n")
                fout.write("OPTIONS\n   85* 1  /\n\n")
                fout.write("OPTIONS\n   231* 1  /\n\n")

            elif "PARALLEL" in line_strip[0:8]:
                fout.write("-- " + new_line)
                for line in fin:
                    new_line = line
                    line_strip = line.strip()
                    if "/" in line_strip:
                        fout.write("-- " + new_line)
                        break

                    fout.write("-- " + new_line)

            elif "REGDIMS" in line_strip[0:7]:

                fout.write(new_line)

                for line in fin:
                    new_line = line
                    line_strip = line.strip()

                    if "/" in line_strip[0]:
                        fout.write(new_line)
                        break

                    if not len(line_strip) == 0:
                        if "--" not in line_strip[0:2]:
                            line_base = line_strip.split("/")[0]
                            line_elements = line_base.split()

                            if len(line_elements) > 3:
                                line_elements[3] = 1  # NB!!

                            else:
                                print("ERROR: Error in REGDIMS for DUMPFLUX")
                                sys.exit(1)

                            spacing = "   "
                            line_string_elements = list(map(str, line_elements))
                            # print line_string_elements
                            new_line = (
                                "  "
                                + spacing.join(line_string_elements)
                                + spacing
                                + "/"
                            )
                            fout.write(new_line)
                            break

                    fout.write(new_line)

            elif "GRID" in line_strip[0:4]:

                fnutt = "'"

                fout.write(new_line)

                # In case there is text after the GRID keyword
                line_strip = line_strip.split()[0]

                if line_strip == "GRID":
                    fout.write("\n\n")
                    fout.write("FLUXTYPE\n")
                    fout.write("  " + fnutt + "PRESSURE" + fnutt + " /\n\n")
                    fout.write("DUMPFLUX\n\n")
                    fout.write("INCLUDE\n")
                    fout.write(("  " + fnutt + "%s" + fnutt + "\n") % fluxnumfile_name)
                    fout.write("/\n\n")
                    fout.write("FLUXREG\n  1 /\n\n")

            elif "INCLUDE" in line_strip[0:7]:
                fnutt = "'"

                fout.write(new_line)

                for line in fin:
                    new_line = line
                    line_strip = line.strip()

                    if "/" in line_strip[0]:
                        fout.write(new_line)
                        break

                    if not len(line_strip) == 0:
                        if "--" not in line_strip[0:2]:
                            # Striping down filename string,
                            # but keeping "/" in path name
                            line_base = line_strip.rsplit("'", 1)[0]
                            line_base = line_base + "'"
                            line_base_strip = line_base.strip().strip("'").strip()

                            if not os.path.isfile(line_base_strip):
                                file_path = (
                                    self.datafile_dirname + "/" + line_base_strip
                                )

                                # print file_path

                                if not os.path.isfile(file_path):
                                    print(
                                        "ERROR: Not able to find path for INCLUDE file"
                                    )
                                    sys.exit(1)

                                # Creates storage dir for include files
                                if not os.path.isdir("./include"):
                                    os.makedirs("./include")

                                new_file_path = "./include/" + os.path.basename(
                                    file_path
                                )
                                shutil.copy2(file_path, new_file_path)

                                new_line = "'" + new_file_path + "'" + "  " + "/"

                            fout.write(new_line)
                            fout.write("\n")
                            break

                    fout.write(new_line)

            else:
                fout.write(new_line)

            if "RESTART" in line_strip[0:7]:
                print("WARNING: DUMPFLUX file contains a RESTART.\n")
                print("This may cause problems with execution of DUMPFLUX run.\n")
                print("Please check the RESTART file path before you proceed!")

        fin.close()
        fout.close()

    def run_DUMPFLUX_NOSIM(self, version="2014.2"):

        """
        Executes interactive ECLIPSE run with DUMPFLUX DATA file.

        ECLIPSE version 2014.2.

        Checks for errors in the output PRT file
        """

        if self.DUMPFLUX_name == "Empty":
            print("ERROR: DUMPFLUX file not found or run")
            sys.exit(1)

        # Delete old FLUX file if present
        if os.path.isfile("%s.FLUX" % self.DUMPFLUX_name.split(".")[0]):
            file_name = "%s.FLUX" % self.DUMPFLUX_name.split(".")[0]
            commandline = "rm %s %s" % ("-f", file_name)
            args = shlex.split(commandline)
            p = subprocess.Popen(args, stdout=subprocess.PIPE)

        if not (version == "2014.2"):
            print("WARNING: Not a default ECL version. ECL version is %s ..." % version)

        commandline = "runeclipse %s -v %s %s" % ("-i", version, self.DUMPFLUX_name)
        args = shlex.split(commandline)
        p = subprocess.Popen(args, stdout=subprocess.PIPE)
        (output, err) = p.communicate()

        if err:
            print(err)

        print("Checking for errors")

        output_list = output.decode("utf8").split("\n")

        index = 0
        for line in output_list:
            line_strip = line.strip()

            line_elements = line_strip.split()

            if (
                len(line_elements) < 3
                and "Errors" in line_elements
                and "0" not in line_elements
            ):
                print("ERROR: Some errors occured during DUMPFLUX run.\n")
                print("Please check PRT output...")
                print(line_elements)
                sys.exit(1)

    def run_DUMPFLUX_NOSIM_v2013(self):
        """
        Executes interactive ECLIPSE run with DUMPFLUX DATA file.

        ECLIPSE version 2013.2.

        Checks for errors in the output PRT file
        """

        if self.DUMPFLUX_name == "Empty":
            print("ERROR: DUMPFLUX file not found or run")
            sys.exit(1)

        # Delete old FLUX file if present
        if os.path.isfile("%s.FLUX" % self.DUMPFLUX_name.split(".")[0]):
            file_name = "%s.FLUX" % self.DUMPFLUX_name.split(".")[0]
            commandline = "rm %s %s" % ("-f", file_name)
            args = shlex.split(commandline)
            p = subprocess.Popen(args, stdout=subprocess.PIPE)

        commandline = "runeclipse %s %s %s" % ("-i", "-v 2013.2", self.DUMPFLUX_name)
        args = shlex.split(commandline)
        p = subprocess.Popen(args, stdout=subprocess.PIPE)
        (output, err) = p.communicate()

        if err:
            print(err)

        print("Checking for errors")

        output_list = output.split("\n")

        # index = 0
        for line in output_list:
            line_strip = line.strip()

            line_elements = line_strip.split()

            if (
                len(line_elements) < 3
                and "Errors" in line_elements
                and "0" not in line_elements
            ):
                print("ERROR: Some errors occured during DUMPFLUX run.\n")
                print("Please check PRT output.")
                print(line_elements)
                sys.exit(1)

    def create_USEFLUX(self, fluxnumfile_name, fluxfile_name):
        """
        Creates a USEFLUX DATA file containing the sector simulation and
        populated boundary conditions.

        @fluxnumfile_name : Name of file containing FLUXNUM kw
        @fluxfile_name : Name of FLUX file populated from full field RESTART data
        """
        self.USEFLUX_name = "USEFLUX_" + self.datafile_shortname

        fin = open(self.datafile_name, "r")
        fout = open(self.USEFLUX_name, "w")

        for line in fin:

            new_line = line
            line_strip = line.strip()

            if "REGDIMS" in line_strip[0:7]:

                fout.write(new_line)

                for line in fin:
                    new_line = line
                    line_strip = line.strip()

                    if "/" in line_strip[0]:
                        fout.write(new_line)
                        break

                    if not len(line_strip) == 0:
                        if "--" not in line_strip[0:2]:
                            line_base = line_strip.split("/")[0]
                            line_elements = line_base.split()

                            if len(line_elements) > 3:
                                line_elements[3] = 1  # NB!!

                            else:
                                print("ERROR: Error in REGDIMS for USEFLUX")
                                sys.exit(1)

                            spacing = "   "
                            line_string_elements = list(map(str, line_elements))
                            # print line_string_elements
                            new_line = (
                                "  "
                                + spacing.join(line_string_elements)
                                + spacing
                                + "/"
                            )
                            fout.write(new_line)
                            break

                    fout.write(new_line)

            elif "RUNSPEC" in line_strip[0:7]:
                fout.write("RUNSPEC\n\n")
                fout.write("OPTIONS\n   85* 1  /\n\n")
                fout.write("OPTIONS\n   231* 1  /\n\n")

            elif "NOSIM" in line_strip[0:5]:
                fout.write("-- " + new_line)

            elif "PARALLEL" in line_strip[0:8]:
                fout.write("-- " + new_line)
                for line in fin:
                    new_line = line
                    line_strip = line.strip()
                    if "/" in line_strip:
                        fout.write("-- " + new_line)
                        break

                    fout.write("-- " + new_line)

            elif "GRID" in line_strip[0:4]:

                fnutt = "'"

                fout.write(new_line)

                # In case there is text after the GRID keyword
                line_strip = line_strip.split()[0]

                if line_strip == "GRID":
                    fout.write("\n\n")
                    fout.write("FLUXTYPE\n")
                    fout.write("  " + fnutt + "PRESSURE" + fnutt + "  /\n\n")
                    fout.write("USEFLUX\n")
                    fout.write(
                        ("  " + fnutt + "%s" + fnutt + "  /\n\n") % fluxfile_name
                    )
                    fout.write("INCLUDE\n")
                    fout.write(
                        ("  " + fnutt + "%s" + fnutt + "  /\n\n") % fluxnumfile_name
                    )
                    fout.write("FLUXREG\n  1 /\n\n")

            elif "SOLUTION" in line_strip[0:8]:

                fnutt = "'"

                fout.write(new_line)

                if line_strip == "SOLUTION":
                    fout.write("\n\n")
                    fout.write("-- *** NOTIFICATION ***\n")
                    fout.write("-- If DUMPFLUX run is based on a RESTART\n")
                    fout.write(
                        "-- USEFLUX run needs to be run based on the DUMPFLUX run\n"
                    )
                    fout.write("-- Use the following and remove any equilibrations\n\n")
                    fout.write("-- RESTART\n")
                    fout.write(
                        ("--  " + fnutt + "%s" + fnutt + " " + "0\n")
                        % self.DUMPFLUX_name.split(".")[0]
                    )
                    fout.write("-- /\n")

            elif "INCLUDE" in line_strip[0:7]:
                fnutt = "'"

                fout.write(new_line)

                for line in fin:
                    new_line = line
                    line_strip = line.strip()

                    if "/" in line_strip[0]:
                        fout.write(new_line)
                        break

                    if not len(line_strip) == 0:
                        if "--" not in line_strip[0:2]:
                            # Striping down filename string,
                            # but keeping "/" in path name
                            line_base = line_strip.rsplit("'", 1)[0]
                            line_base = line_base + "'"
                            line_base_strip = line_base.strip().strip("'").strip()

                            if not os.path.isfile(line_base_strip):
                                file_path = (
                                    self.datafile_dirname + "/" + line_base_strip
                                )

                                if not os.path.isfile(file_path):
                                    print(
                                        "ERROR: Not able to find path for INCLUDE file"
                                    )
                                    sys.exit(1)

                                new_file_path = "./include/" + os.path.basename(
                                    file_path
                                )

                                new_line = "'" + new_file_path + "'" + "  " + "/"

                            fout.write(new_line)
                            fout.write("\n")
                            break

                    fout.write(new_line)

            else:
                fout.write(new_line)

        fin.close()
        fout.close()

    def add_USEFLUX_header_coarse(self, args):
        """
        Adds header to the output USEFLUX file

        Input
        @args: Arguments from the intput to the wrapper scripts
        """
        import datetime

        today = datetime.date.today()
        date_str = today.strftime("%d %b %Y")

        if self.USEFLUX_name == "Empty":
            print("ERROR: DUMPFLUX file not found or run")
            sys.exit(1)

        fin_name = self.USEFLUX_name
        fout_name = "%s_tmp" % self.USEFLUX_name

        fin = open(fin_name, "r")
        fout = open(fout_name, "w")

        header_flag = False
        for line in fin:
            if not header_flag:
                fout.write("-- **************************************************\n")
                fout.write("-- **              SECTOR MODEL                    **\n")
                fout.write("-- **************************************************\n")
                fout.write("-- DATA file created %s\n" % (date_str))
                fout.write("--\n")
                fout.write(
                    "-- This is an automatic generated file for sector simulation "
                )
                fout.write("in ECLIPSE\n")
                fout.write(
                    "-- The resolution is the same as for the full field model\n"
                )
                fout.write("-- DATA file created %s\n" % (date_str))
                fout.write("--\n")
                fout.write(
                    "-- The sector is selected from the following region"
                )
                fout.write(" in the FF model\n")
                fout.write("-- Box dimensions i-dir =  %s\n" % (args.i))
                fout.write("-- Box dimensions j-dir =  %s\n" % (args.j))
                fout.write("-- Box dimensions k-dir =  %s\n" % (args.k))
                fout.write("-- FIPNUM regions = %s\n" % (args.fipnum))
                if args.fluxfile:
                    fout.write("-- FLUXNUM from file = %s\n" % (args.fluxfile))
                fout.write("--\n")
                fout.write("-- FF case is: %s\n" % (args.ECLIPSE_CASE))
                if args.version:
                    fout.write("-- Eclipse version is = %s\n" % (args.version))
                else:
                    fout.write("-- Eclipse version is = 2014.2\n")
                fout.write("--\n")
                fout.write(
                    "-- **************************************************\n\n\n"
                )

            header_flag = True

            fout.write(line)

        fin.close()
        fout.close()

        shutil.move(fout_name, fin_name)

    def add_USEFLUX_header_refined(self, args):
        """
        Adds header to the output USEFLUX file

        Input
        @args: Arguments from the intput to the wrapper scripts
        """

        import datetime

        today = datetime.date.today()
        date_str = today.strftime("%d %b %Y")

        if self.USEFLUX_name == "Empty":
            print("ERROR: DUMPFLUX file not found or run")
            sys.exit(1)

        fin_name = self.USEFLUX_name
        fout_name = "%s_tmp" % self.USEFLUX_name

        fin = open(fin_name, "r")
        fout = open(fout_name, "w")

        header_flag = False
        for line in fin:
            if not header_flag:
                fout.write("-- ********************************************\n")
                fout.write("-- **              SECTOR MODEL              **\n")
                fout.write("-- ********************************************\n")
                fout.write("--\n")
                fout.write("-- This is an automatic generated file for ")
                fout.write("sector simulation in ECLIPSE\n")
                fout.write("-- The sector resolution is refined\n")
                fout.write("-- Refinement in i-dir =  %s\n" % (args.scale_i))
                fout.write("-- Refinement in j-dir =  %s\n" % (args.scale_j))
                fout.write("--\n")
                fout.write("-- FF data file is: %s\n" % (args.ECLIPSE_CASE))
                fout.write("--\n")
                fout.write(
                    "-- Refined data file case is: %s\n" % (args.ECLIPSE_CASE_FINE)
                )
                fout.write("--\n")
                fout.write(
                    "-- The refined grid is shifted in i-dir in RMS:  %s\n"
                    % (args.shift_i)
                )
                fout.write(
                    "-- The refined grid is shifted in j-dir in RMS:  %s\n"
                    % (args.shift_j)
                )
                fout.write("--\n")
                fout.write("-- The sector is selected from the following ")
                fout.write("region in the FF model\n")
                fout.write("-- Box dimensions i-dir =  %s\n" % (args.i))
                fout.write("-- Box dimensions j-dir =  %s\n" % (args.j))
                fout.write("-- Box dimensions k-dir =  %s\n" % (args.k))
                fout.write("-- FIPNUM regions = %s\n" % (args.fipnum))
                if args.version:
                    fout.write("-- Eclipse version is = %s\n" % (args.version))
                else:
                    fout.write("-- Eclipse version is = 2014.2\n")
                fout.write("--\n")
                fout.write(
                    "-- *********************************************\n\n\n"
                )

                header_flag = True

            fout.write(line)

        fin.close()
        fout.close()

        shutil.move(fout_name, fin_name)

    def create_dummy_lgr_GRID_include(
        self,
        file_name,
        args,
        dummy_lgr_cells=(),
        dummy_lgr_wells=(),
        dummy_lgr_names=(),
    ):
        """

        """

        with open(file_name, "w") as fout:

            self.write_dummy_lgr_header(fout)

            # Pulls main LGR one cell from boundary
            i_start = int(args.i.split("-")[0]) + 1
            i_end = int(args.i.split("-")[1]) - 1

            j_start = int(args.j.split("-")[0]) + 1
            j_end = int(args.j.split("-")[1]) - 1

            k_start = int(args.k.split("-")[0]) + 1
            k_end = int(args.k.split("-")[1]) - 1

            size_i = i_end - i_start + 1
            size_j = j_end - j_start + 1
            size_k = k_end - k_start + 1

            fout.write("CARFIN\n")
            fout.write("-- NAME --  I1  I2  J1  J2  K1  K2  NX  NY  NZ --\n")
            fout.write("  " + "LGRMAIN")
            fout.write("  " + str(i_start) + "  " + str(i_end))
            fout.write("  " + str(j_start) + "  " + str(j_end))
            fout.write("  " + str(k_start) + "  " + str(k_end))
            fout.write(
                "  " + str(size_i) + "  " + str(size_j) + "  " + str(size_k) + " /\n"
            )
            fout.write("ENDFIN\n\n")

            dummylgr_nr = 0
            LGR_names = []
            for index in range(len(dummy_lgr_cells)):
                (i, j, k) = dummy_lgr_cells[index]
                i = i + 1  # Convert to ECL index
                j = j + 1  # Convert to ECL index
                k = k + 1  # Convert to ECL index

                dummylgr_nr += 1
                dummy_lgr_name = dummy_lgr_names[index]

                if dummy_lgr_name not in LGR_names:
                    fout.write("CARFIN\n")
                    fout.write("-- NAME --  I1  I2  J1  J2  K1  K2  NX  NY  NZ --\n")
                    fout.write("  " + dummy_lgr_name)
                    fout.write("  " + str(i) + "  " + str(i))
                    fout.write("  " + str(j) + "  " + str(j))
                    fout.write("  " + str(k) + "  " + str(k))
                    fout.write("  1  1  1 /\n")
                    fout.write("ENDFIN\n\n")

            fout.write("AMALGAM\n")
            fout.write("  '" + "LGRMAIN" + "'" + " " + "'" + "LGRD*" + "'" + " /\n/\n")

    def write_dummy_lgr_header(self, outfile):

        outfile.write("-- This is an automatically generated INCLUDE file\n")
        outfile.write("-- The INCLUDE file needs to be placed in the GRID section\n")
        outfile.write("-- Fill in the intended grid refinement in LGRMAIN\n")
        outfile.write("-- Dummy LGR regions are amalgamated with the main LGR\n")
        outfile.write("-- Dummy LGR has refinement 1\n\n\n")

    def write_dummy_lgr_data(self, dummy_lgr_cells, dummy_lgr_wells, dummy_lgr_names):

        with open("Dummy_lgr_data.txt", "w") as fout:

            LGR_names = []
            fout.write("-- Dummy LGR data\n\n")
            fout.write("-- i    j    k    lgr_name    well\n")
            for index in range(len(dummy_lgr_cells)):
                (i, j, k) = dummy_lgr_cells[index]
                well = dummy_lgr_wells[index]
                lgr_name = dummy_lgr_names[index]

                if lgr_name not in LGR_names:
                    fout.write(
                        "   " + str(i + 1) + "   " + str(j + 1) + "   " + str(k + 1)
                    )
                    fout.write("   " + lgr_name)
                    fout.write("     " + well + "\n")

            fout.write("--**********************--\n")
