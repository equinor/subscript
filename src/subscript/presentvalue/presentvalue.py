"""NPV calculation of oil and gas production income"""

import argparse
import datetime
import logging
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd
import res2df
import scipy.optimize

from subscript import __version__, getLogger

logger = getLogger(__name__)

DESCRIPTION = """Calculated present value of oil and gas streams from an Eclipse
simulation. Optional yearly costs, and optional variation in prices."""

BARRELSPRCUBIC = 6.28981077

NOKUNIT = 1000000.0  # all NOK figures are scaled by this value (input and output)


def get_parser() -> argparse.ArgumentParser:
    """Parser for command line arguments and for documentation.

    Returns:
        argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter, description=DESCRIPTION
    )
    parser.add_argument("datafiles", nargs="+", help="Input Eclipse DATA files")
    parser.add_argument(
        "--oilprice", type=float, default=60, help="Constant oil price in USD/bbl"
    )
    parser.add_argument(
        "--gasprice", type=float, default=1.7, help="Constant gas price in MNOK/Gsm3"
    )
    parser.add_argument(
        "--usdtonok", type=float, default=7.0, help="USD to NOK conversion"
    )
    parser.add_argument(
        "--discountrate", type=float, default=8, help="Discount rate in percent"
    )
    parser.add_argument(
        "--discountto",
        type=int,
        default=datetime.datetime.now().year,
        help="Which year to discount to",
    )
    parser.add_argument(
        "--writetoparams",
        action="store_true",
        default=False,
        help="Write results to parameters.txt",
    )
    parser.add_argument(
        "--paramname",
        type=str,
        default="PresentValue",
        help="Parameter-name in parameters.txt",
    )
    parser.add_argument(
        "--oilvector",
        type=str,
        help=(
            "Eclipse vector to read cumulative oil production from. "
            "Use None to ignore."
        ),
        default="FOPT",
    )
    parser.add_argument(
        "--gasvector",
        type=str,
        help=(
            "Eclipse vector to read cumulative gas production from. "
            "Use None to ignore."
        ),
        default="FGPT",
    )
    parser.add_argument(
        "--gasinjvector",
        type=str,
        help=(
            "Eclipse vector to read cumulative gas injection from. "
            "Use None to ignore."
        ),
        default="FGIT",
    )
    parser.add_argument(
        "--cutoffyear",
        type=int,
        default=2100,
        help="Ignore data beyond 1 Jan this year",
    )
    parser.add_argument(
        "--econtable",
        type=str,
        help=(
            "Comma separated table with years as rows, and column names specifying "
            "economical parameters. Supported column names: oilprice (USD/bbl), "
            "gasprice (NOK/sm3), usdtonok, costs (MNOK)"
        ),
    )
    parser.add_argument(
        "--basedatafiles",
        nargs="+",
        default=[],
        help=(
            "Input Eclipse DATA files to be used as base "
            "cases to calculate delta production profiles"
        ),
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    parser.add_argument("--quiet", "-q", action="store_true", help="Be quiet")
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + __version__ + ")",
    )
    return parser


def main() -> None:
    """Function for command line invocation.

    Parses command line arguments, and writes output to file and/or terminal."""
    parser = get_parser()
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)

    if args.quiet:
        logger.warning("Command line option --quiet is deprecated")

    econ_df = prepare_econ_table(
        args.econtable,
        oilprice=args.oilprice,
        gasprice=args.gasprice,
        usdtonok=args.usdtonok,
        discountrate=args.discountrate,
    )

    if (
        args.basedatafiles
        and len(args.basedatafiles) > 1
        and len(args.basedatafiles) != len(args.datafiles)
    ):
        msg = (
            "Supply either no base case, a single base case or "
            "exactly as many base cases as datafiles."
        )
        raise ValueError(msg)

    for idx, datafile in enumerate(args.datafiles):
        if args.basedatafiles:
            if len(args.basedatafiles) > 1:
                basedatafile = args.basedatafiles[idx]
            else:
                basedatafile = args.basedatafiles[0]
        else:
            basedatafile = None

        results = presentvalue_main(
            datafile=datafile,
            economics=econ_df,
            discountrate=args.discountrate,
            discountto=args.discountto,
            oilvector=args.oilvector,
            gasvector=args.gasvector,
            gasinjvector=args.gasinjvector,
            cutoffyear=args.cutoffyear,
            basedatafile=basedatafile,
        )

        logger.info(str(results))

        paramfile = get_paramfilename(datafile)
        if args.writetoparams and paramfile:
            logger.info("Writing results to %s", paramfile)
            with open(paramfile, "a", encoding="utf8") as f_handle:
                f_handle.write(dict_to_parameterstxt(results, args.paramname))
        elif not args.verbose:
            # Ensure user gets a response
            print(str(results))


def dict_to_parameterstxt(results: Dict[str, float], paramname: str) -> str:
    """Produce a key-value string with newlines from a dict of results

    Args:
        results: depth-1 dictionary
        paramname: Basename for parameters to produce

    Returns:
        multiline, ready to be appended to parameters.txt
    """
    str_result = ""
    for key, value in results.items():
        if key == "PresentValue":
            str_result += paramname + " " + str(value) + "\n"
        else:
            str_result += paramname + "_" + key + " " + str(value) + "\n"
    return str_result.strip()


def get_paramfilename(eclfile: str) -> str:
    """Locate the parameters.txt file closest to the Eclipse DATA file

    Args:
        eclfile: Path to Eclipse DATA file.

    Returns.
        Empty string if no file found. Full path if found.
    """
    for paramcandidate in [
        "parameters.txt",
        "../parameters.txt",
        "../../parameters.txt",
    ]:
        parampath = Path(eclfile).absolute().parent / paramcandidate
        if parampath.exists():
            return str(parampath)
    return ""


def presentvalue_main(
    datafile: str,
    economics: pd.DataFrame,
    discountrate: float = 8,
    discountto: int = datetime.datetime.now().year,
    oilvector: str = "FOPT",
    gasvector: str = "FGPT",
    gasinjvector: str = "FGIT",
    cutoffyear: int = 2100,
    basedatafile: Optional[str] = None,
) -> Dict[str, float]:
    """Calculate presentvalue and financial parameters for a single Eclipse
    run

    Args:
        datafile: Path to Eclipse DATA-file
        economics: Year-indexed data with economic parameters
        discountrate: Yearly discount factor
        discountto: Which year to discount to, defaults to current year
        oilvector: Eclipse summary cumulative oil production vector
        gasvector: Eclipse summary cumulative gas production vector
        gasinjvector: Eclipse summary cumulative gas injection vector
        cutoffyear: Production/costs beyond this year will be dropped
        basedatafile: Path to Eclipse DATA file to use as reference
            data (production from this file will be deducted)

    Returns:
        Dictionary with keys "PresentValue", and if input data allows it: "BEP1", "BEP",
        "IRR" and "CEI".
    """
    # pylint: disable=too-many-arguments

    logger.info("Discount rate: %s", str(discountrate))
    logger.info("Cutoff year: %s", str(cutoffyear))
    logger.info("Discount to year: %s", str(discountto))

    logger.info("Economics:\n%s", str(economics))

    summary_df = get_yearly_summary(datafile, oilvector, gasvector, gasinjvector)

    if basedatafile:
        summary_df = summary_df - get_yearly_summary(
            basedatafile, oilvector, gasvector, gasinjvector
        )
    if max(summary_df.index) < discountto:
        logger.warning("All production is in the past. This gives zero value")
        return {"PresentValue": 0}

    pv_df = calc_presentvalue_df(summary_df, economics, discountto)

    pvalue = pv_df.loc[: cutoffyear - 1]["presentvalue"].sum() / NOKUNIT

    pd.set_option("expand_frame_repr", False)  # Avoid line wrapping in tabular output
    logger.info(
        "Production and economic parameters:\n%s", str(pv_df.loc[: cutoffyear - 1])
    )

    results = {}
    results["PresentValue"] = pvalue
    results.update(calculate_financials(pv_df, cutoffyear))
    return results


def calculate_financials(pv_df: pd.DataFrame, cutoffyear: int) -> Dict[str, float]:
    """Calculate economical parameters given a dataframe with
    income and costs.

    Args:
        pv_df: A dataframe prepared with data for
            presentvalue computations.

    Return:
        dict: Results, with keys: BEP1, BEP2, IRR, CEI. Keys
        will only exist if computation was successful."""
    if not pv_df["costs"].abs().sum() > 0:
        return {}

    finance = {}
    try:
        if pv_df["OPR"].abs().sum() > 0.0:
            finance["BEP1"] = scipy.optimize.newton(
                calc_pv_bep_relativegas, 50, args=(pv_df, cutoffyear), maxiter=50
            )
        else:
            logger.warning("BEP1 is meaningless without oil production")
    except ImportError:
        logger.warning("BEP1 computation failed")
    try:
        if pv_df["OPR"].abs().sum() > 0.0:
            finance["BEP2"] = scipy.optimize.newton(
                calc_pv_bep_constantgas, 50, args=(pv_df, cutoffyear), maxiter=50
            )
        else:
            logger.warning("BEP2 is meaningless without oil production")
    except ImportError:
        logger.warning("BEP2 computation failed")
    try:
        if len(pv_df) < 2:
            logger.warning("IRR meaningless on dataset with only one year")
        else:
            finance["IRR"] = scipy.optimize.newton(
                calc_pv_irr, 10, args=(pv_df, cutoffyear), maxiter=50
            )
    except RuntimeError:
        logger.warning("IRR computation failed")

    if "presentvalue" in pv_df.columns:
        pvalue = pv_df.loc[: cutoffyear - 1]["presentvalue"].sum() / NOKUNIT
        pv_negativecashflow = abs(
            pv_df.loc[: cutoffyear - 1]["presentvalue"][pv_df["presentvalue"] < 0].sum()
            / NOKUNIT
        )
        if pv_negativecashflow > 0:
            finance["CEI"] = pvalue / pv_negativecashflow
    return finance


def calc_presentvalue_df(
    summary_df: pd.DataFrame, econ_df: pd.DataFrame, discountto: int
) -> pd.DataFrame:
    """
    Calculate a dataframe for present value computations.

    Discount rate will be obtained from the econ_df dataframe.

    Args:
        summary_df: summary dataframe,  OPT, GPT, GIT, indexed
            year
        econ_df: Dataframe with economical input (prices and
            costs)
        discountto: Which year to discount to.

    Returns:
        pd.DataFrame: A column "presentvalue" will be added, which
        can then be summed to obtain the presentvalue over all years.
    """
    # Merge with econonics table, ffill NaN's coming
    # from limited economics information
    prodecon = pd.concat([summary_df, econ_df], axis=1, sort=True)
    prodecon[["oilprice", "gasprice", "usdtonok", "discountrate"]] = prodecon[
        ["oilprice", "gasprice", "usdtonok", "discountrate"]
    ].ffill()
    # Avoid ffilling costs...
    # There could be situations where we need to bfill prices as well,
    # if the user provided a econtable
    prodecon[["oilprice", "gasprice", "usdtonok", "discountrate"]] = prodecon[
        ["oilprice", "gasprice", "usdtonok", "discountrate"]
    ].bfill()
    prodecon.fillna(value=0, inplace=True)  # Zero-pad other data (costs)

    prodecon["deltayears"] = prodecon.index - discountto

    prodecon["discountfactors"] = 1.0 / (
        (1.0 + prodecon["discountrate"] / 100.0) ** np.array(prodecon["deltayears"])
    )

    prodecon["presentvalue"] = (
        prodecon["OPR"] * BARRELSPRCUBIC * prodecon["oilprice"] * prodecon["usdtonok"]
        + prodecon["GSR"] * prodecon["gasprice"]
        - prodecon["costs"] * NOKUNIT
    ) * prodecon["discountfactors"]

    # Remove the year 1900 that was added for flat prices:
    prodecon = prodecon[prodecon.index != 1900]

    # Return only rows after the year we are discounting to:
    return prodecon[prodecon.index >= discountto]


def get_yearly_summary(
    eclfile: str,
    oilvector: str = "FOPT",
    gasvector: str = "FGPT",
    gasinjvector: str = "FGIT",
) -> pd.DataFrame:
    """Obtain a yearly summary with only three production vectors from
    an Eclipse output file.

    Only cumulative vectors can be used, which will be linearly interpolated
    to 1st of January for each year, and then yearly volumes are
    calculated from the cumulatives.

    Args:
        eclfile: Path to Eclipse DATA file
        oilvector: Name of cumulative summary vector with oil production
        gasvector: Name of cumulative summary vector with gas production
        gasinjvector: Name of cumulative summary vector with gas injection

    Returns:
        pd.DataFrame. Indexed by year, with the columns OPR, GPR, GIR and GSR.

    """
    if not all(
        vec.split(":")[0].endswith("T") for vec in [oilvector, gasvector, gasinjvector]
    ):
        raise ValueError("Only cumulative Eclipse vectors can be used")
    eclfiles = res2df.ResdataFiles(eclfile)
    sum_df = res2df.summary.df(
        eclfiles, column_keys=[oilvector, gasvector, gasinjvector], time_index="yearly"
    )
    sum_df.rename(
        {oilvector: "OPT", gasvector: "GPT", gasinjvector: "GIT"},
        axis="columns",
        inplace=True,
    )
    sum_df = sum_df.reset_index()

    if "GIT" not in sum_df:
        sum_df["GIT"] = 0
    if "GPT" not in sum_df:
        sum_df["GPT"] = 0
    if "OPT" not in sum_df:
        sum_df["OPT"] = 0
    sum_df["YEAR"] = pd.to_datetime(sum_df["DATE"]).dt.year

    sum_df["OPR"] = sum_df["OPT"].shift(-1) - sum_df["OPT"]
    sum_df["GPR"] = sum_df["GPT"].shift(-1) - sum_df["GPT"]
    sum_df["GIR"] = sum_df["GIT"].shift(-1) - sum_df["GIT"]
    sum_df["GSR"] = sum_df["GPR"] - sum_df["GIR"]
    return sum_df.drop("DATE", axis="columns").set_index("YEAR").dropna()


def prepare_econ_table(
    filename: Optional[str] = None,
    oilprice: Optional[float] = None,
    gasprice: Optional[float] = None,
    usdtonok: Optional[float] = None,
    discountrate: float = 8,
) -> pd.DataFrame:
    """Parse a CSV file with economical input

    Args:
        filename: Path to a CSV file to be parsed with pd.read_csv()
        oilprice: Default for oilprice if not included in CSV file.
        gasprice: Default for gasprice if not included in CSV file.
        usdtonok: Default for usdtonk if not included in CSV file.
        discountrate: Default for discountrate if not included (as
            constant) in CSV file.

    Returns:
        pd.DataFrame: dataframe with economical data to be given
        to calc_presentvalue_df().
    """
    # False positives from pylint:
    # pylint: disable=E1136,E1137,E1101
    if filename:
        econ_df = pd.read_csv(filename, index_col=0)
        econ_df.columns = econ_df.columns.map(str.strip)
        if "discountrate" in econ_df and len(econ_df["discountrate"]) > 1:
            raise ValueError("discountrate must be constant")
        # assert first column is year.
    else:
        # Make a default dataframe if nothing provided.
        # Only one early year is needed for providing defaults
        econ_df = pd.DataFrame(index=[1900])
    if "oilprice" not in econ_df and oilprice is not None:
        econ_df["oilprice"] = oilprice
    if "gasoprice" not in econ_df and gasprice is not None:
        econ_df["gasprice"] = gasprice
    if "usdtonok" not in econ_df and usdtonok is not None:
        econ_df["usdtonok"] = usdtonok
    if "costs" not in econ_df:
        econ_df["costs"] = 0
    if "discountrate" not in econ_df:
        econ_df["discountrate"] = discountrate

    econ_df.index.name = "year"

    required_columns = {"oilprice", "gasprice", "usdtonok", "costs", "discountrate"}

    if not required_columns.issubset(set(econ_df)):
        raise ValueError(
            f"Missing economical input columns: {required_columns - set(econ_df)}"
        )

    if len(econ_df.columns) > len(required_columns):
        logger.warning("Superfluous columns in economical input")

    return econ_df


def calc_pv_irr(rate: float, pv_df: pd.DataFrame, cutoffyear: int) -> float:
    """Calculate internal rate of return (IRR)

    Args:
        rate: discountfactor to be used
        pv_df: Production and economical data
        cutoffyear: Ignore production beyond this year.

    Returns:
        Computed presentvalue
    """
    discountfactors_irr = 1.0 / (1.0 + rate / 100.0) ** np.array(
        list(range(len(pv_df)))
    )
    if len(pv_df) < 2:
        raise ValueError("IRR computation meaningless on a single year")
    pv_irr = (
        pv_df["OPR"] * BARRELSPRCUBIC * pv_df["oilprice"] * pv_df["usdtonok"]
        + pv_df["GSR"] * pv_df["gasprice"]
        - pv_df["costs"] * NOKUNIT
    ) * discountfactors_irr
    return pv_irr.loc[: cutoffyear - 1].sum() / NOKUNIT


def calc_pv_bep_relativegas(
    oilprice: float,
    pv_df: pd.DataFrame,
    cutoffyear: int,
    relativegasprice: float = 9.3 * 3.79127 / 100 / 100,
) -> float:
    """Calculate break-even oilprice with gasprice strongly correlated to
    oilprice using EPA QX 201X External Assumptions;
    there is a link between gas and oil prices and the
    resulting break-even price is in USD/boe.

    Args:
        oilprice: Price pr. barrel of oil in USD
        pv_df: Production and economical data.
        cutoffyear: Production/costs beyond this year is ignored
        relativegasprice: Gasprice (in MNOK/GSm3) is oilprice
            (usd/bbl) multiplied with this constant.
    Returns:
        Computed presentvalue.
    """
    gasprice = oilprice * relativegasprice

    pv_bep = (
        pv_df["OPR"] * BARRELSPRCUBIC * oilprice * pv_df["usdtonok"]
        + (pv_df["GSR"] * gasprice * pv_df["usdtonok"])
        - pv_df["costs"] * NOKUNIT
    ) * pv_df["discountfactors"]
    return pv_bep.loc[: cutoffyear - 1].sum() / NOKUNIT


def calc_pv_bep_constantgas(
    oilprice: float, pv_df: pd.DataFrame, cutoffyear: int
) -> float:
    """Calculate break-even oilprice without touching the gas price:

    Gas price is fixed, from the dataframe, the resulting break-even price
    is in USD/bbl. This can be used to evaluate gas injection/deferral projects.

    Args:
        oilprice: Price pr. barrel of oil in USD
        pv_df: Production and economical data, with gasprice
        cutoffyear: Production/costs beyond this year is ignored

    Returns:
        Computed presentvalue.
    """
    pv_bep = (
        pv_df["OPR"] * BARRELSPRCUBIC * oilprice * pv_df["usdtonok"]
        + (pv_df["GSR"] * pv_df["gasprice"])
        - pv_df["costs"] * NOKUNIT
    ) * pv_df["discountfactors"]

    return pv_bep.loc[: cutoffyear - 1].sum() / NOKUNIT


if __name__ == "__main__":
    main()
