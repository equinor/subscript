# -*- coding: utf-8 -*-
"""
Created on Sat Aug 17 09:45:15 2019

@author: iari
"""
import numpy as np
import pandas as pd
from wellbuilder import completion

# from wellbuilder import prepare_outputs
# import wellbuilder.wellbuilder_error as err

# from wellbuilder.read_casefile import ReadCasefile
# from wellbuilder.read_schedule import ReadSchedule


class CreateWells:
    """Class for creating well completion structure

    the inputs to this class are two objects:
    1. class ReadCasefile
    2. class ReadSchedule

    Attributes:
    1. class_case (ReadCasefile) : class ReadCasefile
    2. class_schedule (ReadSchedule) : class ReadSchedule
    3. active_wells (array str) : list of wells to be completed
    4. method (str) : method for segment creation
    5. well (str) : well in loop
    6. laterals (array int) : list of lateral number of the well in loop
    7. lateral (int) : lateral number in loop
    8. df_completion (pandas dataframe) : completion dataframe in loop
    9. df_reservoir (pandas dataframe) : COMPDAT and COMPSEGS dataframe fusion in loop
    10. df_welsegs1 : WELSEGS first record
    11. df_welsegs2 : WELSEGS second record
    12. df_mdtvd (pandas dataframe) : dataframe of MD and TVD relation
    13. df_tubingsegments (pandas dataframe) : dataframe of tubing segments
    14. df_well (pandas dataframe) : dataframe after completion
    15. df_well_all (pandas dataframe) : df_well for all lateral
    16. df_reservoir_all (pandas dataframe) : df_reservoir for all lateral


    """

    # pylint: disable=too-many-instance-attributes
    def __init__(self, class_case, class_schedule):
        self.class_case = class_case
        self.class_schedule = class_schedule
        # self.class_case = ReadCasefile()
        # self.class_schedule = ReadSchedule()
        self.get_activewells()
        self.define_method()
        for self.well in self.active_wells:
            self.get_activelaterals()
            for self.lateral in self.laterals:
                self.select_well()
                self.well_trajectory()
                self.define_annuluszone()
                self.create_tubingsegments()
                self.insert_missingsegments()
                self.complete_thewell()
                self.get_devices()
                self.correct_annuluszone()
                self.connect_cellstosegments()
                self.update_connectionfactor()
                self.add_welllateralcolumn()
                self.combine_df()

    def get_activewells(self):
        """get list of active wells specified by users
        """
        self.active_wells = self.class_case.completion_table["WELL"].unique()

    def define_method(self):
        """define how the user wants to create segments
        """
        if self.class_case.segment_length == 0.0:
            self.method = "cells"
        elif self.class_case.segment_length > 0.0:
            self.method = "fix"
        elif self.class_case.segment_length < 0.0:
            self.method = "user"

    def get_activelaterals(self):
        """get the lateral numbers of the well
        """
        self.laterals = self.class_case.completion_table[
            self.class_case.completion_table["WELL"] == self.well
        ]["BRANCH"].unique()

    def select_well(self):
        """filter all of the required dataframe for this well and lateral
        """
        self.df_completion = self.class_case.get_completion(self.well, self.lateral)
        self.df_welsegs1, self.df_welsegs2 = self.class_schedule.get_welsegs(
            self.well, self.lateral
        )
        df_compsegs = self.class_schedule.get_compsegs(self.well, self.lateral)
        df_compdat = self.class_schedule.get_compdat(self.well)
        self.df_reservoir = pd.merge(
            df_compdat,
            df_compsegs,
            how="inner",
            left_on=["I", "J", "K"],
            right_on=["I", "J", "K"],
        )
        # remove WELL column in the df_reservoir
        self.df_reservoir.drop(["WELL"], inplace=True, axis=1)

    def well_trajectory(self):
        """create trajectory dataframe relation between md and tvd
        """
        self.df_mdtvd = completion.well_trajectory(self.df_welsegs1, self.df_welsegs2)

    def define_annuluszone(self):
        """define annulus zone if specified
        """
        self.df_completion = completion.define_annuluszone(self.df_completion)

    def create_tubingsegments(self):
        """create tubing segments as the basis
        """
        self.df_tubingsegments = completion.create_tubingsegments(
            self.df_reservoir,
            self.df_completion,
            self.df_mdtvd,
            self.method,
            self.class_case.segment_length,
        )

    def insert_missingsegments(self):
        """create a dummy segment for inactive cells
        """
        self.df_tubingsegments = completion.insert_missingsegments(
            self.df_tubingsegments
        )

    def complete_thewell(self):
        """complete the well using user completion design
        """
        self.df_well = completion.complete_thewell(
            self.df_tubingsegments, self.df_completion, self.class_case.joint_length
        )

    def get_devices(self):
        """now complete the well with the devicce information
        """
        active_devices = self.df_completion["DEVICETYPE"].unique()
        if "VALVE" in active_devices:
            self.df_well = completion.get_device(
                self.df_well, self.class_case.wsegvalv_table, "VALVE"
            )
        if "ICD" in active_devices:
            self.df_well = completion.get_device(
                self.df_well, self.class_case.wsegsicd_table, "ICD"
            )
        if "AICD" in active_devices:
            self.df_well = completion.get_device(
                self.df_well, self.class_case.wsegaicd_table, "AICD"
            )
        if "DAR" in active_devices:
            self.df_well = completion.get_device(
                self.df_well, self.class_case.wsegdar_table, "DAR"
            )
        if "AICV" in active_devices:
            self.df_well = completion.get_device(
                self.df_well, self.class_case.wsegaicv_table, "AICV"
            )

    def correct_annuluszone(self):
        """remove annulus zone if there are no connection to tubing
        """
        self.df_well = completion.correct_annuluszone(self.df_well)

    def connect_cellstosegments(self):
        """connect cells to the well

        from well dataframe we only need columns MD, NDEVICES, DEVICETYPE
        SCREENPORTION and ANNULUS_ZONE
        """
        # drop BRANCH column, not needed
        self.df_reservoir.drop(["BRANCH"], axis=1, inplace=True)
        self.df_reservoir = completion.connectcells_tosegments(
            self.df_well[
                ["TUB_MD", "NDEVICES", "DEVICETYPE", "ANNULUS_ZONE", "SCREENPORTION"]
            ],
            self.df_reservoir,
        )

    def update_connectionfactor(self):
        """Update the CF and KH of COMPDAT

        only in the case where there are blank portion
        and CF and KH are explicitly specified
        """
        self.df_compdat = completion.update_connectionfactor(self.df_reservoir)

    def add_welllateralcolumn(self):
        """adding well & lateral column in the df_well and df_compsegs
        """
        self.df_well["WELL"] = self.well
        self.df_reservoir["WELL"] = self.well
        self.df_well["LATERAL"] = self.lateral
        self.df_reservoir["LATERAL"] = self.lateral

    def combine_df(self):
        """combining all dataframe for this well
        """
        if self.lateral == self.laterals[0] and self.well == self.active_wells[0]:
            self.df_well_all = self.df_well.copy(deep=True)
            self.df_reservoir_all = self.df_reservoir.copy(deep=True)
        else:
            self.df_well_all = pd.concat([self.df_well_all, self.df_well], sort=False)
            self.df_reservoir_all = pd.concat(
                [self.df_reservoir_all, self.df_reservoir], sort=False
            )
