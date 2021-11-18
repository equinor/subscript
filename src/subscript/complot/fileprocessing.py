from io import StringIO


def ClearComments(inputfile):
    """
    Reads a file or a text string, clears trash, and returns a StringIO object.

    Args:
        inputfile (str): The file or string to be treated

    Returns:
        A StringIO object.
    """

    try:
        mydata = open(inputfile, "r").readlines()
    except Exception:
        mydata = inputfile.split("\n")
    nline = len(mydata)
    nocomments = " " * 15
    for i in range(nline):
        myline = mydata[i].lstrip("\t")
        myline = myline.lstrip(" ")
        myline = myline.replace("\t", " ")
        myline = myline.replace("\n", "")
        myline = " ".join(myline.split())
        myline = myline.split("--", 1)[0]
        if "--" not in myline and (len(myline) > 1 or myline == "/"):
            if myline[len(myline) - 1] != "\n":
                if nocomments != "":
                    nocomments = nocomments + "\n" + myline
                else:
                    nocomments = myline
            else:
                nocomments = nocomments + myline
    return StringIO(nocomments)
