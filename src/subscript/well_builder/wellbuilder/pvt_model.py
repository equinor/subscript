# -*- coding: utf-8 -*-
"""
Created on Mon Aug 19 16:02:18 2019

@author: iari
"""

import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
import wellbuilder.file_reader as fr
import wellbuilder.wellbuilder_error as err
import wellbuilder.visualization as viz


class PvtModel(object):
    """
    This class does the following:
        1. read PVT tables e.g. PVTO, PVTG, PVDG, PVDO
        2. Fits the table with polynomial equation
    """

    # pylint: disable=too-many-instance-attributes
    def __init__(self, pvt_file):
        self.content = fr.file_makeup(pvt_file, "--")
        # read tables
        self.pvtw = fr.read_pvt_family(self.content, "PVTW")
        self.density = fr.read_pvt_family(self.content, "DENSITY")
        # read oil and gas table
        if "PVTO" in self.content:
            self.oil_keyword = "PVTO"
            self.pvto = fr.read_pvt_family(self.content, "PVTO")
            self.df_oil = self.pvto.copy(deep=True)
        else:
            self.pvto = pd.DataFrame()
        if "PVDO" in self.content:
            self.oil_keyword = "PVDO"
            self.pvdo = fr.read_pvt_family(self.content, "PVDO")
            # add dummy column for GOR
            self.pvdo["GOR"] = 0.0
            self.df_oil = self.pvdo.copy(deep=True)
        else:
            self.pvdo = pd.DataFrame()
        if "PVTG" in self.content:
            self.gas_keyword = "PVTG"
            self.pvtg = fr.read_pvt_family(self.content, "PVTG")
            self.df_gas = self.pvtg.copy(deep=True)
        else:
            self.pvtg = pd.DataFrame()
        if "PVDG" in self.content:
            self.gas_keyword = "PVDG"
            self.pvdg = fr.read_pvt_family(self.content, "PVDG")
            # add dummy column for OGR
            self.pvdg["OGR"] = 0.0
            self.df_gas = self.pvdg.copy(deep=True)
        else:
            self.pvdg = pd.DataFrame()
        # give error if no oil and gas table is defined
        if self.pvto.shape[0] == 0 and self.pvdo.shape[0] == 0:
            err.wb_error("Either PVTO and PVDO must be defined")
        if self.pvtg.shape[0] == 0 and self.pvdg.shape[0] == 0:
            err.wb_error("Either PVTG and PVDG must be defined")

        # number of pvt table
        self.ntable = self.density["PVTTABLE"].iloc[-1]

        # give errors if the number of pvt table is not the same
        list_ntable = np.asarray(
            [self.df_oil.iloc[-1, 0], self.df_gas.iloc[-1, 0], self.pvtw.iloc[-1, 0]]
        )
        if np.any(list_ntable != self.ntable):
            err.wb_error("The number of PVT table is not consistent")

        # fitting parameters to determine weight
        self.min_pressure = 0.0

        # get coefficients dataframe
        self.bo_coefficients = self.get_bo_coefficients()
        self.bg_coefficients = self.get_bg_coefficients()
        self.bw_coefficients = self.get_bw_coefficients()

        # combine all in one dataframe
        self.all_coefficients = pd.merge(
            self.bo_coefficients,
            self.bg_coefficients,
            how="left",
            left_on=["PVTTABLE"],
            right_on=["PVTTABLE"],
        )
        self.all_coefficients = pd.merge(
            self.all_coefficients,
            self.bw_coefficients,
            how="left",
            left_on=["PVTTABLE"],
            right_on=["PVTTABLE"],
        )

        # visualize data
        visualize_pvt(
            self.df_oil,
            self.bo_coefficients,
            self.df_gas,
            self.bg_coefficients,
            pvt_file,
        )

    def weight(self, df_pvt):
        """This function calculates the weighting factor of the data

        Args:
            df_pvt (pandas dataframe) : pvt table dataframe

        Output:
            np.ndarray : Weighting factor
        """
        ndata = df_pvt.shape[0]
        low_w = np.full(ndata, 1.0)
        high_w = np.full(ndata, 0.5)
        pressure = df_pvt["PRESSURE"].values
        return np.where(pressure < self.min_pressure, low_w, high_w)

    def fit_bo(self, df_pvt):
        """This function finds the coefficient value which fits bo pvt data

        Args:
            df_pvt (pandas dataframe) : pvt table dataframe

        Returns:
            err (float) : average last square error
            coeff_bo (np.ndarray) : array of the 6 equation coefficients
        """
        df_pvt = df_pvt.copy(deep=True)
        sigma = self.weight(df_pvt)
        arr_rsp = df_pvt[["GOR", "PRESSURE"]].values
        bop = df_pvt["BO"].values
        coeff_bo = curve_fit(
            fun_bo, arr_rsp, bop, p0=[1.0] * 6, sigma=sigma, maxfev=50000
        )[0]
        coeff_bo = coeff_bo
        lsq_error = np.mean((bop - fun_bo(arr_rsp, *coeff_bo)) ** 2)
        return lsq_error, coeff_bo

    def fit_bgt(self, df_pvt):
        """This function finds the coefficient value which fits 1/bg pvt data

        Args:
            df_pvt (pandas dataframe) : the table must contain columns PRESSURE, OGR and BG

        Returns:
            err (float) : average last square error
            coeff_bg (np.ndarray) : array of the 5 equation coefficients
        """
        df_pvt = df_pvt.copy(deep=True)
        sigma = self.weight(df_pvt)
        arr_prv = df_pvt[["PRESSURE", "OGR"]].values
        bgp = df_pvt["BG"].values
        coeff_bg = curve_fit(
            fun_bgt, arr_prv, 1.0 / bgp, p0=[1.0] * 5, sigma=sigma, maxfev=50000
        )[0]
        lsq_error = np.mean((1.0 / bgp - fun_bgt(arr_prv, *coeff_bg)) ** 2)
        return lsq_error, coeff_bg

    def get_bo_coefficients(self):
        """This procedure calculates the coefficients of Bo equation which fits PVT data

        Returns:
            pandas dataframe : the table contains coefficients for Bo calculation
        """
        coeff_summary = []
        for itab in range(self.ntable):
            if self.oil_keyword == "PVTO":
                df_pvt = self.pvto[self.pvto["PVTTABLE"] == itab + 1]
            elif self.oil_keyword == "PVDO":
                df_pvt = self.pvdo[self.pvdo["PVTTABLE"] == itab + 1]
            lsq_error, eq_coeff = self.fit_bo(df_pvt)
            if self.oil_keyword == "PVDO":
                # set the 1st, 3rd and 4th coeff to 0
                eq_coeff[0] = eq_coeff[2] = eq_coeff[3] = 0.0
            coeff_summary.append(np.insert(eq_coeff, 0, [itab + 1, lsq_error]))
        columns = ["PVTTABLE", "LSQ_ERROR_BO", "AO", "BO", "CO", "DO", "EO", "FO"]
        return pd.DataFrame(coeff_summary, columns=columns)

    def get_bg_coefficients(self):
        """This procedure calculates the coefficients of Bg equation which fits PVT data

        Returns:
            pandas dataframe : the table contains coefficients for Bg calculation
        """
        coeff_summary = []
        for itab in range(self.ntable):
            if self.gas_keyword == "PVTG":
                df_pvt = self.pvtg[self.pvtg["PVTTABLE"] == itab + 1]
            elif self.gas_keyword == "PVDG":
                df_pvt = self.pvdg[self.pvdg["PVTTABLE"] == itab + 1]
            lsq_error, eq_coeff = self.fit_bgt(df_pvt)
            if self.gas_keyword == "PVDG":
                # set the 4th coeff to 0
                eq_coeff[3] = 0.0
            coeff_summary.append(np.insert(eq_coeff, 0, [itab + 1, lsq_error]))
        columns = ["PVTTABLE", "LSQ_ERROR_BG", "AG", "BG", "CG", "DG", "EG"]
        return pd.DataFrame(coeff_summary, columns=columns)

    def get_bw_coefficients(self):
        """This procedure calculates the coefficients of Bg equation which fits PVT data

        Returns:
            pandas dataframe : the table contains coefficients for Bw calculation
        """
        coeff_summary = []
        for itab in range(self.ntable):
            df_pvt = self.pvtw[self.pvtw["PVTTABLE"] == itab + 1]
            pref = df_pvt["PRESSURE"].iloc[0]
            comp = df_pvt["CW"].iloc[0]
            bwp = df_pvt["BW"].iloc[0]
            coeff_summary.append([itab + 1, pref, bwp, comp])
        return pd.DataFrame(coeff_summary, columns=["PVTTABLE", "PW", "BW", "CW"])


def fun_bo(arr_rsp, *eq_coeff):
    """This function calculate bo from GOR and Pressure

    Args:
        arr_rsp (np.ndarray) : 2d array GOR (1st col) and pressure (2nd col)
        eq_coeff (tupple): the equation 6 coefficients

    Returns:
        np.ndarray : Bo array
    """
    rs_ = arr_rsp[:, 0]
    pr_ = arr_rsp[:, 1]
    a_x = eq_coeff[0]
    b_x = eq_coeff[1]
    c_x = eq_coeff[2]
    d_x = eq_coeff[3]
    e_x = eq_coeff[4]
    f_x = eq_coeff[5]
    bo = (
        a_x * (rs_ ** 2)
        + b_x * (pr_ ** 2)
        + c_x * rs_ * pr_
        + d_x * rs_
        + e_x * pr_
        + f_x
    )
    return bo


def fun_bgt(arr_prv, *eq_coeff):
    """This function calculate 1/bg from Rv and P

    Args:
        arr_prv (p.ndarray): 2d array pressure (1st col) and OGR (2nd col)
        eq_coeff (tupple): the equation 5 coefficients
    Output:
        np.ndarray : 1/Bg
    """
    pr_ = arr_prv[:, 0]
    rv_ = arr_prv[:, 1]
    a_x = eq_coeff[0]
    b_x = eq_coeff[1]
    c_x = eq_coeff[2]
    d_x = eq_coeff[3]
    e_x = eq_coeff[4]
    bgb_t = a_x * (pr_ ** 3) + b_x * (pr_ ** 2) + c_x * pr_ + d_x * rv_ + e_x
    return bgb_t


def bo_crossplot(df_oil, bo_coefficients):
    """This function plots the bo from PVT table and from the correlation

    Args:
        df_oil (pandas dataframe) : must contain GOR, PRESSURE and BO
        bo_coefficients (pandas dataframe) : must contain coefficients AO, BO, CO, DO, EO, FO

    Returns:
        matplotlib figure : matplotlib figure
    """
    fig = viz.create_figure(figsize=[18, 12])
    fig.suptitle("Bo Calculation Accuracy")
    ntables = bo_coefficients.shape[0]
    row, col = viz.subplot_position(ntables)
    for tab in range(1, ntables + 1):
        idf_oil = df_oil[df_oil["PVTTABLE"] == tab]
        ibo_coeff = bo_coefficients[bo_coefficients["PVTTABLE"] == tab]
        ibo_coeff = ibo_coeff[["AO", "BO", "CO", "DO", "EO", "FO"]].values.flatten()
        subplot = fig.add_subplot(row, col, tab)
        bo_true = idf_oil["BO"].values
        bo_calc = fun_bo(idf_oil[["GOR", "PRESSURE"]].values, *ibo_coeff)
        subplot.scatter(bo_true, bo_calc)
        # plot ideal lines
        ideal_line = [min(bo_true) * 0.9, max(bo_true) * 1.1]
        subplot.plot(ideal_line, ideal_line)
        # format plots
        viz.format_axis(subplot, "", "Bo Table m3/Sm3", "Bo Calc m3/Sm3")
        viz.format_scale(subplot)
        viz.format_legend(subplot, False)
    return fig


def bg_crossplot(df_gas, bg_coefficients):
    """This function plots the bg from PVT table and from the correlation

    Args:
        df_gas (pandas dataframe) : must contain OGR, PRESSURE and BG
        bg_coefficients (pandas dataframe) : must contain coefficients AG, BG, CG, DG, EG

    Returns:
        matplotlib figure : matplotlib figure
    """
    fig = viz.create_figure(figsize=[18, 12])
    fig.suptitle("Bg Calculation Accuracy")
    ntables = bg_coefficients.shape[0]
    row, col = viz.subplot_position(ntables)
    for tab in range(1, ntables + 1):
        idf_gas = df_gas[df_gas["PVTTABLE"] == tab]
        ibg_coeff = bg_coefficients[bg_coefficients["PVTTABLE"] == tab]
        ibg_coeff = ibg_coeff[["AG", "BG", "CG", "DG", "EG"]].values.flatten()
        subplot = fig.add_subplot(row, col, tab)
        bg_true = idf_gas["BG"].values
        bg_calc = 1.0 / fun_bgt(idf_gas[["PRESSURE", "OGR"]].values, *ibg_coeff)
        subplot.scatter(bg_true, bg_calc)
        # plot ideal lines
        ideal_line = [min(bg_true) * 0.9, max(bg_true) * 1.1]
        subplot.plot(ideal_line, ideal_line)
        # format plots
        viz.format_axis(subplot, "", "Bg Table m3/Sm3", "Bg Calc m3/Sm3")
        viz.format_scale(subplot, xscale="log", yscale="log")
        viz.format_legend(subplot, False)
    return fig


def bogor_plot(df_oil, bo_coefficients):
    """This function plots the bo vs. pressure @ different GOR both from table and correlation

    Args:
        df_oil (pandas dataframe) : must contain GOR, PRESSURE and BO
        bo_coefficients (pandas dataframe) : must contain coefficients AO, BO, CO, DO, EO, FO

    Returns:
        matplotlib figure : matplotlib figure
    """
    fig = viz.create_figure(figsize=[18, 12])
    fig.suptitle("Bo Vs. GOR and Pressure")
    ntables = bo_coefficients.shape[0]
    row, col = viz.subplot_position(ntables)
    for tab in range(1, ntables + 1):
        idf_oil = df_oil[df_oil["PVTTABLE"] == tab]
        ibo_coeff = bo_coefficients[bo_coefficients["PVTTABLE"] == tab]
        ibo_coeff = ibo_coeff[["AO", "BO", "CO", "DO", "EO", "FO"]].values.flatten()
        subplot = fig.add_subplot(row, col, tab)
        gor = idf_oil["GOR"].unique()
        for igor in gor:
            df_gor = idf_oil[idf_oil["GOR"] == igor]
            pres = df_gor["PRESSURE"].values
            rsp = np.column_stack((np.full(len(pres), igor), pres))
            subplot.scatter(pres, df_gor["BO"].values)
            subplot.plot(pres, fun_bo(rsp, *ibo_coeff))
            # format plots
            viz.format_axis(subplot, "", "Pressure, Bar", "Bo, m3/Sm3")
            viz.format_scale(subplot)
            viz.format_legend(subplot, False)
    return fig


def bgogr_plot(df_gas, bg_coefficients):
    """This function plots the 1/bg vs. OGR @ different pressure both from table and correlation

    Args:
        df_gas (pandas dataframe) : must contain OGR, PRESSURE and BG
        bg_coefficients (pandas dataframe) : must contain coefficients AG, BG, CG, DG, EG

    Returns:
        matplotlib figure : matplotlib figure
    """
    fig = viz.create_figure(figsize=[18, 12])
    fig.suptitle("1/Bg Vs. OGR and Pressure")
    ntables = bg_coefficients.shape[0]
    row, col = viz.subplot_position(ntables)
    for tab in range(1, ntables + 1):
        idf_gas = df_gas[df_gas["PVTTABLE"] == tab]
        ibg_coeff = bg_coefficients[bg_coefficients["PVTTABLE"] == tab]
        ibg_coeff = ibg_coeff[["AG", "BG", "CG", "DG", "EG"]].values.flatten()
        subplot = fig.add_subplot(row, col, tab)
        pressure = idf_gas["PRESSURE"].unique()
        max_ogr = max(idf_gas["OGR"].values)
        if max_ogr == 0.0:
            max_ogr = 1e-5
        for ipres in pressure:
            df_pres = idf_gas[idf_gas["PRESSURE"] == ipres]
            ogr = df_pres["OGR"].values
            prv = np.column_stack((np.full(len(ogr), ipres), ogr))
            subplot.scatter(ogr, 1.0 / df_pres["BG"].values)
            subplot.plot(ogr, fun_bgt(prv, *ibg_coeff))
            # format plots
            viz.format_axis(subplot, "", "OGR, Sm3/Sm3", "1/Bg, Sm3/m3")
            viz.format_scale(subplot, xlim=[0, max_ogr])
            viz.format_legend(subplot, False)
    return fig


def bob_plot(df_oil, bo_coefficients):
    """This function plots the bob vs. gor both from table and correlation

    Args:
        df_oil (pandas dataframe) : must contain GOR, PRESSURE and BO
        bo_coefficients (pandas dataframe) : must contain coefficients AO, BO, CO, DO, EO, FO

    Returns:
        matplotlib figure : matplotlib figure
    """
    fig = viz.create_figure(figsize=[18, 12])
    fig.suptitle("Saturated Bo Profiles")
    ntables = bo_coefficients.shape[0]
    row, col = viz.subplot_position(ntables)
    for tab in range(1, ntables + 1):
        idf_oil = df_oil[df_oil["PVTTABLE"] == tab]
        ibo_coeff = bo_coefficients[bo_coefficients["PVTTABLE"] == tab]
        ibo_coeff = ibo_coeff[["AO", "BO", "CO", "DO", "EO", "FO"]].values.flatten()
        subplot = fig.add_subplot(row, col, tab)
        gor = idf_oil["GOR"].unique()
        bob_true = np.zeros(len(gor))
        pro = np.zeros(len(gor))
        for idx, igor in enumerate(gor):
            df_gor = idf_oil[idf_oil["GOR"] == igor]
            bob_true[idx] = df_gor["BO"].iloc[0]
            pro[idx] = df_gor["PRESSURE"].iloc[0]
        rsp = np.column_stack((gor, pro))
        subplot.scatter(gor, bob_true)
        subplot.plot(gor, fun_bo(rsp, *ibo_coeff))
        # format plots
        viz.format_axis(subplot, "", "GOR, Sm3/Sm3", "Bob, m3/Sm3")
        viz.format_scale(subplot)
        viz.format_legend(subplot, False)
    return fig


def bgb_plot(df_gas, bg_coefficients):
    """This function plots the 1/bgb vs. pressure both from table and correlation

    Args:
        df_gas (pandas dataframe) : must contain OGR, PRESSURE and BG
        bg_coefficients (pandas dataframe) : must contain coefficients AG, BG, CG, DG, EG

    Returns:
        matplotlib figure : matplotlib figure
    """
    fig = viz.create_figure(figsize=[18, 12])
    fig.suptitle("Saturated 1/Bg Profiles")
    ntables = bg_coefficients.shape[0]
    row, col = viz.subplot_position(ntables)
    for tab in range(1, ntables + 1):
        idf_gas = df_gas[df_gas["PVTTABLE"] == tab]
        ibg_coeff = bg_coefficients[bg_coefficients["PVTTABLE"] == tab]
        ibg_coeff = ibg_coeff[["AG", "BG", "CG", "DG", "EG"]].values.flatten()
        subplot = fig.add_subplot(row, col, tab)
        prg = idf_gas["PRESSURE"].unique()
        bgbt_true = np.zeros(len(prg))
        ogr = np.zeros(len(prg))
        for idx, iprg in enumerate(prg):
            df_prg = idf_gas[idf_gas["PRESSURE"] == iprg]
            bgbt_true[idx] = 1.0 / df_prg["BG"].iloc[0]
            ogr[idx] = df_prg["OGR"].iloc[0]
        prv = np.column_stack((prg, ogr))
        subplot.scatter(prg, bgbt_true)
        subplot.plot(prg, fun_bgt(prv, *ibg_coeff))
        # format plots
        viz.format_axis(subplot, "", "Pressure, Bars", "1/Bgb, Sm3/m3")
        viz.format_scale(subplot)
        viz.format_legend(subplot, False)
    return fig


def visualize_pvt(df_oil, bo_coefficients, df_gas, bg_coefficients, filename):
    """This procedure creates plots of Bo from table vs. model

    Args:
        df_oil (pandas dataframe) : must contain GOR, PRESSURE and BO
        bo_coefficients (pandas dataframe) : must contain coefficients AO, BO, CO, DO, EO, FO
        df_gas (pandas dataframe) : must contain OGR, PRESSURE and BG
        bg_coefficients (pandas dataframe) : must contain coefficients AG, BG, CG, DG, EG
        filename (str) : name of the output file .pdf extension
    """
    # update fonts
    viz.update_fonts(size=12)
    # create 3 figures
    pages = viz.create_pdfpages(filename)
    fig1 = bo_crossplot(df_oil, bo_coefficients)
    fig2 = bogor_plot(df_oil, bo_coefficients)
    fig3 = bob_plot(df_oil, bo_coefficients)
    fig4 = bg_crossplot(df_gas, bg_coefficients)
    fig5 = bgogr_plot(df_gas, bg_coefficients)
    fig6 = bgb_plot(df_gas, bg_coefficients)
    pages.savefig(fig1, orientation="lanscape")
    pages.savefig(fig2, orientation="lanscape")
    pages.savefig(fig3, orientation="lanscape")
    pages.savefig(fig4, orientation="lanscape")
    pages.savefig(fig5, orientation="lanscape")
    pages.savefig(fig6, orientation="lanscape")
    viz.close_figure()
    pages.close()


def create_correlation_udq():
    """This function creates UDQ keyword for calculating BO, BG and BW.

    It also creates variables to calculate downhole water cut and gas volume fraction
    """
    define = "DEFINE"
    sp = " "
    end = " /\n"
    newline = " \n"
    # Create input to the equation
    udq_inp = "--Inputs to the Bo, Bg and Bw correlation" + newline
    # adding tollerance 1e-20 (small numbers) to avoid zero division
    udq_inp = udq_inp + define + sp + "SURS" + sp + "(SGFR-SGFRF)/(SOFRF+1e-20)" + end
    udq_inp = udq_inp + define + sp + "SURV" + sp + "(SOFR-SOFRF)/(SGFRF+1e-20)" + end
    udq_inp = udq_inp + define + sp + "SUPR" + sp + "SPR" + end
    # Bo equation
    udq_eq = "--Equation of the Bo correlation" + newline
    udq_eq = (
        udq_eq
        + define
        + sp
        + "SUBOS"
        + sp
        + "SUAO*(SURS^2)+SUBO*(SUPR^2)+SUCO*SURS*SUPR+SUDO*SURS+SUEO*SUPR+SUFO"
        + end
    )
    # Bg equation
    udq_eq = udq_eq + "--Equation of the Bg correlation" + newline
    udq_eq = (
        udq_eq
        + define
        + sp
        + "SUBGS"
        + sp
        + "1.0/(SUAG*(SUPR^3)+SUBG*(SUPR^2)+SUCG*SUPR+SUDG*SURV+SUEG)"
        + end
    )
    # Bw equation
    udq_eq = udq_eq + "--Equation of the Bw correlation" + newline
    udq_eq = (
        udq_eq
        + define
        + sp
        + "SUBWS"
        + sp
        + "SUBW/(1.0+SUCW*(SUPR-SUPW)+0.5*((SUCW*(SUPR-SUPW))^2))"
        + end
    )
    # downhole water cut
    udq_eq = udq_eq + "--Water cut definition" + newline
    # round it to 2 decimals by using NINT / 100
    # add tollerance 1e-20 in case it only flows gas (zero liquid rate)
    udq_eq = (
        udq_eq
        + define
        + sp
        + "SUWCT"
        + sp
        + "NINT((SWFR*SUBWS)*100/(SWFR*SUBWS+SOFRF*SUBOS+1e-20))/100"
        + end
    )
    # downhole gas fraction
    udq_eq = udq_eq + "--Gas fraction definition" + newline
    # round it to 2 decimals by using NINT / 100
    # no need tollerance because it must be something to flow
    udq_eq = (
        udq_eq
        + define
        + sp
        + "SUGVF"
        + sp
        + "NINT((SGFRF*SUBGS)*100/(SWFR*SUBWS+SOFRF*SUBOS+SGFRF*SUBGS))/100"
        + end
    )
    # return UDQ correlation
    return "UDQ\n" + udq_inp + udq_eq + "/\n\n\n"


def create_parameter_udq(df_parameters, well, table_number):
    """This function creates UDQ which define the variables for calculating BO, BW and BG

    Args:
        df_parameters (pandas dataframe) : information which contains correlation coefficients 
            it must contain PVTTABLE, AO, BO, CO, DO, EO, FO, AG, BG, CG, DG, EG, PW, BW, CW
        well (str) : well name
        table_number (int) : the number of PVT table of the well

    Returns:
        str : UDQ statements
    """
    assign = "ASSIGN"
    sp = " "
    par = "SU"
    end = " /\n"
    newline = " \n"
    # filtering df_parameters
    df_parameters = df_parameters[df_parameters["PVTTABLE"] == table_number]
    # getting coefficients for Bo correlation
    oil_coeff_column = ["AO", "BO", "CO", "DO", "EO", "FO"]
    udq_oil = "-- Bo correlation coefficients for well : " + well + newline
    for column in oil_coeff_column:
        # variable
        var = par + column
        # value of the variable
        val = df_parameters[column].iloc[0]
        udq_oil = (
            udq_oil + assign + sp + var + sp + well + sp + "{:.10g}".format(val) + end
        )
    # getting coefficients for Bg correlation
    gas_coeff_column = ["AG", "BG", "CG", "DG", "EG"]
    udq_gas = "-- 1/Bg correlation coefficients for well : " + well + newline
    for column in gas_coeff_column:
        # variable
        var = par + column
        # value of the variable
        val = df_parameters[column].iloc[0]
        udq_gas = (
            udq_gas + assign + sp + var + sp + well + sp + "{:.10g}".format(val) + end
        )
    # getting coefficients for Bw correlation
    water_coeff_column = ["PW", "BW", "CW"]
    udq_water = "-- Bw correlation coefficients for well : " + well + newline
    for column in water_coeff_column:
        # variable
        var = par + column
        # value of the variable
        val = df_parameters[column].iloc[0]
        udq_water = (
            udq_water + assign + sp + var + sp + well + sp + "{:.10g}".format(val) + end
        )
    return "UDQ\n" + udq_oil + udq_gas + udq_water + "/\n\n\n"
