#!/usr/bin/env python
import argparse
import shutil

from jinja2 import DebugUndefined, Environment, FileSystemLoader, meta
from yaml import Loader, load

from subscript import getLogger
from subscript.casegen_upcars.model import Model
from subscript.casegen_upcars.udf import TERMINALCOLORS, conversion, flatten, listify
from subscript.casegen_upcars.udf_arg_parser import fill_parser

DESCRIPTION = """casegen_upcars is script to create conceptual model
based on sugar-cube representation of fracture.

It has capability to:

- simple geometric: tilting, hull and dome shape
- Layers heterogeneity (streaks)
- multple throws (vertical shifting in any part of the model)
- vugs distribution: random, near fracture and near streak
- etc. Check wiki for more details:
  https://wiki.equinor.com/wiki/index.php/UpCaRs_Upscaling_casegen"""

CATEGORY = "modelling.reservoir"

EXAMPLES = """
.. code-block:: console

  DEFINE <CASEGEN_CONFIG_FILE>      <RUNPATH>/model.yaml
  DEFINE <CASEGEN_ECLIPSE_TEMPLATE> <CONFIG_PATH>/../input/config/eclipse.tmpl
  FORWARD_MODEL CASEGEN_UPCARS(<CONFIG>=<CASEGEN_CONFIG_FILE>, <ECLIPSE_TEMPLATE>=<CASEGEN_ECLIPSE_TEMPLATE>, <ECLIPSE_OUTPUT>=<ECLIPSE_NAME>-<IENS>)

"""  # noqa

logger = getLogger(__name__)


def mask_token(stream_buffer, unique_token="#|{}^", unmask=False):
    """
    Replace '< ' with some unique token and vice versa
    Jinja2 has flexibility so that it allows white space in the variable template
    This creates some issue when user have a comment with '< '
    :param stream_buffer: Jinja template/content
    :param unique_token: Token to replace with
    :param unmask: Toggle to mask or unmask
    :return: Jinja template/content with character replaced
    """
    if unmask:
        return stream_buffer.replace(unique_token, "< ")
    return stream_buffer.replace("< ", unique_token)


def get_value(config_value, args_value):
    """
    Override the value read from configuration file
    with the one from command line argument
    """
    if args_value is None:
        return config_value
    return args_value


def get_parser():
    """Returns an Argparse parser for parsing
    arguments and generating documentation"""

    arg_parse = argparse.ArgumentParser(
        prog="UpCars Case Generator",
        description="Case generator for UpCars project",
        epilog="For more information, "
        "check https://wiki.equinor.com/wiki/index.php/UpCaRs_Upscaling_casegen",
    )
    fill_parser(arg_parse)
    return arg_parse


def main():
    """Entry subroutine"""
    dictionary = {}
    arg_parse = get_parser()
    parser = arg_parse.parse_args()

    # YAML format
    with open(parser.config_file, "r", encoding="utf8") as file_handle:
        config = load(file_handle.read(), Loader=Loader)

        general = config["General"]
        geometry = config["Geometry"]

        matrix = config["Layers"]["Background Matrix"]
        streaks = config["Layers"]["Streaks"]

        throws_section = config["Throws"]
        fracture = config["Fracture"]
        fracture_x = fracture["FractureX"]
        fracture_y = fracture["FractureY"]
        vug1 = config["Near Fracture Vug"]
        vug2 = config["Random Vug"]
        vug3 = config["Near Streak Vug"]
        variables = config["Variables"]

        # General
        template_file = get_value(general["TemplateFile"], parser.eclipse_template)
        base_name = get_value(general["BaseName"], parser.base_name)
        seed = get_value(general["Seed"], parser.seed)

        # Fracture data
        fracture_at_boundary = not fracture["NoBoundaryFracture"]
        if parser.no_boundary is not None:
            fracture_at_boundary = False
        if parser.with_boundary is not None:
            fracture_at_boundary = True
        fracture_thickness = get_value(
            fracture["FractureThickness"], parser.fracture_thickness
        )
        fracture_cell_count = get_value(
            fracture["FractureCells"], parser.cells_damage_zone
        )

        fracture_length_x = conversion(
            get_value(fracture_x["Length"], parser.fracture_length_x)
        )
        fracture_offset_x = conversion(
            get_value(fracture_x["Offset"], parser.fracture_offset_x)
        )
        fracture_height_x = conversion(
            get_value(fracture_x["Height"], parser.fracture_height_x)
        )
        fracture_zoffset_x = conversion(
            get_value(fracture_x["ZOffset"], parser.fracture_zoffset_x)
        )
        fracture_perm_x = conversion(
            get_value(fracture_x["Permeability"], parser.fracture_perm_x)
        )

        fracture_length_y = conversion(
            get_value(fracture_y["Length"], parser.fracture_length_y)
        )
        fracture_offset_y = conversion(
            get_value(fracture_y["Offset"], parser.fracture_offset_y)
        )
        fracture_height_y = conversion(
            get_value(fracture_y["Height"], parser.fracture_height_y)
        )
        fracture_zoffset_y = conversion(
            get_value(fracture_y["ZOffset"], parser.fracture_zoffset_y)
        )
        fracture_perm_y = conversion(
            get_value(fracture_y["Permeability"], parser.fracture_perm_y)
        )

        fracture_poro = float(get_value(fracture["Porosity"], parser.fracture_poro))
        fracture_multx = float(get_value(fracture["MULTX"], parser.fracture_multx))
        fracture_multy = float(get_value(fracture["MULTY"], parser.fracture_multy))
        fracture_multpv = float(get_value(fracture["MULTPV"], parser.fracture_multpv))
        fracture_fipnum = int(get_value(fracture["FIPNUM"], parser.fracture_fipnum))
        fracture_satnum = int(get_value(fracture["SATNUM"], parser.fracture_satnum))
        fracture_swatinit = float(
            get_value(fracture["SWATINIT"], parser.fracture_swatinit)
        )

        # Geometry data
        cell_matrix_x = get_value(geometry["CellMatrixX"], parser.cell_matrix_x)
        cell_dx = get_value(geometry["dx"], parser.dx)
        cell_matrix_y = get_value(geometry["CellMatrixY"], parser.cell_matrix_y)
        cell_dy = get_value(geometry["dy"], parser.dy)

        top_depth = get_value(geometry["top"], parser.top_depth)
        radius_x = get_value(geometry["radius_x"], parser.radius_x)
        radius_y = get_value(geometry["radius_y"], parser.radius_y)
        radius_z = get_value(geometry["radius_z"], parser.radius_z)
        tilt = get_value(geometry["tilt"], parser.tilt)
        centroid_x = get_value(geometry["centroid_x"], parser.centroid_x)
        centroid_y = get_value(geometry["centroid_y"], parser.centroid_y)
        origin_x = get_value(geometry.get("origin_x", 0.0), parser.origin_x)
        origin_x_pos = get_value(geometry.get("origin_x_pos", 0.0), parser.origin_x_pos)
        origin_y = get_value(geometry.get("origin_y", 0.0), parser.origin_y)
        origin_y_pos = get_value(geometry.get("origin_y_pos", 0.0), parser.origin_y_pos)
        origin_top = get_value(geometry.get("origin_top", 0.0), parser.origin_top)
        rotation = get_value(geometry.get("rotation", 0.0), parser.rotation)

        # Merge streak intro background matrix
        matrix_nz = get_value(matrix["NZ"], parser.background_nz)
        matrix_dz = get_value(matrix["dz"], parser.background_dz)
        matrix_poro = get_value(matrix["Porosity"], parser.background_poro)
        matrix_perm = get_value(matrix["Permeability"], parser.background_perm)
        matrix_multx = get_value(matrix["MULTX"], parser.background_multx)
        matrix_multy = get_value(matrix["MULTY"], parser.background_multy)
        matrix_multpv = get_value(matrix["MULTPV"], parser.background_multpv)
        matrix_fipnum = get_value(matrix["FIPNUM"], parser.background_fipnum)
        matrix_satnum = get_value(matrix["SATNUM"], parser.background_satnum)
        matrix_swatinit = get_value(matrix["SWATINIT"], parser.background_swatinit)

        if (streaks is not None) and (not parser.no_streak):
            streak_k = conversion(get_value(streaks["k"], parser.streak_k), int)
            streak_nz = listify(
                conversion(get_value(streaks["NZ"], parser.streak_nz), int),
                len(streak_k),
            )
            streak_dz = listify(
                conversion(get_value(streaks["dz"], parser.streak_dz), float),
                len(streak_k),
            )
            streak_poro = listify(
                conversion(get_value(streaks["Porosity"], parser.streak_poro), float),
                len(streak_k),
            )
            streak_perm = listify(
                conversion(
                    get_value(streaks["Permeability"], parser.streak_perm), float
                ),
                len(streak_k),
            )
            streak_multx = listify(
                conversion(get_value(streaks["MULTX"], parser.streak_multx), float),
                len(streak_k),
            )
            streak_multy = listify(
                conversion(get_value(streaks["MULTY"], parser.streak_multy), float),
                len(streak_k),
            )
            streak_multpv = listify(
                conversion(get_value(streaks["MULTPV"], parser.streak_multpv), float),
                len(streak_k),
            )
            streak_fipnum = listify(
                conversion(get_value(streaks["FIPNUM"], parser.streak_fipnum), int),
                len(streak_k),
            )
            streak_satnum = listify(
                conversion(get_value(streaks["SATNUM"], parser.streak_satnum), int),
                len(streak_k),
            )
            streak_swatinit = listify(
                conversion(
                    get_value(streaks["SWATINIT"], parser.streak_swatinit), float
                ),
                len(streak_k),
            )
            if parser.streak_box is None:
                streak_box = streaks["BoundingBox"]
            else:
                streak_box = flatten(parser.streak_box)
                assert (
                    len(streak_box) % 4 == 0
                ), "Number of input for streak box must be 4 or multiplication of 4"
                streak_box = [
                    streak_box[i : i + 4] for i in range(0, len(streak_box), 4)
                ]
        else:
            streak_k = []
            streak_nz = []
            streak_dz = []
            streak_poro = []
            streak_perm = []
            streak_multx = []
            streak_multy = []
            streak_multpv = []
            streak_fipnum = []
            streak_satnum = []
            streak_swatinit = []
            streak_box = []

        # Throws
        throws = []
        if parser.throws is None:
            throws_i1 = throws_section["i1"]
            throws_i2 = throws_section["i2"]
            throws_j1 = throws_section["j1"]
            throws_j2 = throws_section["j2"]
            throws_dz = throws_section["dz"]
            for _i1, _i2, _j1, _j2, _dz in zip(
                throws_i1, throws_i2, throws_j1, throws_j2, throws_dz
            ):
                throws.append([_i1, _i2, _j1, _j2, _dz])
        else:
            throws = []
            for throw in parser.throws:
                if len(throw) != 5:
                    raise ValueError(
                        f"{TERMINALCOLORS['FAIL']}You need to specify throw "
                        f"in the following order:\r\n"
                        f"{TERMINALCOLORS['OKBLUE']}i1   i2    j1    j2   dz"
                        f"{TERMINALCOLORS['ENDC']}"
                    )
                throws.append(
                    [
                        int(throw[0]),
                        int(throw[1]),
                        int(throw[2]),
                        int(throw[3]),
                        throw[4],
                    ]
                )
        if parser.no_throw:
            throws = []

        # Read near fracture vugs related data
        if parser.vug1_fraction is None:
            vug1_fraction_min, vug1_fraction_max = (
                float(vug1["Fraction"]["Min"]),
                float(vug1["Fraction"]["Max"]),
            )
        else:
            vug1_fraction_min, vug1_fraction_max = parser.vug1_fraction

        vug1_distance_to_fracture = get_value(
            vug1["Distance_to_fracture"], parser.vug1_distance_to_fracture
        )

        if parser.vug1_porosity is None:
            vug1_poro_min, vug1_poro_max = (
                float(vug1["Porosity"]["Min"]),
                float(vug1["Porosity"]["Max"]),
            )
        else:
            vug1_poro_min, vug1_poro_max = parser.vug1_porosity

        if parser.vug1_permeability is None:
            vug1_perm_min, vug1_perm_max = (
                float(vug1["Permeability"]["Min"]),
                float(vug1["Permeability"]["Max"]),
            )
        else:
            vug1_perm_min, vug1_perm_max = parser.vug1_permeability

        vug1_mult_x = get_value(vug1["MULTX"], parser.vug1_multx)
        vug1_mult_y = get_value(vug1["MULTY"], parser.vug1_multy)
        vug1_mult_pv = get_value(vug1["MULTPV"], parser.vug1_multpv)
        vug1_fipnum = get_value(vug1["FIPNUM"], parser.vug1_fipnum)
        vug1_satnum = get_value(vug1["SATNUM"], parser.vug1_satnum)
        vug1_swatinit = get_value(vug1["SWATINIT"], parser.vug1_swatinit)
        vug1_spread = get_value(vug1["SpreadingFactor"], parser.vug1_spread)

        # Read random vugs related data
        if parser.vug2_fraction is None:
            vug2_fraction_min, vug2_fraction_max = (
                float(vug2["Fraction"]["Min"]),
                float(vug2["Fraction"]["Max"]),
            )
        else:
            vug2_fraction_min, vug2_fraction_max = parser.vug2_fraction

        if parser.vug2_porosity is None:
            vug2_poro_min, vug2_poro_max = (
                float(vug2["Porosity"]["Min"]),
                float(vug2["Porosity"]["Max"]),
            )
        else:
            vug2_poro_min, vug2_poro_max = parser.vug2_porosity

        if parser.vug2_permeability is None:
            vug2_perm_min, vug2_perm_max = (
                float(vug2["Permeability"]["Min"]),
                float(vug2["Permeability"]["Max"]),
            )
        else:
            vug2_perm_min, vug2_perm_max = parser.vug2_permeability

        vug2_mult_x = get_value(vug2["MULTX"], parser.vug2_multx)
        vug2_mult_y = get_value(vug2["MULTY"], parser.vug2_multy)
        vug2_mult_pv = get_value(vug2["MULTPV"], parser.vug2_multpv)
        vug2_fipnum = get_value(vug2["FIPNUM"], parser.vug2_fipnum)
        vug2_satnum = get_value(vug2["SATNUM"], parser.vug2_satnum)
        vug2_swatinit = get_value(vug2["SWATINIT"], parser.vug2_swatinit)

        # Read near streak vugs related data
        if parser.vug3_fraction is None:
            vug3_fraction_min, vug3_fraction_max = (
                float(vug3["Fraction"]["Min"]),
                float(vug3["Fraction"]["Max"]),
            )
        else:
            vug3_fraction_min, vug3_fraction_max = parser.vug3_fraction

        vug3_distance_to_streak = get_value(
            vug3["Distance_to_streak"], parser.vug3_distance_to_streak
        )
        if parser.vug3_porosity is None:
            vug3_poro_min, vug3_poro_max = (
                float(vug3["Porosity"]["Min"]),
                float(vug3["Porosity"]["Max"]),
            )
        else:
            vug3_poro_min, vug3_poro_max = parser.vug3_porosity

        if parser.vug3_permeability is None:
            vug3_perm_min, vug3_perm_max = (
                float(vug3["Permeability"]["Min"]),
                float(vug3["Permeability"]["Max"]),
            )
        else:
            vug3_perm_min, vug3_perm_max = parser.vug3_permeability

        vug3_mult_x = get_value(vug3["MULTX"], parser.vug3_multx)
        vug3_mult_y = get_value(vug3["MULTY"], parser.vug3_multy)
        vug3_mult_pv = get_value(vug3["MULTPV"], parser.vug3_multpv)
        vug3_fipnum = get_value(vug3["FIPNUM"], parser.vug3_fipnum)
        vug3_satnum = get_value(vug3["SATNUM"], parser.vug3_satnum)
        vug3_swatinit = get_value(vug3["SWATINIT"], parser.vug3_swatinit)
        vug3_spread = get_value(vug3["SpreadingFactor"], parser.vug3_spread)

        # Read variables
        dict_var = {}
        for key in list(variables.keys()):
            dictionary[key] = variables[key]
            dict_var[key] = listify(variables[key], 1)
        if parser.variables is not None:
            for var in parser.variables:
                dictionary[var[0]] = var[1]

    logger.info("Creating model")
    grid = Model(
        cell_matrix_x,
        cell_matrix_y,
        matrix_nz,
        cell_dx,
        cell_dy,
        matrix_dz,
        streak_k,
        streak_dz,
        streak_nz,
        streak_box,
        fracture_thickness,
        fracture_cell_count,
        fracture_at_boundary,
        top_depth,
        radius_x,
        radius_y,
        radius_z,
        tilt,
        centroid_x,
        centroid_y,
        origin_x,
        origin_y,
        rotation,
        origin_x_pos,
        origin_y_pos,
        origin_top,
        fracture_length_x,
        fracture_offset_x,
        fracture_height_x,
        fracture_zoffset_x,
        fracture_length_y,
        fracture_offset_y,
        fracture_height_y,
        fracture_zoffset_y,
        seed,
    )
    grid.set_throws(throws)

    if vug1_fraction_max + vug2_fraction_max + vug3_fraction_max > 0:
        logger.info("Set vugs")
        grid.set_vug(
            [vug1_fraction_min, vug1_fraction_max],
            [vug1_perm_min, vug1_perm_max],
            [vug1_poro_min, vug1_poro_max],
            vug1_distance_to_fracture,
            vug1_mult_x,
            vug1_mult_y,
            vug1_mult_pv,
            vug1_spread,
            [vug2_fraction_min, vug2_fraction_max],
            [vug2_perm_min, vug2_perm_max],
            [vug2_poro_min, vug2_poro_max],
            vug2_mult_x,
            vug2_mult_y,
            vug2_mult_pv,
            [vug3_fraction_min, vug3_fraction_max],
            [vug3_perm_min, vug3_perm_max],
            [vug3_poro_min, vug3_poro_max],
            vug3_distance_to_streak,
            vug3_mult_x,
            vug3_mult_y,
            vug3_mult_pv,
            vug3_spread,
        )

    logger.info("Set property")
    grid.set_fracture_anisotropy_property("PERM", fracture_perm_x, fracture_perm_y)
    grid.set_layers_property("PERM", matrix_perm, streak_perm)
    for keyword, var_matrix, var_layer, var_fracture in zip(
        ["PORO", "MULTPV", "MULTX", "MULTY"],
        [matrix_poro, matrix_multpv, matrix_multx, matrix_multy],
        [streak_poro, streak_multpv, streak_multx, streak_multy],
        [fracture_poro, fracture_multpv, fracture_multx, fracture_multy],
    ):
        grid.set_fracture_property(keyword, var_fracture)
        grid.set_layers_property(keyword, var_matrix, var_layer)

    grid.distribute_property()

    dictionary.update(grid.dict_info)
    env = Environment(
        loader=FileSystemLoader(searchpath="."),
        undefined=DebugUndefined,
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="<",
        variable_end_string=">",
    )
    base_name = env.from_string(base_name).render(dictionary)

    dictionary["GRDECL_file"] = f"gridinc_{base_name}.GRDECL"

    logger.info("Exporting GRDECL file")
    grid.export_grdecl(dictionary["GRDECL_file"])

    for keyword, var_matrix, var_layer, var_fracture, var_vug in zip(
        ["FIPNUM", "SATNUM", "SWAT"],
        [matrix_fipnum, matrix_satnum, matrix_swatinit],
        [streak_fipnum, streak_satnum, streak_swatinit],
        [fracture_fipnum, fracture_satnum, fracture_swatinit],
        [
            [vug1_fipnum, vug2_fipnum, vug3_fipnum],
            [vug1_satnum, vug2_satnum, vug3_satnum],
            [vug1_swatinit, vug2_swatinit, vug3_swatinit],
        ],
    ):
        logger.info("Exporting " + keyword + " include file")
        include_file = f"{keyword.lower()}_file"
        dictionary[include_file] = f"{keyword.lower()}_{base_name}.INC"
        grid.export_props(
            dictionary[include_file],
            keyword,
            var_matrix,
            var_layer,
            var_fracture,
            var_vug,
        )

    dictionary.update(grid.dict_info)
    dictionary["swatm"] = matrix_swatinit
    dictionary["swatstreak"] = streak_swatinit
    dictionary["swatf"] = fracture_swatinit
    dictionary["avgSw"] = grid.calculate_avg_prop(
        matrix_swatinit,
        streak_swatinit,
        fracture_swatinit,
        [vug1_swatinit, vug2_swatinit],
    )

    with open(template_file, "r", encoding="utf8") as file_handle:
        buffer_ = mask_token(file_handle.read(), unmask=False)
        case_template = env.from_string(buffer_)
        ast = env.parse(buffer_)
    undefined_var = []
    built_in_functions = ["range"]

    for var in sorted(meta.find_undeclared_variables(ast)):
        if dictionary.get(var) is None and var not in built_in_functions:
            undefined_var.append(var)

    if undefined_var:
        logger.warning(
            f"Found {len(undefined_var)} undefined variables."
            f"Please verify your output files.\n{undefined_var}"
        )

    with open(base_name + ".DATA", "w", encoding="utf8") as file_handle:
        file_handle.write(mask_token(case_template.render(dictionary), unmask=True))

    if parser.debug_model is not None:
        # create debug model
        file_list = [
            dictionary[f"{keyword.lower()}_file"]
            for keyword in ["FIPNUM", "SATNUM", "SWAT"]
        ]
        file_list.insert(0, dictionary["GRDECL_file"])
        with open(parser.debug_model, "wb", encoding="utf8") as wfd:
            for _file in file_list:
                with open(_file, "rb") as file_handle:
                    shutil.copyfileobj(file_handle, wfd)


if __name__ == "__main__":
    main()
