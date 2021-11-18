"""Test functions for complot."""

from subscript.complot import complot
from ecl.summary import EclSum
from matplotlib import rcParams
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas._testing import assert_frame_equal

inputfile = """
DATAFILE
  testfile.DATA
  testfile_advanced_wells.DATA
--Some arbitrary comments here.
/
WELLFILE
  testfile.SCH
  testfile_advanced.wells
/
INFORMATION
-- Some random content
  WELL 1 2-6 7-11 12-16 1000
/
CASENAME
  testfile.case
/

OUTPUTFILE
  a_sample_output_file.org
/
"""

wellfile = """
--- This is a test schedule file for complot.
COMPDAT
--well i  j  k1 k2 stat. sn     T        ID    KH     s  D
  WELL 1  2  5  5  OPEN  1*  10000.0  0.216  50.0 -10.0  0 /
/
WELSEGS
--well   D    L  Vol  Type  Comp.  Mod.
  WELL 0.0  0.0   1*   ABS    HFA    HO /
-- Tubing segment
-- seg1  seg2   brn  seg0    len   dep.      id   eps
      2     2     1     1  500.0  500.0   0.157  1e-4 /
-- Device segment
      3     3     1     2  250.1  250.1   0.160  1e-4 /
      4     4     1     3  500.1  500.1   0.160  1e-4 /
-- Annulus segment
      5     5     1     3  250.2  250.2   0.163  1e-4 /
      6     6     1     5  300.2  300.2   0.163  1e-4 /
      7     7     1     6  500.2  500.2   0.163  1e-4 /
/
COMPSEGS
--well
  WELL /
-- i  j  k  brn  start    end  dir.
   1  2  5    1    0.0  501.0     Z /
/
"""

datafile = """
PATHS
 'ECL' '../include/schedule' /
/
"""


def test_update_fonts():
    """
    Tests the update_fonts function in complot.
    """

    family = "DejaVu Serif"
    size = 8
    complot.update_fonts(size=8)
    assert rcParams["font.family"] == [family]
    assert rcParams["font.size"] == size


def test_format_subplot():
    """
    Tests the format_subplot function in completor.
    """

    plt.figure(num=1)
    ax = plt.gca()
    title = "myplot"
    xlabel = "myxaxis"
    ylabel = "myylabel"
    xlim = [0.0, 100.0]
    ylim = [5.0, 10.0]

    complot.format_subplot(ax, title, xlabel, ylabel, xlim, ylim)
    assert ax.get_title() == title
    assert ax.xaxis.get_label().get_text() == xlabel
    assert ax.yaxis.get_label().get_text() == ylabel
    assert ax.get_xlim() == (0.0, 100.0)
    assert ax.get_ylim() == (5.0, 10.0)


def test_segmentplot_datafile_kw():
    """
    Tests the datafile_kw() method in the complot SegmentPlot class
    """

    classinst = complot.SegmentPlot(inputfile)
    classinst.data_file == ["testfile.DATA", "testfile_advanced_wells.DATA"]


def test_SegmentPlot_casename_kw():
    """
    Tests the datafile_kw() method in the complot SegmentPlot class.
    """

    classinst = complot.SegmentPlot(inputfile)
    classinst.case_name == "testfile.case"


def test_read_wellfile():
    """
    Tests the method read_well_file() in the SegmentPlot class.
    """

    welsegsheader_columns = [
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
    welsegsheader_true = pd.DataFrame(
        [
            [
                "WELL",
                "0.0",
                "0.0",
                "1*",
                "ABS",
                "HFA",
                "HO",
                "1*",
                "1*",
                "1*",
                "1*",
                "1*",
            ]
        ],
        columns=welsegsheader_columns,
    )
    welsegstable_columns = [
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
    welsegstable_true = pd.DataFrame(
        [
            [
                "2",
                "2",
                "1",
                "1",
                "500.0",
                "500.0",
                "0.157",
                "1e-4",
                "1*",
                "1*",
                "1*",
                "1*",
                "1*",
                "1*",
                "1*",
            ],
            [
                "3",
                "3",
                "1",
                "2",
                "250.1",
                "250.1",
                "0.160",
                "1e-4",
                "1*",
                "1*",
                "1*",
                "1*",
                "1*",
                "1*",
                "1*",
            ],
            [
                "4",
                "4",
                "1",
                "3",
                "500.1",
                "500.1",
                "0.160",
                "1e-4",
                "1*",
                "1*",
                "1*",
                "1*",
                "1*",
                "1*",
                "1*",
            ],
            [
                "5",
                "5",
                "1",
                "3",
                "250.2",
                "250.2",
                "0.163",
                "1e-4",
                "1*",
                "1*",
                "1*",
                "1*",
                "1*",
                "1*",
                "1*",
            ],
            [
                "6",
                "6",
                "1",
                "5",
                "300.2",
                "300.2",
                "0.163",
                "1e-4",
                "1*",
                "1*",
                "1*",
                "1*",
                "1*",
                "1*",
                "1*",
            ],
            [
                "7",
                "7",
                "1",
                "6",
                "500.2",
                "500.2",
                "0.163",
                "1e-4",
                "1*",
                "1*",
                "1*",
                "1*",
                "1*",
                "1*",
                "1*",
            ],
        ],
        columns=welsegstable_columns,
    )
    welsegstable_true = welsegstable_true.astype(
        {
            "TUBINGSEGMENT": np.int32,
            "TUBINGSEGMENT2": np.int32,
            "TUBINGBRANCH": np.int32,
            "TUBINGOUTLET": np.int32,
            "TUBINGMD": np.float64,
            "TUBINGTVD": np.float64,
        }
    )
    compsegstable_columns = [
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
    compsegstable_true = pd.DataFrame(
        [[1, 2, 5, 1, 0.0, 501.0, "Z", "1*", "1*", "1*", "1*"]],
        columns=compsegstable_columns,
    )
    compsegstable_true = compsegstable_true.astype(
        {
            "I": np.int32,
            "J": np.int32,
            "K": np.int32,
            "BRANCH": np.int32,
            "STARTMD": np.float64,
            "ENDMD": np.float64,
        }
    )
    compdattable_columns = [
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
    compdattable_true = pd.DataFrame(
        [
            [
                "WELL",
                1,
                2,
                5,
                5,
                "OPEN",
                "1*",
                10000.0,
                "0.216",
                50.0,
                "-10.0",
                "0",
                "1*",
                "1*",
            ]
        ],
        columns=compdattable_columns,
    )
    compdattable_true = compdattable_true.astype(
        {
            "I": np.int32,
            "J": np.int32,
            "K": np.int32,
            "K2": np.int32,
        }
    )
    classinst = complot.SegmentPlot(inputfile)
    classinst.read_well_file(wellfile)
    welsegsheader = classinst.welsegs_header[0]
    welsegstable = classinst.welsegs_table[0]
    compsegstable = classinst.compsegs_table[0]
    compdattable = classinst.compdat_table
    assert_frame_equal(welsegsheader.content, welsegsheader_true)
    assert_frame_equal(welsegstable.content, welsegstable_true)
    assert_frame_equal(compsegstable.content, compsegstable_true)
    assert_frame_equal(compdattable, compdattable_true)


def test_clean_trailing():
    """
    Tests the clean_trailing method in the SegmentPlot class.
    """

    classinst = complot.SegmentPlot(inputfile)
    mystr_spc = " This is a string with trailing spaces "
    mystr_tab = "\t This is a string with trailing tabs \t"
    mystr_nln = "\n This is a string with trailing newlines \n"

    spc = classinst.clean_trailing(mystr_spc)
    assert spc == "Thisisastringwithtrailingspaces"
    tab = classinst.clean_trailing(mystr_tab)
    assert tab == "Thisisastringwithtrailingtabs"
    nln = classinst.clean_trailing(mystr_nln)
    assert nln == "Thisisastringwithtrailingnewlines"


def test_relative_path():
    """
    Tests the relative_path method in the SegmentPlot class.
    """

    classinst = complot.SegmentPlot(inputfile)
    relativepath_true = "../include/schedule"
    relativepath = classinst.relative_path(datafile)
    assert relativepath["ECL"] == relativepath_true


def test_wellfile_kw():
    """
    Tests the wellfile_kw method in the SegmentPlot class.
    """

    classinst = complot.SegmentPlot(inputfile)
    assert classinst.well_file == ["testfile.SCH", "testfile_advanced.wells"]


def test_outputfile_kw():
    """
    Tests the outputfile_kw method in the SegmentsPlot class.
    """

    classinst = complot.SegmentPlot(inputfile)
    assert classinst.output_file == "a_sample_output_file.org"


def test_information_kw():
    """
    Tests the information_kw method in the SegmentsPlot class.
    """

    classinst = complot.SegmentPlot(inputfile)
    info_columns = [
        "WELL",
        "LATERAL",
        "TUBINGSEGMENT",
        "DEVICESEGMENT",
        "ANNULUSSEGMENT",
        "DAYS",
    ]
    info_true = pd.DataFrame(
        [["WELL", "1", "2-6", "7-11", "12-16", "1000"]], columns=info_columns
    )
    info_true = info_true.astype(
        {
            "WELL": np.str,
            "LATERAL": np.int32,
            "TUBINGSEGMENT": np.str,
            "DEVICESEGMENT": np.str,
            "ANNULUSSEGMENT": np.str,
            "DAYS": np.str,
        }
    )
    info = classinst.information
    assert_frame_equal(info, info_true)


def test_get_info_perwell():
    """
    Tests the get_info_perwell method in the SegmentsPlot class.
    """

    well = "WELL"
    lateral = 1
    classinst = complot.SegmentPlot(inputfile)
    tubing_segment, device_segment, annulus_segment, days = classinst.get_info_perwell(
        well, lateral
    )
    assert all([a == b for a, b in zip(tubing_segment, [2, 3, 4, 5, 6])])
    assert all([a == b for a, b in zip(device_segment, [7, 8, 9, 10, 11])])
    assert all([a == b for a, b in zip(annulus_segment, [12, 13, 14, 15, 16])])
    assert days == 1000


def test_get_trajectory():
    """
    Tests the get_trajectory method in the SegmentsPlot class.
    """

    well = "WELL"
    tubing_segment = [2]
    classinst = complot.SegmentPlot(inputfile)
    classinst.read_well_file(wellfile)
    welsegs = classinst.get_trajectory(well, tubing_segment)
    welsegs_true = pd.DataFrame([[500.0, 500.0]], columns=["TUBINGMD", "TUBINGTVD"])
    assert_frame_equal(welsegs, welsegs_true)


def test_get_packer():
    """
    Tests the get_packer method in the SegmentsPlot class.
    """

    well = "WELL"
    annulus_segment = [5, 6, 7]
    classinst = complot.SegmentPlot(inputfile)
    classinst.read_well_file(wellfile)
    packer_segments, annulus_segments = classinst.get_packer(well, annulus_segment)
    packer_columns = ["PACKERMD", "PACKERTVD"]
    annulus_columns = ["SEGMENT", "MD", "ANNULUS_ZONE"]
    packer_true = pd.DataFrame([[250.2, 250.2], [500.2, 500.2]], columns=packer_columns)
    annulus_true = pd.DataFrame(
        [[5, 250.2, 1], [6, 300.2, 1], [7, 500.2, 1]], columns=annulus_columns
    )
    annulus_true = annulus_true.astype({"SEGMENT": np.int32, "ANNULUS_ZONE": np.int32})
    assert_frame_equal(packer_segments, packer_true)
    assert_frame_equal(annulus_segments, annulus_true)


def test_get_dayindex(capfd):
    """
    Tests the get_dayindex method in the SegmentsPlot class.
    """

    list_of_days = [1, 2, 3, 4]
    classinst = complot.SegmentPlot(inputfile)
    classinst.eclipse_days = np.array([1, 3, 5, 7])
    day_idx = classinst.get_dayindex(list_of_days)
    assert all([a == b for a, b in zip(day_idx, [0, 0, 1, 1])])
    output_true = (
        "Warning: No exact day is found in Eclipse for 2 "
        + ". The program uses the closest day.\n"
        + "Warning: No exact day is found in Eclipse for 4 . "
        + "The program uses the closest day.\n"
    )
    out, err = capfd.readouterr()
    assert out == output_true


def test_get_md():
    """
    Tests the method get_md in the SegmentsPlot class.
    """
    welsegs_columns = [
        "WELL",
        "Segment",
        "MD",
        "DIAMETER",
        "STARTMD",
        "ENDMD",
        "I",
        "J",
        "K",
        "CF",
        "KH",
    ]
    welsegs_tubing = pd.DataFrame(
        [["WELL", 2, 500.0, 0.157, 0.0, 501.0, 1, 2, 5, 10000.0, 50.0]],
        columns=welsegs_columns,
    )
    welsegs_tubing = welsegs_tubing.astype({"Segment": np.int32})
    welsegs_device = pd.DataFrame(
        [
            ["WELL", 3, 250.1, 0.16, 0.0, 501.0, 1, 2, 5, 10000.0, 50.0],
            ["WELL", 4, 500.1, 0.16, 0.0, 501.0, 1, 2, 5, 10000.0, 50.0],
        ],
        columns=welsegs_columns,
    )
    welsegs_device = welsegs_device.astype({"Segment": np.int32})
    welsegs_annulus = pd.DataFrame(
        [
            ["WELL", 5, 250.2, 0.163, 0.0, 501.0, 1, 2, 5, 10000.0, 50.0],
            ["WELL", 6, 300.2, 0.163, 0.0, 501.0, 1, 2, 5, 10000.0, 50.0],
            ["WELL", 7, 500.2, 0.163, 0.0, 501.0, 1, 2, 5, 10000.0, 50.0],
        ],
        columns=welsegs_columns,
    )
    welsegs_annulus = welsegs_annulus.astype({"Segment": np.int32})
    well = "WELL"
    lateral = 1
    segment = [2]
    section = "tubing"
    classinst = complot.SegmentPlot(inputfile)
    classinst.read_well_file(wellfile)
    welsegs = classinst.get_md(well, segment, lateral, section)
    assert_frame_equal(welsegs, welsegs_tubing)
    segment = [3, 4]
    section = "device"
    welsegs = classinst.get_md(well, segment, lateral, section)
    assert_frame_equal(welsegs, welsegs_device)
    segment = [5, 6, 7]
    section = "annulus"
    welsegs = classinst.get_md(well, segment, lateral, section)
    assert_frame_equal(welsegs, welsegs_annulus)


def test_get_well_profile():
    """
    Tests the method get_well_profile in the SegmentPlot class.
    """

    classinst = complot.SegmentPlot(inputfile)
    classinst.eclipse = EclSum("tests/data/TEST.DATA")
    classinst.eclipse_days = np.asarray(classinst.eclipse.days)
    classinst.eclipse_dates = classinst.eclipse.dates
    classinst.get_well_profile("WELL")
    well_columns = [
        "DAY",
        "DATE",
        "WBHP",
        "WOPR",
        "WWPR",
        "WGPR",
        "WWCT",
        "WGOR",
        "WLPR",
    ]
    well_true = pd.DataFrame(
        [
            [
                0.0,
                "2000-01-01",
                700.787964,
                0.0,
                0.000000,
                0.000,
                0.000000,
                0.000000,
                0.000000,
            ],
            [
                1.0,
                "2000-01-02",
                611.844543,
                1000.0,
                16.344187,
                628494.375,
                0.016081,
                628.494385,
                1016.344187,
            ],
        ],
        columns=well_columns,
    )
    well_true["DATE"] = pd.to_datetime(well_true["DATE"], format="%Y-%m-%d")
    classinst.df_well = classinst.df_well.round({"WWCT": 6})
    assert_frame_equal(classinst.df_well, well_true)


def test_get_data():
    """
    Tests the method get_data in the SegmentPlot class.
    """

    classinst = complot.SegmentPlot("tests/data/test.plot")
    classinst.main()
    output_df = classinst.df_output
    columns_true = [
        "WELL",
        "SECTION",
        "DATE",
        "SEGMENT",
        "MD",
        "STARTMD",
        "ENDMD",
        "CF",
        "KH",
        "THICKNESS",
        "DIAMETER",
        "SPR",
        "SPRD",
        "SOFR",
        "SWFR",
        "SGFRF",
        "SWCT",
        "SGOR",
        "AREA_10CM",
        "OIL_VELOCITY",
        "OIL_VELOCITY_M/S_10CM",
        "SOFR_M",
        "WATER_VELOCITY",
        "WATER_VELOCITY_M/S_10CM",
        "SWFR_M",
        "GAS_VELOCITY",
        "GAS_VELOCITY_M/S_10CM",
        "SGFRF_M",
    ]
    first_line_true = [
        "WELL",
        "Device",
        "2000-01-02",
        37,
        256.060,
        228.46,
        283.46,
        1.000000e-10,
        1.000000e-10,
        55.00,
        0.127,
        696.991638,
        84.671112,
        67.068817,
        0.017528,
        1.443411e02,
        0.000261,
        2.152134e00,
        0.039898,
        1680.997445,
        0.019456,
        1.219433,
        0.439319,
        0.000005,
        0.000319,
        3617.731705,
        0.041872,
        2.624383,
    ]
    first_line_true = pd.DataFrame([first_line_true], columns=columns_true)
    first_line_true["DATE"] = pd.to_datetime(first_line_true["DATE"], format="%Y-%m-%d")
    first_line = output_df.head(1)
    first_line = first_line.round(
        {"SWCT": 6, "WATER_VELOCITY_M/S_10CM": 6, "SWFR_M": 6}
    )
    first_line_true = first_line_true.astype({"SEGMENT": np.int32})
    assert all([a == b for a, b in zip(output_df.columns, columns_true)])
    assert_frame_equal(first_line, first_line_true)
