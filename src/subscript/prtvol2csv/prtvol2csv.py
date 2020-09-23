import os
import argparse
import pandas
import yaml
import subprocess


DESCRIPTION = """
Extract reservoir volumes from Eclipse PRT files, dump to CSV.

The data from the ascii table "FIELD TOTALS" will be parsed at
initial time step (day 0), and if found, the table called
"RESERVOIR VOLUMES". The latter table will only be written
by Eclipse if you have::

  RPTSOL
    FIP=2 'FIPRESV' /

You can supply a region2fipnum data structure in a YAML-file
which will cause a secondary CSV file to be generated, where
fipnum data are summed up to user specified regions.
"""

CATEGORY = "utility.eclipse"


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    """
    Multiple inheritance used for argparse to get both
    defaults and raw description formatter
    """

    pass


def get_parser():
    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter, description=DESCRIPTION
    )
    parser.add_argument("DATAfile", type=str, help="Name of Eclipse DATA file")
    parser.add_argument(
        "--suffix", type=str, help="Resultdirectory suffix.", default=""
    )
    parser.add_argument(
        "--dir",
        type=str,
        help=(
            "Output directory. Default is FMU standard, "
            "share/results/volumes. "
            "Will be created if necessary."
        ),
        default=None,
    )
    parser.add_argument(
        "--outputfilename",
        type=str,
        help="Output filename in result directory",
        default="simulator_volume_fipnum.csv",  # FMU standard
    )
    parser.add_argument(
        "--regionoutputfilename",
        type=str,
        help="Filename for regrouped region volume output",
        default="simulator_volume_region.csv",
    )
    parser.add_argument(
        "--regions", type=str, help="YAML file containing a fipnum2region dictionary"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Be verbose, print the tables"
    )
    return parser


def prep_output_dir(tablesdir=None, suffix=None):
    """Ensures an output directory exists, and returns
    the name of the directory."""
    if not tablesdir:
        if not suffix or suffix == "":
            tablesdir = "share/results/volumes/"  # FMU standard
        else:
            tablesdir = "share/results-" + suffix + "/volumes"
    if not os.path.exists(tablesdir):
        os.makedirs(tablesdir)
    return tablesdir


def main():
    args = get_parser().parse_args()

    tablesdir = prep_output_dir(args.dir, args.suffix)

    # Temp files, Perl scripts generates these
    simvolumestxt = "eclvolumes_prt_fipnum.txt"
    resvolumestxt = "resvolumes_prt_fipnum.txt"

    PRTfile = args.DATAfile.replace("DATA", "PRT")

    ######################################################################
    # Call Perl scrips
    #
    # The perl scripts we wrap must be deployed to the
    # same directory as the Python-script (!!)
    # This works with ResScript. Rethink for Komodo??
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    subprocess.call(
        [
            "/usr/bin/perl",
            os.path.join(scriptdir, "extract_vol_from_prtfile.pl"),
            PRTfile,
            os.path.join(tablesdir, simvolumestxt),
        ]
    )
    subprocess.call(
        [
            "/usr/bin/perl",
            os.path.join(scriptdir, "extract_resvol_from_prtfile.pl"),
            PRTfile,
            os.path.join(tablesdir, resvolumestxt),
        ]
    )

    ######################################################################
    # Parse output from Perl scripts
    #
    simvolumes_prt = pandas.read_csv(
        os.path.join(tablesdir, simvolumestxt),
        sep=r"\s+",
        skiprows=8,
        usecols=[0, 3, 4, 5, 6, 7, 8, 9, 10],
        names=[
            "FIPTYPE",
            "FIPNUM",
            "STOIIP_OIL",
            "ASSOCIATEDOIL_GAS",
            "STOIIP_TOTAL",
            "WATER_TOTAL",
            "GIIP_GAS",
            "ASSOCIATEDGAS_OIL",
            "GIIP_TOTAL",
        ],
    ).set_index("FIPNUM")
    # Delete FIPXXX
    simvolumes_prt = simvolumes_prt[simvolumes_prt.FIPTYPE == "FIPNUM"]
    simvolumes_prt.drop("FIPTYPE", axis=1, inplace=True)

    simvolumes_prt.to_csv(os.path.join(tablesdir, args.outputfilename))

    print(
        "Written CSV file as first pass without reservoir volume data "
        + os.path.join(tablesdir, args.outputfilename)
    )
    print("Now look for reservoir volumes, will overwrite if successful")

    # The perl script extract_resvol_from_prtfile
    # will repeat the outputted table
    # in case of FIPXXXX is used in the Eclipse run. Therefore we should
    # only look for the data that refers to FIPNUM, and that comes first.
    fipnum_count = len(simvolumes_prt)
    resvolumes_prt = pandas.read_csv(
        os.path.join(tablesdir, resvolumestxt),
        sep=r"\s+",
        skiprows=8,
        nrows=fipnum_count,
        names=[
            "FIPNUM",
            "PORV_TOTAL",
            "HCPV_OIL",
            "WATER_PORV",
            "HCPV_GAS",
            "HCPV_TOTAL",
        ],
    ).set_index("FIPNUM")
    if not len(
        resvolumes_prt
    ):  # if not FIPRESV is included in RPTSOL in *.DATA, then resvolums are missing
        resvolumes_prt = None

    ######################################################################
    # Merge output
    #
    # Set any non-existing valus (Not-a-number) to zero value.
    #
    volumes = pandas.concat([simvolumes_prt, resvolumes_prt], axis=1).fillna(value=0.0)

    ######################################################################
    #
    # Look for a REGION definition in some yaml-file
    # FIPNUM is always at a finer or equal scale as REGION
    # FIPNUM to REGION can be a many-to-many mapping
    # (sums over all REGIONs are thus not always meaningful)
    # The map is specified with REGION as the index, containing a list over FIPNUMs
    #
    # Yaml-file:
    # region2fipnum:
    #    'RegionA' : [1,4,6]
    #    'RegionB' : [2,5]
    #    'FormationA' : [1,2]
    #    'Totals' : [1,2,3,4,5,6]
    #
    # The FIPNUM-indexed table is augmented with a REGION-column,
    # containing space-separated list of referenced REGIONs
    # The REGION-indexed table is augmented with a FIPNUM-column,
    # containing space-separated list of referenced FIPNUMs

    volumesbyregions = None
    if args.regions:
        reg2fip = None
        with open(args.regions, "r") as yamlfile:
            reg2fip = yaml.safe_load(yamlfile)
        if reg2fip and "region2fipnum" in reg2fip:
            reg2fipmap = reg2fip["region2fipnum"]
            # Invert the dictionary of lists, as we alse need to map
            # from fipnum to region:
            fip2regmap = {}
            for reg in reg2fipmap:
                for fip in reg2fipmap[reg]:
                    if fip not in fip2regmap:
                        fip2regmap[fip] = []
                    fip2regmap[fip].append(reg)

            # Now make a REGION-indexed dataframe, with summed volumes
            # from the involved FIPNUMs
            volumesbyregions = {}
            for reg in reg2fipmap:
                volumesbyregions[reg] = pandas.DataFrame(
                    volumes.loc[reg2fipmap[reg]].sum()
                ).transpose()
                # Space separated list of fipnums involved in this region
                volumesbyregions[reg]["FIPNUM"] = " ".join(map(str, reg2fipmap[reg]))
            volumesbyregions = (
                pandas.concat(volumesbyregions)
                .reset_index()
                .drop("level_1", axis=1)
                .set_index("level_0")
            )
            volumesbyregions.index.name = "REGION"

            # Also tag the FIPNUM-indexed dataframe with the regions
            # that are involved in a FIPNUM, space-separated
            for fip in fip2regmap:
                volumes.loc[fip, "REGION"] = " ".join(map(str, fip2regmap[fip]))

        else:
            print("Warning: Could not parse yaml file. No region index can be made")

    if args.verbose:
        print(volumes)
    volumes.to_csv(os.path.join(tablesdir, args.outputfilename))
    print("Written CSV file " + os.path.join(tablesdir, args.outputfilename))

    if volumesbyregions is not None:
        if args.verbose:
            print(volumesbyregions)
        volumesbyregions.to_csv(os.path.join(tablesdir, args.regionoutputfilename))
        print("Written CSV file " + os.path.join(tablesdir, args.regionoutputfilename))


if __name__ == "__main__":
    main()
