"""Takes a list of files with <key> <values> pr. line, and turns them
into a csv database (sort of transposing and concatenation of all the
data, ensuring labels for each value matches).

"""

import argparse
import logging
import re
import shutil
from glob import glob

import pandas as pd
from ert import ErtScript
from ert.shared.plugins.plugin_manager import hook_implementation  # type: ignore

from subscript import __version__, getLogger

logger = getLogger(__name__)


DESCRIPTION = """
Turn one or more parameters.txt for into a CSV file.

parameters.txt is a text file with <key> <value> on each line

In the CSV file, each individual parameter file will be represented by one data row.
The order of parameters in each text file is not conserved.

The original filename for each file is written to the column ‘filename’.
Beware if you have that as a <key> in the text files.
"""

CATEGORY = "utility.eclipse"

EXAMPLES = """
.. code-block:: console

  FORWARD_MODEL PARAMS2CSV(<PARAMETERFILES>=parameters.txt, <OUTPUT>=parameters.csv)
 
This forward model will convert all keys in `parameters.txt` to columns in 
`parameters.csv`. 

In addition, it will add a column `filename` which list the source parameters.txt file. 
This column will be useful when <PARAMETERFILES> contains wildcards.

The `filename` column can be renamed by adding an argument <FILENAMECOLUMN> to the FORWARD_MODEL.
    
.. code-block:: console

  FORWARD_MODEL PARAMS2CSV(<PARAMETERFILES>=parameters.txt, <OUTPUT>=parameters.csv,<FILENAMECOLUMN>=source_file)
  
"""  # noqa

# The following string is used for the ERT workflow documentation, note
# the very subtle difference in variable name.
WORKFLOW_EXAMPLE = """
Add a file named e.g. ``ert/bin/workflows/PARAMS2CSV_ITER0`` with the contents::
  MAKE_DIRECTORY <SCRATCH>/<USER>/<CASE_DIR>/share/results/tables
  PARAMS2CSV "--verbose" "-o" <SCRATCH>/<USER>/<CASE_DIR>/share/results/tables/parameters_iter-0.csv <SCRATCH>/<USER>/<CASE_DIR>/realization-*/iter-0/parameters.txt

Add to your ERT config to have the workflow loaded upon launching::

  LOAD_WORKFLOW ../bin/workflows/PARAMS2CSV_ITER0

It is then possible to run the workflow either through ERT CLI or GUI.
"""  # noqa


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """
    Multiple inheritance used for argparse to get both
    defaults and raw description formatter
    """

    # pylint: disable=unnecessary-pass

    pass


class Params2Csv(ErtScript):
    """A class with a run() function that can be registered as an ERT plugin,
    to be used as an ERT workflow (wrapping the command line utility)"""

    # pylint: disable=too-few-public-methods
    def run(self, *args):
        # pylint: disable=no-self-use
        """Parse with a simplified command line parser, for ERT only,
        calling params2csv_main()"""
        parser = get_parser()
        args = parser.parse_args(args)
        params2csv_main(args)


def get_parser() -> argparse.ArgumentParser:
    """Set up parser for command line utility"""
    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter,
        description="""Turn parameters.txt for an ensemble into a CSV file.  Optionally
also clean parameters.txt for inconsistencies (differing number of
records)

parameters.txt is any text file with <key> <value> on each line

In the CSV file, each individual parameter file will be represented by
one data row. The order of parameters in each text file is not
conserved.

The original filename for each file is written to the column
'filename'. Beware if you have that as a <key> in the text files.""",
    )
    parser.add_argument(
        "parameterfile", nargs="+", help="all parameter files to be merged"
    )
    parser.add_argument(
        "-o", "--output", type=str, help="name of output csv file", default="params.csv"
    )
    parser.add_argument(
        "--filenamecolumnname",
        type=str,
        help="Column name that will contain the name of the parameter file",
        default="filename",
    )
    parser.add_argument(
        "--keepconstantcolumns",
        action="store_true",
        help="Keep constant columns",
        default=False,
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Write back cleaned parameters.txt",
        default=False,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + __version__ + ")",
    )

    return parser


def params2csv_main(args: argparse.Namespace) -> None:
    """A main function to be used both from the command line, and
    when used as an ERT plugin (ERT workflow).

    Args:
        args (argparse.Namespace): Namespace with command line arguments
    """
    if args.verbose:
        logger.setLevel(logging.INFO)

    # Expand wildcards if not being expanded
    args.parameterfile = [
        path for pattern in args.parameterfile for path in sorted(glob(pattern))
    ]

    ens = pd.DataFrame()

    parsedfiles = 0
    for _, parameterfilename in enumerate(args.parameterfile, start=0):
        try:
            paramtable = pd.read_csv(parameterfilename, header=None, sep=r"\s+")
            parsedfiles = parsedfiles + 1
        except IOError:
            logger.warning("%s not found, skipping..", parameterfilename)
            continue

        # Chop to only two colums, set keys, and transpose, and then
        # merge with the previous tables
        paramtable = pd.DataFrame(paramtable.iloc[:, 0:2])
        paramtable.columns = ["key", "value"]
        paramtable.drop_duplicates(
            "key", keep="last", inplace=True
        )  # if key is repeated, keep the last one.
        transposed = paramtable.set_index("key").transpose()
        if args.filenamecolumnname in transposed.columns:
            logger.info(
                "Column name %s was already in %s, not writing this filename "
                "into CSV output. Use --filenamecolumnname to avoid this.",
                args.filenamecolumnname,
                parameterfilename,
            )
        else:
            transposed.insert(0, args.filenamecolumnname, parameterfilename)

        # Look for meta-information in filename
        realregex = r".*realization-(\d*)/"
        iterregex = r".*iter-(\d*)/"
        if (
            re.match(realregex, parameterfilename)
            and "Realization" not in transposed.columns
        ):
            transposed.insert(
                0,
                "Realization",
                re.match(realregex, parameterfilename).group(1),  # type: ignore
            )
        if re.match(iterregex, parameterfilename) and "Iter" not in transposed.columns:
            transposed.insert(
                0,
                "Iter",
                re.match(iterregex, parameterfilename).group(1),  # type: ignore
            )

        ens = pd.concat([ens, transposed], sort=True)

    if args.clean:
        # Users wants the script to write back to parameters.txt a
        # possible subset of parametervalues so that the number of
        # parameters is equal in an entire ensemble, and so that
        # duplicate keys are removed Parameters only existing in some
        # realizations will be NaN-padded in the others.
        ensfilenames = ens.reset_index()["filename"]
        ensidx = ens.reset_index().drop(["index", "filename"], axis=1)
        for row in list(ensidx.index.values):
            paramfile = ensfilenames.loc[row]
            shutil.copyfile(paramfile, paramfile + ".backup")
            logger.info("Writing to %s", paramfile)
            ensidx.loc[row].to_csv(paramfile, sep=" ", na_rep="NaN", header=False)

    # Drop constant columns:
    if not args.keepconstantcolumns:
        for col in ens.columns:
            if len(ens[col].unique()) == 1:
                del ens[col]
                logger.warning("Dropping constant column %s", col)

    ens.to_csv(args.output, index=False)
    logger.info("%s parameterfiles written to %s", parsedfiles, args.output)


def main() -> None:
    """Entry point from command line"""
    parser = get_parser()
    args = parser.parse_args()
    params2csv_main(args)


@hook_implementation
def legacy_ertscript_workflow(config) -> None:
    """Hook the CsvStack class into ERT with the name PARAMS2CSV,
    and inject documentation"""
    workflow = config.add_workflow(Params2Csv, "PARAMS2CSV")
    workflow.parser = get_parser
    workflow.description = DESCRIPTION
    workflow.examples = WORKFLOW_EXAMPLE
    workflow.category = CATEGORY


if __name__ == "__main__":
    main()
