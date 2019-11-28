# -*- coding: utf-8 -*-
"""Module for reading excel file with input for generation of
a design matrix and converting to an OrderedDict that can be
read by fmu.tools.DesignMatrix.generate
"""
from collections import OrderedDict
import numpy as np
import pandas as pd
from fmu.config import oyaml as yaml


def excel2dict_design(input_filename, sheetnames=None):
    """Read excel file with input to design setup
    Currently only specification of
    onebyone design is implemented

    Args:
        input_filename (str): Name of excel input file
        sheetnames (dict): Dictionary of worksheet names to load
            information from. Supported keys: general_input, defaultvalues,
            and designinput.

    Returns:
        OrderedDict on format for DesignMatrix.generate
    """
    if not sheetnames or "general_input" not in sheetnames:
        gen_input_sheet = _find_geninput_sheetname(input_filename)
    else:
        gen_input_sheet = sheetnames["general_input"]

    generalinput = pd.read_excel(
        input_filename, gen_input_sheet, header=None, index_col=0
    )

    if str(generalinput[1]["designtype"]) == "onebyone":
        returndict = _excel2dict_onebyone(input_filename, sheetnames)
    else:
        raise ValueError(
            "Generation of DesignMatrix only "
            "implemented for type onebyone "
            "In general_input designtype was "
            "set to {}".format(str(generalinput[1]["designtype"]))
        )
    return returndict


def inputdict_to_yaml(inputdict, filename):
    """Write inputdict to yaml format

    Args:
        inputdict (OrderedDict)
        filename (str): path for where to write file
    """
    stream = file(filename, "w")
    yaml.dump(inputdict, stream)


def _find_geninput_sheetname(input_filename):
    """Finding general input sheet, allowing for name
    variations."""
    xls = pd.ExcelFile(input_filename)
    sheets = xls.sheet_names
    general_input_sheet = []
    for sheet in sheets:
        if sheet in [
            "general_input",
            "generalinput",
            "GeneralInput",
            "Generalinput",
            "General_Input",
            "General_input",
        ]:
            general_input_sheet.append(sheet)
    if len(general_input_sheet) > 1:
        raise ValueError(
            "More than one sheet with general input"
            "Sheetnames are {} ".format(general_input_sheet)
        )
    elif not general_input_sheet:
        raise ValueError(
            "No general_input sheet provided in Excel file {} "
            "".format(input_filename)
        )

    return general_input_sheet[0]


def _find_onebyone_defaults_sheet(input_filename):
    """Finds correct sheet name for default values to use when parsing
    excel file.

    Returns:
        string, name of a sheet in the excel file
    """
    xls = pd.ExcelFile(input_filename)
    sheets = xls.sheet_names

    default_values_sheet = []

    for sheet in sheets:
        if sheet in [
            "default_values",
            "defaultvalues",
            "DefaultValues",
            "Defaultvalues",
            "Default_Values",
            "Default_values",
        ]:
            default_values_sheet.append(sheet)
    if len(default_values_sheet) > 1:
        raise ValueError(
            "More than one sheet with default values"
            "Sheetnames are {} ".format(default_values_sheet)
        )
    elif len(default_values_sheet) == []:
        raise ValueError(
            "No defaultvalues sheet provided in Excel file {} "
            "".format(input_filename)
        )

    return default_values_sheet[0]


def _find_onebyone_input_sheet(input_filename):
    """Finds correct sheet name for input to use when parsing excel file.

    Returns:
        string, name of a sheet in the excel file
    """
    xls = pd.ExcelFile(input_filename)
    sheets = xls.sheet_names

    design_input_sheet = []

    for sheet in sheets:
        if sheet in [
            "design_input",
            "designinput",
            "DesignInput",
            "Designinput",
            "Design_Input",
            "Design_input",
        ]:
            design_input_sheet.append(sheet)
    if len(design_input_sheet) > 1:
        raise ValueError(
            "More than one sheet with design input"
            "Sheetnames are {} ".format(design_input_sheet)
        )
    elif not design_input_sheet:
        raise ValueError(
            "No designinput sheet provided in Excel file {} " "".format(input_filename)
        )
    return design_input_sheet[0]


def _excel2dict_onebyone(input_filename, sheetnames=None):
    """Reads spesification for onebyone design

    Args:
        input_filename(path): path to excel workbook
        sheetnames (dict): Dictionary of worksheet names to load
            information from. Supported keys: general_input, defaultvalues,
            and designinput.

    Returns:
        OrderedDict on format for DesignMatrix.generate
    """

    seedname = "RMS_SEED"
    inputdict = OrderedDict()

    if not sheetnames or "general_input" not in sheetnames:
        gen_input_sheet = _find_geninput_sheetname(input_filename)
    else:
        gen_input_sheet = sheetnames["general_input"]

    if not sheetnames or "designinput" not in sheetnames:
        design_inp_sheet = _find_onebyone_input_sheet(input_filename)
    else:
        design_inp_sheet = sheetnames["designinput"]

    if not sheetnames or "defaultvalues" not in sheetnames:
        default_val_sheet = _find_onebyone_defaults_sheet(input_filename)
    else:
        default_val_sheet = sheetnames["defaultvalues"]

    # Read general input
    generalinput = pd.read_excel(
        input_filename, gen_input_sheet, header=None, index_col=0
    )

    inputdict["designtype"] = generalinput[1]["designtype"]
    inputdict["seeds"] = generalinput[1]["seeds"]
    inputdict["repeats"] = generalinput[1]["repeats"]

    # Read background
    if "background" in generalinput.index:
        inputdict["background"] = OrderedDict()
        if generalinput[1]["background"].endswith("csv") or generalinput[1][
            "background"
        ].endswith("xlsx"):
            inputdict["background"]["extern"] = generalinput[1]["background"]
        elif str(generalinput[1]["background"]) == "None":
            inputdict["background"] = None
        else:
            inputdict["background"] = _read_background(
                input_filename, generalinput[1]["background"]
            )
    else:
        inputdict["background"] = None

    # Read default values
    inputdict["defaultvalues"] = _read_defaultvalues(input_filename, default_val_sheet)

    # Read input for sensitivities
    inputdict["sensitivities"] = OrderedDict()
    designinput = pd.read_excel(input_filename, design_inp_sheet)

    designinput["sensname"].fillna(method="ffill", inplace=True)

    # Read decimals
    if "decimals" in designinput.keys():
        inputdict["decimals"] = OrderedDict()
        for row in designinput.itertuples():
            if _has_value(row.decimals) and _is_int(row.decimals):
                inputdict["decimals"][row.param_name] = int(row.decimals)

    grouped = designinput.groupby("sensname", sort=False)

    # Read each sensitivity
    for sensname, group in grouped:

        sensdict = OrderedDict()

        if group["type"].iloc[0] == "ref":
            sensdict["senstype"] = "ref"

        elif group["type"].iloc[0] == "background":
            sensdict["senstype"] = "background"

        elif group["type"].iloc[0] == "seed":
            sensdict["seedname"] = seedname
            sensdict["senstype"] = "seed"
            if _has_value(group["param_name"].iloc[0]):
                sensdict["parameters"] = _read_constants(group)
            else:
                sensdict["parameters"] = None

        elif group["type"].iloc[0] == "scenario":
            sensdict = _read_scenario_sensitivity(group)
            sensdict["senstype"] = "scenario"

        elif group["type"].iloc[0] == "dist":
            sensdict["senstype"] = "dist"
            sensdict["parameters"] = _read_dist_sensitivity(group)
            sensdict["correlations"] = None
            if "corr_sheet" in group.keys():
                sensdict["correlations"] = _read_correlations(group, input_filename)

        elif group["type"].iloc[0] == "extern":
            sensdict["extern_file"] = str(group["extern_file"].iloc[0])
            sensdict["senstype"] = "extern"
            sensdict["parameters"] = list(group["param_name"])

        else:
            raise ValueError(
                "Sensitivity {} does not have a valid sensitivity type".format(sensname)
            )

        if "numreal" in group.keys():
            if _has_value(group["numreal"].iloc[0]):
                # Using default number of realisations:
                # 'repeats' from general_input sheet
                sensdict["numreal"] = int(group["numreal"].iloc[0])

        inputdict["sensitivities"][str(sensname)] = sensdict

    return inputdict


def _read_defaultvalues(filename, sheetname):
    """Reads defaultvalues, also used as values for
    reference/base case

    Args:
        filename(path): path to excel file
        sheetname (string): name of defaultsheet

    Returns:
        OrderedDict with defaultvalues (parameter, value)
    """
    default_dict = OrderedDict()
    default_df = pd.read_excel(filename, sheetname, header=0, index_col=0)
    for row in default_df.itertuples():
        default_dict[str(row[0])] = row[1]
    return default_dict


def _read_background(inp_filename, bck_sheet):
    """Reads excel sheet with background parameters and distributions

    Args:
        inp_filename (path): path to Excel workbook
        bck_sheet (str): name of sheet with background parameters

    Returns:
        OrderedDict with parameter names and distributions
    """
    backdict = OrderedDict()
    paramdict = OrderedDict()
    bck_input = pd.read_excel(inp_filename, bck_sheet)

    backdict["correlations"] = None
    if "corr_sheet" in bck_input.keys():
        backdict["correlations"] = _read_correlations(bck_input, inp_filename)

    if "dist_param1" not in bck_input.columns.values:
        bck_input["dist_param1"] = float("NaN")
    if "dist_param2" not in bck_input.columns.values:
        bck_input["dist_param2"] = float("NaN")
    if "dist_param3" not in bck_input.columns.values:
        bck_input["dist_param3"] = float("NaN")
    if "dist_param4" not in bck_input.columns.values:
        bck_input["dist_param4"] = float("NaN")

    for row in bck_input.itertuples():
        if not _has_value(row.param_name):
            raise ValueError(
                "Background parameters specified "
                "where one line has empty parameter "
                "name "
            )
        if not _has_value(row.dist_param1):
            raise ValueError(
                "Parameter {} has been input "
                "in background sheet but with empty "
                "first distribution parameter ".format(row.param_name)
            )
        if not _has_value(row.dist_param2) and _has_value(row.dist_param3):
            raise ValueError(
                "Parameter {} has been input in "
                "background sheet with "
                'value for "dist_param3" while '
                '"dist_param2" is empty. This is not '
                "allowed".format(row.param_name)
            )
        if not _has_value(row.dist_param3) and _has_value(row.dist_param4):
            raise ValueError(
                "Parameter {} has been input in "
                "background sheet with "
                'value for "dist_param4" while '
                '"dist_param3" is empty. This is not '
                "allowed".format(row.param_name)
            )
        distparams = [
            item
            for item in [
                row.dist_param1,
                row.dist_param2,
                row.dist_param3,
                row.dist_param4,
            ]
            if _has_value(item)
        ]
        if "corr_sheet" in bck_input.keys():
            if not _has_value(row.corr_sheet):
                corrsheet = None
            else:
                corrsheet = row.corr_sheet
        else:
            corrsheet = None
        paramdict[str(row.param_name)] = [str(row.dist_name), distparams, corrsheet]
    backdict["parameters"] = paramdict

    if "decimals" in bck_input.keys():
        decimals = OrderedDict()
        for row in bck_input.itertuples():
            if _has_value(row.decimals) and _is_int(row.decimals):
                decimals[row.param_name] = int(row.decimals)
        backdict["decimals"] = decimals

    return backdict


def _read_scenario_sensitivity(sensgroup):
    """Reads parameters and values
    for scenario sensitivities
    """
    sdict = OrderedDict()
    sdict["cases"] = OrderedDict()
    casedict1 = OrderedDict()
    casedict2 = OrderedDict()

    if not _has_value(sensgroup["senscase1"].iloc[0]):
        raise ValueError(
            "Sensitivity {} has been input "
            "as a scenario sensitivity, but "
            "without a name in senscase1 column.".format(sensgroup["sensname"].iloc[0])
        )

    for row in sensgroup.itertuples():
        if not _has_value(row.param_name):
            raise ValueError(
                "Scenario sensitivity {} specified "
                "where one line has empty parameter "
                "name ".format(row.sensname)
            )
        if not _has_value(row.value1):
            raise ValueError(
                "Parameter {} har been input "
                'as type "scenario" but with empty '
                "value in value1 column ".format(row.param_name)
            )
        else:
            casedict1[str(row.param_name)] = row.value1
    if _has_value(sensgroup["senscase2"].iloc[0]):
        for row in sensgroup.itertuples():
            if not _has_value(row.value2):
                raise ValueError(
                    "Sensitivity {} has been input "
                    "with a name in senscase2 column "
                    "but without a value for parameter {} "
                    "in value2 column.".format(
                        sensgroup["sensname"].iloc[0], row.param_name
                    )
                )
            else:
                casedict2[str(row.param_name)] = row.value2
        sdict["cases"][str(sensgroup["senscase1"].iloc[0])] = casedict1
        sdict["cases"][str(sensgroup["senscase2"].iloc[0])] = casedict2
    else:
        for row in sensgroup.itertuples():
            if _has_value(row.value2):
                raise ValueError(
                    "Sensitivity {} has been input "
                    "with a value for parameter {} "
                    "in value2 column "
                    "but without a name for the scenario "
                    "in senscase2 column.".format(
                        sensgroup["sensname"].iloc[0], row.param_name
                    )
                )
        sdict["cases"][str(sensgroup["senscase1"].iloc[0])] = casedict1
    return sdict


def _read_constants(sensgroup):
    """Reads constants to be used together with
    seed sensitivity"""
    if "dist_param1" not in sensgroup.columns.values:
        sensgroup["dist_param1"] = float("NaN")
    paramdict = OrderedDict()
    for row in sensgroup.itertuples():
        if not _has_value(row.dist_param1):
            raise ValueError(
                "Parameter name {} has been input "
                'in a sensitivity of type "seed". \n'
                "If {} was meant to be the name of "
                "the seed parameter, this is "
                "unfortunately not allowed. "
                "The seed parameter name is standardised "
                "to RMS_SEED and should not be specified.\n "
                "If you instead meant to specify a constant "
                "value for another parameter in the seed "
                'sensitivity, please remember "const" in '
                'dist_name and a value in "dist_param1". '.format(
                    row.param_name, row.param_name
                )
            )
        distparams = row.dist_param1
        paramdict[str(row.param_name)] = [str(row.dist_name), distparams]
    return paramdict


def _read_dist_sensitivity(sensgroup):
    """Reads parameters and distributions
    for monte carlo sensitivities
    """
    if "dist_param1" not in sensgroup.columns.values:
        sensgroup["dist_param1"] = float("NaN")
    if "dist_param2" not in sensgroup.columns.values:
        sensgroup["dist_param2"] = float("NaN")
    if "dist_param3" not in sensgroup.columns.values:
        sensgroup["dist_param3"] = float("NaN")
    if "dist_param4" not in sensgroup.columns.values:
        sensgroup["dist_param4"] = float("NaN")
    paramdict = OrderedDict()
    for row in sensgroup.itertuples():
        if not _has_value(row.param_name):
            raise ValueError(
                "Dist sensitivity {} specified "
                "where one line has empty parameter "
                "name ".format(row.sensname)
            )
        if not _has_value(row.dist_param1):
            raise ValueError(
                "Parameter {} has been input "
                'as type "dist" but with empty '
                "first distribution parameter ".format(row.param_name)
            )
        if not _has_value(row.dist_param2) and _has_value(row.dist_param3):
            raise ValueError(
                "Parameter {} has been input with "
                'value for "dist_param3" while '
                '"dist_param2" is empty. This is not '
                "allowed".format(row.param_name)
            )
        if not _has_value(row.dist_param3) and _has_value(row.dist_param4):
            raise ValueError(
                "Parameter {} has been input with "
                'value for "dist_param4" while '
                '"dist_param3" is empty. This is not '
                "allowed".format(row.param_name)
            )
        distparams = [
            item
            for item in [
                row.dist_param1,
                row.dist_param2,
                row.dist_param3,
                row.dist_param4,
            ]
            if _has_value(item)
        ]
        if "corr_sheet" in sensgroup.keys():
            if not _has_value(row.corr_sheet):
                corrsheet = None
            else:
                corrsheet = row.corr_sheet
        else:
            corrsheet = None
        paramdict[str(row.param_name)] = [str(row.dist_name), distparams, corrsheet]

    return paramdict


def _read_correlations(sensgroup, inputfile):

    if "corr_sheet" in sensgroup.keys():
        if not sensgroup["corr_sheet"].dropna().empty:
            correlations = OrderedDict()
            correlations["inputfile"] = inputfile
            correlations["sheetnames"] = []
            for index, row in sensgroup.iterrows():
                if _has_value(row["corr_sheet"]):
                    if row["corr_sheet"] not in correlations["sheetnames"]:
                        correlations["sheetnames"].append(row["corr_sheet"])
        else:
            correlations = None
    else:
        correlations = None

    return correlations


def _has_value(value):
    """Returns False if NaN"""
    return bool(value == value)


def _is_int(teststring):
    """ Test if a string can be parsed as a float"""
    try:
        if not np.isnan(int(teststring)):
            if (float(teststring) % 1) == 0:
                return True
            return False
        return False  # It was a "number", but it was NaN.
    except ValueError:
        return False
