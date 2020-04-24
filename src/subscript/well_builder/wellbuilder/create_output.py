# -*- coding: utf-8 -*-
"""
Created on Sat Aug 17 09:45:15 2019

@author: iari
"""
import getpass
import os
from datetime import datetime
import wellbuilder.prepare_outputs as po
import wellbuilder.wellbuilder_error as err
from wellbuilder.pvt_model import PvtModel, create_correlation_udq, create_parameter_udq
import wellbuilder.visualization as viz


class CreateOutput:
    """This class create outputs from WellBuilder

    There are two outputs from wellbuilder:
    1. well file (text file) -> input to eclipse
    2. well diagram (pdf file) -> well schematic diagram
    """

    # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        class_case,
        class_schedule,
        class_well,
        wb_version,
        user_output=None,
        show_figure=False,
        verbose=1,
    ):
        """Init of the class
        
        Arguments:
            class_case (ReadCasefile object)
            class_schedule (ReadSchedule object)
            class_well (CreateWells object)
            wb_version (str) : WellBuilder version information
        
        Keyword Arguments:
            user_output (str) : user output file. (Default: None)
                then the program will use the case file name
            show_figure (bool) : True if the user wants to create well diagram file
        """
        self.class_case = class_case
        self.class_schedule = class_schedule
        self.class_well = class_well
        self.wb_version = wb_version
        self.name_outputfile(user_output)
        self.verbose = verbose
        # different line connection
        self.newline1 = "\n\n\n"
        self.newline2 = "\n/" + self.newline1
        self.newline3 = "/" + self.newline1

        # create final print
        self.make_wellbuilderheader()

        self.make_welspecs()

        self.make_passivecompdat()

        self.make_passivewelsegs()

        self.make_passivecompsegs()
        self.make_unusedkeywords()

        self.make_udq()
        self.start_finalprint()

        for self.iwell, self.well in enumerate(self.class_well.active_wells):
            self.df_reservoir = self.class_well.df_reservoir_all[
                self.class_well.df_reservoir_all["WELL"] == self.well
            ]
            self.df_well = self.class_well.df_well_all[
                self.class_well.df_well_all["WELL"] == self.well
            ]
            self.laterals = self.df_well[self.df_well["WELL"] == self.well][
                "LATERAL"
            ].unique()
            self.start_printing()
            (self.start_segment, self.start_branch) = (2, 1)
            for self.lateral in self.laterals:
                self.df_tubing = po.prepare_tubinglayer(
                    self.well,
                    self.lateral,
                    self.df_well,
                    self.start_segment,
                    self.start_branch,
                )
                self.df_device = po.prepare_devicelayer(
                    self.well, self.lateral, self.df_well, self.df_tubing
                )
                self.df_annulus, self.df_wseglink = po.prepare_annuluslayer(
                    self.well, self.lateral, self.df_well, self.df_device
                )
                self.df_compsegs = po.prepare_compsegs(
                    self.well,
                    self.lateral,
                    self.df_reservoir,
                    self.df_device,
                    self.df_annulus,
                )
                self.df_compdat = po.prepare_compdat(
                    self.well, self.lateral, self.df_reservoir
                )
                self.df_wsegvalv = po.prepare_wsegvalv(
                    self.well, self.lateral, self.df_well, self.df_device
                )
                self.df_wsegsicd = po.prepare_wsegsicd(
                    self.well, self.lateral, self.df_well, self.df_device
                )
                self.df_wsegaicd = po.prepare_wsegaicd(
                    self.well, self.lateral, self.df_well, self.df_device
                )
                self.df_wsegdar = po.prepare_wsegdar(
                    self.well, self.lateral, self.df_well, self.df_device
                )
                self.df_wsegaicv = po.prepare_wsegaicv(
                    self.well, self.lateral, self.df_well, self.df_device
                )
                self.check_segments()
                self.update_segmentbranch()
                # Start printing
                self.make_compdat()
                self.make_welsegs()
                self.make_wseglink()
                self.make_compsegs()
                self.make_wsegvalv()
                self.make_wsegsicd()
                self.make_wsegaicd()
                self.make_wsegdar()
                self.make_wsegaicv()
            self.fix_printing()
            self.print_perwell()
            if show_figure:
                if self.iwell == 0:
                    pdf_file = viz.create_pdfpages(self.output_pdf)
                    if self.verbose: print('created pdf:', self.output_pdf)
                pdf_file.savefig(
                    visualize_well(self.well, self.df_well, self.df_reservoir),
                    orientation="landscape",
                )
                viz.close_figure()
        # save the final well output
        self.make_finalprint()
        po.save_text(self.output_well, self.finalprint)
        if self.verbose: print('created output:', self.output_well)
        # close the pdf
        if show_figure:
            pdf_file.close()

    def name_outputfile(self, user_output):
        """name the output files

        Args:
            user_output (str) : user name file
        """
        # define output file
        if user_output is None:
            fname = _basename(self.class_case.case_file)
            self.output_well = fname + "_advanced.wells"
        else:
            fname = _basename(user_output)
            self.output_well = fname
        self.output_pdf = fname + "_welldiagram"

    def make_wellbuilderheader(self):
        """Print header note
        """
        self.header = "-" * 100 + "\n"
        self.header = (
            self.header + "-- Output from WellBuilder " + self.wb_version + "\n"
        )
        self.header = self.header + "-- Made in Norway\n"
        self.header = self.header + "-- Copyright Equinor\n"
        self.header = self.header + "-- Case file : " + self.class_case.case_file + "\n"
        self.header = (
            self.header + "-- Schedule file : " + self.class_case.sch_file + "\n"
        )
        if self.class_case.pvt_file is not None:
            self.header = (
                self.header + "-- PVT file : " + self.class_case.pvt_file + "\n"
            )
        self.header = (
            self.header + "-- Created by : " + (getpass.getuser()).upper() + "\n"
        )
        self.header = (
            self.header
            + "-- Created at : "
            + datetime.now().strftime("%d %B %Y %H:%M")
            + "\n"
        )

        self.header = self.header + "-" * 100 + self.newline1

    def make_welspecs(self):
        """print welspecs
        """
        self.welspecs = (
            "WELSPECS\n"
            + po.dataframe_tostring(self.class_schedule.welspecs)
            + self.newline2
        )

    def make_passivecompdat(self):
        """print COMPDAT for wells not in WellBuilder
        """
        all_wells = self.class_schedule.compdat["WELL"].unique()
        active_wells = self.class_well.active_wells
        passive_wells = filter(lambda well: well not in active_wells, all_wells)
        self.passive_compdat = "COMPDAT\n"
        for well in passive_wells:
            df_temp = self.class_schedule.compdat[
                self.class_schedule.compdat["WELL"] == well
            ]
            df_temp = po.rename_compdatheader(df_temp)
            try:
                try_passivecompdat = (
                    self.passive_compdat + po.dataframe_tostring(df_temp, True) + "\n"
                )
            except:
                # meaning that the CF and KH column might be defaulted
                try_passivecompdat = (
                    self.passive_compdat + po.dataframe_tostring(df_temp, False) + "\n"
                )
            self.passive_compdat = try_passivecompdat
        if self.passive_compdat == "COMPDAT\n":
            self.passive_compdat = ""
        else:
            self.passive_compdat = self.passive_compdat + self.newline3

    def make_passivewelsegs(self):
        """print WELSEGS for wells not in WellBuilder
        """
        all_wells = self.class_schedule.welsegs_header["WELL"].unique()
        active_wells = self.class_well.active_wells
        passive_wells = filter(lambda well: well not in active_wells, all_wells)
        self.passive_welsegs = ""
        for well in passive_wells:
            self.passive_welsegs = self.passive_welsegs + "WELSEGS\n"
            df_welsegs1 = self.class_schedule.welsegs_header[
                self.class_schedule.welsegs_header["WELL"] == well
            ]
            df_welsegs2 = self.class_schedule.welsegs_content[
                self.class_schedule.welsegs_content["WELL"] == well
            ]
            # no well should be in the second record
            df_welsegs2 = df_welsegs2.drop(["WELL"], axis=1)
            df_welsegs1, df_welsegs2 = po.rename_welsegsheader(df_welsegs1, df_welsegs2)
            try:
                try_passivewelsegs1 = po.dataframe_tostring(df_welsegs1, True) + "\n"
                try_passivewelsegs2 = (
                    po.dataframe_tostring(df_welsegs2, True) + self.newline2
                )
            except:
                # meaning that the formatting might be wrong then dont format
                try_passivewelsegs1 = po.dataframe_tostring(df_welsegs1, False) + "\n"
                try_passivewelsegs2 = (
                    po.dataframe_tostring(df_welsegs2, False) + self.newline2
                )
            self.passive_welsegs = (
                self.passive_welsegs + try_passivewelsegs1 + try_passivewelsegs2
            )

    def make_passivecompsegs(self):
        """print COMPSEGS for wells not in WellBuilder
        """
        all_wells = self.class_schedule.compsegs["WELL"].unique()
        active_wells = self.class_well.active_wells
        passive_wells = filter(lambda well: well not in active_wells, all_wells)
        self.passive_compsegs = ""
        for well in passive_wells:
            self.passive_compsegs = self.passive_compsegs + "COMPSEGS\n" + well + " /\n"
            df_temp = self.class_schedule.compsegs[
                self.class_schedule.compsegs["WELL"] == well
            ]
            # no well should be in the second record
            df_temp = df_temp.drop(["WELL"], axis=1)
            df_temp = po.rename_compsegsheader(df_temp)
            try:
                try_passivecompsegs = (
                    self.passive_compsegs
                    + po.dataframe_tostring(df_temp, True)
                    + self.newline2
                )
            except:
                # meaning that the formatting might not be correct
                try_passivecompsegs = (
                    self.passive_compsegs
                    + po.dataframe_tostring(df_temp, False)
                    + self.newline2
                )
            self.passive_compsegs = try_passivecompsegs

    def make_unusedkeywords(self):
        """Keep the remaining irrelevant keywords
        """
        self.unused_keywords = ""
        for item in self.class_schedule.unused_keywords:
            self.unused_keywords = self.unused_keywords + item + "\n"
        self.unused_keywords = self.unused_keywords + self.newline1

    def make_udq(self):
        """If PVT file and PVT table is specified

        in the case file then we print the udq statement
        """
        self.print_udq = False
        self.udq_correlation = ""
        self.udq_parameter = {}
        if self.class_case.pvt_file is not None:
            if self.class_case.pvt_table.shape[0] > 0:
                pvt = PvtModel(self.class_case.pvt_file)
                self.print_udq = True
                self.udq_correlation = create_correlation_udq()
                for iwell, well in enumerate(
                    self.class_case.pvt_table["WELL"].unique()
                ):
                    tabnum = self.class_case.pvt_table["PVTTABLE"].iloc[iwell]
                    self.udq_parameter[well] = create_parameter_udq(
                        pvt.all_coefficients, well, tabnum
                    )

    def start_finalprint(self):
        """start printing all wells
        """
        # start printing
        self.finalprint = self.header
        self.finalprint = self.finalprint + self.welspecs
        # passive wells
        self.finalprint = self.finalprint + self.passive_compdat
        self.finalprint = self.finalprint + self.passive_welsegs
        self.finalprint = self.finalprint + self.passive_compsegs
        # print udq equation if relevent
        if self.print_udq:
            self.finalprint = self.finalprint + self.udq_correlation

    def start_printing(self):
        """start printing per well
        """
        self.welsegs_header, content = self.class_schedule.get_welsegs(
            well=self.well, branch=1
        )
        content = ""
        self.check_welsegs1()
        self.print_welsegs = (
            "WELSEGS\n" + po.dataframe_tostring(self.welsegs_header, True) + "\n"
        )
        self.print_welsegsinit = self.print_welsegs
        self.print_wseglink = "WSEGLINK\n"
        self.print_wseglinkinit = self.print_wseglink
        self.print_compsegs = "COMPSEGS\n" + self.well + " /\n"
        self.print_compsegsinit = self.print_compsegs
        self.print_compdat = "COMPDAT\n"
        self.print_compdatinit = self.print_compdat
        self.print_wsegvalv = "WSEGVALV\n"
        self.print_wsegvalvinit = self.print_wsegvalv
        self.print_wsegaicd = "WSEGAICD\n"
        self.print_wsegaicdinit = self.print_wsegaicd
        self.print_wsegsicd = "WSEGSICD\n"
        self.print_wsegsicdinit = self.print_wsegsicd
        self.print_wsegdar = "-" * 100 + "\n"
        self.print_wsegdar = (
            self.print_wsegdar
            + "-- This is how we model DAR technology using sets of ACTIONX keyword\n"
        )
        self.print_wsegdar = self.print_wsegdar + (
            "-- the segment dP curves changes according to the "
            "segment water cut (at downhole condition )\n"
        )
        self.print_wsegdar = (
            self.print_wsegdar + "-- and gas volume fraction (at downhole condition)\n"
        )
        self.print_wsegdar = self.print_wsegdar + (
            "-- the value of Cv is adjusted according to "
            "the segment length and the number of device perjoint\n"
        )
        self.print_wsegdar = (
            self.print_wsegdar
            + "-- the value of Ac varies according to the water cut and gvf values\n"
        )
        self.print_wsegdar = self.print_wsegdar + "-" * 100 + self.newline1
        self.print_wsegdarinit = self.print_wsegdar
        self.print_wsegaicv = "-" * 100 + "\n"
        self.print_wsegaicv = (
            self.print_wsegaicv
            + "-- This is how we model AICV technology using sets of ACTIONX keyword\n"
        )
        self.print_wsegaicv = self.print_wsegaicv + (
            "-- the DP parameters change according"
            "to the segment water cut (at downhole condition )\n"
        )
        self.print_wsegaicv = (
            self.print_wsegaicv + "-- and gas volume fraction (at downhole condition)\n"
        )
        self.print_wsegaicv = self.print_wsegaicv + "-" * 100 + self.newline1
        self.print_wsegaicvinit = self.print_wsegaicv

    def check_welsegs1(self):
        """Check if the MD of the first segment is deeper than first cell STARTMD

        if yes then adjust it so that it is shallower by 1 meter
        """
        start_md = self.df_reservoir["STARTMD"].iloc[0]
        if self.welsegs_header["SEGMENTMD"].iloc[0] > start_md:
            self.welsegs_header["SEGMENTMD"] = start_md - 1.0

    def check_segments(self):
        """check if segment creation are ok
        """
        if self.df_annulus.shape[0] == 0:
            err.wb_message(
                "No annular flow in Well : "
                + self.well
                + " Lateral : "
                + str(self.lateral)
            )
        if self.df_device.shape[0] == 0:
            err.wb_warning(
                "No connection from reservoir to tubing in Well : "
                + self.well
                + " Lateral : "
                + str(self.lateral)
            )

    def update_segmentbranch(self):
        """Update the numbering of the tubing segment and branch
        """
        if self.df_annulus.shape[0] == 0 and self.df_device.shape[0] > 0:
            self.start_segment = max(self.df_device["SEG"].values) + 1
            self.start_branch = max(self.df_device["BRANCH"].values) + 1
        elif self.df_annulus.shape[0] > 0:
            self.start_segment = max(self.df_annulus["SEG"].values) + 1
            self.start_branch = max(self.df_annulus["BRANCH"].values) + 1

    def make_compdat(self):
        """Update print compdat
        """
        nchar = po.get_numberofcharacters(self.df_compdat)
        if self.df_compdat.shape[0] > 0:
            self.print_compdat = (
                self.print_compdat
                + po.get_header(self.well, "COMPDAT", self.lateral, "", nchar)
                + po.dataframe_tostring(self.df_compdat, True)
                + "\n"
            )

    def make_welsegs(self):
        """Update print welsegs
        """
        nchar = po.get_numberofcharacters(self.df_tubing)
        if self.df_device.shape[0] > 0:
            self.print_welsegs = (
                self.print_welsegs
                + po.get_header(self.well, "WELSEGS", self.lateral, "Tubing", nchar)
                + po.dataframe_tostring(self.df_tubing, True)
                + "\n"
            )
        if self.df_device.shape[0] > 0:
            nchar = po.get_numberofcharacters(self.df_tubing)
            self.print_welsegs = (
                self.print_welsegs
                + po.get_header(self.well, "WELSEGS", self.lateral, "Device", nchar)
                + po.dataframe_tostring(self.df_device, True)
                + "\n"
            )
        if self.df_annulus.shape[0] > 0:
            nchar = po.get_numberofcharacters(self.df_tubing)
            self.print_welsegs = (
                self.print_welsegs
                + po.get_header(self.well, "WELSEGS", self.lateral, "Annulus", nchar)
                + po.dataframe_tostring(self.df_annulus, True)
                + "\n"
            )

    def make_wseglink(self):
        """Update print wseglink
        """
        if self.df_wseglink.shape[0] > 0:
            nchar = po.get_numberofcharacters(self.df_wseglink)
            self.print_wseglink = (
                self.print_wseglink
                + po.get_header(self.well, "WSEGLINK", self.lateral, "", nchar)
                + po.dataframe_tostring(self.df_wseglink, True)
                + "\n"
            )

    def make_compsegs(self):
        """Update print compsegs
        """
        nchar = po.get_numberofcharacters(self.df_compsegs)
        if self.df_compsegs.shape[0] > 0:
            self.print_compsegs = (
                self.print_compsegs
                + po.get_header(self.well, "COMPSEGS", self.lateral, "", nchar)
                + po.dataframe_tostring(self.df_compsegs, True)
                + "\n"
            )

    def make_wsegaicd(self):
        """Update print wsegaicd
        """
        if self.df_wsegaicd.shape[0] > 0:
            nchar = po.get_numberofcharacters(self.df_wsegaicd)
            self.print_wsegaicd = (
                self.print_wsegaicd
                + po.get_header(self.well, "WSEGAICD", self.lateral, "", nchar)
                + po.dataframe_tostring(self.df_wsegaicd, True)
                + "\n"
            )

    def make_wsegsicd(self):
        """Update print wsegsicd
        """
        if self.df_wsegsicd.shape[0] > 0:
            nchar = po.get_numberofcharacters(self.df_wsegsicd)
            self.print_wsegsicd = (
                self.print_wsegsicd
                + po.get_header(self.well, "WSEGSICD", self.lateral, "", nchar)
                + po.dataframe_tostring(self.df_wsegsicd, True)
                + "\n"
            )

    def make_wsegvalv(self):
        """Update print wsegvalv
        """
        if self.df_wsegvalv.shape[0] > 0:
            nchar = po.get_numberofcharacters(self.df_wsegvalv)
            self.print_wsegvalv = (
                self.print_wsegvalv
                + po.get_header(self.well, "WSEGVALV", self.lateral, "", nchar)
                + po.dataframe_tostring(self.df_wsegvalv, True)
                + "\n"
            )

    def make_wsegdar(self):
        """Update print wsegdar
        """
        if self.df_wsegdar.shape[0] > 0:
            self.print_wsegdar = (
                self.print_wsegdar
                + po.print_wsegdar(self.df_wsegdar, self.iwell + 1)
                + "\n"
            )

    def make_wsegaicv(self):
        """Update print wsegaicv
        """
        if self.df_wsegaicv.shape[0] > 0:
            self.print_wsegaicv = (
                self.print_wsegaicv
                + po.print_wsegaicv(self.df_wsegaicv, self.iwell + 1)
                + "\n"
            )

    def fix_printing(self):
        """Fix the printing of active wells
        """
        # if no compdat then dont print it
        if self.print_compdat == self.print_compdatinit:
            self.print_compdat = ""
        else:
            self.print_compdat = self.print_compdat + self.newline3
        # if no welsegs then dont print it
        if self.print_welsegs == self.print_welsegsinit:
            self.print_welsegs = ""
        else:
            self.print_welsegs = self.print_welsegs + self.newline3
        # if no compsegs then dont print it
        if self.print_compsegs == self.print_compsegsinit:
            self.print_compsegs = ""
        else:
            self.print_compsegs = self.print_compsegs + self.newline3
        # if no weseglink then dont print it
        if self.print_wseglink == "WSEGLINK\n":
            self.print_wseglink = ""
        else:
            self.print_wseglink = self.print_wseglink + self.newline3
        # if no VALVE then dont print
        if self.print_wsegvalv == "WSEGVALV\n":
            self.print_wsegvalv = ""
        else:
            self.print_wsegvalv = self.print_wsegvalv + self.newline3
        # if no ICD then dont print
        if self.print_wsegsicd == "WSEGSICD\n":
            self.print_wsegsicd = ""
        else:
            self.print_wsegsicd = self.print_wsegsicd + self.newline3
        # if no AICD then dont print
        if self.print_wsegaicd == "WSEGAICD\n":
            self.print_wsegaicd = ""
        else:
            self.print_wsegaicd = self.print_wsegaicd + self.newline3
        # if no DAR then dont print
        if self.print_wsegdar == self.print_wsegdarinit:
            self.print_wsegdar = ""
        else:
            self.print_wsegdar = self.print_wsegdar + self.newline1
        # if no DAR then dont print
        if self.print_wsegaicv == self.print_wsegaicvinit:
            self.print_wsegaicv = ""
        else:
            self.print_wsegaicv = self.print_wsegaicv + self.newline1

    def print_perwell(self):
        """collect final printing for all wells
        """
        # here starts active wells
        self.finalprint = self.finalprint + self.print_compdat
        self.finalprint = self.finalprint + self.print_welsegs
        self.finalprint = self.finalprint + self.print_wseglink
        self.finalprint = self.finalprint + self.print_compsegs
        # print udq parameter if relevant
        if self.well in self.udq_parameter and self.print_udq:
            self.finalprint = self.finalprint + self.udq_parameter[self.well]
        self.finalprint = self.finalprint + self.print_wsegvalv
        self.finalprint = self.finalprint + self.print_wsegsicd
        self.finalprint = self.finalprint + self.print_wsegaicd
        self.finalprint = self.finalprint + self.print_wsegdar
        self.finalprint = self.finalprint + self.print_wsegaicv

    def make_finalprint(self):
        """make final print before saving it
        """
        self.finalprint = self.finalprint + self.unused_keywords


def visualize_tubing(axs, df_well):
    """Visualize tubing layer

    Args:
        axs (pyplot axis))
        df_well (pandas dataframe)

    Returns:
        (pylot axis)
    """
    df_device = df_well[(df_well["NDEVICES"] > 0) | (df_well["DEVICETYPE"] == "PERF")]
    if df_device.shape[0] > 0:
        axs.plot(df_well["TUB_MD"].values, [1] * df_well.shape[0], "go-")
    return axs


def visualize_device(axs, df_well):
    """Visualize device layer

    Args:
        axs (pyplot axis))
        df_well (pandas dataframe)

    Returns:
        (pylot axis)
    """
    df_device = df_well[(df_well["NDEVICES"] > 0) | (df_well["DEVICETYPE"] == "PERF")]
    for i in range(df_device.shape[0]):
        xpar = [df_device["TUB_MD"].iloc[i]] * 2
        ypar = [1.0, 2.0]
        if df_device["DEVICETYPE"].iloc[i] == "PERF":
            axs.plot(xpar, ypar, "ro-", markevery=[1])
        elif df_device["DEVICETYPE"].iloc[i] == "AICD":
            axs.plot(xpar, ypar, "rD-", markevery=[1])
        elif df_device["DEVICETYPE"].iloc[i] == "ICD":
            axs.plot(xpar, ypar, "rs-", markevery=[1])
        elif df_device["DEVICETYPE"].iloc[i] == "VALVE":
            axs.plot(xpar, ypar, "rv-", markevery=[1])
        elif df_device["DEVICETYPE"].iloc[i] == "DAR":
            axs.plot(xpar, ypar, "rP-", markevery=[1])
        elif df_device["DEVICETYPE"].iloc[i] == "AICV":
            axs.plot(xpar, ypar, "r*-", markevery=[1])
    return axs


def visualize_annulus(axs, df_well):
    """Visualize annulus layer

    Args:
        axs (pyplot axis))
        df_well (pandas dataframe)

    Returns:
        (pylot axis)
    """
    df_annulus = df_well[df_well["ANNULUS_ZONE"] > 0]
    branches = df_well["ANNULUS_ZONE"].unique()
    for branch in branches:
        df_branch = df_annulus[df_annulus["ANNULUS_ZONE"] == branch]
        xpar = df_branch["TUB_MD"].values
        ypar = [3] * len(xpar)
        axs.plot(xpar, ypar, "bo-")
        # find the first connection in branches
        df_annulus_with_connection_to_tubing = df_branch[
            (df_branch["NDEVICES"] > 0) | (df_branch["DEVICETYPE"] == "PERF")
        ]
        for i in range(df_annulus_with_connection_to_tubing.shape[0]):
            xpar = [df_annulus_with_connection_to_tubing["TUB_MD"].iloc[i]] * 2
            ypar = [2.0, 3.0]
            if i == 0:
                axs.plot(xpar, ypar, "bo-", markevery=[1])
            else:
                axs.plot(xpar, ypar, "bo:", markevery=[1])
    return axs


def visualize_reservoir(axs, ax_twinx, df_reservoir):
    """visualize reservoir layer

    Args:
        axs (pyplot axis)
        ax_twinx (pyplot axis)
        df_reservoir (pandas dataframe)

    Returns:
        (tupple of pylot axis)
    """
    for i in range(df_reservoir.shape[0]):
        xpar = [df_reservoir["STARTMD"].iloc[i], df_reservoir["ENDMD"].iloc[i]]
        ypar = [4.0, 4.0]
        axs.plot(xpar, ypar, "k|-")
        if df_reservoir["ANNULUS_ZONE"].iloc[i] > 0:
            axs.annotate(
                "",
                xy=(df_reservoir["TUB_MD"].iloc[i], 3.0),
                xytext=(df_reservoir["MD"].iloc[i], 4.0),
                arrowprops=dict(
                    facecolor="black", shrink=0.05, width=0.5, headwidth=4.0
                ),
            )
        else:
            if (
                df_reservoir["NDEVICES"].iloc[i] > 0
                or df_reservoir["DEVICETYPE"].iloc[i] == "PERF"
            ):
                axs.annotate(
                    "",
                    xy=(df_reservoir["TUB_MD"].iloc[i], 2.0),
                    xytext=(df_reservoir["MD"].iloc[i], 4.0),
                    arrowprops=dict(
                        facecolor="black", shrink=0.05, width=0.5, headwidth=4.0
                    ),
                )
    # get connection factor
    if "1*" not in df_reservoir["CF"].values.tolist():
        max_cf = max(df_reservoir["CF"].values)
        ax_twinx.plot(df_reservoir["MD"], df_reservoir["CF"], "k-")
        ax_twinx.invert_yaxis()
        ax_twinx.set_ylim([max_cf * 5.0 + 1e-5, 0])
        ax_twinx.fill_between(df_reservoir["MD"], 0, df_reservoir["CF"], alpha=0.5)

    return axs, ax_twinx


def visualize_annotation(axs, ax_twinx, max_md, min_md):
    """adding annotation in the plot

    Args:
        axs (pyplot axis)
        ax_twinx (pyplot axis)
        max_md (float)
        min_md (float)

    Returns:
        (tupple of pylot axis)
    """
    axs.annotate(
        "Tubing Layer",
        xy=(max_md + 0.1 * (max_md - min_md), 1.0),
        xytext=(max_md + 0.1 * (max_md - min_md), 1.0),
    )
    axs.annotate(
        "Device/Screen Layer",
        xy=(max_md + 0.1 * (max_md - min_md), 2.0),
        xytext=(max_md + 0.1 * (max_md - min_md), 2.0),
    )
    axs.annotate(
        "Annulus Layer",
        xy=(max_md + 0.1 * (max_md - min_md), 3.0),
        xytext=(max_md + 0.1 * (max_md - min_md), 3.0),
    )
    axs.annotate(
        "Reservoir Layer",
        xy=(max_md + 0.1 * (max_md - min_md), 4.0),
        xytext=(max_md + 0.1 * (max_md - min_md), 4.0),
    )
    axs.set_ylim([0, 5])
    axs.set_xlim([min_md - 0.1 * (max_md - min_md), max_md + 0.3 * (max_md - min_md)])
    axs.set_xlabel("mMD")
    ax_twinx.set_ylabel("CF")
    axs.minorticks_on()
    return axs, ax_twinx


def visualize_well(well, df_well, df_reservoir):
    """Visualizing well completion schematic

    Args:
        well (str) : well name
        df_well (pandas dataframe) : well dataframe for this well
        df_reservoir (pandas dataframe) : reservoir dataframe for this well

    Returns:
        (pyplot)
    """
    fig = viz.create_figure()
    laterals = df_well["LATERAL"].unique()
    max_md = max(df_well["TUB_MD"].values)
    min_md = min(df_well["TUB_MD"].values)
    for ilat, lateral in enumerate(laterals):
        df_thiswell = df_well[df_well["LATERAL"] == lateral]
        df_thisreservoir = df_reservoir[df_reservoir["LATERAL"] == lateral]
        axs = fig.add_subplot(len(laterals), 1, ilat + 1)
        axs.get_yaxis().set_visible(False)
        axs.set_title(" Well : " + well + " : Lateral : " + str(lateral))
        ax_twinx = axs.twinx()
        axs.tick_params(which="both", direction="in")
        ax_twinx.tick_params(which="both", direction="in")
        # Tubing layer
        axs = visualize_tubing(axs, df_thiswell)
        # Device / screen layer
        axs = visualize_device(axs, df_thiswell)
        # Annulus layer
        axs = visualize_annulus(axs, df_thiswell)
        # Reservoir layer
        axs, ax_twinx = visualize_reservoir(axs, ax_twinx, df_thisreservoir)
        # print annotation in the plot
        axs, ax_twinx = visualize_annotation(axs, ax_twinx, max_md, min_md)
    fig.subplots_adjust(hspace=0.5, wspace=0.5)
    fig.set_size_inches(18, 3 * len(laterals))
    return fig

def _basename(fname):
    '''
    gives case1 for ../../case1.case
    '''
    return os.path.basename(fname).split('.')[0]
