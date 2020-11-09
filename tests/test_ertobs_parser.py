"""Test the ERT observation file format parser"""

import datetime

import pandas as pd
import pytest


from subscript.ertobs.parsers import (
    INCLUDE_RE,
    OBS_ARGS_RE,
    ertobs2df,
    expand_includes,
    filter_comments,
    fix_dtype,
    flatten_observation_unit,
    mask_curly_braces,
    parse_observation_unit,
    split_by_sep_in_masked_string,
    dfsmry2ertobs,
)


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
    ],
)
def test_fix_dtype(string, expected):
    """Test that values are converted to numeric when possible"""
    assert fix_dtype(string) == expected


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


def test_expand_includes(tmpdir):
    """Test that include <filename> statements can be resolved"""
    tmpdir.chdir()
    with open("foo.txt", "w") as f_handle:
        f_handle.write("foo;")
    assert expand_includes("hallo; include foo.txt; hei") == "hallo; foo; hei"

    # Multiple files:
    with open("bar.txt", "w") as f_handle:
        f_handle.write("bar;")
    assert (
        expand_includes("hallo; include foo.txt; hei; include bar.txt;")
        == "hallo; foo; hei; bar;"
    )

    # Test relative directory support:
    tmpdir.mkdir("subdir")
    with open("subdir/leaf.txt", "w") as f_handle:
        f_handle.write("foo;")
    assert (
        expand_includes("hallo; include leaf.txt; hei", cwd="subdir")
        == "hallo; foo; hei"
    )


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
        (
            "SUM WCT {DATE=01/01/2001;VALUE=1;ERROR=0.1;};",
            pd.DataFrame(
                [
                    {
                        "CLASS": "SUM",
                        "LABEL": "WCT",
                        "DATE": datetime.datetime(2001, 1, 1, 0, 0),
                        "VALUE": 1,
                        "ERROR": 0.1,
                    }
                ]
            ),
        ),
        (
            "SUM SEP_1 {VALUE = 100;}; SUM SEP_2 {VALUE=200;};",
            pd.DataFrame(
                [
                    {"CLASS": "SUM", "LABEL": "SEP_1", "VALUE": 100},
                    {"CLASS": "SUM", "LABEL": "SEP_2", "VALUE": 200},
                ]
            ),
        ),
        (
            "BLOCK R1 {FIELD=PR; OBS P1 {I=1;}; OBS P2 {J=2;};};",
            pd.DataFrame(
                [
                    {
                        "CLASS": "BLOCK",
                        "LABEL": "R1",
                        "FIELD": "PR",
                        "OBS": "P1",
                        "I": 1,
                    },
                    {
                        "CLASS": "BLOCK",
                        "LABEL": "R1",
                        "FIELD": "PR",
                        "OBS": "P2",
                        "J": 2,
                    },
                ]
            ),
        ),
        (
            "HIST WOPR:P1;",
            pd.DataFrame(
                [
                    {
                        "CLASS": "HIST",
                        "LABEL": "WOPR:P1",
                    }
                ]
            ),
        ),
        (
            "HIST WOPR:P1{ERROR=10;};",
            pd.DataFrame(
                [
                    {
                        "CLASS": "HIST",
                        "LABEL": "WOPR:P1",
                        "ERROR": 10,
                    }
                ]
            ),
        ),
        (
            "HIST WOPR:P2 {ERROR=10; SEGMENT SEG1 {ERROR=20;START=2};};",
            pd.DataFrame(
                [
                    {
                        "CLASS": "HIST",
                        "LABEL": "WOPR:P2",
                        "ERROR": 10,
                        "SEGMENT": "DEFAULT",
                    },
                    {
                        "CLASS": "HIST",
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
    pd.testing.assert_frame_equal(
        ertobs2df(string).sort_index(axis=1), expected.sort_index(axis=1)
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
def test_dfsmry2ertobs(obs_df, expected_str):
    """Test that we can generate ERT summary observation text format
    from the internal dataframe representation"""
    assert dfsmry2ertobs(obs_df).strip() == expected_str.strip()

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
