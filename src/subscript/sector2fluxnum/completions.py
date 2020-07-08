#!/usr/bin/env python3
from ecl2df import compdat, EclFiles


def generate_compdat_dataframe(ECL_DATA_file_name):
    """
    Create a datafram of unrolled well completions

    Args:
       Input DATA file name

    Returns:
       dataFrame with the following header:

    """
    ECL_file = EclFiles(ECL_DATA_file_name)
    compdat_df = compdat.df(ECL_file)
    compdat_df = compdat.unrolldf(compdat_df)

    return compdat_df


def get_completion_list(dframe):
    """
    Create a datafram of unrolled well completions

    Args:
       Pandas data frame with completions

    Returns:
       List of unique well names
       List of completions associated to well names

    """
    # Convert from ECL index
    dframe[['I', 'J', 'K1', 'K2']] = dframe[['I', 'J', 'K1', 'K2']] - 1

    # Create tuples
    dframe['IJK'] = dframe[['I', 'J', 'K1']].apply(tuple, axis=1)

    well_list = dframe['WELL'].unique().tolist()
    completion_list = []
    for well in well_list:
        completion_list.append(dframe['IJK'].loc[dframe['WELL'] == well].to_list())

    return completion_list, well_list
