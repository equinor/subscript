"""Test the fmuobs writers, these convert from the internal dataframe
representation to various other formats, csv, ert-observations format,
resinsight and yaml (webviz)"""
import datetime

import pandas as pd

import pytest


from subscript.fmuobs.writers import (
    dfblock2ertobs,
    dfsummary2ertobs,
    dfgeneral2ertobs,
    dfhistory2ertobs,
    df2obsdict,
    df2resinsight_df,
)
from subscript.fmuobs.parsers import ertobs2df


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
                        "DATE": "2025-01-01",
                        "VALUE": 2222.3,
                        "ERROR": 100,
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
    DATE = 01/01/2025;
    VALUE = 2222.3;
    ERROR = 100.0;
};
SUMMARY_OBSERVATION WOPR:OP2
{
    DATE = 01/01/2026;
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
    # a subset:
    obs_df["DATE"] = pd.to_datetime(obs_df["DATE"])
    pd.testing.assert_frame_equal(
        ertobs2df(expected_str),
        obs_df[obs_df["CLASS"] == "SUMMARY_OBSERVATION"].dropna(
            axis="columns", how="all"
        ),
        # We relax int/float problems as long as the values are equal:
        check_dtype=False,
    )


# dfblock2ertobs:
@pytest.mark.parametrize("obs_df, expected_str",
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
    DATE = 05/04/1986;
    OBS P1 {};
};
"""),
        (
            pd.DataFrame(
                [
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "RFT_SWAT_2006_OP1",
                        "FIELD": "SWAT",
                        "DATE": datetime(1900, 1, 1),
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
    DATE = 01/01/1900;
    OBS P1 { I = 1; J = 2;};
};
"""),
        ]
)
def  test_dfblock2ertobs(obs_df, expected_str):
    print(dfblock2ertobs(obs_df))
    assert dfblock2ertobs(obs_df).strip() == expected_str.strip()


# dfhistory2ertobs:
#    writeme

# dfgeneral2ertobs:
# writeme. add test that it filters to only general obs.

# dfertobs:
# writeme
# test that it splits correctly.

# summary_df2obsdict
# block_df2obsdict

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
