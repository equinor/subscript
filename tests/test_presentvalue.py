import os
import sys
import shutil

import subprocess
import pytest

import numpy as np
import pandas as pd

from subscript.presentvalue import presentvalue

ECLDIR = os.path.join(os.path.dirname(__file__), "data/reek/eclipse/model")


@pytest.mark.parametrize(
    "res_dict, paramname, expected_str",
    [
        ({}, "", ""),
        ({"foo": 1}, "bar", "bar_foo 1"),
        ({"foo": 1, "com": 3}, "bar", "bar_foo 1\nbar_com 3"),
        ({"PresentValue": 100}, "PresentValue", "PresentValue 100"),
        ({"PresentValue": 100}, "aaaa", "aaaa 100"),
        (
            {"PresentValue": 100, "irr": 1},
            "PresentValue",
            "PresentValue 100\nPresentValue_irr 1",
        ),
    ],
)
def test_dict_to_parameterstxt(res_dict, paramname, expected_str):
    """Test that we can produce a text string for use in parameters.txt
    from a result dictionary"""
    assert presentvalue.dict_to_parameterstxt(res_dict, paramname) == expected_str


def test_get_paramfilename(tmpdir):
    """Test that we can locate the parameters.txt relative to an Eclipse file"""
    tmpdir.chdir()
    tmpdir.mkdir("foo1")
    tmpdir.mkdir("foo1/foo2")
    tmpdir.mkdir("foo1/foo2/foo3")

    def touch(f_name, string):
        with open(f_name, "w") as f_handle:
            f_handle.write(string)

    assert presentvalue.get_paramfilename("foo1/foo2/foo3/FOO.DATA") == ""

    touch("foo1/parameters.txt", "foo1")
    assert (
        open(presentvalue.get_paramfilename("foo1/foo2/foo3/FOO.DATA")).read() == "foo1"
    )

    touch("foo1/foo2/parameters.txt", "foo2")
    assert (
        open(presentvalue.get_paramfilename("foo1/foo2/foo3/FOO.DATA")).read() == "foo2"
    )

    touch("foo1/foo2/foo3/parameters.txt", "foo3")
    assert (
        open(presentvalue.get_paramfilename("foo1/foo2/foo3/FOO.DATA")).read() == "foo3"
    )


def test_prepare_econ_table_simpletest():
    """A simple test of preparation of an economics dataframe,
    without loading from CSV"""
    econ_df = presentvalue.prepare_econ_table(
        oilprice=122, gasprice=33, usdtonok=11, discountrate=99
    )
    assert len(econ_df) == 1
    assert econ_df["oilprice"].unique() == [122]
    assert econ_df["gasprice"].unique() == [33]
    assert econ_df["usdtonok"].unique() == [11]
    assert econ_df["discountrate"].unique() == [99]
    assert econ_df.index.name == "year"


def test_prepare_econ_table_csv(tmpdir):
    """Testing loading economics data from a CSV file"""
    tmpdir.chdir()
    with open("econ.csv", "w") as f_handle:
        f_handle.write("year, oilprice, gasprice, costs\n2030, 60, 2, 100")

    with pytest.raises(ValueError):
        # usdtonok is not present:
        econ_df = presentvalue.prepare_econ_table("econ.csv")

    econ_df = presentvalue.prepare_econ_table("econ.csv", usdtonok=7)
    assert len(econ_df) == 1
    assert econ_df["discountrate"].unique() == [8]  # defaulted
    assert econ_df["usdtonok"].unique() == [7]
    assert econ_df["costs"].unique() == [100]
    assert econ_df.index.values == [2030]


ECONCOLS = ["year", "oilprice", "gasprice", "usdtonok", "costs", "discountrate"]


@pytest.mark.parametrize(
    "summary_df, econ_df, discountto, expected_value",
    [
        (
            # Trivial:
            pd.DataFrame(columns=["year", "OPR", "GSR"], data=[[2020, 1, 0]]).set_index(
                "year"
            ),
            pd.DataFrame(
                columns=ECONCOLS,
                data=[[2020, 1, 0, 1, 0, 0]],
            ).set_index("year"),
            2020,
            presentvalue.BARRELSPRCUBIC,
        ),
        (
            # One year discount, zero discount rate:
            pd.DataFrame(columns=["year", "OPR", "GSR"], data=[[2020, 1, 0]]).set_index(
                "year"
            ),
            pd.DataFrame(
                columns=ECONCOLS,
                data=[[2020, 1, 0, 1, 0, 0]],
            ).set_index("year"),
            2019,
            presentvalue.BARRELSPRCUBIC,
        ),
        (
            # Gas cancels oil
            pd.DataFrame(
                columns=["year", "OPR", "GSR"], data=[[2020, 1, -1]]
            ).set_index("year"),
            pd.DataFrame(
                columns=ECONCOLS,
                data=[[2020, 1, presentvalue.BARRELSPRCUBIC, 1, 0, 0]],
            ).set_index("year"),
            2020,
            0,
        ),
        (
            # One year discount, 10% discount rate:
            pd.DataFrame(columns=["year", "OPR", "GSR"], data=[[2020, 1, 0]]).set_index(
                "year"
            ),
            pd.DataFrame(
                columns=ECONCOLS,
                data=[[2020, 1, 0, 1, 0, 10]],
            ).set_index("year"),
            2019,
            presentvalue.BARRELSPRCUBIC / (1.1),
        ),
        (
            # Test  usdtonok:
            pd.DataFrame(columns=["year", "OPR", "GSR"], data=[[2020, 1, 0]]).set_index(
                "year"
            ),
            pd.DataFrame(
                columns=ECONCOLS,
                data=[[2020, 1, 0, 10, 0, 0]],
            ).set_index("year"),
            2020,
            presentvalue.BARRELSPRCUBIC * 10,
        ),
        (
            # Test oilprice:
            pd.DataFrame(columns=["year", "OPR", "GSR"], data=[[2020, 1, 0]]).set_index(
                "year"
            ),
            pd.DataFrame(
                columns=ECONCOLS,
                data=[[2020, 10, 0, 1, 0, 0]],
            ).set_index("year"),
            2020,
            presentvalue.BARRELSPRCUBIC * 10,
        ),
        (
            # Test "old" econ data:
            pd.DataFrame(columns=["year", "OPR", "GSR"], data=[[2020, 1, 0]]).set_index(
                "year"
            ),
            pd.DataFrame(
                columns=ECONCOLS,
                data=[[2010, 1, 0, 1, 0, 0]],
            ).set_index("year"),
            2020,
            presentvalue.BARRELSPRCUBIC,
        ),
        (
            # Test two years of production, undiscounted
            pd.DataFrame(
                columns=["year", "OPR", "GSR"], data=[[2020, 1, 0], [2021, 1, 0]]
            ).set_index("year"),
            pd.DataFrame(
                columns=ECONCOLS,
                data=[[2020, 1, 0, 1, 0, 0]],
            ).set_index("year"),
            2020,
            presentvalue.BARRELSPRCUBIC * 2,
        ),
        (
            # Test two years of production, discounted
            pd.DataFrame(
                columns=["year", "OPR", "GSR"], data=[[2020, 1, 0], [2021, 1, 0]]
            ).set_index("year"),
            pd.DataFrame(
                columns=ECONCOLS,
                data=[[2020, 1, 0, 1, 0, 10]],
            ).set_index("year"),
            2020,
            presentvalue.BARRELSPRCUBIC + presentvalue.BARRELSPRCUBIC / 1.1,
        ),
    ],
)
def test_calc_presentvalue_df(summary_df, econ_df, discountto, expected_value):
    """Parametrized testing of presentvalue computations from dataframes"""
    pv_df = presentvalue.calc_presentvalue_df(summary_df, econ_df, discountto)
    print(pv_df)
    assert pv_df["presentvalue"].sum() == expected_value


@pytest.mark.parametrize(
    "summary_df, econ_df, discountto, expected_results",
    [
        (
            # Costs, pay attention to units:
            pd.DataFrame(columns=["year", "OPR", "GSR"], data=[[2020, 1, 0]]).set_index(
                "year"
            ),
            pd.DataFrame(
                columns=ECONCOLS,
                data=[[2020, 1, 0, 1, 1 / 1e6, 0]],
            ).set_index("year"),
            2020,
            {
                "BEP1": 1.0 / presentvalue.BARRELSPRCUBIC,
                "BEP2": 1.0 / presentvalue.BARRELSPRCUBIC,
            },
        ),
    ],
)
def test_calculate_financials(summary_df, econ_df, discountto, expected_results):
    """Parametrized testing of presentvalue computations from dataframes"""
    pv_df = presentvalue.calc_presentvalue_df(summary_df, econ_df, discountto)
    fin = presentvalue.calculate_financials(pv_df, 3000)
    for key, value in expected_results.items():
        assert np.isclose(fin[key], value)


# Example dataframe for trying IRR. The data values chosen must allow
# a zero to be found, here tuned by having only gas prices, and a gas
# income in year 2 20% higher than the cost in year 1:
IRR_DF = pd.DataFrame(
    columns=[
        "year",
        "OPR",
        "GSR",
        "oilprice",
        "usdtonok",
        "gasprice",
        "costs",
        "discountfactors",
    ],
    data=[[2020, 0, 0, 0, 0, 1, 1 / 1e6, 1], [2021, 0, 1.2, 0, 0, 1, 0, 1 / 1.1]],
).set_index("year")


def test_calc_pv_irr():
    """A single test of the IRR functionality"""
    results = presentvalue.calculate_financials(IRR_DF, 2100)
    assert np.isclose(results["IRR"], 20)  # remember 20 % higher income in year 2.
    assert np.isclose(presentvalue.calc_pv_irr(results["IRR"], IRR_DF, 2100), 0.0)
    assert presentvalue.calc_pv_irr(results["IRR"] / 2, IRR_DF, 2100) > 0.0
    assert presentvalue.calc_pv_irr(results["IRR"] * 2, IRR_DF, 2100) < 0.0


def test_main(tmpdir):
    """Test the main functionality of presentvalue as endpoint script, writing
    back results to parameters.txt in the original runpath"""
    tmpdir.chdir()
    shutil.copytree(
        ECLDIR,
        "model"
        # This is somewhat spacious, 39M, but the test will fail
        # if you try with a symlink (presentvalue.py looks through symlinks)
    )
    tmpdir.join("model").chdir()

    parameterstxt_fname = "parameters.txt"

    # Remove the potential copy we have got in our tmpdir:
    if os.path.exists(parameterstxt_fname):
        os.unlink(parameterstxt_fname)

    # Create an empty file called parameters.txt, otherwise
    # the presentvalue script will not write to it.
    with open(parameterstxt_fname, "w"):
        pass
    sys.argv = [
        "presentvalue",
        "--writetoparams",
        "--cutoffyear",
        "2003",
        "--discountto",
        "2001",
        "2_R001_REEK-0.DATA",
    ]
    presentvalue.main()
    parametersline = open(parameterstxt_fname).readlines()[0].strip()
    assert parametersline.split()[0] == "PresentValue"
    assert round(float(parametersline.split()[1]), 1) == 11653.9


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    subprocess.check_output(["presentvalue", "-h"])
