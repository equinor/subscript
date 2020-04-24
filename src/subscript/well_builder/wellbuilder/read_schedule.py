# -*- coding: utf-8 -*-
"""
Created on Sat Aug 17 09:45:15 2019

@author: iari
"""

import pandas as pd
import numpy as np
import wellbuilder.file_reader as fr


class ReadSchedule(object):
    """Class for reading and processing of schedule/well files

    This class reads the schedule/well file.
    It reads the following keywords WELSPECS, COMPDAT, WELSEGS, COMPSEGS.
    The program also reads other keywords, but the unrelated keywords
    will just be printed in the output file.

    Attributes:
        content (list) : list of strings
        collection (class collection) : content collection of keywords in schedule file
        unused_keywords (np.ndarray) : array of strings of unused keywords in the schedule file
        welspecs (pandas dataframe) : table of WELSPECS keyword
        compdat (pandas dataframe) : table of COMPDAT keyword
        compsegs (pandas dataframe) : table of COMPSEGS keyword
        welsegs_header (pandas dataframe) : table of the first record of WELSEGS keyword
        welsegs_content (pandas dataframe) : table of the second record of WELSEGS keyword

    """

    # pylint: disable=too-many-instance-attributes
    def __init__(self, sch_file):
        """Init of the class

        Args:
            sch_file (str) : schedule/well file which contains at least COMPDAT,
                COMPSEGS and WELSEGS

        """
        # read the file
        self.content = fr.file_makeup(sch_file, "--")
        # keywords to be searched
        list_keywords = ["WELSPECS", "COMPDAT", "WELSEGS", "COMPSEGS"]

        # get contents of the listed keywords
        # and the content of the not listed keywords
        self.collections, self.unused_keywords = fr.read_schedulekeywords(
            self.content, list_keywords
        )

        # initiate values
        self.welspecs = pd.DataFrame()
        self.compdat = pd.DataFrame()
        self.compsegs = pd.DataFrame()
        self.welsegs_header = pd.DataFrame()
        self.welsegs_content = pd.DataFrame()

        # extract tables
        self.get_tables()

    def get_tables(self):
        """This procedures get tables of the listed keywords

        Format the data type of the columns which will be used in the WellBuilder program

        """
        # get dataframe table
        self.welspecs = fr.get_welspecs_table(self.collections)
        self.compdat = fr.get_compdat_table(self.collections)
        self.welsegs_header, self.welsegs_content = fr.get_welsegs_table(
            self.collections
        )
        self.compsegs = fr.get_compsegs_table(self.collections)

        # COMPSEGS
        columns1 = ["I", "J", "K", "BRANCH"]
        columns2 = ["STARTMD", "ENDMD"]
        self.compsegs[columns1] = self.compsegs[columns1].astype(np.int64)
        self.compsegs[columns2] = self.compsegs[columns2].astype(np.float64)

        # COMPDAT
        columns1 = ["I", "J", "K", "K2"]
        columns2 = ["CF", "KH"]
        self.compdat[columns1] = self.compdat[columns1].astype(np.int64)
        try:
            # Only if CF and KH are not defaulted by the users
            self.compdat[columns2] = self.compdat[columns2].astype(np.float64)
        except ValueError:
            pass

        # WELSEGS
        columns1 = [
            "TUBINGSEGMENT",
            "TUBINGSEGMENT2",
            "TUBINGBRANCH",
            "TUBINGOUTLET",
            "TUBINGBRANCH",
        ]
        columns2 = ["TUBINGMD", "TUBINGTVD"]
        columns3 = ["SEGMENTTVD", "SEGMENTMD"]
        self.welsegs_content[columns1] = self.welsegs_content[columns1].astype(np.int64)
        self.welsegs_content[columns2] = self.welsegs_content[columns2].astype(
            np.float64
        )
        self.welsegs_header[columns3] = self.welsegs_header[columns3].astype(np.float64)

    def get_welspecs(self, well):
        """This function returns the WELSPECS table of the selected well

        Args:
            well (str) : well name

        Returns:
            pandas dataframe : WELSPECS table for that well
        """
        df_temp = self.welspecs[self.welspecs["WELL"] == well]
        # reset index after filtering
        df_temp.reset_index(drop=True, inplace=True)
        return df_temp

    def get_compdat(self, well):
        """This function returns the COMPDAT table for that well

        Args:
            well (str) : well name

        Returns:
            pandas dataframe : COMPDAT table for that well
        """
        df_temp = self.compdat[self.compdat["WELL"] == well]
        # reset index after filtering
        df_temp.reset_index(drop=True, inplace=True)
        return df_temp

    def get_welsegs(self, well, branch=None):
        """This function returns the WELSEGS table for that well

        Both header and content of the selected well

        Args:
            well (str) : well name
            branch (int) : branch/lateral number

        Returns
            df_header (pandas dataframe) : WELSEGS first record
            df_content (pandas dataframe) : WELSEGS second record

        """
        df1_welsegs = self.welsegs_header[self.welsegs_header["WELL"] == well]
        df2_welsegs = self.welsegs_content[self.welsegs_content["WELL"] == well].copy()
        if branch is not None:
            df2_welsegs = df2_welsegs[df2_welsegs["TUBINGBRANCH"] == branch]
        # remove the well column because it does not exist
        # in the original input
        df2_welsegs.drop(["WELL"], inplace=True, axis=1)
        # reset index after filtering
        df1_welsegs.reset_index(drop=True, inplace=True)
        df2_welsegs.reset_index(drop=True, inplace=True)
        df_header, df_content = fix_welsegs(df1_welsegs, df2_welsegs)
        return df_header, df_content

    def get_compsegs(self, well, branch=None):
        """This function returns the COMPSEGS table

        Args:
            well (str) : well name
            branch (int) : branch/lateral number

        Returns
            pandas dataframe : COMPSEGS table
        """
        df_temp = self.compsegs[self.compsegs["WELL"] == well].copy()
        if branch is not None:
            df_temp = df_temp[df_temp["BRANCH"] == branch]
        # remove the well column because it does not exist
        # in the original input
        df_temp.drop(["WELL"], inplace=True, axis=1)
        # reset index after filtering
        df_temp.reset_index(drop=True, inplace=True)
        return fix_compsegs(df_temp)


def fix_welsegs(df_header, df_content):
    """This procedure fix the welsegs if it is specified in INC instead of ABS

    Args:
        df_header (pandas dataframe) : first record table of WELSEGS
        df_content (pandas dataframe) : second record table of WELSEGS

    Returns:
        df_header (pandas dataframe) : updated dataframe
        df_content (pandas dataframe) : updated dataframe
    """
    df_header = df_header.copy()
    df_content = df_content.copy()
    if df_header["INFOTYPE"].iloc[0] == "ABS":
        return df_header, df_content
    else:
        ref_tvd = df_header["SEGMENTTVD"].iloc[0]
        ref_md = df_header["SEGMENTMD"].iloc[0]
        inlet_segment = df_content["TUBINGSEGMENT"].values
        outlet_segment = df_content["TUBINGOUTLET"].values
        md_inc = df_content["TUBINGMD"].values
        tvd_inc = df_content["TUBINGTVD"].values
        md_new = np.zeros(inlet_segment.shape[0])
        tvd_new = np.zeros(inlet_segment.shape[0])
        for idx, isegout in enumerate(outlet_segment):
            if isegout == 1:
                md_new[idx] = ref_md + md_inc[idx]
                tvd_new[idx] = ref_tvd + tvd_inc[idx]
            else:
                out_idx = np.where(inlet_segment == isegout)[0][0]
                md_new[idx] = md_new[out_idx] + md_inc[idx]
                tvd_new[idx] = tvd_new[out_idx] + tvd_inc[idx]
        # update dataframe
        df_header["INFOTYPE"] = ["ABS"]
        df_content["TUBINGMD"] = md_new
        df_content["TUBINGTVD"] = tvd_new
    return df_header, df_content


def fix_compsegs(df_temp):
    """This procedure fixes the problems of having multiple connection in one cell.

    Meaning one cell is penetrated more than one time by the well.
    It could be because it is a big cell or the well path is complex
    If it happens then we can see it from the COMPSEGS definition
    which have overlapping start MD and End MD.

    Args:
        df_temp (pandas dataframe) : COMPSEGS table

    Returns:
        df_temp (pandas dataframe) : updated table
    """
    df_temp = df_temp.copy(deep=True)
    start_md = df_temp["STARTMD"].values
    end_md = df_temp["ENDMD"].values
    ndata = len(start_md)
    start_md_new = np.zeros(ndata)
    end_md_new = np.zeros(ndata)
    # Check the cells connection
    for idx, istart in enumerate(start_md):
        if idx == 0:
            # assume correct for first entry
            start_md_new[idx] = istart
            end_md_new[idx] = end_md[idx]
        else:
            if (istart - end_md[idx - 1]) < -0.1:
                # only fix if there is overlapping
                start_md_new[idx] = end_md[idx - 1]
                end_md_new[idx] = end_md[idx]
            else:
                start_md_new[idx] = istart
                end_md_new[idx] = end_md[idx]
    df_temp["STARTMD"] = start_md_new
    df_temp["ENDMD"] = end_md_new
    return df_temp
