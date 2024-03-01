"""Test the fmuobs writers, these convert from the internal dataframe
representation to various other formats, csv, ert-observations format,
resinsight and yaml (webviz)"""

import datetime

import numpy as np
import pandas as pd
import pytest
from subscript.fmuobs.parsers import ertobs2df
from subscript.fmuobs.writers import (
    block_df2obsdict,
    convert_dframe_date_to_str,
    df2ertobs,
    df2obsdict,
    df2resinsight_df,
    dfblock2ertobs,
    dfgeneral2ertobs,
    dfhistory2ertobs,
    dfsummary2ertobs,
    summary_df2obsdict,
)


# dfsummary2ertobs
@pytest.mark.parametrize(
    "obs_df, expected_str",
    [
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "LABEL": "WOPR:OP1",
                        "DATE": "2025-06-01",
                        "VALUE": 2222.3,
                        "ERROR": 100,
                        "COMMENT": "FOO BAR\ndontcrash",
                    },
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "LABEL": "WOPR:OP2",
                        "DATE": "2026-01-01",
                        "VALUE": 222.3,
                        "ERROR": 10,
                    },
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "LABEL": "FOPT",
                        "RESTART": 32,
                        "VALUE": 2033320,
                        "ERROR": 1000,
                    },
                    {
                        # This is not SUMMARY and is ignored.
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "RFT_2006_OP1",
                        "DATE": "1986-04-05",
                        "VALUE": 100,
                        "K": 4,
                    },
                ]
            ),
            """SUMMARY_OBSERVATION WOPR:OP1
{
    -- FOO BAR
    -- dontcrash
    DATE = 2025-06-01;
    VALUE = 2222.3;
    ERROR = 100.0;
};
SUMMARY_OBSERVATION WOPR:OP2
{
    DATE = 2026-01-01;
    VALUE = 222.3;
    ERROR = 10.0;
};
SUMMARY_OBSERVATION FOPT
{
    RESTART = 32.0;
    VALUE = 2033320.0;
    ERROR = 1000.0;
};
""",
        )
    ],
)
def test_dfsummary2ertobs(obs_df, expected_str):
    """Test that we can generate ERT summary observation text format
    from the internal dataframe representation"""
    assert dfsummary2ertobs(obs_df).strip() == expected_str.strip()

    # Should be able to go back again also for
    # a subset, but the comments are not attempted parsed:
    obs_df["DATE"] = pd.to_datetime(obs_df["DATE"])
    pd.testing.assert_frame_equal(
        ertobs2df(expected_str),
        obs_df[obs_df["CLASS"] == "SUMMARY_OBSERVATION"]
        .dropna(axis="columns", how="all")
        .drop("COMMENT", axis=1, errors="ignore"),
        # We relax int/float problems as long as the values are equal:
        check_dtype=False,
    )


# dfblock2ertobs:
@pytest.mark.parametrize(
    "obs_df, expected_str",
    [
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "RFT_2006_OP1",
                        "DATE": "1986-04-05",
                        "OBS": "P1",
                    },
                ]
            ),
            """BLOCK_OBSERVATION RFT_2006_OP1
{
    DATE = 1986-04-05;
    OBS P1 {};
};
""",
        ),
        ############################################################
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "RFT_2006_OP1",
                        "DATE": "1986-04-05",
                        "OBS": "P1",
                        "COMMENT": "FOO",
                        "SUBCOMMENT": "bza",
                    },
                ]
            ),
            """BLOCK_OBSERVATION RFT_2006_OP1
{
    -- FOO
    DATE = 1986-04-05;
    -- bza
    OBS P1 {};
};
""",
        ),
        ############################################################
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "RFT_2006_OP1",
                        "DATE": "1986-04-05",
                        "OBS": "P1",
                        "COMMENT": "FOO\ndontcrash",
                        "SUBCOMMENT": "bza",
                    },
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "RFT_2006_OP1",
                        "DATE": "1986-04-05",
                        "OBS": "P2",
                        "COMMENT": "FOO",
                        "SUBCOMMENT": "bzarrr\ndonterror!",
                    },
                ]
            ),
            """BLOCK_OBSERVATION RFT_2006_OP1
{
    -- FOO
    -- dontcrash
    DATE = 1986-04-05;
    -- bza
    OBS P1 {};
    -- bzarrr
    -- donterror!
    OBS P2 {};
};
""",
        ),
        ############################################################
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "RFT_SWAT_2006_OP1",
                        "FIELD": "SWAT",
                        "DATE": datetime.date(1900, 1, 1),
                        "OBS": "P1",
                        "I": 1,
                        "J": 2,
                        "NOTINCLUDED": "SKIPME",
                    },
                ]
            ),
            """BLOCK_OBSERVATION RFT_SWAT_2006_OP1
{
    FIELD = SWAT;
    DATE = 1900-01-01;
    OBS P1 { I = 1; J = 2;};
};
""",
        ),
    ],
)
def test_dfblock2ertobs(obs_df, expected_str):
    """Test generating BLOCK_OBSERVATION ert observation from dataframe
    format"""
    assert dfblock2ertobs(obs_df).strip() == expected_str.strip()


# dfhistory2ertobs:
@pytest.mark.parametrize(
    "obs_df, expected_str",
    [
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "HISTORY_OBSERVATION",
                        "LABEL": "WOPR:P1",
                    }
                ]
            ),
            "HISTORY_OBSERVATION WOPR:P1;",
        ),
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "HISTORY_OBSERVATION",
                        "LABEL": "WOPR:P1",
                        "ERROR": 2,
                    },
                    {
                        # This is not HISTORY and should be ignored
                        "CLASS": "SUMMARY_OBSERVATION",
                        "LABEL": "FOPT",
                    },
                ]
            ),
            "HISTORY_OBSERVATION WOPR:P1 { ERROR = 2.0;};",
        ),
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "HISTORY_OBSERVATION",
                        "LABEL": "WOPR:P1",
                        "ERROR": 2,
                        "NOTINCLUDED": "SKIPPED",
                    }
                ]
            ),
            "HISTORY_OBSERVATION WOPR:P1 { ERROR = 2;};",
        ),
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "HISTORY_OBSERVATION",
                        "LABEL": "WOPR:P1",
                        "ERROR": 2,
                        "SEGMENT": "DEFAULT",
                    },
                    {
                        "CLASS": "HISTORY_OBSERVATION",
                        "LABEL": "WOPR:P1",
                        "ERROR": 4,
                        "SEGMENT": "LATE",
                    },
                ]
            ),
            "HISTORY_OBSERVATION WOPR:P1 { ERROR = 2; SEGMENT LATE { ERROR = 4;};};",
        ),
    ],
)
def test_dfhistory2ertobs(obs_df, expected_str):
    """Test making HISTORY_OBSERVATION from dataframe format"""
    # Relaxed on whitespace
    assert dfhistory2ertobs(obs_df).strip().replace("\n", "").replace(
        "  ", " "
    ) == expected_str.strip().replace("\n", "")


# dfgeneral2ertobs:
@pytest.mark.parametrize(
    "obs_df, expected_str",
    [
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "GENERAL_OBSERVATION",
                        "LABEL": "GEN_OBS1",
                        "DATA": "RFT_BH67",
                        "RESTART": 20,
                        "OBS_FILE": "some_file.txt",
                        "INDEX_LIST": "1,2,3,4",
                        "ERROR_COVAR": "e_covar.txt",
                        "SKIPME": None,
                    }
                ]
            ),
            """GENERAL_OBSERVATION GEN_OBS1 {
   DATA = RFT_BH67;
   RESTART = 20;
   OBS_FILE = some_file.txt;
   INDEX_LIST = 1,2,3,4;
   ERROR_COVAR = e_covar.txt;
};""",
        ),
    ],
)
def test_dfgeneral2ertobs(obs_df, expected_str):
    """Test making GENERAL_OBSERVATION from dataframe format"""
    # Relaxed on whitespace
    assert dfgeneral2ertobs(obs_df).strip().replace("\n", "").replace(
        "  ", " "
    ) == expected_str.strip().replace("\n", "").replace("  ", " ")


@pytest.mark.parametrize(
    "obs_df, expected_str",
    [
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "LABEL": "WOPR:OP1",
                        "DATE": "2025-01-01",
                        "VALUE": 2222.3,
                        "ERROR": 100,
                    },
                    {
                        "CLASS": "HISTORY_OBSERVATION",
                        "LABEL": "WOPR:P1",
                    },
                    # Note that order is not preserved.
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "RFT_2006_OP1",
                        "DATE": "1986-04-05",
                        "OBS": "P1",
                    },
                    {
                        "CLASS": "GENERAL_OBSERVATION",
                        "LABEL": "GEN_OBS1",
                        "DATA": "RFT_BH67",
                        "RESTART": 20,
                    },
                ]
            ),
            """
SUMMARY_OBSERVATION WOPR:OP1
{
    DATE = 2025-01-01;
    VALUE = 2222.3;
    ERROR = 100.0;
};
BLOCK_OBSERVATION RFT_2006_OP1
{
    DATE = 1986-04-05;
    OBS P1 {};
};
HISTORY_OBSERVATION WOPR:P1;
GENERAL_OBSERVATION GEN_OBS1 {
    DATA = RFT_BH67;
    RESTART = 20.0;
};""",
        ),
    ],
)
def test_df2ertobs(obs_df, expected_str):
    """Test making any kind of *OBSERVATION in ert format from dataframe format"""
    # Relaxed on whitespace
    assert df2ertobs(obs_df).strip().replace("\n", "").replace(
        "  ", " "
    ) == expected_str.strip().replace("\n", "").replace("  ", " ")


# summary_df2obsdict
@pytest.mark.parametrize(
    "obs_df, expected_list",
    [
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "KEY": "WOPR:OP1",
                        "DATE": datetime.date(2025, 1, 1),
                        "COMMENT": "foo",
                    },
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "KEY": "WOPR:OP1",
                        "DATE": datetime.date(2026, 1, 1),
                        "IGNOREME": None,
                    },
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "KEY": "WOPR:OP2",
                        "DATE": datetime.date(2026, 1, 1),
                        "VALUE": 1000,
                        "ERROR": 100,
                        "LABEL": "OP2_2026",
                        "SUBCOMMENT": "verygood",
                    },
                ]
            ),
            [
                {
                    "key": "WOPR:OP1",
                    "comment": "foo",
                    "observations": [
                        {"date": "2025-01-01"},
                        {"date": "2026-01-01"},
                    ],
                },
                {
                    "key": "WOPR:OP2",
                    "observations": [
                        {
                            "date": "2026-01-01",
                            "value": 1000.0,
                            "error": 100.0,
                            "label": "OP2_2026",
                            "comment": "verygood",
                        },
                    ],
                },
            ],
        ),
    ],
)
def test_summary_df2obsdict(obs_df, expected_list):
    """Test the summary part of the yaml/dict format. The summary_df2obsdict
    function returns a list"""
    assert summary_df2obsdict(obs_df) == expected_list


# test_block_df2obsdict()
@pytest.mark.parametrize(
    "obs_df, expected_dict",
    [
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "RFT_2006_OP1",
                        "DATE": "1986-04-05",
                        "VALUE": 100,
                        "FIELD": "PRESSURE",
                        "K": 4,
                        "COMMENT": "first well",
                        "SUBCOMMENT": "bad measurement",
                    },
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "RFT_2006_OP1",
                        "DATE": datetime.date(1986, 4, 5),
                        "VALUE": 101,
                        "K": 5,
                        # This is a required label in ERT obs, but optional here:
                        "OBS": "P2",
                    },
                ]
            ),
            [
                {
                    "well": "RFT_2006_OP1",
                    "field": "PRESSURE",
                    "comment": "first well",
                    "date": "1986-04-05",
                    "observations": [
                        {"k": 4, "value": 100, "comment": "bad measurement"},
                        {"k": 5, "value": 101, "obs": "P2"},
                    ],
                },
            ],
        ),
    ],
)
def test_block_df2obsdict(obs_df, expected_dict):
    """Test converting from dataframe representation for BLOCK/rft observations
    to the dictionary representation designed for yaml output"""
    assert block_df2obsdict(obs_df) == expected_dict


@pytest.mark.parametrize(
    "dframe, expected_dframe",
    [
        (pd.DataFrame(), pd.DataFrame()),
        (pd.DataFrame([{"date": 1}]), pd.DataFrame([{"date": 1}])),
        (pd.DataFrame([{"DATE": 1}]), pd.DataFrame([{"DATE": "1"}])),
        (
            pd.DataFrame([{"DATE": datetime.date(2020, 1, 1)}]),
            pd.DataFrame([{"DATE": "2020-01-01"}]),
        ),
        (
            pd.DataFrame([{"DATE": datetime.datetime(2020, 1, 1, 2, 3, 4)}]),
            pd.DataFrame([{"DATE": "2020-01-01 02:03:04"}]),
        ),
        (
            pd.DataFrame(
                [{"DATE": datetime.date(2020, 1, 1)}, {"DATE": np.datetime64("NaT")}]
            ),
            pd.DataFrame([{"DATE": "2020-01-01"}, {"DATE": np.nan}]),
        ),
        (
            pd.DataFrame([{"DATE": datetime.date(2020, 1, 1)}, {"DATE": np.nan}]),
            pd.DataFrame([{"DATE": "2020-01-01"}, {"DATE": np.nan}]),
        ),
        (pd.DataFrame([{"DATE": "nan"}]), pd.DataFrame([{"DATE": np.nan}])),
    ],
)
def test_convert_dframe_date_to_str(dframe, expected_dframe):
    """Test that we treat date as correct python objects in dataframes.

    This is used for generating yaml, where we want to output strings and void
    "datetime"-objects embedded in the yaml output.
    """
    pd.testing.assert_frame_equal(
        convert_dframe_date_to_str(dframe),
        expected_dframe,
    )


# df2obsdict()
@pytest.mark.parametrize(
    "obs_df, expected_dict",
    [
        (pd.DataFrame(), {}),
        (pd.DataFrame([{"FOO": "BAR"}]), {}),
        #################################################################
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "KEY": "WOPR:OP1",
                        "DATE": datetime.date(2025, 1, 1),
                    },
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "KEY": "WOPR:OP1",
                        "DATE": datetime.date(2026, 1, 1),
                    },
                ]
            ),
            {
                "smry": [
                    {
                        "key": "WOPR:OP1",
                        "observations": [
                            {"date": "2025-01-01"},
                            {"date": "2026-01-01"},
                        ],
                    }
                ]
            },
        ),
        #################################################################
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "KEY": "WOPR:OP1",
                        "DATE": "2025-01-01",
                    },
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "KEY": "WOPR:OP2",
                        "DATE": "2026-01-01",
                    },
                ]
            ),
            {
                "smry": [
                    {"key": "WOPR:OP1", "observations": [{"date": "2025-01-01"}]},
                    {"key": "WOPR:OP2", "observations": [{"date": "2026-01-01"}]},
                ]
            },
        ),
        #################################################################
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "RFT_2006_OP1",
                        "DATE": "1986-04-05",
                    },
                ]
            ),
            {
                "rft": [
                    {
                        "well": "RFT_2006_OP1",
                        "date": "1986-04-05",
                        "observations": [{}],
                    },
                ]
            },
        ),
        #################################################################
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "RFT_2006_OP1",
                        "DATE": "1986-04-05",
                        "VALUE": 100,
                        "K": 4,
                    },
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "RFT_2006_OP1",
                        "DATE": "1986-04-05",
                        "VALUE": 101,
                        "K": 5,
                    },
                ]
            ),
            {
                "rft": [
                    {
                        "well": "RFT_2006_OP1",
                        "date": "1986-04-05",
                        "observations": [
                            {"k": 4, "value": 100},
                            {"k": 5, "value": 101},
                        ],
                    },
                ]
            },
        ),
    ],
)
def test_df2obsdict(obs_df, expected_dict):
    """Test converting from dataframe representation to the dictionary
    representation designed for yaml output"""
    assert df2obsdict(obs_df) == expected_dict


# test_df2resinsight_df
@pytest.mark.parametrize(
    "obs_df, expected_ri_df",
    [
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "KEY": "WOPR:OP1",
                        "DATE": "2025-01-01",
                        "VALUE": 2222.3,
                        "ERROR": 100,
                    },
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "KEY": "WOPR:OP2",
                        "DATE": "2026-01-01",
                        "VALUE": 222.3,
                        "ERROR": 10,
                    },
                    {
                        # This row triggers a warning and is ignored.
                        "CLASS": "SUMMARY_OBSERVATION",
                        "KEY": "FOPT",
                        "RESTART": 32,
                        "VALUE": 2033320,
                        "ERROR": 1000,
                    },
                    {
                        # This row is not supported by ri, and is ignored.
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "RFT_2006_OP1",
                        "DATE": "1986-04-05",
                        "VALUE": 100,
                        "K": 4,
                    },
                ]
            ),
            pd.DataFrame(
                [
                    {
                        "DATE": "2025-01-01",
                        "VECTOR": "WOPR:OP1",
                        "VALUE": 2222.3,
                        "ERROR": 100.0,
                    },
                    {
                        "DATE": "2026-01-01",
                        "VECTOR": "WOPR:OP2",
                        "VALUE": 222.3,
                        "ERROR": 10,
                    },
                ]
            ),
        )
    ],
)
def test_df2resinsight_df(obs_df, expected_ri_df):
    """Test that we can go from internal dataframe representation
    to the resinsight dataframe representation of observations
    (which only supports a subset of ERT observations)"""
    pd.testing.assert_frame_equal(df2resinsight_df(obs_df), expected_ri_df)
