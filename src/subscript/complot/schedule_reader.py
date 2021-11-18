import copy
from copy import deepcopy
import re
import numpy as np
import pandas as pd


class kw(list):
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
        return super(kw, self).__new__(self, args, kwargs)

    def __init__(self, *args, **kwargs):
        if len(args) == 1 and hasattr(args[0], "__iter__"):
            list.__init__(self, args[0])
        else:
            list.__init__(self, args)
        self.__dict__.update(kwargs)

    def __call__(self, **kwargs):
        self.__dict__.update(kwargs)
        return self


class pandacollection:
    def __init__(self, panda):
        self.content = panda.copy(deep=True)

    def __call__(self, **kwargs):
        self.__dict__.update(kwargs)
        return self


def stripcomments(code):
    code = str(code)
    code = code.split("--", 1)
    return code[0]


def cleantolist(string):
    myline = stripcomments(string)
    myline = myline.replace("\t", " ")
    myline = myline.replace("\n", " ")
    myline = myline.split("/")[0]
    mylist = myline.split(" ")
    mylist = list(filter(None, mylist))
    return mylist


def cleantolist2(string):
    myline = stripcomments(string)
    myline = myline.replace("\t", " ")
    myline = myline.replace("\n", " ")
    mylist = myline.split(" ")
    mylist = list(filter(None, mylist))
    return mylist


def expanddefaultcolumn(xin):
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


def read_schedule_keywords(wellfile, keywordlist):
    """"""
    mydata = deepcopy(wellfile)
    nline = len(mydata)
    i = -1
    allkw = []
    while i < nline - 1:
        i = i + 1
        mylist = cleantolist(mydata[i])
        if len(mylist) > 0:
            keyword = mylist[0]
            if keyword in keywordlist:
                kw_idx = i
                keyword = str(mylist[0])
                content = []
                while i < nline:
                    i = i + 1
                    mylist2 = cleantolist2(mydata[i])
                    if len(mylist2) > 0:
                        if mylist2[0] == "/":
                            break
                        else:
                            mydata[i] = mydata[i].replace("'", "")
                            mydata[i] = mydata[i].replace('"', "")
                            mylist = cleantolist(mydata[i])
                            if len(mylist) > 0:
                                mylist = expanddefaultcolumn(mylist)
                                if keyword == "WELSPECS":
                                    mylist = fill_default_columns(mylist, 17)
                                elif keyword == "COMPDAT":
                                    mylist = fill_default_columns(mylist, 14)
                                elif keyword == "WELSEGS" and i > (kw_idx + 1):
                                    # print mylist
                                    mylist = fill_default_columns(mylist, 15)
                                # print mylist
                                elif keyword == "WELSEGS" and i == (kw_idx + 1):
                                    mylist = fill_default_columns(mylist, 12)
                                # print mylist
                                elif keyword == "COMPSEGS" and i > (kw_idx + 1):
                                    mylist = fill_default_columns(mylist, 11)
                                content.append(mylist)
                obj = kw(content)
                obj.name = keyword
                if keyword == "WELSEGS" or keyword == "COMPSEGS":
                    wellname = content[0][0]
                    wellname = wellname.replace("'", "")
                    obj.well = wellname
                allkw.append(obj)
    return allkw


def read_schedule_keywords_backup(wellfile, keyword):
    """"""
    mydata = deepcopy(wellfile)
    nline = len(mydata)
    i = -1
    allkw = []
    while i < nline - 1:
        i = i + 1
        mylist = cleantolist(mydata[i])
        if len(mylist) > 0:
            if mylist[0] == keyword:
                kw_idx = i
                keyword = str(mylist[0])
                content = []
                while i < nline:
                    i = i + 1
                    mylist2 = cleantolist2(mydata[i])
                    if len(mylist2) > 0:
                        if mylist2[0] == "/":
                            break
                        else:
                            mydata[i] = mydata[i].replace("'", "")
                            mydata[i] = mydata[i].replace('"', "")
                            mylist = cleantolist(mydata[i])
                            if len(mylist) > 0:
                                mylist = expanddefaultcolumn(mylist)
                                if keyword == "WELSPECS":
                                    mylist = fill_default_columns(mylist, 17)
                                elif keyword == "COMPDAT":
                                    mylist = fill_default_columns(mylist, 14)
                                elif keyword == "WELSEGS" and i > (kw_idx + 1):
                                    # print(mylist)
                                    mylist = fill_default_columns(mylist, 15)
                                # print(mylist)
                                elif keyword == "COMPSEGS" and i > (kw_idx + 1):
                                    mylist = fill_default_columns(mylist, 11)
                                content.append(mylist)
                obj = kw(content)
                obj.name = keyword
                if keyword == "WELSEGS" or keyword == "COMPSEGS":
                    # print(content)
                    wellname = content[0][0]
                    wellname = wellname.replace("'", "")
                    obj.well = wellname
                allkw.append(obj)
    return allkw


def fill_default_columns(mylist, n):
    ncol = len(mylist)
    if ncol < n:
        extension = ["1*"] * (n - ncol)
        mylist.extend(extension)
    return mylist


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


def compdat_panda(myobject):
    i = -1
    for iobject in myobject:
        if iobject.name == "COMPDAT" and len(iobject) > 0:
            i = i + 1
            if i == 0:
                compdat = np.asarray(iobject)
            else:
                compdat = np.row_stack((compdat, iobject))
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


def welsegs_panda(myobject):
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
    for iobject in myobject:
        if iobject.name == "WELSEGS":
            i = i + 1
            if i == 0:
                welsegs_content_collection = []
                welsegs_opening_collection = []

            welsegs_opening = np.asarray(iobject[:1])
            welsegs_opening = pd.DataFrame(
                welsegs_opening, columns=welsegs_opening_header
            )

            welsegs_opening = pandacollection(welsegs_opening)
            welsegs_opening.well = iobject.well
            welsegs_opening_collection.append(welsegs_opening)

            welsegs = np.asarray(iobject[1:])
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

            welsegs = pandacollection(welsegs)
            welsegs.well = iobject.well
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
    for iobject in myobject:
        if iobject.name == "COMPSEGS":
            i = i + 1
            if i == 0:
                compsegs_collection = []
            compsegs = np.asarray(iobject[1:])
            compsegs = pd.DataFrame(compsegs, columns=compsegs_header)
            compsegs[["I", "J", "K", "BRANCH"]] = compsegs[
                ["I", "J", "K", "BRANCH"]
            ].astype(np.int32)
            compsegs[["STARTMD", "ENDMD"]] = compsegs[["STARTMD", "ENDMD"]].astype(
                np.float64
            )

            compsegs = pandacollection(compsegs)
            compsegs.well = iobject.well
            compsegs_collection.append(compsegs)
    return compsegs_collection
