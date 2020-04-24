# -*- coding: utf-8 -*-
"""
Created on Tue Aug 13 12:14:59 2019

@author: iari
"""
# Importing the required modules
from io import StringIO
import pandas as pd
import numpy as np
import wellbuilder.file_reader as fr
import wellbuilder.input_validation as val
import wellbuilder.wellbuilder_error as err


class ReadCasefile(object):
    """Class for reading WellBuilder case files

    This class reads the case/input file of the WellBuilder program
    it reads the following keywords:
    SCHFILE, COMPLETION, SEGMENTLENGTH, JOINTLENGTH
    WSEGAICD, WSEGVALV, WSEGSICD, WSEGDAR, WSEGAICV
    PVTFILE, PVTTABLE.

    In the case of the absence of some keywords the program
    uses the default values.

    Attributes:
        case_file (str) : the case/input file
        content (list) : list of strings
        n_content (int) : dimension of content
        joint_length (float) : JOINTLENGTH keyword. Default: 12.0
        segment_length (float) : SEGMENTLENGTH keywors. Default: 0.0
        pvt_file (str) : the pvt file
        wsegaicd_table (pandas dataframe) : WSEGAICD
        wsegsicd_table (pandas dataframe) : WSEGSICD
        wsegvalv_table (pandas dataframe) : WSEGVALV
        wsegdar_table (pandas dataframe) : WSEGDAR
        wsegaicv_table (pandas dataframe) : WSEGAICV

    """

    # pylint: disable=too-many-instance-attributes
    def __init__(self, case_file, user_schfile=None, user_pvt=None):
        """Init of the class

        Arguments:
            case_file (str) : case/input file name
            user_schfile (str) : schedule/well file if not defined in case file
            user_pvt (str) : PVT file if not defined in case file


        """
        self.case_file = case_file
        self.content = fr.file_makeup(case_file, "--")
        self.n_content = len(self.content)

        # assign default values
        self.joint_length = 12.0
        self.segment_length = 0.0
        self.pvt_file = user_pvt
        self.sch_file = user_schfile
        self.completion_table = pd.DataFrame()
        self.pvt_table = pd.DataFrame()
        self.wsegaicd_table = pd.DataFrame()
        self.wsegsicd_table = pd.DataFrame()
        self.wsegvalv_table = pd.DataFrame()
        self.wsegdar_table = pd.DataFrame()
        self.wsegaicv_table = pd.DataFrame()

        # Run programs
        self.read_schfile()
        self.read_completion()
        self.read_joinlength()
        self.read_segmentlength()
        self.read_pvtfile()
        self.read_pvttable()
        self.read_wsegaicd()
        self.read_wsegvalv()
        self.read_wsegsicd()
        self.read_wsegdar()
        self.read_wsegaicv()

    def read_schfile(self):
        """This procedure reads the SCHFILE keyword in the case file

        Raises:
            WellBuilder Error : if the schedule/well file is not defined
                in the case file or directly in the argument
        """
        start_index, end_index = fr.locate_keyword(self.content, "SCHFILE", "/")
        # Take the first occurence
        start_index, end_index = fr.take_firstrecord(start_index, end_index)
        if end_index == start_index + 2:
            # the content is in between the keyword and the /
            if self.sch_file is None:
                self.sch_file = fr.remove_stringcharacters(
                    self.content[start_index + 1]
                )
        else:
            if self.sch_file is None:
                err.wb_error(
                    "No well file is defined in the case file or in the command line"
                )

    def read_completion(self):
        """This procedure reads the COMPLETION keyword in the case file

        Raises:
            WellBuilder Error : if COMPLETION keyword is not defined in the case

        """
        start_index, end_index = fr.locate_keyword(self.content, "COMPLETION", "/")
        # Take the first occurence
        start_index, end_index = fr.take_firstrecord(start_index, end_index)
        if start_index == end_index:
            err.wb_error("No completion is defined in the case file")
        else:
            # Table headers
            header = [
                "WELL",
                "BRANCH",
                "STARTMD",
                "ENDMD",
                "INNER_ID",
                "OUTER_ID",
                "ROUGHNESS",
                "ANNULUS",
                "NVALVEPERJOINT",
                "DEVICETYPE",
                "DEVICENUMBER",
                "BLANKPORTION",
            ]
            completion = " ".join(header) + "\n"
            # Combine table headers with the table content
            completion = completion + "\n".join(
                self.content[start_index + 1 : end_index]
            )
            df_temp = pd.read_csv(
                StringIO(completion), sep=" ", dtype=object, index_col=False
            )
            df_temp = fr.remove_stringcharacters(df_temp)
            # Set default value for packer segment
            df_temp = val.setdefault_packersection(df_temp)
            # Set default value for PERF segments
            df_temp = val.setdefault_perfsection(df_temp)
            # Set default value for BLANK segments
            df_temp = val.setdefault_blanksection(df_temp)
            # Give errors if 1* is found for non packer segments
            df_temp = val.checkdefault_nonpacker(df_temp)
            # Align inputs
            df_temp = val.aligninputs_completion(df_temp)
            # Fix the data types format
            df_temp = val.setformat_completion(df_temp)
            # Check overal user inputs on completion
            val.assess_completion(df_temp)
            # store it in a class variable
            self.completion_table = df_temp.copy(deep=True)
            # release memory
            df_temp = None
            completion = None

    def read_joinlength(self):
        """This procedure reads the JOINTLENGTH keyword in the case file

        Raises:
            WellBuilder Warning : if the value is negative
            WellBuilder Message : if it is not defined then use default value
        """
        start_index, end_index = fr.locate_keyword(self.content, "JOINTLENGTH", "/")
        # Take the first occurence
        start_index, end_index = fr.take_firstrecord(start_index, end_index)
        if end_index == start_index + 2:
            self.joint_length = float(self.content[start_index + 1])
            if self.joint_length <= 0:
                err.wb_warning("Invalid joint length. It is set to default 12 m")
                self.joint_length = 12.0
        else:
            err.wb_message("No joint length is defined. It is set to default 12.0 m")

    def read_segmentlength(self):
        """This procedure reads the SEGMENTLENGTH keyword in the case file

        Raises:
            WellBuilder Message : to explain the selection also if it is not defined
        """
        start_index, end_index = fr.locate_keyword(self.content, "SEGMENTLENGTH", "/")
        # Take the first occurence
        start_index, end_index = fr.take_firstrecord(start_index, end_index)
        if end_index == start_index + 2:
            self.segment_length = float(self.content[start_index + 1])
            if self.segment_length < 0.0:
                err.wb_message("Segments are defined based on the COMPLETION keyword")
            elif self.segment_length > 1.0:
                err.wb_message(
                    "Segments are defined per " + str(self.segment_length) + " meters"
                )
        else:
            err.wb_message(
                "No segment length is defined. "
                "Segments are created based on the grid dimension"
            )

    def read_pvtfile(self):
        """This procedure reads the PVTFILE keyword in the case file

        Raises:
            WellBuilder Error : if it is not defined and AICD/DAR device is used in
                COMPLETION keyword
        """
        start_index, end_index = fr.locate_keyword(self.content, "PVTFILE", "/")
        # Take the first occurence
        start_index, end_index = fr.take_firstrecord(start_index, end_index)
        if end_index == start_index + 2:
            # the content is in between the keyword and the /
            if self.pvt_file is None:
                self.pvt_file = fr.remove_stringcharacters(
                    self.content[start_index + 1]
                )
        else:
            comp_device = self.completion_table["DEVICETYPE"].values
            if (self.pvt_file is None) and (
                any(ide in comp_device for ide in ["DAR", "AICV"])
            ):
                err.wb_error("PVT file must be defined, " "if DAR/AICV is selected")

    def read_pvttable(self):
        """This procedure reads the PVTTABLE keyword in the case file

        Raises:
            WellBuilder Error : if it is not defined and AICD/DAR device is used in 
                COMPLETION keyword
        """
        start_index, end_index = fr.locate_keyword(self.content, "PVTTABLE", "/")
        # Take the first occurence
        start_index, end_index = fr.take_firstrecord(start_index, end_index)
        if start_index == end_index:
            comp_device = self.completion_table["DEVICETYPE"].values
            if any(ide in comp_device for ide in ["DAR", "AICV"]):
                err.wb_error(
                    "PVTTABLE keyword must be defined, "
                    "if DAR/AICV is used in the completion"
                )
        else:
            # Table headers
            header = ["WELL", "PVTTABLE"]
            temp_table = " ".join(header) + "\n"
            # Combine table headers with the table content
            temp_table = temp_table + "\n".join(
                self.content[start_index + 1 : end_index]
            )
            try:
                self.pvt_table = fr.string_todf(temp_table)
            except ValueError:
                err.wb_error("Invalid entries in PVTTABLE")
            self.pvt_table = fr.remove_stringcharacters(self.pvt_table)
            # Fix format
            self.pvt_table["PVTTABLE"] = self.pvt_table["PVTTABLE"].astype(np.int64)
            # remove either " or ' from the well name
            self.pvt_table = fr.remove_stringcharacters(self.pvt_table, ["WELL"])
            # Release memory
            temp_table = None
            # Check if wells with DAR/AICV has PVTTABLE
            wells_check = self.completion_table[
                (
                    (self.completion_table["WELL"] == "DAR")
                    | (self.completion_table["WELL"] == "AICV")
                )
            ]["WELL"].values
            if not check_contents(wells_check, self.pvt_table["WELL"].values):
                err.wb_error(
                    "Not all wells with AICD/AICV in COMPLETION is specified in PVTTABLE"
                )

    def read_wsegvalv(self):
        """This procedure reads the WSEGVALV keyword in the case file

        Raises:
            WellBuilder Error : if WESEGVALV is not defined and VALVE is used
                in COMPLETION. Or if the device number is not found
        """
        start_index, end_index = fr.locate_keyword(self.content, "WSEGVALV", "/")
        # Take the first occurence
        start_index, end_index = fr.take_firstrecord(start_index, end_index)
        if start_index == end_index:
            if "VALVE" in self.completion_table["DEVICETYPE"]:
                err.wb_error(
                    "WSEGVALV keyword must be defined, "
                    "if VALVE is used in the completion"
                )
        else:
            # Table headers
            header = ["DEVICENUMBER", "CV", "AC", "L"]
            temp_table = " ".join(header) + "\n"
            # Combine table headers with the table content
            temp_table = temp_table + "\n".join(
                self.content[start_index + 1 : end_index]
            )
            try:
                df_temp = fr.string_todf(temp_table)
            except ValueError:
                err.wb_error("Invalid entries in WSEGVALV")
            # Fix format
            self.wsegvalv_table = val.setformat_wsegvalv(df_temp)
            # Release memory
            df_temp = None
            # Check if the device in COMPLETION is exist in WSEGVALV
            device_checks = self.completion_table[
                self.completion_table["DEVICETYPE"] == "VALVE"
            ]["DEVICENUMBER"].values
            if not check_contents(
                device_checks, self.wsegvalv_table["DEVICENUMBER"].values
            ):
                err.wb_error("Not all device in COMPLETION is specified in WSEGVALV")

    def read_wsegsicd(self):
        """This procedure reads the WSEGSICD keyword in the case file

        Raises:
            WellBuilder Error : if WSEGSICD is not defined and ICD is used
                in COMPLETION. Or if the device number is not found
        """
        start_index, end_index = fr.locate_keyword(self.content, "WSEGSICD", "/")
        # Take the first occurence
        start_index, end_index = fr.take_firstrecord(start_index, end_index)
        if start_index == end_index:
            if "ICD" in self.completion_table["DEVICETYPE"]:
                err.wb_error(
                    "WSEGSICD keyword must be defined, "
                    "if ICD is used in the completion"
                )
        else:
            # Table headers
            header = ["DEVICENUMBER", "STRENGTH", "RHOCAL_ICD", "VISCAL_ICD", "WCUT"]
            temp_table = " ".join(header) + "\n"
            # Combine table headers with the table content
            temp_table = temp_table + "\n".join(
                self.content[start_index + 1 : end_index]
            )
            try:
                df_temp = fr.string_todf(temp_table)
            except ValueError:
                err.wb_error("Invalid entries in WSEGSICD")
            self.wsegsicd_table = val.setformat_wsegsicd(df_temp)
            # Release memory
            df_temp = None
            # Check if the device in COMPLETION is exist in WSEGSICD
            device_checks = self.completion_table[
                self.completion_table["DEVICETYPE"] == "ICD"
            ]["DEVICENUMBER"].values
            if not check_contents(
                device_checks, self.wsegsicd_table["DEVICENUMBER"].values
            ):
                err.wb_error("Not all device in COMPLETION is specified in WSEGSICD")

    def read_wsegaicd(self):
        """This procedure reads the WSEGAICD keyword in the case file

        Raises:
            WellBuilder Error : if WSEGAICD is not defined and AICD is used
                in COMPLETION. Or if the device number is not found
        """
        start_index, end_index = fr.locate_keyword(self.content, "WSEGAICD", "/")
        # Take the first occurence
        start_index, end_index = fr.take_firstrecord(start_index, end_index)
        if start_index == end_index:
            if "AICD" in self.completion_table["DEVICETYPE"]:
                err.wb_error(
                    "WSEGAICD keyword must be defined, "
                    "if AICD is used in the completion"
                )
        else:
            # Table headers
            header = [
                "DEVICENUMBER",
                "ALPHA",
                "X",
                "Y",
                "A",
                "B",
                "C",
                "D",
                "E",
                "F",
                "RHOCAL_AICD",
                "VISCAL_AICD",
            ]
            temp_table = " ".join(header) + "\n"
            # Combine table headers with the table content
            temp_table = temp_table + "\n".join(
                self.content[start_index + 1 : end_index]
            )
            try:
                df_temp = fr.string_todf(temp_table)
            except ValueError:
                err.wb_error("Invalid entries in WSEGAICD")
            # Fix table format
            self.wsegaicd_table = val.setformat_wsegaicd(df_temp)
            # Release memory
            df_temp = None
            # Check if the device in COMPLETION is exist in WSEGAICD
            device_checks = self.completion_table[
                self.completion_table["DEVICETYPE"] == "AICD"
            ]["DEVICENUMBER"].values
            if not check_contents(
                device_checks, self.wsegaicd_table["DEVICENUMBER"].values
            ):
                err.wb_error("Not all device in COMPLETION is specified in WSEGAICD")

    def read_wsegdar(self):
        """This procedure reads the WSEGDAR keyword in the case file

        Raises:
            WellBuilder Error : if WSEGDAR is not defined and DAR is used
                in COMPLETION. Or if the device number is not found
        """
        start_index, end_index = fr.locate_keyword(self.content, "WSEGDAR", "/")
        # Take the first occurence
        start_index, end_index = fr.take_firstrecord(start_index, end_index)
        if start_index == end_index:
            if "DAR" in self.completion_table["DEVICETYPE"]:
                err.wb_error(
                    "WSEGDAR keyword must be defined, "
                    "if DAR is used in the completion"
                )
        else:
            # Table headers
            header = [
                "DEVICENUMBER",
                "CV_DAR",
                "BIG_AC_DAR",
                "SMALL_AC_DAR",
                "SMALLEST_AC_DAR",
                "WCT_DAR",
                "GVF_DAR",
            ]
            temp_table = " ".join(header) + "\n"
            # Combine table headers with the table content
            temp_table = temp_table + "\n".join(
                self.content[start_index + 1 : end_index]
            )
            try:
                df_temp = fr.string_todf(temp_table)
            except ValueError:
                err.wb_error("Invalid entries in WSEGDAR")
            # Fix table format
            self.wsegdar_table = val.setformat_wsegdar(df_temp)
            # Release memory
            df_temp = None
            # Check if the device in COMPLETION is exist in WSEGDAR
            device_checks = self.completion_table[
                self.completion_table["DEVICETYPE"] == "DAR"
            ]["DEVICENUMBER"].values
            if not check_contents(
                device_checks, self.wsegdar_table["DEVICENUMBER"].values
            ):
                err.wb_error("Not all device in COMPLETION is specified in WSEGDAR")

    def read_wsegaicv(self):
        """This procedure reads the WSEGAICV keyword in the case file

        Raises:
            WellBuilder Error : if WSEGAICV is not defined and AICV is used
                in COMPLETION. Or if the device number is not found
        """
        start_index, end_index = fr.locate_keyword(self.content, "WSEGAICV", "/")
        # Take the first occurence
        start_index, end_index = fr.take_firstrecord(start_index, end_index)
        if start_index == end_index:
            if "AICV" in self.completion_table["DEVICETYPE"]:
                err.wb_error(
                    "WSEGAICV keyword must be defined, "
                    "if AICV is used in the completion"
                )
        else:
            # Table headers
            header = [
                "DEVICENUMBER",
                "WCT_AICV",
                "GVF_AICV",
                "RHOCAL_AICV",
                "VISCAL_AICV",
                "ALPHA_MAIN",
                "X_MAIN",
                "Y_MAIN",
                "A_MAIN",
                "B_MAIN",
                "C_MAIN",
                "D_MAIN",
                "E_MAIN",
                "F_MAIN",
                "ALPHA_PILOT",
                "X_PILOT",
                "Y_PILOT",
                "A_PILOT",
                "B_PILOT",
                "C_PILOT",
                "D_PILOT",
                "E_PILOT",
                "F_PILOT",
            ]
            temp_table = " ".join(header) + "\n"
            # Combine table headers with the table content
            temp_table = temp_table + "\n".join(
                self.content[start_index + 1 : end_index]
            )
            try:
                df_temp = fr.string_todf(temp_table)
            except ValueError:
                err.wb_error("Invalid entries in WSEGAICV")
            # Fix table format
            self.wsegaicv_table = val.setformat_wsegaicv(df_temp)
            # Release memory
            df_temp = None
            # Check if the device in COMPLETION is exist in WSEGAICV
            device_checks = self.completion_table[
                self.completion_table["DEVICETYPE"] == "AICV"
            ]["DEVICENUMBER"].values
            if not check_contents(
                device_checks, self.wsegaicv_table["DEVICENUMBER"].values
            ):
                err.wb_error("Not all device in COMPLETION is specified in WSEGAICV")

    def get_completion(self, well, branch):
        """This function returns the COMPLETION table for the selected well and branch

        Args:
            well (str) : well name
            branch (int) : branch/lateral number

        Returns:
            pandas dataframe : COMPLETION for that well and branch
        """
        df_temp = self.completion_table[self.completion_table["WELL"] == well]
        df_temp = df_temp[df_temp["BRANCH"] == branch]
        return df_temp


def check_contents(val_array, ref_array):
    """Check if all members of a list is in another list

    Args:
        val_array (array) : array to be evaluated
        ref_array (array) : reference array

    Returns:
        bol : True if members of val_array are present in ref_array
            False otherwise
    """
    return all(comp in ref_array for comp in val_array)
