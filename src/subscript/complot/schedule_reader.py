import copy
from copy import deepcopy
import re
import numpy as np
import pandas as pd


class KW(list):
    """
    A subclass of list that can accept additional attributes.
    Should be able to be used just like a regular list.

    The problem:
    a = [1, 2, 4, 8]
    a.x = "Hey!" # AttributeError: 'list' object has no attribute 'x'

    The solution:
    a = L(1, 2, 4, 8)
    a.x = "Hey!"
    print a       # [1, 2, 4, 8]
    print a.x     # "Hey!"
    print len(a)  # 4

    You can also do these:
    a = L( 1, 2, 4, 8 , x="Hey!" )                 # [1, 2, 4, 8]
    a = L( 1, 2, 4, 8 )( x="Hey!" )                # [1, 2, 4, 8]
    a = L( [1, 2, 4, 8] , x="Hey!" )               # [1, 2, 4, 8]
    a = L( {1, 2, 4, 8} , x="Hey!" )               # [1, 2, 4, 8]
    a = L( [2 ** b for b in range(4)] , x="Hey!" ) # [1, 2, 4, 8]
    a = L( (2 ** b for b in range(4)) , x="Hey!" ) # [1, 2, 4, 8]
    a = L( 2 ** b for b in range(4) )( x="Hey!" )  # [1, 2, 4, 8]
    a = L( 2 )                                     # [2]
    """

    def __new__(self, *args, **kwargs):
        return super(KW, self).__new__(self, args, kwargs)

    def __init__(self, *args, **kwargs):
        if len(args) == 1 and hasattr(args[0], "__iter__"):
            list.__init__(self, args[0])
        else:
            list.__init__(self, args)
        self.__dict__.update(kwargs)

    def __call__(self, **kwargs):
        self.__dict__.update(kwargs)
        return self


class PandaCollection:
    def __init__(self, panda):
        self.content = panda.copy(deep=True)

    def __call__(self, **kwargs):
        self.__dict__.update(kwargs)
        return self


def strip_comments(code):
    code = str(code)
    code = code.split("--", 1)
    return code[0]


def clean_to_list(text: str):
    my_line = strip_comments(text)
    my_line = my_line.replace("\t", " ")
    my_line = my_line.replace("\n", " ")
    my_line = my_line.split("/")[0]
    my_list = my_line.split(" ")
    my_list = list(filter(None, my_list))
    return my_list


def clean_to_list2(text: str):
    my_line = strip_comments(text)
    my_line = my_line.replace("\t", " ")
    my_line = my_line.replace("\n", " ")
    my_list = my_line.split(" ")
    my_list = list(filter(None, my_list))
    return my_list


def expand_default_column(xin):
    x = copy.deepcopy(xin)
    a = len(x)
    i = -1
    while i < a - 1:
        i = i + 1
        if "*" in str(x[i]):
            df = int(re.search(r"\d+", x[i]).group())
            x[i] = "1*"
            for j in range(df - 1):
                x.insert(i, "1*")
            a = len(x)
    return x


def read_schedule_keywords(well_file, keyword_list):
    """"""
    my_data = deepcopy(well_file)
    n_line = len(my_data)
    i = -1
    all_kw = []
    while i < n_line - 1:
        i = i + 1
        my_list = clean_to_list(my_data[i])
        if len(my_list) > 0:
            keyword = my_list[0]
            if keyword in keyword_list:
                kw_idx = i
                keyword = str(my_list[0])
                content = []
                while i < n_line:
                    i = i + 1
                    mylist2 = clean_to_list2(my_data[i])
                    if len(mylist2) > 0:
                        if mylist2[0] == "/":
                            break
                        else:
                            my_data[i] = my_data[i].replace("'", "")
                            my_data[i] = my_data[i].replace('"', "")
                            my_list = clean_to_list(my_data[i])
                            if len(my_list) > 0:
                                my_list = expand_default_column(my_list)
                                if keyword == "WELSPECS":
                                    my_list = fill_default_columns(my_list, 17)
                                elif keyword == "COMPDAT":
                                    my_list = fill_default_columns(my_list, 14)
                                elif keyword == "WELSEGS" and i > (kw_idx + 1):
                                    # print mylist
                                    my_list = fill_default_columns(my_list, 15)
                                # print mylist
                                elif keyword == "WELSEGS" and i == (kw_idx + 1):
                                    my_list = fill_default_columns(my_list, 12)
                                # print mylist
                                elif keyword == "COMPSEGS" and i > (kw_idx + 1):
                                    my_list = fill_default_columns(my_list, 11)
                                content.append(my_list)
                obj = KW(content)
                obj.name = keyword
                if keyword == "WELSEGS" or keyword == "COMPSEGS":
                    well_name = content[0][0]
                    well_name = well_name.replace("'", "")
                    obj.well = well_name
                all_kw.append(obj)
    return all_kw


def read_schedule_keywords_backup(well_file, keyword):
    """"""
    my_data = deepcopy(well_file)
    n_line = len(my_data)
    i = -1
    all_kw = []
    while i < n_line - 1:
        i = i + 1
        my_list = clean_to_list(my_data[i])
        if len(my_list) > 0:
            if my_list[0] == keyword:
                kw_idx = i
                keyword = str(my_list[0])
                content = []
                while i < n_line:
                    i = i + 1
                    my_list2 = clean_to_list2(my_data[i])
                    if len(my_list2) > 0:
                        if my_list2[0] == "/":
                            break
                        else:
                            my_data[i] = my_data[i].replace("'", "")
                            my_data[i] = my_data[i].replace('"', "")
                            my_list = clean_to_list(my_data[i])
                            if len(my_list) > 0:
                                my_list = expand_default_column(my_list)
                                if keyword == "WELSPECS":
                                    my_list = fill_default_columns(my_list, 17)
                                elif keyword == "COMPDAT":
                                    my_list = fill_default_columns(my_list, 14)
                                elif keyword == "WELSEGS" and i > (kw_idx + 1):
                                    # print(mylist)
                                    my_list = fill_default_columns(my_list, 15)
                                # print(mylist)
                                elif keyword == "COMPSEGS" and i > (kw_idx + 1):
                                    my_list = fill_default_columns(my_list, 11)
                                content.append(my_list)
                obj = KW(content)
                obj.name = keyword
                if keyword == "WELSEGS" or keyword == "COMPSEGS":
                    # print(content)
                    well_name = content[0][0]
                    well_name = well_name.replace("'", "")
                    obj.well = well_name
                all_kw.append(obj)
    return all_kw


def fill_default_columns(my_list, n):
    n_col = len(my_list)
    if n_col < n:
        extension = ["1*"] * (n - n_col)
        my_list.extend(extension)
    return my_list


def welspecs_panda(myobject):
    i = -1
    for iobject in myobject:
        if iobject.name == "WELSPECS":
            i = i + 1
            if i == 0:
                welspecs = np.asarray(iobject)
            else:
                welspecs = np.row_stack((welspecs, iobject))
    welspecs_header = [
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
    return pd.DataFrame(welspecs, columns=welspecs_header)


def compdat_panda(my_object):
    i = -1
    for i_object in my_object:
        if i_object.name == "COMPDAT" and len(i_object) > 0:
            i = i + 1
            if i == 0:
                compdat = np.asarray(i_object)
            else:
                compdat = np.row_stack((compdat, i_object))
    compdat_header = [
        "WELL",
        "I",
        "J",
        "K",
        "K2",
        "STATUS",
        "SATNUM",
        "CF",
        "RAD",
        "KH",
        "SKIN",
        "DFACT",
        "COMPDAT_DIRECTION",
        "RO",
    ]
    compdat = pd.DataFrame(compdat, columns=compdat_header)
    compdat[["I", "J", "K", "K2"]] = compdat[["I", "J", "K", "K2"]].astype(np.int32)
    try:
        compdat["CF"] = compdat["CF"].astype(np.float64)
    except Exception:
        pass
    try:
        compdat["KH"] = compdat["KH"].astype(np.float64)
    except Exception:
        pass

    return compdat


def welsegs_panda(my_object):
    i = -1
    welsegs_header = [
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
    welsegs_opening_header = [
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

    welsegs_content_collection = []
    welsegs_opening_collection = []

    for i_object in my_object:
        if i_object.name == "WELSEGS":
            i = i + 1
            if i == 0:
                welsegs_content_collection = []
                welsegs_opening_collection = []

            welsegs_opening = np.asarray(i_object[:1])
            welsegs_opening = pd.DataFrame(
                welsegs_opening, columns=welsegs_opening_header
            )

            welsegs_opening = PandaCollection(welsegs_opening)
            welsegs_opening.well = i_object.well
            welsegs_opening_collection.append(welsegs_opening)

            welsegs = np.asarray(i_object[1:])
            welsegs = pd.DataFrame(welsegs, columns=welsegs_header)
            welsegs[
                ["TUBINGSEGMENT", "TUBINGSEGMENT2", "TUBINGBRANCH", "TUBINGOUTLET"]
            ] = welsegs[
                ["TUBINGSEGMENT", "TUBINGSEGMENT2", "TUBINGBRANCH", "TUBINGOUTLET"]
            ].astype(
                np.int32
            )
            welsegs[["TUBINGMD", "TUBINGTVD"]] = welsegs[
                ["TUBINGMD", "TUBINGTVD"]
            ].astype(np.float64)

            welsegs = PandaCollection(welsegs)
            welsegs.well = i_object.well
            welsegs_content_collection.append(welsegs)
    return welsegs_opening_collection, welsegs_content_collection


def compsegs_panda(myobject):
    i = -1
    compsegs_header = [
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
    for i_object in myobject:
        if i_object.name == "COMPSEGS":
            i = i + 1
            if i == 0:
                compsegs_collection = []
            compsegs = np.asarray(i_object[1:])
            compsegs = pd.DataFrame(compsegs, columns=compsegs_header)
            compsegs[["I", "J", "K", "BRANCH"]] = compsegs[
                ["I", "J", "K", "BRANCH"]
            ].astype(np.int32)
            compsegs[["STARTMD", "ENDMD"]] = compsegs[["STARTMD", "ENDMD"]].astype(
                np.float64
            )

            compsegs = PandaCollection(compsegs)
            compsegs.well = i_object.well
            compsegs_collection.append(compsegs)
    return compsegs_collection
