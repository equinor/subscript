"""Test the fmuobs parsers, for ERT observation file, YAML and ResInsight.

They all parse and transform the data into the internal dataframe
representation."""

import datetime
import os
from pathlib import Path

import pandas as pd
import pytest
from subscript.fmuobs.parsers import (
    INCLUDE_RE,
    OBS_ARGS_RE,
    blockdictlist2df,
    ertobs2df,
    expand_includes,
    filter_comments,
    fix_dtype,
    flatten_observation_unit,
    mask_curly_braces,
    obsdict2df,
    parse_observation_unit,
    smrydictlist2df,
    split_by_sep_in_masked_string,
)
from subscript.fmuobs.writers import df2ertobs, df2obsdict


def test_expand_includes(tmp_path):
    """Test that include <filename> statements can be resolved"""
    os.chdir(tmp_path)
    Path("foo.txt").write_text("foo;", encoding="utf8")
    assert expand_includes("hallo; include foo.txt; hei") == "hallo; foo; hei"

    # Multiple files:
    Path("bar.txt").write_text("bar;", encoding="utf8")
    assert (
        expand_includes("hallo; include foo.txt; hei; include bar.txt;")
        == "hallo; foo; hei; bar;"
    )

    # Test relative directory support:
    Path("subdir").mkdir()
    (Path("subdir") / "leaf.txt").write_text("foo;", encoding="utf8")
    assert (
        expand_includes("hallo; include leaf.txt; hei", cwd="subdir")
        == "hallo; foo; hei"
    )


@pytest.mark.parametrize(
    "string, expected",
    [
        ("", ""),
        ("foo", "foo"),
        ("foo;", "foo;"),
        ("foo {}", "foo {}"),
        ("foo {};", "foo XX;"),
        ("foo \n{}\n;", "foo \nXX\n;"),
        ("foo {}; bar {};", "foo XX; bar XX;"),
        ("foo {{};};", "foo XXXXX;"),
        ("foo {DATE=01/01/2001;};", "foo XXXXXXXXXXXXXXXXXX;"),
        ("foo {A=0.1;};", "foo XXXXXXXX;"),
        ("foo {A=1e-5;};", "foo XXXXXXXXX;"),
        ("foo {A=a_b;};", "foo XXXXXXXX;"),
        ("foo {A=a,b;};", "foo XXXXXXXX;"),
        ("foo\n {\n  {};\n}\n;", "foo\n XXXXXXXXX\n;"),
        (
            "SUM WCT {DATE=01/01/2001;VALUE=1;ERROR=0.1;};",
            "SUM WCT XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX;",
        ),
        (
            "SUM SEP_1 {VALUE = 100;}; SUM SEP_2 {VALUE=200;};",
            "SUM SEP_1 XXXXXXXXXXXXXX; SUM SEP_2 XXXXXXXXXXXX;",
        ),
        (
            "BLOCK R1 {FIELD=PR; OBS P1 {I=1;}; OBS P2 {J=2;};};",
            "BLOCK R1 XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX;",
        ),
    ],
)
def test_mask_curly_braces(string, expected):
    """Test that curly braces can be masked, to facilitate splitting
    by semicolons but ignore semicolons inside curly braces"""
    assert mask_curly_braces(string) == expected


@pytest.mark.parametrize(
    "string, masked_string, expected",
    [
        ("", "", []),
        (";", ";", []),
        ("foo", "foo", ["foo"]),
        ("foo", "XXX", ["foo"]),
        ("foo;", "XXX;", ["foo"]),
        ("foo; ", "XXX; ", ["foo"]),
        ("foo {hei;};", "foo XXXXXX;", ["foo {hei;}"]),
        (
            "foo {hei;}; bar {hopp;};",
            "foo XXXXXX; bar XXXXXXX;",
            ["foo {hei;}", "bar {hopp;}"],
        ),
    ],
)
def test_split_by_sep_in_masked_string(string, masked_string, expected):
    """Test that we are able to split strings by separator positions in
    an auxiliary string"""
    assert list(split_by_sep_in_masked_string(string, masked_string)) == expected


@pytest.mark.parametrize(
    "string, expected",
    [
        ("foo\n-- hallo\nhei", "foo\nhei"),
        ("foo --a comment", "foo"),
        ("\n", ""),
        (" ", ""),
        ("foo -- hallo -- hopp", "foo"),
    ],
)
def test_filter_comments(string, expected):
    """Test that comments are properly filtered out"""
    assert filter_comments(string) == expected


@pytest.mark.parametrize(
    "string, expected",
    [
        ("", ""),
        ("1", 1),
        ("1.0", 1),
        ("1.1", 1.1),
        ("1e4", 10000),
        ("1.0e4", 10000),
        ("1.1e4", 11000),
        ("foo", "foo"),
        ("01/01/1900", datetime.datetime(1900, 1, 1)),
        ("12/24/2020", "12/24/2020"),
        ("01/12/2020", datetime.datetime(2020, 12, 1)),
        ("2020-12-01", datetime.datetime(2020, 12, 1)),
    ],
)
def test_fix_dtype(string, expected):
    """Test that values are converted to numeric when possible"""
    assert fix_dtype(string) == expected


@pytest.mark.parametrize(
    "string, filename",
    [
        ("include foo.txt;", "foo.txt"),
        ("include 'foo.txt';", "foo.txt"),
        ('include "foo.txt" ;', "foo.txt"),
        (" include    'foo.txt' ; ", "foo.txt"),
        ("include foo-bar_com.txt; ", "foo-bar_com.txt"),
        ("include føø_9-.txt;", "føø_9-.txt"),
        ("include 'hei hopp.txt';", "hei hopp.txt"),
    ],
)
def test_include_re(string, filename):
    """Test that we can deduce the filename for an include"""
    assert INCLUDE_RE.match(string).groups()[1] == filename


@pytest.mark.parametrize(
    "string, expected",
    [
        ("obs p1 {i=1; };", ("obs p1 ", "{i=1; }")),
        ("field=pressure; obs p1 {i=1; };", ("field=pressure", None)),
        ("obs p1 {i=1; }; obs p2 {i=2;};", ("obs p1 ", "{i=1; }")),
        ("value=100;", ("value=100", None)),
    ],
)
def test_obs_args_re(string, expected):
    """Test that a regular expression is able to parse and split the observation
    arguments (inside a curly brace set)"""
    assert OBS_ARGS_RE.match(string).groups() == expected


@pytest.mark.parametrize(
    "obsunit, expected",
    [
        ({"a": 1}, [{"a": 1}]),
        ({"obs a": {"b": 3}}, [{"obs": "a", "b": 3}]),
        ({"a": 1, "obs p1": {"i": 3}}, [{"a": 1, "obs": "p1", "i": 3}]),
        (
            {"a": 1, "obs p1": {"i": 3}, "obs p2": {"j": 4}},
            [
                {"a": 1, "obs": "p1", "i": 3},
                {"a": 1, "obs": "p2", "j": 4},
            ],
        ),
    ],
)
def test_flatten_observation_unit(obsunit, expected):
    """Test that a observation unit dictionary resembling the ERT observation
    file syntax can be "flattened" into a list structure more suitable for
    a tabular representation form"""
    assert flatten_observation_unit(obsunit) == expected


@pytest.mark.parametrize(
    "string, expected",
    [
        ("missingsemicolon", {}),
        ("something=0;", {"something": 0}),
        ("foo=0;bar=1", {"foo": 0}),
        ("something;", {"something": {}}),  # (missing '=' )
        (
            "field=pressure; date=now; obs p1 {i=1; };",
            {"field": "pressure", "date": "now", "obs p1": {"i": 1.0}},
        ),
        (
            "VALUE = 100; ERROR = 5; RESTART = 42; KEY  = GOPR:BRENT;",
            {"VALUE": 100, "ERROR": 5, "RESTART": 42, "KEY": "GOPR:BRENT"},
        ),
        (
            (
                "FIELD = PRESSURE; DATE  = 22/10/2006; "
                "OBS P1 { I = 1;  J = 1;  K = 1; VALUE = 100;  ERROR = 5; }; "
                "OBS P2 { I = 2;  J = 2;  K = 1;   VALUE = 101;  ERROR = 5; }; "
            ),
            {
                "FIELD": "PRESSURE",
                "DATE": datetime.datetime(2006, 10, 22, 0, 0),
                "OBS P1": {"I": 1.0, "J": 1.0, "K": 1.0, "VALUE": 100.0, "ERROR": 5.0},
                "OBS P2": {"I": 2.0, "J": 2.0, "K": 1.0, "VALUE": 101.0, "ERROR": 5.0},
            },
        ),
        (
            """   ERROR       = 0.20;
   ERROR_MODE  = RELMIN;
   ERROR_MIN   = 100;

   SEGMENT FIRST_YEAR
   {
      START = 0;
      STOP  = 10;
      ERROR = 0.50;
      ERROR_MODE = REL;
   };
            """,
            {
                "ERROR": 0.2,
                "ERROR_MODE": "RELMIN",
                "ERROR_MIN": 100.0,
                "SEGMENT FIRST_YEAR": {
                    "START": 0.0,
                    "STOP": 10.0,
                    "ERROR": 0.5,
                    "ERROR_MODE": "REL",
                },
            },
        ),
    ],
)
def test_parse_observation_unit(string, expected):
    """Test that observations in ERT observation format can be converted into
    a dictionary format (with same structure as the ERT format)"""
    assert parse_observation_unit(string) == expected


@pytest.mark.parametrize(
    "string, expected",
    [
        (";", pd.DataFrame()),
        (";", pd.DataFrame()),
        # ########################################################
        (
            (
                "SUMMARY_OBSERVATION WCT "
                "{DATE=01/04/2001;KEY=WWCT:OP1;VALUE=1;ERROR=0.1;};"
            ),
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "LABEL": "WCT",
                        "KEY": "WWCT:OP1",
                        "DATE": datetime.datetime(2001, 4, 1, 0, 0),
                        "VALUE": 1,
                        "ERROR": 0.1,
                    }
                ]
            ),
        ),
        # ########################################################
        (
            (
                "SUMMARY_OBSERVATION WCT "
                # Testing alternative date input format:
                "{DATE=01.04.2001;KEY=WWCT:OP1;VALUE=1;ERROR=0.1;};"
            ),
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "LABEL": "WCT",
                        "KEY": "WWCT:OP1",
                        "DATE": datetime.datetime(2001, 4, 1, 0, 0),
                        "VALUE": 1,
                        "ERROR": 0.1,
                    }
                ]
            ),
        ),
        # #########################################################
        (
            (
                "SUMMARY_OBSERVATION FGPT_1{"
                "VALUE=1e+10;ERROR=3.0e+8;DATE=01/01/2020;KEY=FGPT;};"
            ),
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "LABEL": "FGPT_1",
                        "KEY": "FGPT",
                        "DATE": datetime.datetime(2020, 1, 1, 0, 0),
                        "VALUE": 1e10,
                        "ERROR": 3.0e8,
                    }
                ]
            ),
        ),
        # ########################################################
        (
            (
                "SUMMARY_OBSERVATION SEP_1 {VALUE = 100;}; "
                "SUMMARY_OBSERVATION SEP_2 {VALUE=200;};"
            ),
            pd.DataFrame(
                [
                    {"CLASS": "SUMMARY_OBSERVATION", "LABEL": "SEP_1", "VALUE": 100},
                    {"CLASS": "SUMMARY_OBSERVATION", "LABEL": "SEP_2", "VALUE": 200},
                ]
            ),
        ),
        # ########################################################
        (
            "BLOCK_OBSERVATION R1 {FIELD=PR; OBS P1 {I=1;}; OBS P2 {J=2;};};",
            pd.DataFrame(
                [
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "R1",
                        "FIELD": "PR",
                        "OBS": "P1",
                        "I": 1,
                    },
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "LABEL": "R1",
                        "FIELD": "PR",
                        "OBS": "P2",
                        "J": 2,
                    },
                ]
            ),
        ),
        # ########################################################
        (
            "HISTORY_OBSERVATION WOPR:P1;",
            pd.DataFrame(
                [
                    {
                        "CLASS": "HISTORY_OBSERVATION",
                        "LABEL": "WOPR:P1",
                    }
                ]
            ),
        ),
        # ########################################################
        (
            "HISTORY_OBSERVATION WOPR:P1 {};",  # NB: Empty {}
            pd.DataFrame(
                [
                    {
                        "CLASS": "HISTORY_OBSERVATION",
                        "LABEL": "WOPR:P1",
                    }
                ]
            ),
        ),
        # ########################################################
        (
            "HISTORY_OBSERVATION WOPR:P1 {\n};",  # NB: Empty {}, with newline
            pd.DataFrame(
                [
                    {
                        "CLASS": "HISTORY_OBSERVATION",
                        "LABEL": "WOPR:P1",
                    }
                ]
            ),
        ),
        # ########################################################
        (
            "HISTORY_OBSERVATION WOPR:P1{ERROR=10;};",
            pd.DataFrame(
                [
                    {
                        "CLASS": "HISTORY_OBSERVATION",
                        "LABEL": "WOPR:P1",
                        "ERROR": 10,
                    }
                ]
            ),
        ),
        # ########################################################
        (
            "HISTORY_OBSERVATION WOPR:P2 {ERROR=10; SEGMENT SEG1 {ERROR=20;START=2};};",
            pd.DataFrame(
                [
                    {
                        "CLASS": "HISTORY_OBSERVATION",
                        "LABEL": "WOPR:P2",
                        "ERROR": 10,
                        "SEGMENT": "DEFAULT",
                    },
                    {
                        "CLASS": "HISTORY_OBSERVATION",
                        "LABEL": "WOPR:P2",
                        "ERROR": 20,
                        "START": 2,
                        "SEGMENT": "SEG1",
                    },
                ]
            ),
        ),
    ],
)
def test_ertobs2df(string, expected):
    """Test converting all the way from ERT observation format to a Pandas
    Dataframe works as expected (this includes many of the other functions
    that are also tested individually)"""
    dframe = ertobs2df(string)
    pd.testing.assert_frame_equal(
        dframe.sort_index(axis=1), expected.sort_index(axis=1), check_dtype=False
    )

    pd.testing.assert_frame_equal(
        ertobs2df(df2ertobs(dframe)).sort_index(axis=1), dframe.sort_index(axis=1)
    )

    # Round-trip test via yaml:
    if "DATE" not in expected:
        return
    round_trip_yaml_dframe = obsdict2df(df2obsdict(dframe))
    pd.testing.assert_frame_equal(
        round_trip_yaml_dframe.sort_index(axis=1), dframe.sort_index(axis=1)
    )


@pytest.mark.parametrize(
    "string, expected",
    [
        ########################################################################
        (
            (
                "SUMMARY_OBSERVATION 2S_BHP1 {VALUE=501.3; ERROR=5; "
                "DAYS=1.404965; KEY=WBHP:2S;};"
            ),
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "LABEL": "2S_BHP1",
                        "KEY": "WBHP:2S",
                        "DATE": datetime.datetime(2020, 1, 1, 0, 0)
                        + datetime.timedelta(days=1.404965),
                        "DAYS": 1.404965,
                        "VALUE": 501.3,
                        "ERROR": 5,
                    }
                ]
            ),
        ),
        ########################################################################
        (
            (
                "SUMMARY_OBSERVATION 2S_BHP1 {VALUE=501.3; ERROR=5; "
                "DATE=2020-01-01; DAYS=1.404965; KEY=WBHP:2S;};"
            ),
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "LABEL": "2S_BHP1",
                        "KEY": "WBHP:2S",
                        "DATE": pd.to_datetime(
                            datetime.date(2020, 1, 1)
                        ),  # in-place DATE overrides
                        "DAYS": 1.404965,
                        "VALUE": 501.3,
                        "ERROR": 5,
                    }
                ]
            ),
        ),
    ],
)
def test_ertobs2df_starttime(string, expected):
    """Test that when DAYS is given but no DATES, we can
    get a computed DATE if starttime is provided"""
    pd.testing.assert_frame_equal(
        ertobs2df(string, starttime="2020-01-01").sort_index(axis=1),
        expected.sort_index(axis=1),
    )
    # Test again with datetime object passed, not string:
    pd.testing.assert_frame_equal(
        ertobs2df(string, starttime=datetime.date(2020, 1, 1)).sort_index(axis=1),
        expected.sort_index(axis=1),
    )


# smrydictlist2df
@pytest.mark.parametrize(
    "smrylist, expected_df",
    [
        ([{"key": "WOPR:P"}], pd.DataFrame()),
        ([{"key": "WOPR:P1", "observations": []}], pd.DataFrame()),
        (
            [{"key": "WOPR:P1", "observations": [{"date": "2020"}]}],
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "DATE": datetime.date(2020, 1, 1),
                        "LABEL": "WOPR:P1-1",  # Auto-generated label
                        "KEY": "WOPR:P1",
                    }
                ]
            ),
        ),
        #################################################################
        (
            [
                {
                    "key": "WOPR:P1",
                    "comment": "first oil producer",
                    "observations": [{"date": "2020"}],
                }
            ],
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "DATE": datetime.date(2020, 1, 1),
                        "LABEL": "WOPR:P1-1",  # Auto-generated label
                        "KEY": "WOPR:P1",
                        "COMMENT": "first oil producer",
                    }
                ]
            ),
        ),
        #################################################################
        (
            [
                {
                    "key": "WOPR:P1",
                    "comment": "first oil producer",
                    "observations": [
                        {"date": "2020", "comment": "uncertain first point"}
                    ],
                }
            ],
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "DATE": datetime.date(2020, 1, 1),
                        "LABEL": "WOPR:P1-1",  # Auto-generated label
                        "KEY": "WOPR:P1",
                        "COMMENT": "first oil producer",
                        "SUBCOMMENT": "uncertain first point",
                    }
                ]
            ),
        ),
        #################################################################
        (
            [{"key": "WOPR:P1", "observations": [{"date": "2020", "label": "FOO"}]}],
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "DATE": datetime.date(2020, 1, 1),
                        # The handling of key vs label here might change
                        "LABEL": "FOO",
                        "KEY": "WOPR:P1",
                    }
                ]
            ),
        ),
        #################################################################
        (
            [
                {
                    "key": "WOPR:P1",
                    "observations": [
                        {"date": "2020-01-01", "value": 1000, "error": 100}
                    ],
                }
            ],
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "DATE": datetime.date(2020, 1, 1),
                        "KEY": "WOPR:P1",
                        "LABEL": "WOPR:P1-1",
                        "VALUE": 1000,
                        "ERROR": 100,
                    }
                ]
            ),
        ),
        #################################################################
        (
            [
                {
                    "key": "WOPR:P1",
                    "observations": [
                        {"date": "2020-01-01", "value": 1000, "error": 100.0},
                        {"date": "2030-01-01", "value": 2000, "error": 200},
                    ],
                }
            ],
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "DATE": datetime.date(2020, 1, 1),
                        "KEY": "WOPR:P1",
                        "LABEL": "WOPR:P1-1",
                        "VALUE": 1000.0,
                        "ERROR": 100.0,
                    },
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "DATE": datetime.date(2030, 1, 1),
                        "KEY": "WOPR:P1",
                        "LABEL": "WOPR:P1-2",
                        "VALUE": 2000.0,
                        "ERROR": 200.0,
                    },
                ]
            ),
        ),
        #################################################################
        (
            [
                {
                    "key": "WOPR:P1",
                    "observations": [
                        {"date": "2020-01-01", "value": 1000, "error": 100},
                        {"date": "2030-01-01", "value": 2000, "error": 200},
                    ],
                },
                {
                    "key": "WOPR:P2",
                    "observations": [
                        {"date": "2020-01-01", "value": 3000, "error": 300},
                    ],
                },
            ],
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "DATE": datetime.date(2020, 1, 1),
                        "KEY": "WOPR:P1",
                        "LABEL": "WOPR:P1-1",
                        "VALUE": 1000.0,
                        "ERROR": 100.0,
                    },
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "DATE": datetime.date(2030, 1, 1),
                        "KEY": "WOPR:P1",
                        "LABEL": "WOPR:P1-2",
                        "VALUE": 2000.0,
                        "ERROR": 200.0,
                    },
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "DATE": datetime.date(2020, 1, 1),
                        "KEY": "WOPR:P2",
                        "LABEL": "WOPR:P2-1",
                        "VALUE": 3000.0,
                        "ERROR": 300.0,
                    },
                ]
            ),
        ),
    ],
)
def test_smrydictlist2df(smrylist, expected_df):
    """Test converting summary observations as dictionaries (yaml) into
    internal dataframe format"""
    if "DATE" in expected_df:
        expected_df["DATE"] = pd.to_datetime(expected_df["DATE"])
    pd.testing.assert_frame_equal(
        smrydictlist2df(smrylist).sort_index(axis=1),
        expected_df.sort_index(axis=1),
        check_dtype=False,
    )


# blockdictlist2df
@pytest.mark.parametrize(
    "blocklist, expected_df",
    [
        ([{"well": "P1"}], pd.DataFrame()),
        ([{"well": "P1", "observations": []}], pd.DataFrame()),
        (
            [{"well": "OP1", "observations": [{"date": "2020", "value": 100, "i": 4}]}],
            pd.DataFrame(
                [
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "DATE": datetime.date(2020, 1, 1),
                        "LABEL": "OP1",  # Auto-generated label
                        "OBS": "P1",  # Auto-generated label
                        "WELL": "OP1",
                        "VALUE": 100.0,
                        "I": 4,
                    }
                ]
            ),
        ),
        #################################################################
        (
            [
                {
                    "well": "OP1",
                    "field": "PRESSURE",
                    "observations": [{"date": "2020", "value": 100, "i": 4}],
                }
            ],
            pd.DataFrame(
                [
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "DATE": datetime.date(2020, 1, 1),
                        "FIELD": "PRESSURE",
                        "LABEL": "OP1",  # Auto-generated label
                        "OBS": "P1",  # Auto-generated label
                        "WELL": "OP1",
                        "VALUE": 100.0,
                        "I": 4,
                    }
                ]
            ),
        ),
        #################################################################
        (
            [
                {
                    "well": "OP1",
                    "field": "PRESSURE",
                    "observations": [{"date": "2020", "field": "overwritten"}],
                }
            ],
            pd.DataFrame(
                [
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "DATE": datetime.date(2020, 1, 1),
                        "FIELD": "overwritten",
                        "LABEL": "OP1",  # Auto-generated label
                        "OBS": "P1",  # Auto-generated label
                        "WELL": "OP1",
                    }
                ]
            ),
        ),
        #################################################################
        (
            [
                {
                    "well": "OP1",
                    "comment": "first well",
                    "observations": [{"date": "2020", "comment": "bad measurement"}],
                }
            ],
            pd.DataFrame(
                [
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "DATE": datetime.date(2020, 1, 1),
                        "LABEL": "OP1",  # Auto-generated label
                        "OBS": "P1",  # Auto-generated label
                        "WELL": "OP1",
                        "COMMENT": "first well",
                        "SUBCOMMENT": "bad measurement",
                    }
                ]
            ),
        ),
        #################################################################
        (
            [{"well": "OP1", "observations": [{"date": "2020"}]}],
            pd.DataFrame(
                [
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "DATE": datetime.date(2020, 1, 1),
                        "LABEL": "OP1",
                        "OBS": "P1",
                        "WELL": "OP1",
                    }
                ]
            ),
        ),
        #################################################################
        (
            [{"well": "OP1", "observations": [{"date": "2020"}, {"date": "2021"}]}],
            pd.DataFrame(
                [
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "DATE": datetime.date(2020, 1, 1),
                        "LABEL": "OP1",
                        "OBS": "P1",
                        "WELL": "OP1",
                    },
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "DATE": datetime.date(2021, 1, 1),
                        "LABEL": "OP1",
                        "OBS": "P2",
                        "WELL": "OP1",
                    },
                ]
            ),
        ),
        #################################################################
    ],
)
def test_blockdictlist2df(blocklist, expected_df):
    """Test converting block/rft observations in dict (yaml) format into
    internal dataframe format"""
    # print(blockdictlist2df(blocklist))
    # print(expected_df)
    if "DATE" in expected_df:
        expected_df["DATE"] = pd.to_datetime(expected_df["DATE"])
    pd.testing.assert_frame_equal(
        blockdictlist2df(blocklist).sort_index(axis=1),
        expected_df.sort_index(axis=1),
        check_dtype=False,
    )


# obsdictlist2df
@pytest.mark.parametrize(
    "obsdict, expected_df",
    [
        (
            {
                "rft": [
                    {
                        "well": "OP1",
                        "field": "PRESSURE",
                        "observations": [{"date": "2020", "value": 100, "i": 4}],
                    }
                ],
                "smry": [{"key": "WOPR:OP1", "observations": [{"date": "2020"}]}],
            },
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUMMARY_OBSERVATION",
                        "DATE": datetime.date(2020, 1, 1),
                        "LABEL": "WOPR:OP1-1",  # Auto-generated label
                        "KEY": "WOPR:OP1",
                    },
                    {
                        "CLASS": "BLOCK_OBSERVATION",
                        "DATE": datetime.date(2020, 1, 1),
                        "LABEL": "OP1",  # Auto-generated label
                        "OBS": "P1",  # Auto-generated label
                        "FIELD": "PRESSURE",
                        "WELL": "OP1",
                        "VALUE": 100.0,
                        "I": 4,
                    },
                ]
            ),
        ),
    ],
)
def test_obsdict2df(obsdict, expected_df):
    """Test converting yaml format (any kind of observation) into internal
    dataframe format. Specifics in each class of observation has its own test
    functions"""
    if "DATE" in expected_df:
        expected_df["DATE"] = pd.to_datetime(expected_df["DATE"])
    pd.testing.assert_frame_equal(
        obsdict2df(obsdict).sort_index(axis=1),
        expected_df.sort_index(axis=1),
        check_dtype=False,
    )
