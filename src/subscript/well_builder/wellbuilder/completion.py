# -*- coding: utf-8 -*-
"""
Created on Sat Aug 17 09:45:15 2019

@author: iari
"""

import pandas as pd
import numpy as np
import wellbuilder.wellbuilder_error as err


def well_trajectory(df_welsegs1, df_welsegs2):
    """create trajectory dataframe relation between md and tvd

    WELSEGS must be defined as ABS and not INC

    Args:
        df_welsegs1 (pandas dataframe) : first record of WELSEGS
        df_welsegs2 (pandas dataframe) : second record WELSEGS

    Returns:
        (pandas dataframe) : md vs. tvd
    """
    df_mdtvd = pd.DataFrame()
    md_ = df_welsegs2["TUBINGMD"].values
    md_ = np.insert(md_, 0, df_welsegs1["SEGMENTMD"].iloc[0])
    tvd = df_welsegs2["TUBINGTVD"].values
    tvd = np.insert(tvd, 0, df_welsegs1["SEGMENTTVD"].iloc[0])
    df_mdtvd["MD"] = md_
    df_mdtvd["TVD"] = tvd
    # sort based on md
    df_mdtvd.sort_values(by=["MD", "TVD"], inplace=True)
    # reset index after sorting
    df_mdtvd.reset_index(drop=True, inplace=True)
    return df_mdtvd


def define_annuluszone(df_completion):
    """Defining the annulus zone from the COMPLETION

    Arguments:
        df_completion (pandas dataframe): it must contain
            STARTMD, ENDMD and ANNULUS

    Raises:
        error: It is because the dimension is not correct

    Returns:
        (pandas dataframe) : updated COMPLETION with
            additional column ANNULUS_ZONE
    """
    # define annular zone
    start = df_completion["STARTMD"].iloc[0]
    end = df_completion["ENDMD"].iloc[-1]
    gp_loc = df_completion[df_completion["ANNULUS"] == "GP"][
        ["STARTMD", "ENDMD"]
    ].values
    pa_loc = df_completion[df_completion["ANNULUS"] == "PA"][
        ["STARTMD", "ENDMD"]
    ].values
    # update df_completion by removing PA rows
    df_completion = df_completion[df_completion["ANNULUS"] != "PA"].copy()
    # reset index after filter
    df_completion.reset_index(drop=True, inplace=True)
    annulus_content = df_completion["ANNULUS"].values
    df_completion["ANNULUS_ZONE"] = 0
    if "OA" in annulus_content:
        # only if there are open annulus
        boundary = np.concatenate((pa_loc.flatten(), gp_loc.flatten()))
        boundary = np.sort(np.append(np.insert(boundary, 0, start), end))
        boundary = np.unique(boundary)
        start_bound = boundary[:-1]
        end_bound = boundary[1:]
        # get annulus zone
        # initiate with 0
        annulus_zone = np.full(len(start_bound), 0)
        for i, start in enumerate(start_bound):
            end = end_bound[i]
            thisis_gp = np.any((gp_loc[:, 0] == start) & (gp_loc[:, 1] == end))
            if not thisis_gp:
                annulus_zone[i] = max(annulus_zone) + 1
            # else it is 0
        df_annulus = pd.DataFrame()
        df_annulus["STARTMD"] = start_bound
        df_annulus["ENDMD"] = end_bound
        df_annulus["ANNULUS_ZONE"] = annulus_zone
        annulus_zone = np.full(df_completion.shape[0], 0)
        for i in range(df_completion.shape[0]):
            start = df_completion["STARTMD"].iloc[i]
            end = df_completion["ENDMD"].iloc[i]
            idx0, idx1 = completion_index(df_annulus, start, end)
            if idx0 != idx1 or idx0 == -1:
                raise ValueError("Check Define Annulus Zone")
            else:
                annulus_zone[i] = df_annulus["ANNULUS_ZONE"].iloc[idx0]
        df_completion["ANNULUS_ZONE"] = annulus_zone
    df_completion["ANNULUS_ZONE"] = df_completion["ANNULUS_ZONE"].astype(np.int64)
    return df_completion


def create_tubingsegments(
    df_reservoir, df_completion, df_mdtvd, method="cells", segment_length=0.0
):
    """Procedure to create segments on the tubing layer

    Args:
        df_reservoir (pandas dataframe) : must contain STARTMD and ENDMD
        df_completion (pandas dataframe) : must contain ANNULUS, STARTMD,
            ENDMD, ANNULUS_ZONE and no packer content in the completion
        df_mdtvd (pandas dataframe) : must contain MD and TVD

    Keyword Args:
        method (str) : method for segmentation. Default : cells
            cells : create one segment per cell
            user : create segment based on the completion definition
            fix : create segment based on fix interval
        segment_length (float) : only if fix is selected in the method.

    Returns:
        (pandas dataframe) : with column STARTMD, ENDMD, TUB_MD, TUB_TVD
    """
    if method == "cells":
        # in this method we create the tubing layer
        # one cell one segment
        start_md = df_reservoir["STARTMD"].values
        end_md = df_reservoir["ENDMD"].values
    elif method == "user":
        # in this method we create tubing layer
        # based on the definition of COMPLETION keyword
        # in the case file
        # read all segments except PA which has no segment length
        start_md = df_completion["STARTMD"].values
        end_md = df_completion["ENDMD"].values
        # fix the start and end
        start_md[0] = max(df_reservoir["STARTMD"].iloc[0], start_md[0])
        end_md[-1] = min(df_reservoir["ENDMD"].iloc[-1], end_md[-1])
    elif method == "fix":
        # in this method we create tubing layer
        # with fix interval according to the user input
        # in the case file keyword SEGMENTLENGTH
        min_md = min(df_reservoir["STARTMD"].values)
        max_md = max(df_reservoir["ENDMD"].values)
        start_md = np.arange(min_md, max_md, segment_length)
        end_md = start_md + segment_length
        # update the end point of the last segment
        end_md[-1] = min(end_md[-1], max_md)
    # md for tubing segments
    md_ = 0.5 * (start_md + end_md)
    # estimate TVD
    tvd = np.interp(md_, df_mdtvd["MD"].values, df_mdtvd["TVD"].values)
    # create dataframe
    df_tubingsegments = pd.DataFrame()
    df_tubingsegments["STARTMD"] = start_md
    df_tubingsegments["ENDMD"] = end_md
    df_tubingsegments["TUB_MD"] = md_
    df_tubingsegments["TUB_TVD"] = tvd
    return df_tubingsegments


def insert_missingsegments(df_tubingsegments):
    """Create segments for inactive cells

    Sometimes inactive cells have no segments
    and if this is the case we need to create segments for this cell
    We need to do this to get the scaling factor correct.
    Inactive cells are indicated if there are segments which
    starts at MD deeper than the end MD of the previous cells

    Arguments:
        df_tubingsegments (pandas dataframe) : must contain column STARTMD and ENDMD

    Returns:
        (pandas dataframe) : updated dataframe if missing cells are found
    """
    # sort the dataframe based on STARTMD
    df_tubingsegments.sort_values(by=["STARTMD"], inplace=True)
    # add column to indicate original segment
    df_tubingsegments["SEGMENT_DESC"] = ["OriginalSegment"] * df_tubingsegments.shape[0]
    # get endmd
    endmd = df_tubingsegments["ENDMD"].values
    # get startmd and start from segment 2 and add last item to be the last endmd
    startmd = np.append(df_tubingsegments["STARTMD"].values[1:], endmd[-1])
    # find rows which has startmd > endmd
    missing_index = np.argwhere(startmd > endmd).flatten()
    # proceed only if there are missing index
    if missing_index.size > 0:
        # shift one row down because we move it up one row
        missing_index = missing_index + 1
        df_copy = df_tubingsegments.iloc[missing_index, :].copy(deep=True)
        # new startmd is the previous segment end md
        df_copy["STARTMD"] = df_tubingsegments["ENDMD"].values[missing_index - 1]
        df_copy["ENDMD"] = df_tubingsegments["STARTMD"].values[missing_index]
        df_copy["SEGMENT_DESC"] = ["AdditionalSegment"] * df_copy.shape[0]
        # combine the two dataframe
        df_tubingsegments = pd.concat([df_tubingsegments, df_copy])
        df_tubingsegments.sort_values(by=["STARTMD"], inplace=True)
        df_tubingsegments.reset_index(drop=True, inplace=True)
    return df_tubingsegments


def completion_index(df_completion, start, end):
    """This function returns  the index in the completion dataframe of start MD and end MD

    Args:
        df_completion (pandas dataframe) : must contain STARTMD and ENDMD
        start (float) : start measured depth
        end (float) : end measured depth

    Returns:
        (tupple int)
    """
    start_md = df_completion["STARTMD"].values
    end_md = df_completion["ENDMD"].values
    start = np.argwhere((start_md <= start) & (end_md > start)).flatten()
    end = np.argwhere((start_md < end) & (end_md >= end)).flatten()
    if start.size == 0 or end.size == 0:
        # completion index not found then give negative value for both
        return -1, -1
    return (start[0], end[0])


def get_completion(start, end, df_completion, joint_length):
    """Get the information from the COMPLETION

    Args:
        start (float) : start MD of the segment
        end (end) : end MD of the segment
        df_completion (pandas dataframe) : COMPLETION table.
            It must contain column STARTMD, ENDMD, NVALVEPERJOINT
            BLANKPORTION, INNER_ID, OUTER_ID, ROUGHNESS
            DEVICETYPE, DEVICENUMBER and ANNULUS_ZONE
        joint_length (float) : length of a joint

    Returns:
        (dictionary) : a dictionary which contains information as follow:
            1. ndevice : number of device
            2. device_type
            3. device_number
            4. inner_d : inner diameter
            5. outer_d : equivalent outer diameter
            6. roughness
            7. blanklength
            8. annulus_zone
    """
    start_comp = df_completion["STARTMD"].values
    end_comp = df_completion["ENDMD"].values
    idx0, idx1 = completion_index(df_completion, start, end)
    if idx0 == -1 or idx1 == -1:
        err.wb_error("No completion is define from " + str(start) + " to " + str(end))
    else:
        # previous length start with 0
        prev_length = 0.0
        blanklength = 0.0
        ndevice = 0.0
        for icomp in range(idx0, idx1 + 1):
            comp_length = min(end_comp[icomp], end) - max(start_comp[icomp], start)
            # calculate cumulative parameter
            ndevice = (
                ndevice
                + (comp_length / joint_length)
                * df_completion["NVALVEPERJOINT"].iloc[icomp]
            )

            blanklength = (
                blanklength + df_completion["BLANKPORTION"].iloc[icomp] * comp_length
            )
            if comp_length > prev_length:
                # get well geometry
                inner_d = df_completion["INNER_ID"].iloc[icomp]
                outer_d = df_completion["OUTER_ID"].iloc[icomp]
                roughness = df_completion["ROUGHNESS"].iloc[icomp]
                outer_d = (outer_d ** 2 - inner_d ** 2) ** 0.5
                # get device information
                device_type = df_completion["DEVICETYPE"].iloc[icomp]
                device_number = df_completion["DEVICENUMBER"].iloc[icomp]
                # other information
                annulus_zone = df_completion["ANNULUS_ZONE"].iloc[icomp]
                # set prev_length to this segment
                prev_length = comp_length
            information_dict = {
                "ndevice": ndevice,
                "device_type": device_type,
                "device_number": device_number,
                "inner_d": inner_d,
                "outer_d": outer_d,
                "roughness": roughness,
                "blanklength": blanklength,
                "annulus_zone": annulus_zone,
            }
    return information_dict


def complete_thewell(df_tubingsegments, df_completion, joint_length):
    """Complete the well with the user completion

    Arguments:
        df_tubingsegments (pandas dataframe) : output from function
            create_tubingsegments
        df_completion (pandas dataframe) : output from define_annuluszone
        joint_length (float) : length of the joint

    Returns:
        (pandas dataframe) : well dataframe
    """
    nrow = df_tubingsegments.shape[0]
    start = df_tubingsegments["STARTMD"].values
    end = df_tubingsegments["ENDMD"].values
    # get the well geometry
    # e.g. inner and outer diameter
    # initiate completion
    df_well = pd.DataFrame()
    df_well["TUB_MD"] = df_tubingsegments["TUB_MD"].values
    df_well["TUB_TVD"] = df_tubingsegments["TUB_TVD"].values
    df_well["LENGTH"] = end - start
    df_well["SEGMENT_DESC"] = df_tubingsegments["SEGMENT_DESC"].values
    # loop through the cells
    information = {
        "ndevice": [],
        "device_type": [],
        "device_number": [],
        "inner_d": [],
        "outer_d": [],
        "roughness": [],
        "blanklength": [],
        "annulus_zone": [],
    }
    for irow in range(nrow):
        information_dict = get_completion(
            start[irow], end[irow], df_completion, joint_length
        )
        information["ndevice"].append(information_dict["ndevice"])
        information["device_number"].append(information_dict["device_number"])
        information["device_type"].append(information_dict["device_type"])
        information["inner_d"].append(information_dict["inner_d"])
        information["outer_d"].append(information_dict["outer_d"])
        information["roughness"].append(information_dict["roughness"])
        information["blanklength"].append(information_dict["blanklength"])
        information["annulus_zone"].append(information_dict["annulus_zone"])
    df_well["NDEVICES"] = information["ndevice"]
    df_well["DEVICENUMBER"] = information["device_number"]
    df_well["DEVICETYPE"] = information["device_type"]
    df_well["INNER_DIAMETER"] = information["inner_d"]
    df_well["OUTER_DIAMETER"] = information["outer_d"]
    df_well["ROUGHNESS"] = information["roughness"]
    df_well["BLANKLENGTH"] = information["blanklength"]
    df_well["ANNULUS_ZONE"] = information["annulus_zone"]
    df_well["BLANKPORTION"] = df_well["BLANKLENGTH"] / df_well["LENGTH"]
    df_well["SCREENPORTION"] = 1.0 - df_well["BLANKPORTION"]
    # lumping segments
    df_well = lumping_segments(df_well)
    # create scaling factor
    df_well["SCALINGFACTOR"] = np.where(
        df_well["NDEVICES"] > 0.0, -1.0 / df_well["NDEVICES"], 0.0
    )
    return df_well


def lumping_segments(df_well):
    """It lumps additional segments to the original segments

    Only if the additional segments have annulus zone
    Args:
        df_well (pandas dataframe) : must contain ANNULUS_ZONE
            NDEVICES and SEGMENT_DESC

    Returns:
        (pandas dataframe): updated df_well
    """
    ndevices = df_well["NDEVICES"].values
    annulus_zone = df_well["ANNULUS_ZONE"].values
    seg_desc = df_well["SEGMENT_DESC"].values
    nrow = df_well.shape[0]
    for irow in range(nrow):
        if seg_desc[irow] == "AdditionalSegment":
            # only additional segments
            if annulus_zone[irow] > 0:
                # meaning only annular zones
                # compare it to the segment before and after
                been_lumped = False
                if (irow - 1) >= 0 and not been_lumped:
                    # compare it to the segment before
                    if annulus_zone[irow] == annulus_zone[irow - 1]:
                        ndevices[irow - 1] = ndevices[irow - 1] + ndevices[irow]
                        been_lumped = True
                if (irow + 1) < nrow and not been_lumped:
                    # compare it to the segment after
                    if annulus_zone[irow] == annulus_zone[irow + 1]:
                        ndevices[irow + 1] = ndevices[irow + 1] + ndevices[irow]
            # update the ndevice to 0 for this segment
            # because it is lumped to others
            # and it is 0 if it has no annulus zone
            ndevices[irow] = 0.0
    df_well["NDEVICES"] = ndevices
    # from now on it is only original segment
    df_well = df_well[df_well["SEGMENT_DESC"] == "OriginalSegment"].copy()
    # reset index after filter
    df_well.reset_index(drop=True, inplace=True)
    return df_well


def get_device(df_well, df_device, device_type):
    """get device caharacteristics

    Arguments:
        df_well (pandas dataframe) : must contain column
            DEVICETYPE, DEVICENUMBER and SCALINGFACTOR
        df_device (pandas dataframe) : device table
        device_type (str) : device type. AICD, ICD, DAR, VALVE, AICV

    Returns:
        (pandas dataframe) : updated df_well with device characteristics
    """
    on_col = ["DEVICETYPE", "DEVICENUMBER"]
    df_well = pd.merge(df_well, df_device, how="left", left_on=on_col, right_on=on_col)
    if device_type == "VALVE":
        # rescale the Cv
        # because no scaling factor in WSEGVALV eclipse
        df_well["CV"] = -df_well["CV"] / df_well["SCALINGFACTOR"]
    elif device_type == "DAR":
        # rescale the Cv
        # because no scaling factor in WSEGVALV eclipse
        df_well["CV_DAR"] = -df_well["CV_DAR"] / df_well["SCALINGFACTOR"]
    return df_well


def correct_annuluszone(df_well):
    """Correcting annulus zone

    If in that annulus zone there are no connection
    to the tubing then no annulus zone

    Arguments:
        df_temp (pandas dataframe) : must contain ANNULUS_ZONE, NDEVICES
            and DEVICETYPE

    Returns:
        (pandas dataframe) : updated dataframe with updated annulus zone
    """
    zones = df_well["ANNULUS_ZONE"].unique()
    for zone in zones:
        if zone > 0:
            df_zone = df_well[df_well["ANNULUS_ZONE"] == zone]
            df_zone_device = df_zone[
                (df_zone["NDEVICES"].values > 0)
                | (df_zone["DEVICETYPE"].values == "PERF")
            ]
            if df_zone_device.shape[0] == 0:
                df_well["ANNULUS_ZONE"].replace(zone, 0, inplace=True)
    return df_well


def connectcells_tosegments(df_well, df_reservoir):
    """Connect cells to segments

    Args:
        df_well (pandas dataframe) : segment table. Must contain column TUB_MD
        df_reservoir (pandas dataframe) : COMPSEGS table. Must contain column
            STARTMD and ENDMD

    Returns:
        (pandas dataframe) : merge dataframe
    """
    # Calculate mid cell MD
    df_reservoir["MD"] = (df_reservoir["STARTMD"] + df_reservoir["ENDMD"]) * 0.5
    # Merge
    return pd.merge_asof(
        left=df_reservoir,
        right=df_well,
        left_on=["MD"],
        right_on=["TUB_MD"],
        direction="nearest",
    )


def update_connectionfactor(df_reservoir):
    """Update the CF and KH of COMPDAT

    only in the case where there are blank portion
    and CF and KH are explicitly specified

    Args:
        df_reservoir (pandas dataframe) : must contain
            CF, KH and SCREENPORTION

    Returns:
        (pandas dataframe) : dataframe with updated CF and KH
            if needed
    """
    # apply correction to the connection factor
    if "1*" in df_reservoir["CF"].values.tolist():
        if min(df_reservoir["SCREENPORTION"]) < 1.0:
            err.wb_warning(
                "CF values is not adjusted because it is not explicitly specified in COMPDAT"
            )
    else:
        df_reservoir["CF"] = df_reservoir["CF"] * df_reservoir["SCREENPORTION"].values

    # apply correction to the kh
    if "1*" in df_reservoir["KH"].values.tolist():
        if min(df_reservoir["SCREENPORTION"]) < 1.0:
            err.wb_warning(
                "KH values is not adjusted because it is not explicitly specified in COMPDAT"
            )
    else:
        df_reservoir["KH"] = df_reservoir["KH"] * df_reservoir["SCREENPORTION"].values
    return df_reservoir
