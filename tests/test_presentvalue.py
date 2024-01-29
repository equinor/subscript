import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import res2df
from resdata.summary import Summary
from subscript.presentvalue import presentvalue

ECLDIR = Path(__file__).absolute().parent / "data" / "reek" / "eclipse" / "model"


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


def test_get_paramfilename(tmp_path):
    """Test that we can locate the parameters.txt relative to an Eclipse file"""
    os.chdir(tmp_path)
    (tmp_path / "foo1").mkdir()
    (tmp_path / "foo1" / "foo2").mkdir(parents=True)
    (tmp_path / "foo1" / "foo2" / "foo3").mkdir(parents=True)

    assert presentvalue.get_paramfilename("foo1/foo2/foo3/FOO.DATA") == ""

    Path("foo1/parameters.txt").write_text("foo1", encoding="utf8")
    assert (
        Path(presentvalue.get_paramfilename("foo1/foo2/foo3/FOO.DATA")).read_text(
            encoding="utf8"
        )
        == "foo1"
    )

    Path("foo1/foo2/parameters.txt").write_text("foo2", encoding="utf8")
    assert (
        Path(presentvalue.get_paramfilename("foo1/foo2/foo3/FOO.DATA")).read_text(
            encoding="utf8"
        )
        == "foo2"
    )

    Path("foo1/foo2/foo3/parameters.txt").write_text("foo3", encoding="utf8")
    assert (
        Path(presentvalue.get_paramfilename("foo1/foo2/foo3/FOO.DATA")).read_text(
            encoding="utf8"
        )
        == "foo3"
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


def test_prepare_econ_table_csv(tmp_path):
    """Testing loading economics data from a CSV file"""
    os.chdir(tmp_path)
    Path("econ.csv").write_text(
        "year, oilprice, gasprice, costs\n2030, 60, 2, 100", encoding="utf8"
    )

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


def test_main(tmp_path, mocker):
    """Test the main functionality of presentvalue as endpoint script, writing
    back results to parameters.txt in the original runpath"""
    shutil.copytree(
        ECLDIR,
        tmp_path / "model",
        # This is somewhat spacious, 39M, but the test will fail
        # if you try with a symlink (presentvalue.py looks through symlinks)
    )
    os.chdir(tmp_path / "model")

    parameterstxt_fname = "parameters.txt"

    # Create an empty file called parameters.txt, otherwise
    # the presentvalue script will not write to it.
    Path(parameterstxt_fname).write_text("", encoding="utf8")
    mocker.patch(
        "sys.argv",
        [
            "presentvalue",
            "--writetoparams",
            "--cutoffyear",
            "2003",
            "--discountto",
            "2001",
            "2_R001_REEK-0.DATA",
        ],
    )
    presentvalue.main()
    parametersline = (
        Path(parameterstxt_fname).read_text(encoding="utf8").splitlines()[0].strip()
    )
    assert parametersline.split()[0] == "PresentValue"
    assert round(float(parametersline.split()[1]), 1) == 11653.9


def test_no_gasinj(tmp_path):
    """Test that summary files with no gas injection works
    (missing GIT is the same as zero GIT)"""
    os.chdir(tmp_path)
    smry = pd.DataFrame(
        [
            {"DATE": "2030-01-01", "FOPT": 0, "FGPT": 0},
            {"DATE": "2031-01-01", "FOPT": 1000, "FGPT": 0},
        ]
    )
    smry["DATE"] = pd.to_datetime(smry["DATE"])
    smry.set_index("DATE")
    eclsum = res2df.summary.df2ressum(smry, "NOGASINJ")
    Summary.fwrite(eclsum)
    econ_df = presentvalue.prepare_econ_table(
        oilprice=100, gasprice=0, usdtonok=10, discountrate=0
    )
    assert np.isclose(
        presentvalue.presentvalue_main("NOGASINJ", econ_df, discountto=2030)[
            "PresentValue"
        ],
        presentvalue.BARRELSPRCUBIC,
    )


def test_no_gas(tmp_path):
    """Test that summary files with no gas prod/injection works
    (missing GPT is the same as zero GPT)"""
    os.chdir(tmp_path)
    smry = pd.DataFrame(
        [
            {"DATE": "2030-01-01", "FOPT": 0},
            {"DATE": "2031-01-01", "FOPT": 1000},
        ]
    )
    smry["DATE"] = pd.to_datetime(smry["DATE"])
    smry.set_index("DATE")
    eclsum = res2df.summary.df2ressum(smry, "NOGAS")
    Summary.fwrite(eclsum)
    econ_df = presentvalue.prepare_econ_table(
        oilprice=100, gasprice=0, usdtonok=10, discountrate=0
    )
    assert np.isclose(
        presentvalue.presentvalue_main("NOGAS", econ_df, discountto=2030)[
            "PresentValue"
        ],
        presentvalue.BARRELSPRCUBIC,
    )


def test_no_oil(tmp_path):
    """Test that summary files with only gas prod/injection works"""

    os.chdir(tmp_path)
    smry = pd.DataFrame(
        [
            {"DATE": "2030-01-01", "FGPT": 0},
            {"DATE": "2031-01-01", "FGPT": 1000},
        ]
    )
    smry["DATE"] = pd.to_datetime(smry["DATE"])
    smry.set_index("DATE")
    eclsum = res2df.summary.df2ressum(smry, "NOOIL")
    Summary.fwrite(eclsum)
    econ_df = presentvalue.prepare_econ_table(
        oilprice=0, gasprice=10, usdtonok=10, discountrate=0
    )
    assert np.isclose(
        presentvalue.presentvalue_main("NOOIL", econ_df, discountto=2030)[
            "PresentValue"
        ],
        0.01,
    )


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["presentvalue", "-h"])
