#!/usr/bin/env python
import sys
import os
import subprocess
import shlex
import shutil
import numpy as np


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

        self.DUMPFLUX_name = "DUMPFLUX_" + self.datafile_shortname
        self.USEFLUX_name = "USEFLUX_" + self.datafile_shortname
        
        self.lines = self.get_datafile_content()


    def get_datafile_content(self):
        with open(self.datafile_name, "r") as f:
            file_content = f.readlines()

        return file_content

    def get_datafile_text_content(self):
        with open(self.datafile_name, "r") as f:
            file_content = f.read()

        return file_content


    def get_lines_clean(self, comment_char = "--"):
        lines_clean = []
        for line in self.lines:
            line = line.strip()
            line = line.split(comment_char)[0]
            line = line.replace("'", "")
            lines_clean.append(line)
        
        return lines_clean


    def has_KW(self, kw):

        return kw in self.get_lines_clean()


    def get_KW_position(self, kw, end_char = "/"):
    
        lines_clean = self.get_lines_clean()
        ncontent = len(lines_clean)
        start_index = np.where(np.asarray(lines_clean) == kw)[0]
    
        if start_index.shape[0] == 0:
            # the keyword is not found
            print("KW " + kw + " not found in DATA\n")
            return np.asarray([-1]), np.asarray([-1])
    
        else:
            end_index = []
            for istart in start_index:
                if end_char != "":
                    idx = istart + 1
                    for idx in range(istart + 1, ncontent):
                        if end_char in lines_clean[idx]:
                            break
                
                else:
                    idx = istart
                    break
                    
                end_index.append(idx)
        
        # return all in a numpy array format
        return start_index, np.asarray(end_index)


    def set_update_RUNSPEC(self, sim_type = ""):
        
        if not self.has_KW('RUNSPEC'):
            raise Exception("ERROR: No RUNSPEC section in DATA file!")

        if sim_type == "DUMPFLUX":
            insert_lines = ["NOSIM\n\n",
                            "OPTIONS\n",
                            "85* 1  /\n\n",
                            "OPTIONS\n",
                            "231* 1  /\n\n"]

        elif sim_type == "USEFLUX":
            insert_lines = ["OPTIONS\n",
                            "85* 1  /\n\n",
                            "OPTIONS\n",
                            "231* 1  /\n\n"]

        else:
            raise Exception("ERROR: Not specified if DUMPFLUX or USEFLUX")

    
        lines_clean = self.get_lines_clean()
        start_idx, end_idx = self.get_KW_position('RUNSPEC', end_char = "/")
        
        idx = start_idx[0]
        for line in insert_lines:
            idx += 1
            self.lines.insert(idx, line)


    def set_update_GRID_DUMPFLUX(self, fluxnumfile_name):
        
       if not self.has_KW('GRID'):
           raise Exception("ERROR: No GRID section in DATA file!")
       
       insert_lines = ["\n\n",
                       "FLUXTYPE\n",
                       "'PRESSURE' /\n\n",
                       "DUMPFLUX\n\n",
                       "INCLUDE\n",
                       "'" + fluxnumfile_name + "'" + " \n",
                       "/\n\n",
                       "FLUXREG\n",
                       "1 /\n\n"]
       

       lines_clean = self.get_lines_clean()
       start_idx, end_idx = self.get_KW_position('GRID', end_char = "/")
       
       idx = start_idx[0]
       for line in insert_lines:
           idx += 1
           self.lines.insert(idx, line)

    
    def set_update_GRID_USEFLUX(self, fluxnumfile_name, fluxfile_name):
        
       if not self.has_KW('GRID'):
           raise Exception("ERROR: No GRID section in DATA file!")
       
       insert_lines = ["\n\n",
                       "FLUXTYPE\n",
                       "'PRESSURE' /\n\n",
                       "USEFLUX\n\n",
                       "'" + fluxfile_name + "'" + "  /\n\n",
                       "INCLUDE\n",
                       "'" + fluxnumfile_name + "'" + " \n",
                       "/\n\n",
                       "FLUXREG\n",
                       "1 /\n\n"]

       lines_clean = self.get_lines_clean()
       start_idx, end_idx = self.get_KW_position('GRID', end_char = "/")
       
       idx = start_idx[0]
       for line in insert_lines:
           idx += 1
           self.lines.insert(idx, line)

           
    def set_update_SOLUTION(self):
        
        if not self.has_KW('SOLUTION'):
           return
       
        insert_lines = [
            "\n\n",
            "-- *** NOTIFICATION ***\n",
            "-- If DUMPFLUX run is based on a RESTART\n",
            "-- USEFLUX run needs to be run based on the DUMPFLUX run\n",
            "-- Use the following and remove any equilibrations\n\n",
            "-- RESTART\n",
            "--  " + "'" + self.DUMPFLUX_name.split(".")[0] + "'" + " " + "0\n",
            "-- /\n"
            ]

        lines_clean = self.get_lines_clean()
        start_idx, end_idx = self.get_KW_position('GRID', end_char = "/")
        
        idx = start_idx[0]
        for line in insert_lines:
            idx += 1
            self.lines.insert(idx, line)
       

    def set_update_PARALLEL(self):
    
        if not self.has_KW('PARALLEL'):
            return

        lines_clean = self.get_lines_clean()
        start_idx, end_idx = self.get_KW_position('PARALLEL', end_char = "/")
        
        for idx in range(start_idx[0], end_idx[0] + 1):
            self.lines[idx] = "-- " + self.lines[idx]
        

    def set_update_NOSIM(self):
    
        if not self.has_KW('NOSIM'):
            return

        lines_clean = self.get_lines_clean()
        start_idx, end_idx = self.get_KW_position('NOSIM', end_char = "")
        
        for idx in range(start_idx[0], end_idx[0] + 1):
            self.lines[idx] = "-- " + self.lines[idx]
        

    
    def set_update_REGDIMS(self):

        if not self.has_KW('REGDIMS'):
            return

        lines_clean = self.get_lines_clean()
        start_idx, end_idx = self.get_KW_position('REGDIMS', end_char = "/")
        
        for idx in range(start_idx[0], end_idx[0] + 1):
            if "/" not in lines_clean[idx]:
                continue
            
            line_clean_elements = lines_clean[idx].split()
            if len(line_clean_elements) > 3:
                line_clean_elements[3] = '1'
                self.lines[idx] = "   ".join(line_clean_elements) + ' \n'
                break

            else:
                raise Exception("Check REGDIMS kw!")

    
    def set_update_INCLUDE(self):
        
        if not self.has_KW('INCLUDE'):
            return
        
        dst_dir = "include/"

        if not os.path.exists(dst_dir):
            try:
                os.mkdir(dst_dir)
            except IOError as err:
                print("ERROR: Could not create new INCLUDE directory\n")
                raise

        lines_clean = self.get_lines_clean()
        start_idx, end_idx = self.get_KW_position('INCLUDE', end_char = "/")
         
        for idx_s in range(len(start_idx)):
            for idx in range(start_idx[idx_s] + 1, end_idx[idx_s] + 1):
                
                if lines_clean[idx] == "":
                    continue
                 
                line_clean_elements = lines_clean[idx].split()
                line_elements = self.lines[idx].split()
                src_file_path = line_clean_elements[0]
                if not os.path.exists(src_file_path):
                    src_file_path = os.path.join(self.datafile_dirname, src_file_path)

                if not os.path.exists(src_file_path):
                    raise OSError("Could not find include file", idx)
                    
                file_name = os.path.basename(src_file_path)
                dst_file_path = os.path.join(dst_dir, file_name)

                # Copy text content in read/write sequence
                try:
                    with open(src_file_path, "r", errors = 'ignore') as fin:
                        infile_text_content = fin.read()
                except:
                    print("Could not open ", src_file_path, "at", idx)
                    raise

                with open(dst_file_path, "w") as fout:
                    fout.write(infile_text_content)
    

                line_elements[0] = "'" + dst_file_path + "'"
                self.lines[idx] = "  " + " ".join(line_elements) + ' \n'
                 
    
    def get_RESTART_warning(self):
        
        if self.has_KW('RESTART'):
           print("WARNING: DUMPFLUX file contains a RESTART.\n")
           print("This may cause problems with execution of DUMPFLUX run.\n")
           print("Please check the RESTART file path before you proceed!")

        else:
            return


    def set_USEFLUX_header(self, args):
        """
        Adds header to the output USEFLUX file

        Input
        @args: Arguments from the intput to the wrapper scripts
        """
        import datetime

        today = datetime.date.today()
        date_str = today.strftime("%d %b %Y")
        
        insert_lines = [
            "-- **************************************************\n",
            "-- **              SECTOR MODEL                    **\n",
            "-- **************************************************\n",
            "-- DATA file created %s\n" % (date_str),
            "--\n",
            "-- This is an automatic generated file for sector simulation ",
            "in ECLIPSE\n",
            "-- The resolution is the same as for the full field model\n",
            "-- DATA file created %s\n" % (date_str),
            "--\n",
            "-- The sector is selected from the following region",
            " in the FF model\n",
            "-- Box dimensions i-dir =  %s\n" % (args.i),
            "-- Box dimensions j-dir =  %s\n" % (args.j),
            "-- Box dimensions k-dir =  %s\n" % (args.k),
            "-- FIPNUM regions = %s\n" % (args.fipnum),
            "-- FLUXNUM from file = %s\n" % (args.fluxfile),
            "--\n",
            "-- FF case is: %s\n" % (args.ECLIPSE_CASE),
            
            "-- Eclipse version is = %s\n" % (args.version),
            "--\n",
            "-- **************************************************\n\n\n",
            ]

        with open(self.USEFLUX_name, "r") as fin:
            lines = fin.readlines()

        idx = 0
        for line in insert_lines:
            idx += 1
            lines.insert(idx, line)

        with open(self.USEFLUX_name, "w") as fout:
            fout.writelines(lines)


    
    def create_DUMPFLUX_file(self, fluxnumfile_name):
        """
        Writes a DATA file with DUMPFLUX keyword.

        Also includes NOSIM and OPTION entries for EOR functionality.

        @fluxnumfile_name : Name of the FLUXNUM kw file to be included
        """
        
        self.set_update_INCLUDE()
        self.set_update_GRID_DUMPFLUX(fluxnumfile_name)
        self.set_update_RUNSPEC(sim_type = "DUMPFLUX")
        self.set_update_PARALLEL()
        self.set_update_REGDIMS()
        self.get_RESTART_warning()
                    
        with open(self.DUMPFLUX_name, "w") as fout:
            fout.writelines(self.lines)

        self.lines = self.get_datafile_content()
        
        if not os.path.isfile(self.DUMPFLUX_name):
            raise Exception("ERROR: DUMPFLUX file not created!")


    
    def create_USEFLUX_file(self, fluxnumfile_name, fluxfile_name):
        """
        Writes a DATA file with USEFLUX keyword.

        @fluxnumfile_name : Name of the FLUXNUM kw file to be included
        """

        if not os.path.isfile(fluxfile_name + ".FLUX"):
            raise Exception("ERROR: FLUX file not found!")
        
        self.set_update_INCLUDE()
        self.set_update_RUNSPEC(sim_type = "USEFLUX")
        self.set_update_NOSIM()
        self.set_update_PARALLEL()
        self.set_update_REGDIMS()
        self.set_update_GRID_USEFLUX(fluxnumfile_name, fluxfile_name)
        self.set_update_SOLUTION()
        self.get_RESTART_warning()
                    
        with open(self.USEFLUX_name, "w") as fout:
            fout.writelines(self.lines)

        self.lines = self.get_datafile_content()
        
        if not os.path.isfile(self.USEFLUX_name):
            raise Exception("ERROR: USEFLUX file not created!")

    


    def run_DUMPFLUX_nosim(self, version="2014.2"):

        """
        Executes interactive ECLIPSE run with DUMPFLUX DATA file.

        ECLIPSE version 2014.2.

        Checks for errors in the output PRT file
        """

        if not (version == "2014.2"):
            print("WARNING: Not a default ECL version. ECL version is %s ..." % version)

        if not os.path.isfile(self.DUMPFLUX_name):
            raise Exception("ERROR: DUMPFLUX file not found!")

            
        # Delete old FLUX file if present
        old_FLUX_file = "%s.FLUX" % self.DUMPFLUX_name.split(".")[0]
        if os.path.isfile(old_FLUX_file):
            try:
                os.remove(old_FLUX_file)
            except OSError as err:
                print("Could not remove old FLUX file ", err)
                raise
        
        commandline = "runeclipse %s -v %s %s" % ("-i", version, self.DUMPFLUX_name)
        args = shlex.split(commandline)
        p = subprocess.Popen(args, stdout=subprocess.PIPE)
        (output, err) = p.communicate()

        if err:
            raise Exception(err)

        print("Checking for errors")
        output_list = output.decode("utf8").split("\n")

        for line in output_list:
            line_strip = line.strip()
            line_elements = line_strip.split()
            
            if (len(line_elements) < 3 
                and "Errors" in line_elements
                and "0" not in line_elements):
                
                print("ERROR: Some errors occured during DUMPFLUX run.\n")
                print("Please check PRT output...")
                print(line_elements)
                sys.exit()

        if not os.path.isfile("%s.FLUX" % self.DUMPFLUX_name.split(".")[0]):
            raise Exception("FLUX file template not created!")


         

