#!/usr/bin/env python
"""Argument parser for casegen_upcars"""

from subscript import __version__


def fill_parser_fracture(parser):
    """Set arguments parser for fracture related"""
    parser.add_argument(
        "--noBoundaryFracture",
        action="store_true",
        dest="no_boundary",
        required=False,
        help="No fracture around the model",
    )
    parser.add_argument(
        "--BoundaryFracture",
        action="store_true",
        dest="with_boundary",
        required=False,
        help="Put fracture around the model",
    )
    parser.add_argument(
        "--ft",
        "--FT",
        "--fractureThickness",
        dest="fracture_thickness",
        type=float,
        help="Fracture thickness",
        required=False,
    )
    parser.add_argument(
        "--ndz",
        "--NDZ",
        "--cellsDamageZone",
        dest="cells_damage_zone",
        type=int,
        help="Number of cells in damage zone",
        required=False,
    )
    parser.add_argument(
        "--porf",
        "--PORF",
        "--poroFracture",
        dest="fracture_poro",
        type=float,
        help="Fracture porosity",
        required=False,
    )
    parser.add_argument(
        "--satnumf",
        "--SATNUMF",
        "--satnumF",
        dest="fracture_satnum",
        type=int,
        help="Fracture SATNUM",
        required=False,
    )
    parser.add_argument(
        "--fipnumf",
        "--FIPNUMF",
        "--fipnumF",
        dest="fracture_fipnum",
        type=int,
        help="Fracture FIPNUM",
        required=False,
    )
    parser.add_argument(
        "--multx",
        "--MULTX",
        "--multx",
        dest="fracture_multx",
        type=float,
        help="MULTX for faults",
        required=False,
    )
    parser.add_argument(
        "--multy",
        "--MULTY",
        "--multy",
        dest="fracture_multy",
        type=float,
        help="MULTY for faults",
        required=False,
    )
    parser.add_argument(
        "--pvDamage",
        "--PVDAMAGE",
        "--pvDamage",
        dest="fracture_multpv",
        type=float,
        help="Pore volume multiplier inside damage zone",
        required=False,
    )
    parser.add_argument(
        "--swatinitf",
        "--swatinitF",
        "--SWATINITF",
        dest="fracture_swatinit",
        type=float,
        help="Initial water saturation inside damage zone",
        required=False,
    )

    # Fracture along x-axis
    parser.add_argument(
        "--fLengthX",
        "--FLENGTHX",
        "--flengthx",
        dest="fracture_length_x",
        nargs="+",
        type=float,
        help="Fault length for faults in x-dir. Has to be specified for each faults",
        required=False,
    )
    parser.add_argument(
        "--fOffsetX",
        "--FOFFSETX",
        "--foffsetx",
        dest="fracture_offset_x",
        nargs="+",
        type=float,
        help="Fracture/fault offset location for x-dir faults. "
        "Has to be specified for each faults",
        required=False,
    )
    parser.add_argument(
        "--fHeightX",
        "--FHEIGHTX",
        "--fheightx",
        dest="fracture_height_x",
        nargs="+",
        type=float,
        help="Fracture/fault height for x-dir faults. "
        "Has to be specified for each faults",
        required=False,
    )
    parser.add_argument(
        "--fVertOffsetX",
        "--FVERTOFFSETX",
        "--fvertoffsetx",
        dest="fracture_zoffset_x",
        nargs="+",
        type=float,
        help="Fracture/fault z-offset for x-dir faults. "
        "Has to be specified for each faults",
        required=False,
    )
    parser.add_argument(
        "--fracPermX",
        "--FRACPERMX",
        "--fracpermx",
        dest="fracture_perm_x",
        nargs="+",
        type=float,
        help="Fracture/fault permeability for x-dir faults. "
        "Has to be specified for each faults",
        required=False,
    )

    parser.add_argument(
        "--fLengthY",
        "--FLENGTHY",
        "--flengthy",
        dest="fracture_length_y",
        nargs="+",
        type=float,
        help="Fault length for faults in y-dir. Has to be specified for each faults",
        required=False,
    )
    parser.add_argument(
        "--fOffsetY",
        "--FOFFSETY",
        "--foffsety",
        dest="fracture_offset_y",
        nargs="+",
        type=float,
        help="Fracture/fault offset location for y-dir faults. "
        "Has to be specified for each faults",
        required=False,
    )
    parser.add_argument(
        "--fHeightY",
        "--FHEIGHTY",
        "--fheighty",
        dest="fracture_height_y",
        nargs="+",
        type=float,
        help="Fracture/fault height for y-dir faults. "
        "Has to be specified for each faults",
        required=False,
    )
    parser.add_argument(
        "--fVertOffsetY",
        "--FVERTOFFSETY",
        "--fvertoffsety",
        dest="fracture_zoffset_y",
        nargs="+",
        type=float,
        help="Fracture/fault z-offset for y-dir faults. "
        "Has to be specified for each faults",
        required=False,
    )
    parser.add_argument(
        "--fracPermY",
        "--FRACPERMY",
        "--fracpermy",
        dest="fracture_perm_y",
        nargs="+",
        type=float,
        help="Fracture/fault permeability for y-dir faults. "
        "Has to be specified for each faults",
        required=False,
    )


def fill_parser_vugs(parser):
    """Set arguments parser for vugs related"""
    # Vug1 - Near fracture vugs
    parser.add_argument(
        "--distanceVug1ToFracture",
        type=int,
        dest="vug1_distance_to_fracture",
        help="Number of cells between fracture and vugs, "
        "put 0 to allow connection to fracture",
        required=False,
    )
    parser.add_argument(
        "--vug1Volume",
        "--VUG1VOLUME",
        "--vug1volume",
        nargs=2,
        type=float,
        metavar=["Min", "Max"],
        dest="vug1_fraction",
        help="Volume fraction of near fracture vugs, between 0 and 1",
        required=False,
    )
    parser.add_argument(
        "--vug1Spread",
        "--VUG1SPREAD",
        "--vug1_spread",
        type=float,
        dest="vug1_spread",
        help="Spreading factor of near fracture vug",
        required=False,
    )
    parser.add_argument(
        "--vug1Poro",
        "--VUG1PORO",
        "--vug1Poro",
        nargs=2,
        type=float,
        metavar=["Min", "Max"],
        dest="vug1_porosity",
        help="Near fracture vugs porosity, min-max",
        required=False,
    )
    parser.add_argument(
        "--vug1perm",
        "--VUG1PERM",
        "--vug1Perm",
        nargs=2,
        type=float,
        metavar=["Min", "Max"],
        dest="vug1_permeability",
        help="Near fracture vugs permeability, min-max",
        required=False,
    )
    parser.add_argument(
        "--vug1MULTX",
        "--vug1multx",
        type=float,
        dest="vug1_multx",
        help="Near fracture vugs transmissibility multiplier in x- direction",
        required=False,
    )
    parser.add_argument(
        "--vug1MULTY",
        "--vug1multy",
        type=float,
        dest="vug1_multy",
        help="Near fracture vugs transmissibility multiplier in y- direction",
        required=False,
    )
    parser.add_argument(
        "--vug1MULTPV",
        "--vug1multpv",
        type=float,
        dest="vug1_multpv",
        help="Near fracture vugs pore volume multiplier",
        required=False,
    )
    parser.add_argument(
        "--vug1SWATINIT",
        "--vug1swatinit",
        type=float,
        dest="vug1_swatinit",
        help="Near fracture vugs initial water saturation",
        required=False,
    )
    parser.add_argument(
        "--vug1FIPNUM",
        "--vug1fipnum",
        type=int,
        dest="vug1_fipnum",
        help="near fracture vugs FIPNUM",
        required=False,
    )
    parser.add_argument(
        "--vug1SATNUM",
        "--vug1satnum",
        type=int,
        dest="vug1_satnum",
        help="near fracture vugs SATNUM",
        required=False,
    )

    # Vug2 - Random vug distribution
    parser.add_argument(
        "--vug2Volume",
        "--vug2VOLUME",
        "--vug2volume",
        nargs=2,
        type=float,
        metavar=["Min", "Max"],
        dest="vug2_fraction",
        help="Volume fraction of random vugs, between 0 and 1",
        required=False,
    )
    parser.add_argument(
        "--vug2Poro",
        "--vug2PORO",
        "--vug2Poro",
        nargs=2,
        type=float,
        metavar=["Min", "Max"],
        dest="vug2_porosity",
        help="Random vugs porosity, min-max",
        required=False,
    )
    parser.add_argument(
        "--vug2Perm",
        "--vug2PERM",
        "--vug2Perm",
        nargs=2,
        type=float,
        metavar=["Min", "Max"],
        dest="vug2_permeability",
        help="Random vugs permeability, min-max",
        required=False,
    )
    parser.add_argument(
        "--vug2MULTX",
        "--vug2multx",
        type=float,
        dest="vug2_multx",
        help="Random vugs transmissibility multiplier in x- direction",
        required=False,
    )
    parser.add_argument(
        "--vug2MULTY",
        "--vug2multy",
        type=float,
        dest="vug2_multy",
        help="Random vugs transmissibility multiplier in y- direction",
        required=False,
    )
    parser.add_argument(
        "--vug2MULTPV",
        "--vug2multpv",
        type=float,
        dest="vug2_multpv",
        help="Random vugs pore volume multiplier",
        required=False,
    )
    parser.add_argument(
        "--vug2SWATINIT",
        "--vug2swatinit",
        type=float,
        dest="vug2_swatinit",
        help="Random vugs initial water saturation",
        required=False,
    )
    parser.add_argument(
        "--vug2FIPNUM",
        "--vug2fipnum",
        type=int,
        dest="vug2_fipnum",
        help="Random vugs FIPNUM",
        required=False,
    )
    parser.add_argument(
        "--vug2SATNUM",
        "--vug2satnum",
        type=int,
        dest="vug2_satnum",
        help="Random vugs SATNUM",
        required=False,
    )

    # Vug3 - Near streak vugs
    parser.add_argument(
        "--distanceVug3ToStreak",
        type=int,
        dest="vug3_distance_to_streak",
        help="Number of cells between streak and vugs, "
        "put 0 to allow connection to streak",
        required=False,
    )
    parser.add_argument(
        "--vug3Volume",
        "--VUG3VOLUME",
        "--vug3volume",
        nargs=2,
        type=float,
        metavar=["Min", "Max"],
        dest="vug3_fraction",
        help="Volume fraction of near fracture vugs, between 0 and 1",
        required=False,
    )
    parser.add_argument(
        "--vug3Spread",
        "--VUG3SPREAD",
        "--vug3_spread",
        type=float,
        dest="vug3_spread",
        help="Spreading factor of near streak vug",
        required=False,
    )
    parser.add_argument(
        "--vug3Poro",
        "--VUG3PORO",
        "--vug3Poro",
        nargs=2,
        type=float,
        metavar=["Min", "Max"],
        dest="vug3_porosity",
        help="Near streak vugs porosity, min-max",
        required=False,
    )
    parser.add_argument(
        "--vug3perm",
        "--VUG3PERM",
        "--vug3Perm",
        nargs=2,
        type=float,
        metavar=["Min", "Max"],
        dest="vug3_permeability",
        help="Near streak vugs permeability, min-max",
        required=False,
    )
    parser.add_argument(
        "--vug3MULTX",
        "--vug3multx",
        type=float,
        dest="vug3_multx",
        help="Near streak vugs transmissibility multiplier in x- direction",
        required=False,
    )
    parser.add_argument(
        "--vug3MULTY",
        "--vug3multy",
        type=float,
        dest="vug3_multy",
        help="Near streak vugs transmissibility multiplier in y- direction",
        required=False,
    )
    parser.add_argument(
        "--vug3MULTPV",
        "--vug3multpv",
        type=float,
        dest="vug3_multpv",
        help="Near streak vugs pore volume multiplier",
        required=False,
    )
    parser.add_argument(
        "--vug3SWATINIT",
        "--vug3swatinit",
        type=float,
        dest="vug3_swatinit",
        help="Near streak vugs initial water saturation",
        required=False,
    )
    parser.add_argument(
        "--vug3FIPNUM",
        "--vug3fipnum",
        type=int,
        dest="vug3_fipnum",
        help="Near streak vugs FIPNUM",
        required=False,
    )
    parser.add_argument(
        "--vug3SATNUM",
        "--vug3satnum",
        type=int,
        dest="vug3_satnum",
        help="Near streak vugs SATNUM",
        required=False,
    )


def fill_parser(parser):
    """
    Build argparse for casegen_upcars, parse it and return to main program
    """
    # Required arguments
    parser.add_argument(
        "config_file", help="Configuration file with all default values"
    )

    # Geometry
    parser.add_argument(
        "--top",
        "--depth",
        type=float,
        dest="top_depth",
        required=False,
        help="Top of the model",
    )
    parser.add_argument(
        "--radiusX",
        "--radius_x",
        type=float,
        dest="radius_x",
        required=False,
        help="Curvature radius in x-direction, for dome/hull shape",
    )
    parser.add_argument(
        "--radiusY",
        "--radius_y",
        type=float,
        dest="radius_y",
        required=False,
        help="Curvature radius in y-direction, for dome/hull shape",
    )
    parser.add_argument(
        "--radiusZ",
        "--radius_z",
        type=float,
        dest="radius_z",
        required=False,
        help="Curvature radius in z-direction, for dome/hull shape, "
        "set to zero for slab",
    )
    parser.add_argument(
        "--centroidX",
        "--centroid_x",
        type=float,
        dest="centroid_x",
        required=False,
        help="Fractional number to specify center of curvature in X-direction",
    )
    parser.add_argument(
        "--centroidY",
        "--centroid_y",
        type=float,
        dest="centroid_y",
        required=False,
        help="Fractional number to specify center of curvature in Y-direction",
    )

    parser.add_argument(
        "--originX",
        "--origin_x",
        type=float,
        dest="origin_x",
        required=False,
        help="Origin coordinate of model in X-direction",
    )

    parser.add_argument(
        "--originXPos",
        "--origin_x_pos",
        type=float,
        dest="origin_x_pos",
        required=False,
        help="Origin position as fraction of model size in X-direction",
    )

    parser.add_argument(
        "--originY",
        "--origin_y",
        type=float,
        dest="origin_y",
        required=False,
        help="Origin coordinate of model in Y-direction",
    )

    parser.add_argument(
        "--originYPos",
        "--origin_y_pos",
        type=float,
        dest="origin_y_pos",
        required=False,
        help="Origin position as fraction of model size in Y-direction",
    )

    parser.add_argument(
        "--originTop",
        "--origin_top",
        type=float,
        dest="origin_top",
        required=False,
        help="Origin top depth",
    )

    parser.add_argument(
        "--rotation",
        type=float,
        dest="rotation",
        required=False,
        help="Cell coordinate rotation in degree",
    )

    parser.add_argument(
        "--tilt",
        type=float,
        dest="tilt",
        required=False,
        help="Tilting angle in degree",
    )

    # Background matrix
    parser.add_argument(
        "--matrix_nz",
        type=int,
        dest="background_nz",
        help="Total number of cells in z-direction, including streaks",
        required=False,
    )
    parser.add_argument(
        "--matrix_dz",
        type=float,
        dest="background_dz",
        help="Cell size in z-direction",
        required=False,
    )
    parser.add_argument(
        "--matrix_poro",
        type=float,
        dest="background_poro",
        help="Porosity for background matrix.",
        required=False,
    )
    parser.add_argument(
        "--matrix_perm",
        type=float,
        dest="background_perm",
        help="Permeability for background matrix.",
        required=False,
    )
    parser.add_argument(
        "--matrix_multx",
        type=float,
        dest="background_multx",
        help="X-direction transmissibility multiplier for background matrix.",
        required=False,
    )
    parser.add_argument(
        "--matrix_multy",
        type=float,
        dest="background_multy",
        help="Y-direction transmissibility multiplier for background matrix.",
        required=False,
    )
    parser.add_argument(
        "--matrix_multpv",
        type=float,
        dest="background_multpv",
        help="Pore volume multiplier for background matrix.",
        required=False,
    )
    parser.add_argument(
        "--matrix_fipnum",
        type=int,
        dest="background_fipnum",
        help="FIPNUM for background matrix.",
        required=False,
    )
    parser.add_argument(
        "--matrix_satnum",
        type=int,
        dest="background_satnum",
        help="SATNUM for background matrix.",
        required=False,
    )
    parser.add_argument(
        "--matrix_swatinit",
        type=float,
        dest="background_swatinit",
        help="Initial water saturation for background matrix.",
        required=False,
    )

    # Streak
    parser.add_argument(
        "--no_streak",
        action="store_true",
        dest="no_streak",
        required=False,
        help="Remove all streaks setting",
    )

    parser.add_argument(
        "--streak_k",
        type=int,
        nargs="+",
        dest="streak_k",
        help="Streak starting location (k-index). Specify for each streak",
        required=False,
    )
    parser.add_argument(
        "--streak_nz",
        type=int,
        nargs="+",
        dest="streak_nz",
        help="Number of cells in z-direction for each streak. "
        "Can be one value for all streaks or specified for each streak",
        required=False,
    )
    parser.add_argument(
        "--streak_dz",
        type=float,
        nargs="+",
        dest="streak_dz",
        help=(
            "Cell size in z-direction for each streak. "
            "Can be one value for all streaks or specified for each streak"
        ),
        required=False,
    )
    parser.add_argument(
        "--streak_poro",
        type=float,
        nargs="+",
        dest="streak_poro",
        help="Porosity for each streak. Can be one value for all streaks "
        "or specified for each streak",
        required=False,
    )
    parser.add_argument(
        "--streak_perm",
        type=float,
        nargs="+",
        dest="streak_perm",
        help="Permeability for each streak. Can be one value for all streaks or "
        "specified for each streak",
        required=False,
    )
    parser.add_argument(
        "--streak_multx",
        type=float,
        nargs="+",
        dest="streak_multx",
        help="X-direction transmissibility multiplier for each streak. "
        "Can be one value for all streaks or specified for each streak",
        required=False,
    )
    parser.add_argument(
        "--streak_multy",
        type=float,
        nargs="+",
        dest="streak_multy",
        help="Y-direction transmissibility multiplier for each streak. "
        "Can be one value for all streaks or specified for each streak",
        required=False,
    )
    parser.add_argument(
        "--streak_multpv",
        type=float,
        nargs="+",
        dest="streak_multpv",
        help="Pore volume multiplier for each streak. "
        "Can be one value for all streaks or specified for each streak",
        required=False,
    )
    parser.add_argument(
        "--streak_fipnum",
        type=int,
        nargs="+",
        dest="streak_fipnum",
        help="FIPNUM for each streak. Can be one value for all streaks or "
        "specified for each streak",
        required=False,
    )
    parser.add_argument(
        "--streak_satnum",
        type=int,
        nargs="+",
        dest="streak_satnum",
        help="SATNUM for each streak. Can be one value for all streaks or "
        "specified for each streak",
        required=False,
    )
    parser.add_argument(
        "--streak_swatinit",
        type=float,
        nargs="+",
        dest="streak_swatinit",
        help="Initial water saturation for each streak. Can be one value "
        "for all streaks or specified for each streak",
        required=False,
    )
    parser.add_argument(
        "--streak_box",
        action="append",
        type=int,
        nargs="+",
        dest="streak_box",
        metavar=["i1", "i2", "j1", "j2"],
        help="Specify streak region (i1, i2, j1, j2)",
        required=False,
    )

    parser.add_argument(
        "--throw",
        action="append",
        type=float,
        nargs="+",
        dest="throws",
        metavar=["i1", "i2", "j1", "j2", "shift"],
        help="Specify throw region and shift in z-direction (i1, i2, j1, j2, shift)",
        required=False,
    )
    parser.add_argument(
        "--no_throw",
        action="store_true",
        dest="no_throw",
        required=False,
        help="Remove all throws setting",
    )

    parser.add_argument(
        "--debug_model",
        type=str,
        dest="debug_model",
        help="Create a consolidated grid model to be used for debugging in ResInsight",
    )
    parser.add_argument(
        "--seed",
        "--SEED",
        "--Seed",
        type=int,
        dest="seed",
        required=False,
        help="Seed for random number generation",
    )

    # General
    parser.add_argument(
        "--et",
        "--ET",
        "--eclTemplate",
        type=str,
        dest="eclipse_template",
        required=False,
        help="Eclipse template data file",
    )
    parser.add_argument(
        "--base",
        "--BASE",
        type=str,
        dest="base_name",
        required=False,
        help="Base name of generated simulation data file",
    )

    # Geometry
    # GRID PARAMETERS
    # Number of grid cells per matrix block in each direction -
    # add as many matrix blocks as needed by extending vector
    parser.add_argument(
        "--nMatrixX",
        "--NMATRIXX",
        "--nMatrixX",
        nargs="+",
        type=int,
        dest="cell_matrix_x",
        help="Number of matrix/main element grid cells, x-direction. "
        "Specify for each block",
        required=False,
    )
    parser.add_argument(
        "--nMatrixY",
        "--NMATRIXY",
        "--nMatrixY",
        nargs="+",
        type=int,
        dest="cell_matrix_y",
        help="Number of matrix/main element grid cells, x-direction. "
        "Specify for each block",
        required=False,
    )

    # General grid dimensions
    parser.add_argument(
        "--dx",
        "--DX",
        "--incX",
        type=float,
        dest="dx",
        help="Increment in x-direction",
        required=False,
    )
    parser.add_argument(
        "--dy",
        "--DY",
        "--incY",
        type=float,
        dest="dy",
        help="Increment in y-direction",
        required=False,
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + __version__ + ")",
    )

    fill_parser_vugs(parser)
    fill_parser_fracture(parser)

    # OPTIONAL
    parser.add_argument(
        "--var",
        "--VAR",
        "--Var",
        dest="variables",
        help="Assign optional variables",
        required=False,
        action="append",
        metavar=["Variable", "Value"],
        nargs=2,
    )

    parser.set_defaults(
        no_throw=None,
        no_boundary=None,
        with_boundary=None,
        vug1_allow_connection_to_fracture=None,
        vug1_disallow_connection_to_fracture=None,
    )
    return parser
