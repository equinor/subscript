from res2df import ResdataFiles, compdat


def get_completion_list(ecl_data_file_name):
    """
    Create a datafram of unrolled well completions

    Args:
    Input DATA file name

    Returns:
    Tuple:
    List of unique well names
    List of completions associated to well names
    """

    ecl_file = ResdataFiles(ecl_data_file_name)
    compdat_df = compdat.df(ecl_file)

    # Convert from ECL index
    compdat_df[["I", "J", "K1", "K2"]] = compdat_df[["I", "J", "K1", "K2"]] - 1

    # Create tuples
    compdat_df["IJK"] = compdat_df[["I", "J", "K1"]].apply(tuple, axis=1)

    well_list = compdat_df["WELL"].unique().tolist()
    completion_list = []
    for well in well_list:
        completion_list.append(
            compdat_df["IJK"].loc[compdat_df["WELL"] == well].to_list()
        )

    return completion_list, well_list
