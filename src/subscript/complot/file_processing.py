from io import StringIO


def clear_comments(input_file: str):
    """
    Read a file or a text string, clear trash, and return a StringIO object.

    Args:
        input file (str): The file or string to be treated

    Returns:
        A StringIO object.
    """

    try:
        my_data = open(input_file, "r").readlines()
    except FileNotFoundError:
        my_data = input_file.split("\n")
    n_line = len(my_data)
    no_comments = " " * 15
    for i in range(n_line):
        my_line = my_data[i].lstrip("\t")
        my_line = my_line.lstrip(" ")
        my_line = my_line.replace("\t", " ")
        my_line = my_line.replace("\n", "")
        my_line = " ".join(my_line.split())
        my_line = my_line.split("--", 1)[0]
        if "--" not in my_line and (len(my_line) > 1 or my_line == "/"):
            if my_line[len(my_line) - 1] != "\n":
                if no_comments != "":
                    no_comments = no_comments + "\n" + my_line
                else:
                    no_comments = my_line
            else:
                no_comments = no_comments + my_line
    return StringIO(no_comments)
