# -*- coding: utf-8 -*-
"""
Created on Thu Aug 15 10:33:16 2019

@author: iari
"""
import numpy as np
import wellbuilder.wellbuilder_error as err
import wellbuilder.file_reader as fr


def setdefault_packersection(df_temp):
    """Set default value for packer section

    This procedures set the default values of the
    completion_table in read_casefile class if the annulus is PA (packer)

    Args:
        df_temp (pandas dataframe) : COMPLETION table

    Returns:
        pandas dataframe : updated COMPLETION
    """
    # Set default values for packer sections
    df_temp["INNER_ID"] = np.where(df_temp["ANNULUS"] == "PA", 0.0, df_temp["INNER_ID"])
    df_temp["OUTER_ID"] = np.where(df_temp["ANNULUS"] == "PA", 0.0, df_temp["OUTER_ID"])
    df_temp["ROUGHNESS"] = np.where(
        df_temp["ANNULUS"] == "PA", 0.0, df_temp["ROUGHNESS"]
    )
    df_temp["NVALVEPERJOINT"] = np.where(
        df_temp["ANNULUS"] == "PA", 0.0, df_temp["NVALVEPERJOINT"]
    )
    df_temp["DEVICETYPE"] = np.where(
        df_temp["ANNULUS"] == "PA", "PERF", df_temp["DEVICETYPE"]
    )
    df_temp["DEVICENUMBER"] = np.where(
        df_temp["ANNULUS"] == "PA", 0, df_temp["DEVICENUMBER"]
    )
    df_temp["BLANKPORTION"] = np.where(
        df_temp["ANNULUS"] == "PA", 0.0, df_temp["BLANKPORTION"]
    )
    return df_temp


def setdefault_perfsection(df_temp):
    """This procedures set the default value for PERF section

    Args:
        df_temp (pandas dataframe) : COMPLETION table

    Returns:
        pandas dataframe : updated COMPLETION
    """
    # set default value of the PERF section
    df_temp["NVALVEPERJOINT"] = np.where(
        df_temp["DEVICETYPE"] == "PERF", 0.0, df_temp["NVALVEPERJOINT"]
    )
    df_temp["DEVICENUMBER"] = np.where(
        df_temp["DEVICETYPE"] == "PERF", 0, df_temp["DEVICENUMBER"]
    )
    df_temp["BLANKPORTION"] = np.where(
        df_temp["DEVICETYPE"] == "PERF", 0.0, df_temp["BLANKPORTION"]
    )
    return df_temp


def setdefault_blanksection(df_temp):
    """This procedures set the default value of BLANK section

    Args:
        df_temp (pandas dataframe) : COMPLETION table

    Returns:
        pandas dataframe : updated COMPLETION
    """
    # set default value of the PERF section
    df_temp["NVALVEPERJOINT"] = np.where(
        df_temp["DEVICETYPE"] == "BLANK", 0.0, df_temp["NVALVEPERJOINT"]
    )
    df_temp["DEVICENUMBER"] = np.where(
        df_temp["DEVICETYPE"] == "BLANK", 0, df_temp["DEVICENUMBER"]
    )
    df_temp["BLANKPORTION"] = np.where(
        df_temp["DEVICETYPE"] == "BLANK", 1.0, df_temp["BLANKPORTION"]
    )
    return df_temp


def checkdefault_nonpacker(df_temp):
    """Check default values for non packers

    This procedure checks if the user enter default values 1*
    for the annulus contant not packer e.g. OA, GP.
    If found then give errors

    Args:
        df_temp (pandas dataframe) : COMPLETION table

    Raises:
        WellBuilder Error : if 1* is specified in columns

    Returns:
        pandas dataframe : updated COMPLETION
    """
    df_temp = df_temp.copy(True)
    # set default value of roughness
    df_temp["ROUGHNESS"].replace("1*", 1e-5, inplace=True)
    df_nonpa = df_temp[df_temp["ANNULUS"] != "PA"]
    df_columns = df_nonpa.columns.values
    for column in df_columns:
        if "1*" in df_nonpa[column]:
            err.wb_error("No default value 1* is allowed in " + column + " entry.")
    return df_temp


def setformat_completion(df_temp):
    """Set the column data format

    Args:
        df_temp (pandas dataframe) : COMPLETION table

    Returns:
        pandas dataframe : updated COMPLETION
    """
    df_temp["WELL"] = df_temp["WELL"].astype(np.str)
    df_temp["BRANCH"] = df_temp["BRANCH"].astype(np.int64)
    df_temp["STARTMD"] = df_temp["STARTMD"].astype(np.float64)
    df_temp["ENDMD"] = df_temp["ENDMD"].astype(np.float64)
    df_temp["INNER_ID"] = df_temp["INNER_ID"].astype(np.float64)
    df_temp["OUTER_ID"] = df_temp["OUTER_ID"].astype(np.float64)
    df_temp["ROUGHNESS"] = df_temp["ROUGHNESS"].astype(np.float64)
    df_temp["ANNULUS"] = df_temp["ANNULUS"].astype(np.str)
    df_temp["NVALVEPERJOINT"] = df_temp["NVALVEPERJOINT"].astype(np.float64)
    df_temp["DEVICETYPE"] = df_temp["DEVICETYPE"].astype(np.str)
    df_temp["DEVICENUMBER"] = df_temp["DEVICENUMBER"].astype(np.int64)
    df_temp["BLANKPORTION"] = df_temp["BLANKPORTION"].astype(np.float64)
    return df_temp


def aligninputs_completion(df_temp):
    """This procedure aligns the user inputs

    Args:
        df_temp (pandas dataframe) : COMPLETION table

    Returns:
        pandas dataframe : updated COMPLETION
    """
    # Fix user inputs
    # 1. Set blank portion to 0.0
    # if the annulus is not filled with gravel pack
    df_temp["BLANKPORTION"] = np.where(
        df_temp["ANNULUS"] == "OA", 0.0, df_temp["BLANKPORTION"]
    )
    # 2. If the entire joint is only blank pipe then
    # there is no device is installed therefore
    # set the number of valve perjoint to 0.0
    df_temp["NVALVEPERJOINT"] = np.where(
        df_temp["BLANKPORTION"] == 1.0, 0.0, df_temp["NVALVEPERJOINT"]
    )
    return df_temp


def assess_completion(df_temp):
    """This procedure assesses the user completion inputs

    Args:
        df_temp (pandas dataframe) : COMPLETION table

    Raises:
        WellBuilder Error : if PA segment has length,
            COMPLETION does not describe the entire production interval,
            Overlapping segment definition.
    """
    list_wells = df_temp["WELL"].unique()
    for well in list_wells:
        df_well = df_temp[df_temp["WELL"] == well]
        list_branches = df_well["BRANCH"].unique()
        for branch in list_branches:
            df_comp = df_well[df_well["BRANCH"] == branch]
            nrow = df_comp.shape[0]
            for i in range(0, nrow):
                if df_comp["ANNULUS"].iloc[i] == "PA" and (
                    df_comp["STARTMD"].iloc[i] != df_comp["ENDMD"].iloc[i]
                ):
                    err.wb_error("Packer segments must not have length")
                if df_comp["ANNULUS"].iloc[i] != "PA" and (
                    df_comp["STARTMD"].iloc[i] == df_comp["ENDMD"].iloc[i]
                ):
                    err.wb_error("Non packer segments must have length")
                if i > 0:
                    if df_comp["STARTMD"].iloc[i] > df_comp["ENDMD"].iloc[i - 1]:
                        err.wb_error(
                            "Incomplete completion description in well "
                            + str(well)
                            + " from depth "
                            + str(df_comp["ENDMD"].iloc[i - 1])
                            + " to depth "
                            + str(df_comp["STARTMD"].iloc[i])
                        )
                    if df_comp["STARTMD"].iloc[i] < df_comp["ENDMD"].iloc[i - 1]:
                        err.wb_error(
                            "Overlapping completion description in well "
                            + str(well)
                            + " from depth "
                            + str(df_comp["ENDMD"].iloc[i - 1])
                            + " to depth "
                            + str(df_comp["STARTMD"].iloc[i])
                        )


def setformat_wsegvalv(df_temp):
    """This procedure formats WSEGVALV table

    Args:
        df_temp (pandas dataframe) : WSEGVALV table

    Returns:
        pandas dataframe : updated WSEGVALV
    """
    # set data type
    df_temp["DEVICENUMBER"] = df_temp["DEVICENUMBER"].astype(np.int64)
    df_temp[["CV", "AC"]] = df_temp[["CV", "AC"]].astype(np.float64)
    # allows column L to have default value 1*
    # thus it is not set to float
    # Create ID device column
    df_temp.insert(0, "DEVICETYPE", ["VALVE"] * df_temp.shape[0])
    return df_temp


def setformat_wsegsicd(df_temp):
    """This procedure formats WSEGSICD table

    Args:
        df_temp (pandas dataframe) : WSEGSICD table

    Returns:
        pandas dataframe : updated WSEGSICD
    """
    # if WCUT is defaulted then set to 0.5
    # the same default value as in Eclipse
    df_temp["WCUT"].replace("1*", 0.5, inplace=True)
    # set data type
    df_temp["DEVICENUMBER"] = df_temp["DEVICENUMBER"].astype(np.int64)
    # left out devicenumber because it has been formatted as integer
    columns = df_temp.columns.values[1:]
    df_temp[columns] = df_temp[columns].astype(np.float64)
    # Create ID device column
    df_temp.insert(0, "DEVICETYPE", ["ICD"] * df_temp.shape[0])
    return df_temp


def setformat_wsegaicd(df_temp):
    """This procedure formats WSEGAICD table

    Args:
        df_temp (pandas dataframe) : WSEGAICD table

    Returns:
        pandas dataframe : updated WSEGAICD
    """
    # Fix table format
    df_temp["DEVICENUMBER"] = df_temp["DEVICENUMBER"].astype(np.int64)
    # left out devicenumber because it has been formatted as integer
    columns = df_temp.columns.values[1:]
    df_temp[columns] = df_temp[columns].astype(np.float64)
    # Create ID device column
    df_temp.insert(0, "DEVICETYPE", ["AICD"] * df_temp.shape[0])
    return df_temp


def calculate_totalac(dfs1, dfs2):
    """This function calculates the total Ac for DAR technology

    Args:
        dfs1 (float) : diameter first valve
        dfs2 (float) : diameter second valve
    
    Returns
        float : new diameter
    """
    return ((dfs1 ** 2 * dfs2 ** 2) / (dfs1 ** 2 + dfs2 ** 2)) ** 0.5


def setformat_wsegdar(df_temp):
    """This procedure formats WSEGDAR table & calculate new diameter

    Args:
        df_temp (pandas dataframe) : WSEGDAR table

    Returns:
        pandas dataframe : updated WSEGDAR
    """
    # Set data type
    df_temp["DEVICENUMBER"] = df_temp["DEVICENUMBER"].astype(np.int64)
    # left out devicenumber because it has been formatted as integer
    columns = df_temp.columns.values[1:]
    df_temp[columns] = df_temp[columns].astype(np.float64)
    # Create ID device column
    df_temp.insert(0, "DEVICETYPE", ["DAR"] * df_temp.shape[0])
    # Calculate total Ac size
    # This is the parameter used when
    # water cut is < cutoff and gvf < cutoff
    df_temp["AC_TOT_LOWWCT_LOWGVF"] = calculate_totalac(
        df_temp["BIG_AC_DAR"], df_temp["BIG_AC_DAR"]
    )
    # This is the parameter used when
    # water cut is < cutoff and gvf > cutoff
    df_temp["AC_TOT_LOWWCT_HIGHGVF"] = calculate_totalac(
        df_temp["BIG_AC_DAR"], df_temp["SMALL_AC_DAR"]
    )
    # This is the parameter used when
    # water cut is > cutoff and gvf < cutoff
    df_temp["AC_TOT_HIGHWCT_LOWGVF"] = calculate_totalac(
        df_temp["SMALLEST_AC_DAR"], df_temp["BIG_AC_DAR"]
    )
    # This is the parameter used when
    # water cut is > cutoff and gvf > cutoff
    df_temp["AC_TOT_HIGHWCT_HIGHGVF"] = calculate_totalac(
        df_temp["SMALLEST_AC_DAR"], df_temp["SMALL_AC_DAR"]
    )
    return df_temp


def setformat_wsegaicv(df_temp):
    """This procedure formats WSEGAICV table

    Args:
        df_temp (pandas dataframe) : WSEGAICV table

    Returns:
        pandas dataframe : updated WSEGAICV
    """
    # Fix table format
    df_temp["DEVICENUMBER"] = df_temp["DEVICENUMBER"].astype(np.int64)
    # left out devicenumber because it has been formatted as integer
    columns = df_temp.columns.values[1:]
    df_temp[columns] = df_temp[columns].astype(np.float64)
    # Create ID device column
    df_temp.insert(0, "DEVICETYPE", ["AICV"] * df_temp.shape[0])
    return df_temp
