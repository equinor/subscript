# -*- coding: utf-8 -*-
"""
Created on Tue Aug 13 14:43:02 2019

@author: iari
"""

from io import StringIO
import re
from copy import deepcopy
import numpy as np
import pandas as pd
import wellbuilder.wellbuilder_error as err


class ContentCollection(list):
    """
    A subclass of list that can accept additional attributes.
    Should be able to be used just like a regular list.
    """

    def __new__(self, *args, **kwargs):
        return super(ContentCollection, self).__new__(self, args, kwargs)

    def __init__(self, *args, **kwargs):
        if len(args) == 1 and hasattr(args[0], "__iter__"):
            list.__init__(self, args[0])
        else:
            list.__init__(self, args)
        self.__dict__.update(kwargs)

    def __call__(self, **kwargs):
        self.__dict__.update(kwargs)
        return self


def file_makeup(the_file, comment_char="--"):
    """This procedures remove comments from a text file

    Args:
        the_file (str) : path string
        comment_char (str) : character which initiates comments

    Returns:
        list : list of strings (clean without comments)
    """
    if isinstance(the_file, str):
        file_content = open(the_file, "r").readlines()
    else:
        file_content = the_file.readlines()
    clean_file = []
    for content in file_content:
        # Replace tab with white spaces
        content = content.replace("\t", " ")
        # Remove trailing white spaces
        content = content.lstrip(" ")
        content = content.rstrip(" ")
        # Remove blank lines
        content = content.replace("\n", "")
        # Remove unnecessary white spaces
        content = " ".join(content.split())
        # Split the content by the comment characters
        split_content = content.split(comment_char)
        content = split_content[0]
        # remove comments after / but keep /
        if "/" in content:
            split_content = content.split("/")
            content = split_content[0] + "/"
        # Take the content before the comment
        content = content.lstrip(" ")
        content = content.rstrip(" ")
        # Take the content if it is not empty
        if content not in ["", "\n"]:
            clean_file.append(content)
    return clean_file


def locate_keyword(content, keyword, end_char=""):
    """This function finds the start and end of a keyword

    The start of the keyword is the keyword itself
    The end of the keyword is end_char if specified

    Args:
        content (list) : list of strings
        keyword (str) : keyword name
        end_char (str) : string which ends the keyword

    Returns:
        start_index (np.ndarray) : array which located the keyword
        end_index (np.ndarray) : array which locates the end of the keyword
    """
    ncontent = len(content)
    start_index = np.where(np.asarray(content) == keyword)[0]
    if start_index.shape[0] == 0:
        # the keyword is not found
        return np.asarray([-1]), np.asarray([-1])
    else:
        end_index = []
        for istart in start_index:
            if end_char != "":
                idx = istart + 1
                for idx in range(istart + 1, ncontent):
                    if content[idx] == end_char:
                        break
                if (idx == ncontent - 1) and content[idx] != end_char:
                    # error if until the last line the end char is not found
                    err.wb_error("Keyword " + keyword + " has no end record")
            else:
                # if there is no end character is specified
                # then the end of a record is the next keyword or end of line
                for idx in range(istart + 1, ncontent):
                    first_char = content[idx][0]
                    if first_char.isalpha():
                        # end is before the new keyword
                        idx = idx - 1
                        break
            end_index.append(idx)
    # return all in a numpy array format
    return start_index, np.asarray(end_index)


def take_firstrecord(start_index, end_index):
    """This function takes the first record of a list

    Args:
        start_index (list/array)
        end_index (list/array)

    Returns:
        tupple float

    """
    return (start_index[0], end_index[0])


def string_todf(string):
    """This function converts string into pandas dataframe

    Args:
        string (str) : string where columns are separated by " "

    Returns:
        pandas dataframe without column name
    """
    return pd.read_csv(StringIO(string), sep=" ", index_col=False)


def unpack_records(record):
    """This function unpacks the keyword content

    e.g. 3* --> 1* 1* 1*
    
    Args:
        record (list) : list of string

    Returns:
        record (list) : updated list of string
    """
    record = deepcopy(record)
    nrecord = len(record)
    idx = -1
    while idx < nrecord - 1:
        # Loop and find if default records are found
        idx = idx + 1
        if "*" in str(record[idx]):
            # default is found and get the number before the star *
            ndefaults = int(re.search(r"\d+", record[idx]).group())
            record[idx] = "1*"
            idef = 0
            while idef < ndefaults - 1:
                record.insert(idx, "1*")
                idef = idef + 1
            nrecord = len(record)
    return record


def complete_records(record, keyword):
    """This function completes the record

    Args:
        record (list) : list of strings
        keyword (str) : keyword name

    Returns:
        record (list) : list of updated string
    """
    dict_ncolumns = {
        "WELSPECS": 17,
        "COMPDAT": 14,
        "WELSEGS_H": 12,
        "WELSEGS": 15,
        "COMPSEGS": 11,
    }
    max_column = dict_ncolumns[keyword]
    ncolumn = len(record)
    if ncolumn < max_column:
        extension = ["1*"] * (max_column - ncolumn)
        record.extend(extension)
    return record


def read_schedulekeywords(content, list_keywords):
    """This function reads schedule keywords

    Such as WELSPECS, COMPDAT, WELSEGS, COMPSEGS, or all keywords in table format

    Args:
        content (list) : list of strings
        list_keyword (list) : list of keywords to be found

    Outputs:
        df_collection (pandas dataframe) : object collection
        remaining_content (list) : list of strings of not listed keywords
    """
    content = deepcopy(content)
    used_index = np.asarray([-1])
    collections = []
    # get the contents correspond to the list_keywords
    for keyword in list_keywords:
        start_index, end_index = locate_keyword(content, keyword, "/")
        if start_index[0] == end_index[0]:
            err.wb_error("Keyword " + keyword + " is not found")
        for idx, start in enumerate(start_index):
            end = end_index[idx]
            used_index = np.append(used_index, np.arange(start, end + 1))
            keyword_content = []
            for irec in range(start + 1, end):
                record = content[irec]
                # remove / sign at the end
                record = list(filter(None, record.split("/")))[0]
                # split each column
                record = list(filter(None, record.split(" ")))
                # unpack records
                record = unpack_records(record)
                # complete records
                if keyword == "WELSEGS" and irec == start + 1:
                    record = complete_records(record, "WELSEGS_H")
                else:
                    record = complete_records(record, keyword)
                # combine each line
                keyword_content.append(record)
            collection = ContentCollection(keyword_content)
            collection.name = keyword
            if keyword in ["WELSEGS", "COMPSEGS"]:
                # remove string characters
                collection.well = remove_stringcharacters(keyword_content[0][0])
            collections.append(collection)
    # get anything that is not listed in the keywords
    # ignore the first record -1
    used_index = used_index[1:]
    mask = np.full(len(content), True, dtype=bool)
    mask[used_index] = False
    return collections, np.asarray(content)[mask]


def get_welsegs_table(collections):
    """This function returns dataframe table of WELSEGS

    Args:
        collection (class) : ContentCollection class

    Returns:
        first_table (pandas dataframe) : first record WELSEGS
        second_table (pandas dataframe) : second record WELSEGS
    """
    header_columns = [
        "WELL",
        "SEGMENTTVD",
        "SEGMENTMD",
        "WBVOLUME",
        "INFOTYPE",
        "PDROPCOMP",
        "MPMODEL",
        "ITEM8",
        "ITEM9",
        "ITEM10",
        "ITEM11",
        "ITEM12",
    ]
    content_columns = [
        "WELL",
        "TUBINGSEGMENT",
        "TUBINGSEGMENT2",
        "TUBINGBRANCH",
        "TUBINGOUTLET",
        "TUBINGMD",
        "TUBINGTVD",
        "TUBINGID",
        "TUBINGROUGHNESS",
        "CROSS",
        "VSEG",
        "ITEM11",
        "ITEM12",
        "ITEM13",
        "ITEM14",
        "ITEM15",
    ]
    irec = -1
    for collection in collections:
        if collection.name == "WELSEGS":
            irec = irec + 1
            first_collection = np.asarray(collection[:1])
            second_collection = np.asarray(collection[1:])
            # add additional well column on the second collection
            well_column = [collection.well] * second_collection.shape[0]
            second_collection = np.column_stack((well_column, second_collection))
            if irec == 0:
                first_table = np.asarray(first_collection)
                second_table = np.asarray(second_collection)
            else:
                first_table = np.row_stack((first_table, first_collection))
                second_table = np.row_stack((second_table, second_collection))
    first_table = pd.DataFrame(first_table, columns=header_columns)
    second_table = pd.DataFrame(second_table, columns=content_columns)
    # replace string component " or ' in the columns
    first_table = remove_stringcharacters(first_table)
    second_table = remove_stringcharacters(second_table)
    return (first_table, second_table)


def get_welspecs_table(collections):
    """This function returns dataframe table of WELSPECS

    Args:
        collection (class) : ContentCollection class

    Output:
        pandas dataframe : WELSPECS table
    """
    columns = [
        "WELL",
        "GROUP",
        "I",
        "J",
        "BHP_DEPTH",
        "PHASE",
        "DR",
        "FLAG",
        "SHUT",
        "CROSS",
        "PRESSURETABLE",
        "DENSCAL",
        "REGION",
        "ITEM14",
        "ITEM15",
        "ITEM16",
        "ITEM17",
    ]
    irec = -1
    for collection in collections:
        if collection.name == "WELSPECS":
            irec = irec + 1
            the_collection = np.asarray(collection)
            if irec == 0:
                temp_table = np.copy(the_collection)
            else:
                temp_table = np.row_stack((temp_table, the_collection))
    temp_table = pd.DataFrame(temp_table, columns=columns)
    # replace string component " or ' in the columns
    temp_table = remove_stringcharacters(temp_table)
    return temp_table


def get_compdat_table(collections):
    """This function returns dataframe table of COMPDAT

    Args:
        collection (class) : ContentCollection class

    Returns:
        pandas dataframe : COMPDAT table
    """
    columns = [
        "WELL",
        "I",
        "J",
        "K",
        "K2",
        "STATUS",
        "SATNUM",
        "CF",
        "DIAM",
        "KH",
        "SKIN",
        "DFACT",
        "COMPDAT_DIRECTION",
        "RO",
    ]
    irec = -1
    for collection in collections:
        if collection.name == "COMPDAT":
            irec = irec + 1
            the_collection = np.asarray(collection)
            if irec == 0:
                temp_table = np.copy(the_collection)
            else:
                temp_table = np.row_stack((temp_table, the_collection))
    temp_table = pd.DataFrame(temp_table, columns=columns)
    # replace string component " or ' in the columns
    temp_table = remove_stringcharacters(temp_table)
    return temp_table


def get_compsegs_table(collections):
    """This function returns dataframe table of COMPSEGS

    Args:
        collection (class) : ContentCollection class

    Output:
        pandas dataframe : COMPSEGS table
    """
    irec = -1
    columns = [
        "WELL",
        "I",
        "J",
        "K",
        "BRANCH",
        "STARTMD",
        "ENDMD",
        "COMPSEGS_DIRECTION",
        "ENDGRID",
        "PERFDEPTH",
        "THERM",
        "SEGMENT",
    ]
    for collection in collections:
        if collection.name == "COMPSEGS":
            irec = irec + 1
            the_collection = np.asarray(collection[1:])
            # add additional well column
            well_column = [collection.well] * the_collection.shape[0]
            the_collection = np.column_stack((well_column, the_collection))
            if irec == 0:
                temp_table = np.copy(the_collection)
            else:
                temp_table = np.row_stack((temp_table, the_collection))
    temp_table = pd.DataFrame(temp_table, columns=columns)
    # replace string component " or ' in the columns
    temp_table = remove_stringcharacters(temp_table)
    return temp_table


def read_type1pvt(icontent, keyword):
    """This function reads content in PVTO and PVTG keyword

    Args:
        icontent (list) : list of strings
        keyword (str) : keyword PVT e.g. PVTO, PVTG
    Output:
        np.ndarray
    """
    # remove / from the content
    icontent = np.char.replace(icontent, "/", "")
    pvt = []
    for iline, line in enumerate(icontent):
        # split by space
        line = line.split(" ")
        # remove blank items
        line = list(filter(None, line))
        if len(line) == 4:
            pvt.append(line)
        elif len(line) == 3:
            # complete the item
            line.insert(0, pvt[iline - 1][0])
            pvt.append(line)
        else:
            err.wb_error("Fail in reading " + keyword)
    return np.asarray(pvt)


def read_type2pvt(icontent, keyword):
    """This function reads content PVDO, PVDG, PVTW, DENSITY

    Args:
        icontent (list) : list of strings
        keyword (str) : PVT keywords e.g. PVDO, PVDG, PVTW, DENSITY

    Output:
        np.ndarray
    """
    ncolumn = {"PVDG": 3, "PVDO": 3, "PVTW": 5, "DENSITY": 3}
    # remove / from the content
    icontent = np.char.replace(icontent, "/", "")
    pvt = []
    for line in icontent:
        # split by space
        line = line.split(" ")
        # remove blank items
        line = list(filter(None, line))
        if len(line) == ncolumn[keyword]:
            pvt.append(line)
        else:
            err.wb_error("Fail in reading " + keyword)
    return np.asarray(pvt)


def read_pvt_family(content, keyword):
    """This function reads PVTO, PVTG, PCDO, PVDG, PVTW and DENSITY

    Args:
        content (list) : list of strings
        keyword (str) : PVT keywords

    Returns:
        pandas dataframe
    """
    # column names of the pvt table
    column_dict = {
        "PVTO": ["GOR", "PRESSURE", "BO", "VISCOSITY"],
        "PVTG": ["PRESSURE", "OGR", "BG", "VISCOSITY"],
        "PVDO": ["PRESSURE", "BO", "VISCOSITY"],
        "PVDG": ["PRESSURE", "BG", "VISCOSITY"],
        "PVTW": ["PRESSURE", "BW", "CW", "VW", "dVW"],
        "DENSITY": ["OIL_DENSITY", "WATER_DENSITY", "GAS_DENSITY"],
    }
    column = column_dict[keyword]
    # df header includes the PVT table number
    column.insert(0, "PVTTABLE")
    # get the start and end of the keyword
    content = deepcopy(content)
    start_index, end_index = locate_keyword(content, keyword)
    # take the first occurence
    start_index, end_index = start_index[0], end_index[0]
    if start_index == end_index:
        err.wb_error(keyword + " is not found")
        return pd.DataFrame()
    else:
        content = content[start_index + 1 : end_index + 1]
        # find the index of each PVT region
        if keyword in ["PVTW", "DENSITY"]:
            # this is a rather simple reading
            df_pvt = read_type2pvt(content, keyword)
            # add PVT number column
            df_pvt = np.column_stack((np.arange(0, len(df_pvt)) + 1, df_pvt))
        else:
            last_index = np.where(np.asarray(content) == "/")[0]
            first_index = np.insert(last_index[:-1], 0, -1) + 1
            for idx, ifirst in enumerate(first_index):
                ilast = last_index[idx]
                icontent = content[ifirst:ilast]
                if keyword in ["PVTO", "PVTG"]:
                    pvt = read_type1pvt(icontent, keyword)
                elif keyword in ["PVDO", "PVDG"]:
                    pvt = read_type2pvt(icontent, keyword)
                # add PVT table number
                pvt = np.column_stack(([idx + 1] * len(pvt), pvt))
                # combine all
                if idx == 0:
                    df_pvt = np.copy(pvt)
                else:
                    df_pvt = np.row_stack((df_pvt, pvt))
    # create dataframe
    df_pvt = pd.DataFrame(df_pvt, columns=column)
    # set the data type
    df_pvt[column[:1]] = df_pvt[column[:1]].astype(np.int64)
    df_pvt[column[1:]] = df_pvt[column[1:]].astype(np.float64)
    return df_pvt


def remove_stringcharacters(df, columns=[]):
    """This function removes string characters " and '

    Args:
        df (pandas dataframe) : dataframe or string
        columns (list) : list of column name to be checked

    Returns:
        pandas dataframe
    """
    if isinstance(df, str):
        df = df.replace("'", "")
        df = df.replace('"', "")
    elif isinstance(df, pd.DataFrame):
        if len(columns) == 0:
            for icol in range(df.shape[1]):
                try:
                    df.iloc[:, icol] = df.iloc[:, icol].str.replace('"', "")
                    df.iloc[:, icol] = df.iloc[:, icol].str.replace("'", "")
                except:
                    pass
        else:
            for column in columns:
                try:
                    df[column] = df[column].str.replace('"', "")
                    df[column] = df[column].str.replace("'", "")
                except:
                    pass
    return df
