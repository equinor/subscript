# -*- coding: utf-8 -*-
""" Module with support tools for singlesens"""


def find_combinations(selections):
    """ Finds combinations of values in OrderedDict

    Args:
        selections: Ordered dictionary where for each key
                    the value is a list of lists.

    Returns:
        list: List of all possible combinations of the list items

    Example:
        >>> from collections import OrderedDict
        >>> exampleinput = {'zones': [['zone_a', 'zone_b'], 'zone_c'],
                           'regions': ['reg_1', 'reg_2']}
        >>> find_combinations(exampleinput)
        [
        ['reg_1', ['zone_a', 'zone_b']],
        ['reg_1', 'zone_c'],
        ['reg_2', ['zone_a', 'zone_b']],
        ['reg_2', 'zone_c']
        ]

    """
    # create list of lists with values from dictionary
    values = []
    for item in range(len(selections)):
        values.append(selections.values()[item])

    # find all possible combinations
    combinations = [[]]
    for xitem in values:
        tempcomb = []
        for yitem in xitem:
            for combitem in combinations:
                tempcomb.append(combitem + [yitem])
        combinations = tempcomb

    return combinations
