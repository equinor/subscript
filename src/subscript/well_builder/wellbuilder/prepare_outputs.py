# -*- coding: utf-8 -*-
"""
Created on Sat Aug 17 09:45:15 2019

@author: iari
"""

import numpy as np
import pandas as pd
import wellbuilder.wellbuilder_error as err


def trim_pandas(df_temp):
    """This function trims a pandas dataframe which contains default values

    Args:
        df_temp (pandas dataframe) : dataframe

    Returns:
        pandas dataframe : updated dataframe
    """
    header = df_temp.columns.values
    start_trim = -1
    found_start = False
    for i in range(df_temp.shape[1]):
        col_value = df_temp.iloc[:, i].values.flatten().astype(np.str)
        find_star = all("*" in elem for elem in col_value)
        if find_star:
            if not found_start:
                start_trim = i
                found_start = True
        else:
            start_trim = i + 1
            found_start = False
    new_header = header[:start_trim]
    return df_temp[new_header]


def addcolumns_firstlast(df_temp, addfirst=True, addlast=True):
    """adding first and last column of dataframe

    Args:
        df_temp (pandas dataframe) : e.g. WELSPECS, COMPSEGS, COMPDAT, WELSEGS, etc.
        addfirst (bol) : if want to add first column
        addlast (bol) : if want to add last column

    Returns:
        pandas dataframe : updated dataframe
    """
    # first trim pandas
    df_temp = trim_pandas(df_temp)
    # add first and last column
    nline = df_temp.shape[0]
    if addfirst:
        df_temp.insert(loc=0, column="--", value=[" "] * nline)
    if addlast:
        df_temp[""] = ["/"] * nline
    return df_temp


def dataframe_tostring(df_temp, format_column=False, formatters=None):
    """convert pandas dataframe to string

    Args:
        df_temp (pandas dataframe) : COMPDAT, COMPSEGS, etc.

    Keyword Arguments:
        format_column (bool) : if columns is formatted
        formatters (dict) : dictionary of the column format (default:None)

    Returns:
        string : text string of the dataframe
    """
    if df_temp.shape[0] == 0:
        return ""
    # check if the dataframe has first = "--" and last column ""
    columns = df_temp.columns.values
    if columns[-1] != "":
        # trim it first
        df_temp = trim_pandas(df_temp)
        df_temp = addcolumns_firstlast(df_temp, addfirst=False, addlast=True)
        columns = df_temp.columns.values
    if columns[0] != "--":
        # then add first column
        df_temp = addcolumns_firstlast(df_temp, addfirst=True, addlast=False)
    output_string = df_temp.to_string(index=False, justify="left")
    if format_column:
        if formatters is None:
            formatters = {
                "ALPHA": "{:.10g}".format,
                "SF": "{:.10g}".format,
                "ROUGHNESS": "{:.10g}".format,
                "CF": "{:.10g}".format,
                "KH": "{:.10g}".format,
                "MD": "{:.3f}".format,
                "TVD": "{:.3f}".format,
                "STARTMD": "{:.3f}".format,
                "ENDMD": "{:.3f}".format,
                "CV_DAR": "{:.10g}".format,
                "CV": "{:.10g}".format,
                "AC": "{:.10g}".format,
                "AC_TOT_LOWWCT_LOWGVF": "{:.10g}".format,
                "AC_TOT_LOWWCT_HIGHGVF": "{:.10g}".format,
                "AC_TOT_HIGHWCT_LOWGVF": "{:.10g}".format,
                "AC_TOT_HIGHWCT_HIGHGVF": "{:.10g}".format,
                "ALPHA_MAIN": "{:.10g}".format,
                "ALPHA_PILOT": "{:.10g}".format,
            }
        try:
            output_string = df_temp.to_string(
                index=False, justify="left", formatters=formatters
            )
        except ValueError:
            pass
        return output_string
    return output_string


def get_outletsegment(md_tar, md_ref, seg_ref):
    """This function finds the outlet segment in the othe layers

    For example. Finding the corresponding tubing segment of the device segment
    Or finding the corresponding device segment of the annulus segment

    Args:
        md_tar (np.ndarray float) : target measured depth
        md_ref (np.ndarray float) : reference measured depth
        seg_ref (np.ndarray int) : reference segment number

    Returns:
        (np.ndarray int) : the outlet segments
    """
    df1 = pd.DataFrame(md_tar, columns=["MD"])
    df2 = pd.DataFrame(np.column_stack((md_ref, seg_ref)), columns=["MD", "SEG"])
    df2["SEG"] = df2["SEG"].astype(np.int64)
    df2.sort_values(by=["MD"], inplace=True)
    return pd.merge_asof(
        left=df1, right=df2, left_on=["MD"], right_on=["MD"], direction="nearest"
    )["SEG"].values.flatten()


def get_numberofcharacters(df_temp):
    """calculate the number of characters

    Args:
        df_temp (pandas dataframe)

    Returns:
        (int)
    """
    df_temp = df_temp.iloc[:1, :].copy()
    df_temp = dataframe_tostring(df_temp, True)
    df_temp = df_temp.split("\n")
    return len(df_temp[0])


def get_header(well, keyword, lat, layer, nchar=100):
    """Print the header

    Args:
        well (str) : well name
        keyword (str) : table keyword e.g. WELSEGS, COMPSEGS, COMPDAT, etc.
        lat (int) : lateral number
        layer (str) : layer description e.g. tubing, device and annulus
        nchar (int) : number of characters for line boundary. Default 100

    Returns:
        (str) -- string header
    """
    header = "-" * 100 + "\n"
    if keyword == "WELSEGS":
        header = (
            "-" * nchar
            + "\n"
            + "-- Well : "
            + well
            + " : Lateral : "
            + str(lat)
            + " : "
            + layer
            + " layer\n"
        )
    else:
        header = (
            "-" * nchar + "\n" + "-- Well : " + well + " : Lateral : " + str(lat) + "\n"
        )
    return header + "-" * nchar + "\n"


def rename_compsegsheader(df_compsegs):
    """Rename compsegs table header for print purposes

    The original dataframe column name is too long
    So short it before we print the output
    Why we dont change it from the beginning because we want it to be
    clear enough. Printing is ok to have short name.

    Args:
        df_compsegs (pandas dataframe) : COMPSEGS

    Returns:
        (pandas dataframe) : COMPSEGS with new column name
    """
    df_column_dict = {
        "COMPSEGS_DIRECTION": "DIR",
        "ENDGRID": "DEF",
        "PERFDEPTH": "DEPTH",
        "THERM": "TH",
        "SEGMENT": "SEG",
    }
    df_compsegs = df_compsegs.rename(columns=df_column_dict)
    return df_compsegs


def rename_welsegsheader(welsegs_first, welsegs_second):
    """Rename WELSEGS dataframe for printing purposes

    Args:
        welsegs_first (pandas dataframe) : WELSEGS first record
        welsegs_second (pandas dataframe) : WELSEGS second record

    Returns:
        (tupple pandas dataframe) : updated WELSEGS first record and second record
    """
    welsegs_first_dict = {
        "SEGMENTTVD": "TVD",
        "SEGMENTMD": "MD",
        "WBVOLUME": "WBVOL",
        "INFOTYPE": "INF",
        "PDROPCOMP": "CMP",
        "MPMODEL": "MOD",
        "END": "",
    }
    welsegs_second_dict = {
        "TUBINGSEGMENT": "SEG",
        "TUBINGSEGMENT2": "SEG2",
        "TUBINGBRANCH": "BRANCH",
        "TUBINGOUTLET": "OUT",
        "TUBINGMD": "MD",
        "TUBINGTVD": "TVD",
        "TUBINGID": "DIAM",
        "TUBINGROUGHNESS": "ROUGHNESS",
        "END": "",
    }
    welsegs_first = welsegs_first.rename(columns=welsegs_first_dict)
    welsegs_second = welsegs_second.rename(columns=welsegs_second_dict)
    return welsegs_first, welsegs_second


def rename_compdatheader(df_compdat):
    """Rename COMPDAT dataframe for printing purposes

    Args:
        df_compdat (pandas dataframe) : COMPDAT

    Returns:
        (pandas dataframe): updated COMPDAT
    """
    df_column_dict = {"STATUS": "FLAG", "SATNUM": "SAT", "COMPDAT_DIRECTION": "DIR"}
    df_compdat = df_compdat.rename(columns=df_column_dict)
    return df_compdat


def save_text(filename, text):
    """Saving text file

    Args:
        filename (str) : output file fullpath
        text (str) : text to be printed
    """
    thefile = open(filename, "w")
    thefile.write(text)
    thefile.close()


def prepare_tubinglayer(well, lateral, df_well, start_segment, start_branch):
    """prepare tubing layer dataframe

    Args:
        well (str) : well name
        lateral (int) : lateral number
        df_well (pandas dataframe) : must contain column LATERAL, TUB_MD,
            TUB_TVD, INNER_DIAMETER, ROUGHNESS
        start_segment (int) : start number of the first tubing segment
        start_branch (int) : branch number for this tubing layer

    Returns:
        (pandas dataframe) : dataframe for tubing layer
    """
    df_well = df_well[df_well["WELL"] == well]
    df_well = df_well[df_well["LATERAL"] == lateral]
    df_tubing = pd.DataFrame()
    df_tubing["SEG"] = start_segment + np.arange(df_well.shape[0])
    df_tubing["SEG2"] = df_tubing["SEG"].values
    df_tubing["BRANCH"] = start_branch
    df_tubing["OUT"] = np.where(
        df_tubing["SEG"] == start_segment, 1, df_tubing["SEG"] - 1
    )
    df_tubing["MD"] = df_well["TUB_MD"].values
    df_tubing["TVD"] = df_well["TUB_TVD"].values
    df_tubing["DIAM"] = df_well["INNER_DIAMETER"].values
    df_tubing["ROUGHNESS"] = df_well["ROUGHNESS"].values
    df_tubing[""] = "/"
    return df_tubing


def prepare_devicelayer(well, lateral, df_well, df_tubing, device_length=0.1):
    """prepare device layer dataframe

    Args:
        well (str) : well name
        lateral (int) : lateral number
        df_well (pandas dataframe) : must contain LATERAL, TUB_MD, TUB_TVD,
            INNER_DIAMETER, ROUGHNESS, DEVICETYPE and NDEVICES
        df_tubing (pandas dataframe) : dataframe from function prepare_tubinglayer
            for this well and this lateral
        device_length (float) : segment length (default: 0.1)

    Returns:
        (pandas dataframe) : dataframe for device layer
    """
    start_segment = max(df_tubing["SEG"].values) + 1
    start_branch = max(df_tubing["BRANCH"].values) + 1
    df_well = df_well[df_well["WELL"] == well]
    df_well = df_well[df_well["LATERAL"] == lateral]
    # device segments are only created if:
    # 1. the device type is PERF
    # 2. if it is not PERF then it must have number of device > 0
    # if devicetype is BLANK then it would have the number of device = 0
    df_well = df_well[(df_well["DEVICETYPE"] == "PERF") | (df_well["NDEVICES"] > 0)]
    nrow = df_well.shape[0]
    if nrow == 0:
        # return blank dataframe
        return pd.DataFrame()
    # now create dataframe for device layer
    df_device = pd.DataFrame()
    df_device["SEG"] = start_segment + np.arange(nrow)
    df_device["SEG2"] = df_device["SEG"].values
    df_device["BRANCH"] = start_branch + np.arange(nrow)
    df_device["OUT"] = get_outletsegment(
        df_well["TUB_MD"].values, df_tubing["MD"].values, df_tubing["SEG"].values
    )
    df_device["MD"] = df_well["TUB_MD"].values + device_length
    df_device["TVD"] = df_well["TUB_TVD"].values
    df_device["DIAM"] = df_well["INNER_DIAMETER"].values
    df_device["ROUGHNESS"] = df_well["ROUGHNESS"].values
    device_comment = np.where(
        df_well["DEVICETYPE"] == "PERF",
        "/ -- Open Perforation",
        np.where(
            df_well["DEVICETYPE"] == "AICD",
            "/ -- AICD types      ",
            np.where(
                df_well["DEVICETYPE"] == "ICD",
                "/ -- ICD types       ",
                np.where(
                    df_well["DEVICETYPE"] == "VALVE",
                    "/ -- Valve types     ",
                    np.where(
                        df_well["DEVICETYPE"] == "DAR",
                        "/ -- DAR types     ",
                        np.where(
                            df_well["DEVICETYPE"] == "AICV", "/ -- AICV types    ", ""
                        ),
                    ),
                ),
            ),
        ),
    )
    df_device[""] = device_comment
    return df_device


def prepare_annuluslayer(well, lateral, df_well, df_device, annulus_length=0.1):
    """prepare annulus layer and wseglink dataframe

    Args:
        well (str) : well name
        lateral (int) : lateral number
        df_well (pandas dataframe) : must contain LATERAL, ANNULUS_ZONE,
            TUB_MD, TUB_TVD, OUTER_DIAMETER,
            ROUGHNESS, DEVICETYPE and NDEVICES
        df_device (pandas dataframe) : dataframe from function prepare_devicelayer
            for this well and this lateral
        annulus_length (float) : annulus segment length increment (default: 0.1)

    Returns:
        (tupple of pandas dataframe) : (annulus dataframe, wseglink dataframe)
    """
    # filter for this lateral
    df_well = df_well[df_well["WELL"] == well]
    df_well = df_well[df_well["LATERAL"] == lateral]
    # filter segments which have annular zones
    df_well = df_well[df_well["ANNULUS_ZONE"] > 0]
    # loop through all annular zones
    # initiate annulus and wseglink dataframe
    df_annulus = pd.DataFrame()
    df_wseglink = pd.DataFrame()
    for izone, zone in enumerate(df_well["ANNULUS_ZONE"].unique()):
        # filter only that annular zone
        df_branch = df_well[df_well["ANNULUS_ZONE"] == zone]
        df_active = df_branch[
            (df_branch["NDEVICES"].values > 0)
            | (df_branch["DEVICETYPE"].values == "PERF")
        ]
        # setting the start segment number and start branch number
        if izone == 0:
            start_segment = max(df_device["SEG"]) + 1
            start_branch = max(df_device["BRANCH"]) + 1
        else:
            start_segment = max(df_annulus["SEG"]) + 1
            start_branch = max(df_annulus["BRANCH"]) + 1
        # now find the most downstream connection of the annulus zone
        idx_connection = np.argwhere(
            (df_branch["NDEVICES"].values > 0)
            | (df_branch["DEVICETYPE"].values == "PERF")
        )
        if idx_connection[0] == 0:
            # If the first connection then everything is easy
            df_annulus_upstream = pd.DataFrame()
            df_annulus_upstream["SEG"] = start_segment + np.arange(df_branch.shape[0])
            df_annulus_upstream["SEG2"] = df_annulus_upstream["SEG"]
            df_annulus_upstream["BRANCH"] = start_branch
            # determining the outlet segment of the annulus segment
            # if the annulus segment is not the most downstream which has connection
            # then the outlet is its adjacent annulus segment
            out_segment = df_annulus_upstream["SEG"].values - 1
            # but for the most downstream annulus segment
            # its outlet is the device segment
            device_segment = get_outletsegment(
                df_branch["TUB_MD"].values,
                df_device["MD"].values,
                df_device["SEG"].values,
            )
            out_segment[0] = device_segment[0]
            md_ = df_branch["TUB_MD"].values + annulus_length
            md_[0] = md_[0] + annulus_length
            # completing the dataframe
            df_annulus_upstream["OUT"] = out_segment
            df_annulus_upstream["MD"] = md_
            df_annulus_upstream["TVD"] = df_branch["TUB_TVD"].values
            df_annulus_upstream["DIAM"] = df_branch["OUTER_DIAMETER"].values
            df_annulus_upstream["ROUGHNESS"] = df_branch["ROUGHNESS"].values
            # create WSEGLINK dataframe
            df_wseglink_upstream = pd.DataFrame()
            device_segment = get_outletsegment(
                df_active["TUB_MD"].values,
                df_device["MD"].values,
                df_device["SEG"].values,
            )
            annulus_segment = get_outletsegment(
                df_active["TUB_MD"].values,
                df_annulus_upstream["MD"].values,
                df_annulus_upstream["SEG"].values,
            )
            outlet_segment = get_outletsegment(
                df_active["TUB_MD"].values,
                df_annulus_upstream["MD"].values,
                df_annulus_upstream["OUT"].values,
            )
            df_wseglink_upstream["WELL"] = [well] * device_segment.shape[0]
            df_wseglink_upstream["ANNULUS"] = annulus_segment
            df_wseglink_upstream["DEVICE"] = device_segment
            df_wseglink_upstream["OUTLET"] = outlet_segment
            # basically WSEGLINK is only for those segments
            # whose its outlet segment is not a device segment
            df_wseglink_upstream = df_wseglink_upstream[
                df_wseglink_upstream["DEVICE"] != df_wseglink_upstream["OUTLET"]
            ]
        else:
            # meaning the main connection is not the most downstream segment
            # therefore we have to split the annulus segment into two
            # the splitting point is the most downstream segment
            # which have device segment open or PERF
            df_branch_downstream = df_branch.iloc[0 : idx_connection[0], :]
            df_branch_upstream = df_branch.iloc[
                idx_connection[0] :,
            ]

            # downstream part
            df_annulus_downstream = pd.DataFrame()
            df_annulus_downstream["SEG"] = start_segment + np.arange(
                df_branch_downstream.shape[0]
            )
            df_annulus_downstream["SEG2"] = df_annulus_downstream["SEG"]
            df_annulus_downstream["BRANCH"] = start_branch
            df_annulus_downstream["OUT"] = df_annulus_downstream["SEG"] + 1
            df_annulus_downstream["MD"] = (
                df_branch_downstream["TUB_MD"].values + annulus_length
            )
            df_annulus_downstream["TVD"] = df_branch_downstream["TUB_TVD"].values
            df_annulus_downstream["DIAM"] = df_branch_downstream[
                "OUTER_DIAMETER"
            ].values
            df_annulus_downstream["ROUGHNESS"] = df_branch_downstream[
                "ROUGHNESS"
            ].values

            # no WSEGLINK in the downstream part because no annulus segment have connection to
            # the device segment. in case you wonder why :)

            # upstream part
            # update the start segment and start branch
            start_segment = max(df_annulus_downstream["SEG"]) + 1
            start_branch = max(df_annulus_downstream["BRANCH"]) + 1
            # create dataframe for upstream part
            df_annulus_upstream = pd.DataFrame()
            df_annulus_upstream["SEG"] = start_segment + np.arange(
                df_branch_upstream.shape[0]
            )
            df_annulus_upstream["SEG2"] = df_annulus_upstream["SEG"]
            df_annulus_upstream["BRANCH"] = start_branch

            # determining the outlet segment of the annulus segment
            # if the annulus segment is not the most downstream which has connection
            # then the outlet is its adjacent annulus segment
            device_segment = get_outletsegment(
                df_branch_upstream["TUB_MD"].values,
                df_device["MD"].values,
                df_device["SEG"].values,
            )
            out_segment = df_annulus_upstream["SEG"].values - 1
            # but for the most downstream annulus segment
            # its outlet is the device segment
            out_segment[0] = device_segment[0]
            # determining segment position
            md_ = df_branch_upstream["TUB_MD"].values + annulus_length
            md_[0] = md_[0] + annulus_length

            df_annulus_upstream["OUT"] = out_segment
            df_annulus_upstream["MD"] = md_
            df_annulus_upstream["TVD"] = df_branch_upstream["TUB_TVD"].values
            df_annulus_upstream["DIAM"] = df_branch_upstream["OUTER_DIAMETER"].values
            df_annulus_upstream["ROUGHNESS"] = df_branch_upstream["ROUGHNESS"].values

            df_wseglink_upstream = pd.DataFrame()
            device_segment = get_outletsegment(
                df_active["TUB_MD"].values,
                df_device["MD"].values,
                df_device["SEG"].values,
            )
            annulus_segment = get_outletsegment(
                df_active["TUB_MD"].values,
                df_annulus_upstream["MD"].values,
                df_annulus_upstream["SEG"].values,
            )
            outlet_segment = get_outletsegment(
                df_active["TUB_MD"].values,
                df_annulus_upstream["MD"].values,
                df_annulus_upstream["OUT"].values,
            )
            df_wseglink_upstream["WELL"] = [well] * device_segment.shape[0]
            df_wseglink_upstream["ANNULUS"] = annulus_segment
            df_wseglink_upstream["DEVICE"] = device_segment
            df_wseglink_upstream["OUTLET"] = outlet_segment
            # basically WSEGLINK is only for those segments
            # whose its outlet segment is not a device segment
            df_wseglink_upstream = df_wseglink_upstream[
                df_wseglink_upstream["DEVICE"] != df_wseglink_upstream["OUTLET"]
            ]
            # combine the two dataframe upstream and downstream
            df_annulus_upstream = pd.concat(
                [df_annulus_downstream, df_annulus_upstream]
            )

        # combine annulus and wseglink dataframe
        if izone == 0:
            df_annulus = df_annulus_upstream.copy(deep=True)
            df_wseglink = df_wseglink_upstream.copy(deep=True)
        else:
            df_annulus = pd.concat([df_annulus, df_annulus_upstream])
            df_wseglink = pd.concat([df_wseglink, df_wseglink_upstream])

    if df_wseglink.shape[0] > 0:
        df_wseglink = df_wseglink[["WELL", "ANNULUS", "DEVICE"]]
        df_wseglink["ANNULUS"] = df_wseglink["ANNULUS"].astype(np.int64)
        df_wseglink["DEVICE"] = df_wseglink["DEVICE"].astype(np.int64)
        df_wseglink[""] = "/"

    if df_annulus.shape[0] > 0:
        df_annulus[""] = "/"
    return df_annulus, df_wseglink


def prepare_compsegs(well, lateral, df_reservoir, df_device, df_annulus):
    """prepare output for COMPSEGS

    Args:
        well (str) : well name
        lateral (int) : lateral number
        df_reservoir (pandas dataframe) : the df_reservoir from class
            object CreateWells
        df_device (pandas dataframe) : dataframe from function
            prepare_devicelayer for this well and this lateral
        df_annulus (pandas dataframe) : dataframe from function
            prepare_annuluslayer for this well and this lateral

    Returns:
        (pandas dataframe) : COMPSEGS dataframe
    """
    # filter for this lateral
    df_reservoir = df_reservoir[df_reservoir["WELL"] == well]
    df_reservoir = df_reservoir[df_reservoir["LATERAL"] == lateral]
    # compsegs is only for those who are either:
    # 1. open perforation in the device segment
    # 2. has number of device > 0
    # 3. it is connected in the annular zone
    df_reservoir = df_reservoir[
        (df_reservoir["ANNULUS_ZONE"] > 0)
        | ((df_reservoir["NDEVICES"] > 0) | (df_reservoir["DEVICETYPE"] == "PERF"))
    ]
    # sort device dataframe by MD to be used for pd.merge_asof
    if df_reservoir.shape[0] == 0:
        return pd.DataFrame()
    df_device = df_device.sort_values(by=["MD"])
    if df_annulus.shape[0] == 0:
        # meaning there are no annular zones then
        # all cells in this lateral and this well
        # are connected to the device segment
        df_compseg_device = pd.merge_asof(
            left=df_reservoir,
            right=df_device,
            left_on=["MD"],
            right_on=["MD"],
            direction="nearest",
        )
        compseg = pd.DataFrame()
        compseg["I"] = df_compseg_device["I"].values
        compseg["J"] = df_compseg_device["J"].values
        compseg["K"] = df_compseg_device["K"].values
        # take the BRANCH column from df_device
        compseg["BRANCH"] = df_compseg_device["BRANCH"].values
        compseg["STARTMD"] = df_compseg_device["STARTMD"].values
        compseg["ENDMD"] = df_compseg_device["ENDMD"].values
        compseg["DIR"] = df_compseg_device["COMPSEGS_DIRECTION"].values
        compseg["DEF"] = "3*"
        compseg["SEG"] = df_compseg_device["SEG"].values
    else:
        # sort the df_annulus and df_device
        df_annulus = df_annulus.sort_values(by=["MD"])
        df_compseg_annulus = pd.merge_asof(
            left=df_reservoir,
            right=df_annulus,
            left_on=["MD"],
            right_on=["MD"],
            direction="nearest",
        )
        df_compseg_device = pd.merge_asof(
            left=df_reservoir,
            right=df_device,
            left_on=["MD"],
            right_on=["MD"],
            direction="nearest",
        )

        compseg = pd.DataFrame()
        compseg["I"] = choose_layer(
            df_reservoir, df_compseg_annulus, df_compseg_device, "I"
        )
        compseg["J"] = choose_layer(
            df_reservoir, df_compseg_annulus, df_compseg_device, "J"
        )
        compseg["K"] = choose_layer(
            df_reservoir, df_compseg_annulus, df_compseg_device, "K"
        )
        compseg["BRANCH"] = choose_layer(
            df_reservoir, df_compseg_annulus, df_compseg_device, "BRANCH"
        )
        compseg["STARTMD"] = choose_layer(
            df_reservoir, df_compseg_annulus, df_compseg_device, "STARTMD"
        )
        compseg["ENDMD"] = choose_layer(
            df_reservoir, df_compseg_annulus, df_compseg_device, "ENDMD"
        )
        compseg["DIR"] = choose_layer(
            df_reservoir, df_compseg_annulus, df_compseg_device, "COMPSEGS_DIRECTION"
        )
        compseg["DEF"] = "3*"
        compseg["SEG"] = choose_layer(
            df_reservoir, df_compseg_annulus, df_compseg_device, "SEG"
        )

    compseg[""] = "/"

    return compseg


def choose_layer(df_reservoir, df_compseg_annulus, df_compseg_device, parameter):
    """Return relevant parameters from either
        df_compseg_annulus & df_compseg_device

    Arguments:
        df_reservoir (pandas dataframe)
        df_compseg_annulus (pandas dataframe)
        df_compseg_device (pandas dataframe)
        parameter (str)

    Returns:
        np.ndarray
    """
    branch_num = df_reservoir["ANNULUS_ZONE"].values
    ndevice = df_reservoir["NDEVICES"].values
    dev_type = df_reservoir["DEVICETYPE"].values
    return np.where(
        branch_num > 0,
        df_compseg_annulus[parameter].values,
        np.where(
            (ndevice > 0) | (dev_type == "PERF"),
            df_compseg_device[parameter].values,
            -1,
        ),
    )


def prepare_compdat(well, lateral, df_reservoir):
    """prepare COMPDAT dataframe

    Args:
        well (str) : well name
        lateral (int) : lateral number
        df_reservoir (pandas dataframe) : df_reservoir from class CreateWells

    Returns:
        (pandas dataframe) : COMPDAT
    """
    df_reservoir = df_reservoir[df_reservoir["WELL"] == well]
    df_reservoir = df_reservoir[df_reservoir["LATERAL"] == lateral]
    df_reservoir = df_reservoir[
        (df_reservoir["ANNULUS_ZONE"] > 0)
        | ((df_reservoir["NDEVICES"] > 0) | (df_reservoir["DEVICETYPE"] == "PERF"))
    ]
    if df_reservoir.shape[0] == 0:
        return pd.DataFrame()
    compdat = pd.DataFrame()
    compdat["WELL"] = [well] * df_reservoir.shape[0]
    compdat["I"] = df_reservoir["I"].values
    compdat["J"] = df_reservoir["J"].values
    compdat["K"] = df_reservoir["K"].values
    compdat["K2"] = df_reservoir["K2"].values
    compdat["FLAG"] = df_reservoir["STATUS"].values
    compdat["SAT"] = df_reservoir["SATNUM"].values
    compdat["CF"] = df_reservoir["CF"].values
    compdat["DIAM"] = df_reservoir["DIAM"].values
    compdat["KH"] = df_reservoir["KH"].values
    compdat["SKIN"] = df_reservoir["SKIN"].values
    compdat["DFACT"] = df_reservoir["DFACT"].values
    compdat["DIR"] = df_reservoir["COMPDAT_DIRECTION"].values
    compdat["RO"] = df_reservoir["RO"].values
    # remove default columns
    compdat = trim_pandas(compdat)
    compdat[""] = "/"
    return compdat


def prepare_wsegaicd(well, lateral, df_well, df_device):
    """prepare WSEGAICD dataframe

    Args:
        well (str) : well name
        lateral (int) : lateral number
        df_well (pandas dataframe) : df_well from class CreateWells
        df_device (pandas dataframe) : from function prepare_devicelayer
            for this well and this lateral

    Returns:
        (pandas dataframe) : WSEGAICD
    """
    df_well = df_well[df_well["WELL"] == well]
    df_well = df_well[df_well["LATERAL"] == lateral]
    df_well = df_well[(df_well["DEVICETYPE"] == "PERF") | (df_well["NDEVICES"] > 0)]
    if df_well.shape[0] == 0:
        return pd.DataFrame()
    df_merge = pd.merge_asof(
        left=df_device,
        right=df_well,
        left_on=["MD"],
        right_on=["TUB_MD"],
        direction="nearest",
    )
    df_merge = df_merge[df_merge["DEVICETYPE"] == "AICD"]
    wsegaicd = pd.DataFrame()
    if df_merge.shape[0] > 0:
        wsegaicd["WELL"] = [well] * df_merge.shape[0]
        wsegaicd["SEG"] = df_merge["SEG"].values
        wsegaicd["SEG2"] = df_merge["SEG"].values
        wsegaicd["ALPHA"] = df_merge["ALPHA"].values
        wsegaicd["SF"] = df_merge["SCALINGFACTOR"].values
        wsegaicd["RHO"] = df_merge["RHOCAL_AICD"].values
        wsegaicd["VIS"] = df_merge["VISCAL_AICD"].values
        wsegaicd["DEF"] = ["5*"] * df_merge.shape[0]
        wsegaicd["X"] = df_merge["X"].values
        wsegaicd["Y"] = df_merge["Y"].values
        wsegaicd["FLAG"] = ["OPEN"] * df_merge.shape[0]
        wsegaicd["A"] = df_merge["A"].values
        wsegaicd["B"] = df_merge["B"].values
        wsegaicd["C"] = df_merge["C"].values
        wsegaicd["D"] = df_merge["D"].values
        wsegaicd["E"] = df_merge["E"].values
        wsegaicd["F"] = df_merge["F"].values
        wsegaicd[""] = "/"
    return wsegaicd


def prepare_wsegsicd(well, lateral, df_well, df_device):
    """prepare WSEGSICD dataframe

    Args:
        well (str) : well name
        lateral (int) : lateral number
        df_well (pandas dataframe) : df_well from class CreateWells
        df_device (pandas dataframe) : from function prepare_devicelayer
            for this well and this lateral

    Returns:
        (pandas dataframe) : WSEGSICD
    """
    df_well = df_well[df_well["LATERAL"] == lateral]
    df_well = df_well[(df_well["DEVICETYPE"] == "PERF") | (df_well["NDEVICES"] > 0)]
    if df_well.shape[0] == 0:
        return pd.DataFrame()
    df_merge = pd.merge_asof(
        left=df_device,
        right=df_well,
        left_on=["MD"],
        right_on=["TUB_MD"],
        direction="nearest",
    )
    df_merge = df_merge[df_merge["DEVICETYPE"] == "ICD"]
    wsegsicd = pd.DataFrame()
    if df_merge.shape[0] > 0:
        wsegsicd["WELL"] = [well] * df_merge.shape[0]
        wsegsicd["SEG"] = df_merge["SEG"].values
        wsegsicd["SEG2"] = df_merge["SEG"].values
        wsegsicd["ALPHA"] = df_merge["STRENGTH"].values
        wsegsicd["SF"] = df_merge["SCALINGFACTOR"].values
        wsegsicd["RHO"] = df_merge["RHOCAL_ICD"].values
        wsegsicd["VIS"] = df_merge["VISCAL_ICD"].values
        wsegsicd["WCT"] = df_merge["WCUT"].values
        wsegsicd[""] = "/"
    return wsegsicd


def prepare_wsegvalv(well, lateral, df_well, df_device):
    """prepare WSEGVALV dataframe

    Args:
        well (str) : well name
        lateral (int) : lateral number
        df_well (pandas dataframe) : df_well from class CreateWells
        df_device (pandas dataframe) : from function prepare_devicelayer
            for this well and this lateral

    Returns:
        (pandas dataframe) : WSEGVALV
    """
    df_well = df_well[df_well["LATERAL"] == lateral]
    df_well = df_well[(df_well["DEVICETYPE"] == "PERF") | (df_well["NDEVICES"] > 0)]
    if df_well.shape[0] == 0:
        return pd.DataFrame()
    df_merge = pd.merge_asof(
        left=df_device,
        right=df_well,
        left_on=["MD"],
        right_on=["TUB_MD"],
        direction="nearest",
    )
    df_merge = df_merge[df_merge["DEVICETYPE"] == "VALVE"]
    wsegvalv = pd.DataFrame()
    if df_merge.shape[0] > 0:
        wsegvalv["WELL"] = [well] * df_merge.shape[0]
        wsegvalv["SEG"] = df_merge["SEG"].values
        # the Cv is already corrected by the scaling factor
        wsegvalv["CV"] = df_merge["CV"].values
        wsegvalv["AC"] = df_merge["AC"].values
        wsegvalv["L"] = df_merge["L"].values
        wsegvalv[""] = "/"
    return wsegvalv


def prepare_wsegdar(well, lateral, df_well, df_device):
    """prepare  dataframe for DAR

    Args:
        well (str) : well name
        lateral (int) : lateral number
        df_well (pandas dataframe) : df_well from class CreateWells
        df_device (pandas dataframe) : from function prepare_devicelayer
            for this well and this lateral

    Returns:
        (pandas dataframe) : dataframe for DAR
    """
    df_well = df_well[df_well["LATERAL"] == lateral]
    df_well = df_well[(df_well["DEVICETYPE"] == "PERF") | (df_well["NDEVICES"] > 0)]
    if df_well.shape[0] == 0:
        return pd.DataFrame()
    df_merge = pd.merge_asof(
        left=df_device,
        right=df_well,
        left_on=["MD"],
        right_on=["TUB_MD"],
        direction="nearest",
    )
    df_merge = df_merge[df_merge["DEVICETYPE"] == "DAR"]
    wsegdar = pd.DataFrame()
    if df_merge.shape[0] > 0:
        wsegdar["WELL"] = [well] * df_merge.shape[0]
        wsegdar["SEG"] = df_merge["SEG"].values
        # the Cv is already corrected by the scaling factor
        wsegdar["CV_DAR"] = df_merge["CV_DAR"].values
        wsegdar["AC_TOT_LOWWCT_LOWGVF"] = df_merge["AC_TOT_LOWWCT_LOWGVF"].values
        wsegdar["AC_TOT_LOWWCT_HIGHGVF"] = df_merge["AC_TOT_LOWWCT_HIGHGVF"].values
        wsegdar["AC_TOT_HIGHWCT_LOWGVF"] = df_merge["AC_TOT_HIGHWCT_LOWGVF"].values
        wsegdar["AC_TOT_HIGHWCT_HIGHGVF"] = df_merge["AC_TOT_HIGHWCT_HIGHGVF"].values
        wsegdar["WCT_DAR"] = df_merge["WCT_DAR"].values
        wsegdar["GVF_DAR"] = df_merge["GVF_DAR"].values
        wsegdar[""] = "/"
    return wsegdar


def prepare_wsegaicv(well, lateral, df_well, df_device):
    """prepare  dataframe for AICV

    Args:
        well (str) : well name
        lateral (int) : lateral number
        df_well (pandas dataframe) : df_well from class CreateWells
        df_device (pandas dataframe) : from function prepare_devicelayer
            for this well and this lateral

    Returns:
        (pandas dataframe) : dataframe for AICV
    """
    df_well = df_well[df_well["LATERAL"] == lateral]
    df_well = df_well[(df_well["DEVICETYPE"] == "PERF") | (df_well["NDEVICES"] > 0)]
    if df_well.shape[0] == 0:
        return pd.DataFrame()
    df_merge = pd.merge_asof(
        left=df_device,
        right=df_well,
        left_on=["MD"],
        right_on=["TUB_MD"],
        direction="nearest",
    )
    df_merge = df_merge[df_merge["DEVICETYPE"] == "AICV"]
    wsegaicv = pd.DataFrame()
    if df_merge.shape[0] > 0:
        wsegaicv["WELL"] = [well] * df_merge.shape[0]
        wsegaicv["SEG"] = df_merge["SEG"].values
        wsegaicv["SEG2"] = df_merge["SEG"].values
        wsegaicv["ALPHA_MAIN"] = df_merge["ALPHA_MAIN"].values
        wsegaicv["SF"] = df_merge["SCALINGFACTOR"].values
        wsegaicv["RHO"] = df_merge["RHOCAL_AICV"].values
        wsegaicv["VIS"] = df_merge["VISCAL_AICV"].values
        wsegaicv["DEF"] = ["5*"] * df_merge.shape[0]
        wsegaicv["X_MAIN"] = df_merge["X_MAIN"].values
        wsegaicv["Y_MAIN"] = df_merge["Y_MAIN"].values
        wsegaicv["FLAG"] = ["OPEN"] * df_merge.shape[0]
        wsegaicv["A_MAIN"] = df_merge["A_MAIN"].values
        wsegaicv["B_MAIN"] = df_merge["B_MAIN"].values
        wsegaicv["C_MAIN"] = df_merge["C_MAIN"].values
        wsegaicv["D_MAIN"] = df_merge["D_MAIN"].values
        wsegaicv["E_MAIN"] = df_merge["E_MAIN"].values
        wsegaicv["F_MAIN"] = df_merge["F_MAIN"].values
        wsegaicv["ALPHA_PILOT"] = df_merge["ALPHA_PILOT"].values
        wsegaicv["X_PILOT"] = df_merge["X_PILOT"].values
        wsegaicv["Y_PILOT"] = df_merge["Y_PILOT"].values
        wsegaicv["A_PILOT"] = df_merge["A_PILOT"].values
        wsegaicv["B_PILOT"] = df_merge["B_PILOT"].values
        wsegaicv["C_PILOT"] = df_merge["C_PILOT"].values
        wsegaicv["D_PILOT"] = df_merge["D_PILOT"].values
        wsegaicv["E_PILOT"] = df_merge["E_PILOT"].values
        wsegaicv["F_PILOT"] = df_merge["F_PILOT"].values
        wsegaicv["WCT_AICV"] = df_merge["WCT_AICV"].values
        wsegaicv["GVF_AICV"] = df_merge["GVF_AICV"].values
        wsegaicv[""] = "/"
    return wsegaicv


def print_wsegdar(df_wsegdar, well_number):
    """printing for DAR devices

    Args:
        df_wsegdar (pandas dataframe) : output from function
            prepare_wsegdar
        well_number (int) : well number

    Returns:
        (str) : to be put in the output file
    """
    header = []
    header.append(["WELL", "SEG", "CV_DAR", "AC_TOT_LOWWCT_LOWGVF", ""])
    header.append(["WELL", "SEG", "CV_DAR", "AC_TOT_LOWWCT_HIGHGVF", ""])
    header.append(["WELL", "SEG", "CV_DAR", "AC_TOT_HIGHWCT_LOWGVF", ""])
    header.append(["WELL", "SEG", "CV_DAR", "AC_TOT_HIGHWCT_HIGHGVF", ""])
    sign_water = ["<=", "<=", ">", ">"]
    sign_gas = ["<=", ">", "<=", ">"]
    action = ""
    for i in range(df_wsegdar.shape[0]):
        segment_number = df_wsegdar["SEG"].iloc[i]
        well_name = df_wsegdar["WELL"].iloc[i]
        wct = df_wsegdar["WCT_DAR"].iloc[i]
        gvf = df_wsegdar["GVF_DAR"].iloc[i]
        # LOWWCT_LOWGVF
        for iaction in range(4):
            act_number = iaction + 1
            act_name = (
                "D"
                + str(well_number)
                + "S"
                + str(segment_number)
                + "A"
                + str(act_number)
            )
            if len(act_name) > 8:
                err.wb_error("Too many wells and/or too many segments with DAR")
            action = action + "ACTIONX\n"
            action = action + act_name + " " + str(1000000) + " " + "/\n"
            action = (
                action
                + "SUWCT"
                + " "
                + well_name
                + " "
                + str(segment_number)
                + " "
                + sign_water[iaction]
                + " "
                + str(wct)
                + " AND /\n"
            )
            action = (
                action
                + "SUGVF"
                + " "
                + well_name
                + " "
                + str(segment_number)
                + " "
                + sign_gas[iaction]
                + " "
                + str(gvf)
                + " /\n/\n"
            )

            print_df = df_wsegdar[df_wsegdar["SEG"] == segment_number]
            print_df = print_df[header[iaction]]
            print_df = "WSEGVALV\n" + dataframe_tostring(print_df, True)
            action = action + print_df + "\n/\nENDACTIO\n\n"
    return action


def print_wsegaicv(df_wsegaicv, well_number):
    """printing for AICV devices

    Args:
        df_wsegaicv (pandas dataframe) : output from function
            prepare_wsegaicv
        well_number (int) : well number

    Returns:
        (str) : to be put in the output file
    """
    header = []
    header.append(
        [
            "WELL",
            "SEG",
            "SEG2",
            "ALPHA_MAIN",
            "SF",
            "RHO",
            "VIS",
            "DEF",
            "X_MAIN",
            "Y_MAIN",
            "FLAG",
            "A_MAIN",
            "B_MAIN",
            "C_MAIN",
            "D_MAIN",
            "E_MAIN",
            "F_MAIN",
            "",
        ]
    )
    header.append(
        [
            "WELL",
            "SEG",
            "SEG2",
            "ALPHA_PILOT",
            "SF",
            "RHO",
            "VIS",
            "DEF",
            "X_PILOT",
            "Y_PILOT",
            "FLAG",
            "A_PILOT",
            "B_PILOT",
            "C_PILOT",
            "D_PILOT",
            "E_PILOT",
            "F_PILOT",
            "",
        ]
    )
    new_column = [
        "WELL",
        "SEG",
        "SEG2",
        "ALPHA",
        "SF",
        "RHO",
        "VIS",
        "DEF",
        "X",
        "Y",
        "FLAG",
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "",
    ]
    sign_water = ["<", ">="]
    sign_gas = ["<", ">="]
    operator = ["AND", "OR"]
    action = ""
    for i in range(df_wsegaicv.shape[0]):
        segment_number = df_wsegaicv["SEG"].iloc[i]
        well_name = df_wsegaicv["WELL"].iloc[i]
        wct = df_wsegaicv["WCT_AICV"].iloc[i]
        gvf = df_wsegaicv["GVF_AICV"].iloc[i]
        # LOWWCT_LOWGVF
        for iaction in range(2):
            act_number = iaction + 1
            act_name = (
                "V"
                + str(well_number)
                + "S"
                + str(segment_number)
                + "A"
                + str(act_number)
            )
            if len(act_name) > 8:
                err.wb_error("Too many wells and/or too many segments with AICV")
            action = action + "ACTIONX\n"
            action = action + act_name + " " + str(1000000) + " " + "/\n"
            action = (
                action
                + "SUWCT"
                + " "
                + well_name
                + " "
                + str(segment_number)
                + " "
                + sign_water[iaction]
                + " "
                + str(wct)
                + " "
                + operator[iaction]
                + " /\n"
            )
            action = (
                action
                + "SUGVF"
                + " "
                + well_name
                + " "
                + str(segment_number)
                + " "
                + sign_gas[iaction]
                + " "
                + str(gvf)
                + " /\n/\n"
            )
            print_df = df_wsegaicv[df_wsegaicv["SEG"] == segment_number]
            print_df = print_df[header[iaction]]
            print_df.columns = new_column
            print_df = "WSEGAICD\n" + dataframe_tostring(print_df, True)
            action = action + print_df + "\n/\nENDACTIO\n\n"
    return action
