import shutil
from typing import Optional

from ert import (
    ForwardModelStepDocumentation,
    ForwardModelStepPlugin,
    plugin as ert_plugin,
)

from subscript.csv2ofmvol import csv2ofmvol
from subscript.csv_stack import csv_stack
from subscript.eclcompress import eclcompress
from subscript.ecldiff2roff import ecldiff2roff
from subscript.grav_subs_maps import grav_subs_maps
from subscript.grav_subs_points import grav_subs_points
from subscript.interp_relperm import interp_relperm
from subscript.merge_rft_ertobs import merge_rft_ertobs
from subscript.merge_unrst_files import merge_unrst_files
from subscript.ofmvol2csv import ofmvol2csv
from subscript.params2csv import params2csv
from subscript.prtvol2csv import prtvol2csv
from subscript.sunsch import sunsch
from subscript.welltest_dpds import welltest_dpds


class CasegenUpcars(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="CASEGEN_UPCARS",
            command=[
                shutil.which("casegen_upcars"),
                "<CONFIG>",
                "--et",
                "<ECLIPSE_TEMPLATE>",
                "--base",
                "<ECLIPSE_OUTPUT>",
            ],
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description="""casegen_upcars is script to create conceptual model
based on sugar-cube representation of fracture.

It has capability to:

- simple geometric: tilting, hull and dome shape
- Layers heterogeneity (streaks)
- multiple throws (vertical shifting in any part of the model)
- vugs distribution: random, near fracture and near streak
- etc. Check wiki for more details:
  https://wiki.equinor.com/wiki/index.php/UpCaRs_Upscaling_casegen""",
            category="modelling.reservoir",
            examples="""
.. code-block:: console

  DEFINE <CASEGEN_CONFIG_FILE>      <RUNPATH>/model.yaml
  DEFINE <CASEGEN_ECLIPSE_TEMPLATE> <CONFIG_PATH>/../input/config/eclipse.tmpl
  FORWARD_MODEL CASEGEN_UPCARS(<CONFIG>=<CASEGEN_CONFIG_FILE>, \
        <ECLIPSE_TEMPLATE>=<CASEGEN_ECLIPSE_TEMPLATE>, \
        <ECLIPSE_OUTPUT>=<ECLIPSE_NAME>-<IENS>)

""",
        )


class CheckSwatinit(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="CHECK_SWATINIT",
            command=[
                shutil.which("check_swatinit"),
                "--output",
                "<OUTPUT>",
                "<DATAFILE>",
            ],
            default_mapping={"<OUTPUT>": "check_swatinit.csv"},
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description="QC tool for SWATINIT vs SWAT in Eclipse runs",
            category="utility.eclipse",
            examples="""
.. code-block:: console

  FORWARD_MODEL CHECK_SWATINIT(<DATAFILE>=<ECLBASE>, <OUTPUT>=check_swatinit.csv)

where ``ECLBASE`` is already defined in your ERT config.
""",
        )


class Csv2Ofmvol(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="CSV2OFMVOL",
            command=[
                shutil.which("csv2ofmvol"),
                "--verbose",
                "<CSVFILES>",
                "--output",
                "<OUTPUT>",
            ],
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description=csv2ofmvol.DESCRIPTION,
            category="modelling.production",
        )


class CsvStack(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="CSV_STACK",
            command=[
                shutil.which("csv_stack"),
                "--verbose",
                "--output",
                "<OUTPUT>",
                "<CSVFILE>",
                "<OPTION>",
            ],
            default_mapping={"<OPTION>": ""},
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description=csv_stack.DESCRIPTION,
            category=csv_stack.CATEGORY,
            examples="""
Put this in your ERT config::

  FORWARD_MODEL CSV_STACK(<CSVFILE>=stackme.csv, \
      <OUTPUT>=stacked.csv, <OPTION>="--keepminimal")

""",
        )


class EclCompress(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="ECLCOMPRESS",
            command=[
                shutil.which("eclcompress"),
                "--verbose",
                "--files",
                "<FILES>",
            ],
            default_mapping={"<FILES>": eclcompress.MAGIC_DEFAULT_FILELIST},
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description=eclcompress.DESCRIPTION,
            category="modelling.reservoir",
            examples="""
.. code-block:: console

  FORWARD_MODEL ECLCOMPRESS

You can provide your own list of files to compress with the ``<FILES>``
argument.

.. code-block:: console

  FORWARD_MODEL ECLCOMPRESS(<FILES>=paths_to_compress.txt)

where ``paths_to_compress.txt`` contains a list of files or filepaths to
compress.

.. code-block:: text
  :caption: paths_to_compress.txt

  eclipse/include/grid/*
  eclipse/include/regions/*
  eclipse/include/props/*

Note that this list of file paths is the default list used when no file is
provided.
""",
        )


class Ecldiff2Roff(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="ECLDIFF2ROFF",
            command=[
                shutil.which("ecldiff2roff"),
                "<ECLROOT>",
                "<PROP>",
                "--diffdates",
                "<DIFFDATES>",
                "--outputfilebase",
                "<OUTPUT>",
                "--verbose",
            ],
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description=ecldiff2roff.DESCRIPTION,
            category="utility.eclipse",
            examples="""
.. code-block:: console

    FORWARD_MODEL ECLDIFF2ROFF(<ECLROOT>=<ECLBASE>, <PROP>=SGAS, \
        <DIFFDATES>=diff_dates.txt <OUTPUT>=share/results/grids/eclgrid)

where ``ECLBASE`` is already defined in your ERT config, pointing to the Eclipse
basename relative to ``RUNPATH``.
""",
        )


class Eclgrid2Roff(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="ECLGRID2ROFF",
            command=[
                shutil.which("convert_grid_format"),
                "--conversion",
                "ecl2roff",
                "--file",
                "<ECLROOT>",
                "--output",
                "<OUTPUT>",
            ],
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description="""Convert between Eclipse binary EGRID output to ROFF grid
format.

This forward model uses the script ``convert_grid_format`` from subscript.

Destination directory must exist.

The file extension ``.roff`` will be added to the OUTPUT argument.
""",
            category="utility.eclipse",
            examples="""
..  code-block:: console

   FORWARD_MODEL ECLGRID2ROFF(<ECLROOT>=<ECLBASE>, <OUTPUT>=share/results/grids/eclgrid)

where ``ECLBASE`` is already defined in your ERT config, pointing to the Eclipse
basename relative to ``RUNPATH``.
""",
        )


class Eclinit2Roff(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="ECLINIT2ROFF",
            command=[
                shutil.which("convert_grid_format"),
                "--conversion",
                "ecl2roff",
                "--file",
                "<ECLROOT>",
                "--output",
                "<OUTPUT>",
                "--propnames",
                "<PROP>",
                "--mode",
                "init",
                "--standardfmu",
            ],
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description="""Convert Eclipse INIT file to ROFF grid format.

This forward model uses the script ``convert_grid_format`` from subscript.

Destination directory must exist.

One file will be written for each of the requested parameters, the example
given below will produce the files::

    share/results/grids/eclgrid--poro.roff
    share/results/grids/eclgrid--permx.roff
""",
            category="utility.eclipse",
            examples="""
.. code-block:: console

  FORWARD_MODEL ECLINIT2ROFF(<ECLROOT>=<ECLBASE>, \
      <OUTPUT>=share/results/grids/eclgrid, <PROP>=PORO:PERMX)

where ``ECLBASE`` is already defined in your ERT config, pointing to the Eclipse
basename relative to ``RUNPATH``.
""",
        )


class Eclrst2Roff(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="ECLRST2ROFF",
            command=[
                shutil.which("convert_grid_format"),
                "--conversion",
                "ecl2roff",
                "--file",
                "<ECLROOT>",
                "--output",
                "<OUTPUT>",
                "--propnames",
                "<PROP>",
                "--dates",
                "<DATES>",
                "--mode",
                "restart",
                "--standardfmu",
            ],
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description="""Convert between Eclipse restart files ROFF grid format.

This forward model uses the script ``convert_grid_format`` from subscript.

Destination directory must exist.

One file will be written for each of the requested parameters, the example
given below will produce the files::

    share/results/grids/eclgrid--sgas--20200101.roff
    share/results/grids/eclgrid--soil--20200101.roff

if the file ``dates.txt`` contains only the line::

    20200101
""",
            category="utility.eclipse",
            examples="""
.. code-block:: console

  FORWARD_MODEL ECLRST2ROFF(<ECLROOT>=<ECLBASE>, \
      <OUTPUT>=share/results/grids/eclgrid, <PROP>=SGAS:SWAT, <DATES>=dates.txt)

where ``ECLBASE`` is already defined in your ERT config, pointing to the Eclipse
basename relative to ``RUNPATH``.
""",  #
        )


class GravSubsMaps(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="GRAV_SUBS_MAPS",
            command=[
                shutil.which("grav_subs_maps"),
                "--configfile",
                "<GRAVMAPS_CONFIG>",
                "--outputdir",
                "<OUTPUT_DIR>",
                "<UNRST_FILE>",
            ],
            default_mapping={"<OUTPUT_DIR>": "./"},
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description=grav_subs_maps.DESCRIPTION,
            category="modelling.reservoir",
            examples="""
.. code-block:: console

 FORWARD_MODEL GRAV_SUBS_MAPS(<UNRST_FILE>=<ECLBASE>.UNRST, \
    <GRAVMAPS_CONFIG>=grav_subs_maps.yml)
 FORWARD_MODEL GRAV_SUBS_MAPS(<UNRST_FILE>=<ECLBASE>.UNRST, \
    <GRAVMAPS_CONFIG>=grav_subs_maps.yml, <OUTPUT_DIR>=share/results/maps)


where ``ECLBASE`` is already defined in your ERT config, pointing to the flowsimulator
basename relative to ``RUNPATH``, grav_subs_maps.yml is a YAML file defining
the inputs and modelling parameters and ``OUTPUT_DIR`` is the path to the output folder.
If not specified OUTPUT_DIR will be defaulted to "./".

The directory to export maps to must exist.
""",
        )


class GravSubsPoints(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="GRAV_SUBS_POINTS",
            command=[
                shutil.which("grav_subs_points"),
                "--configfile",
                "<GRAVPOINTS_CONFIG>",
                "--outputdir",
                "<OUTPUT_DIR>",
                "--prefix_gendata",
                "<PREFIX_GENDATA>",
                "--extension_gendata",
                "<EXTENSION_GENDATA>",
                "<UNRST_FILE>",
            ],
            default_mapping={
                "<OUTPUT_DIR>": "./",
                "<PREFIX_GENDATA>": "",
                "<EXTENSION_GENDATA>": ".txt",
            },
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description=grav_subs_points.DESCRIPTION,
            category="modelling.reservoir",
            examples="""
.. code-block:: console

  FORWARD_MODEL GRAV_SUBS_POINTS(<UNRST_FILE=<ECLBASE>.UNRST, \
      <GRAVPOINTS_CONFIG>=grav_subs_points.yml)
  FORWARD_MODEL GRAV_SUBS_POINTS(<UNRST_FILE=<ECLBASE>.UNRST, \
      <GRAVPOINTS_CONFIG>=<CONFIG_PATH>/../input/config/grav_subs_points.yml, \
      <OUTPUT_DIR>=share/results/points)

  FORWARD_MODEL GRAV_SUBS_POINTS(<UNRST_FILE=<ECLBASE>.UNRST, \
      <GRAVPOINTS_CONFIG>=grav_subs_points.yml, <EXTENSION_GENDATA>="_10.txt")
  FORWARD_MODEL GRAV_SUBS_POINTS(<UNRST_FILE=<ECLBASE>.UNRST, \
      <GRAVPOINTS_CONFIG>=grav_subs_points.yml, <PREFIX_GENDATA>="fieldA_")

where ``ECLBASE`` is already defined in your ERT config, pointing to the flowsimulator
basename relative to ``RUNPATH``, grav_subs_points.yml is a YAML file defining
the inputs and modelling parameters and ``OUTPUT_DIR`` is the path to the output folder.
If not specified OUTPUT_DIR will be defaulted to "./".
``PREFIX_GENDATA`` and ``EXTENSION_GENDATA`` is the file prefix and extension used for
the output files of type GEN_DATA. The prefix can be used to separate datasets for
different structures/fields within the dataset and is defaulted to an empty string,
i.e. no prefix. The extension could include the report step number by defining e.g.
"_10.txt", but is defaulted without it a report step number, to only ".txt"

The directory to export point files to must exist.
""",
        )


class InterpRelperm(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="INTERP_RELPERM",
            command=[
                shutil.which("interp_relperm"),
                "-c",
                "<INTERP_CONFIG>",
                "--root-path",
                "<ROOT_PATH>",
            ],
            default_mapping={
                "<ROOT_PATH>": "./",
            },
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description=interp_relperm.DESCRIPTION,
            category="modelling.reservoir",
            examples="""
.. code-block:: console

 FORWARD_MODEL INTERP_RELPERM(<INTERP_CONFIG>=interp_relperm.yml, \
    <ROOT_PATH>=<CONFIG_PATH>)

""",
        )


class MergeRftErtobs(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="MERGE_RFT_ERTOBS",
            command=[
                shutil.which("merge_rft_ertobs"),
                "--verbose",
                "<GENDATACSV>",
                "<OBSDIR>",
                "--output",
                "<OUTPUT>",
            ],
            default_mapping={
                "<OUTPUT>": "rft_ertobs_sim.csv",
            },
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description=merge_rft_ertobs.DESCRIPTION, category="utility.eclipse"
        )


class MergeUnrstFiles(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="MERGE_UNRST_FILES",
            command=[
                shutil.which("merge_unrst_files"),
                "<UNRST1>",
                "<UNRST2>",
                "--output",
                "<OUTPUT>",
            ],
            default_mapping={
                "<OUTPUT>": "MERGED.UNRST",
            },
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description=merge_unrst_files.DESCRIPTION,
            category="utility.eclipse",
            examples="""
.. code-block:: console

  DEFINE <RESTART_DIR>      iter-3
  FORWARD_MODEL MERGE_UNRST_FILES(<UNRST1>=..<RESTART_DIR>/<ECLBASE>.UNRST, \
      <UNRST2>=<ECLBASE>.UNRST, <OUTPUT>=eclipse/model/ECLIPSE_MERGED.UNRST)

""",
        )


class Ofmvol2Csv(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="OFMVOL2CSV",
            command=[
                shutil.which("ofmvol2csv"),
                "--verbose",
                "<VOLFILES>",
                "--output",
                "<OUTPUT>",
            ],
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description=ofmvol2csv.DESCRIPTION,
            category="modelling.production",
            examples="",
        )


class Params2Csv(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="PARAMS2CSV",
            command=[
                shutil.which("params2csv"),
                "--verbose",
                "--filenamecolumnname",
                "<FILENAMECOLUMN>",
                "-o",
                "<OUTPUT>",
                "<PARAMETERFILES>",
                "--keepconstantcolumns",
            ],
            default_mapping={
                "<OUTPUT>": "parameters.csv",
                "<FILENAMECOLUMN>": "filename",
            },
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description=params2csv.DESCRIPTION,
            category=params2csv.CATEGORY,
            examples="""
.. code-block:: console

  FORWARD_MODEL PARAMS2CSV(<PARAMETERFILES>=parameters.txt, <OUTPUT>=parameters.csv)

This forward model will convert all keys in `parameters.txt` to columns in
`parameters.csv`.

In addition, it will add a column `filename` which list the source parameters.txt file.
This column will be useful when <PARAMETERFILES> contains wildcards.

The `filename` column can be renamed by adding an argument <FILENAMECOLUMN> to the
FORWARD_MODEL.

.. code-block:: console

  FORWARD_MODEL PARAMS2CSV(<PARAMETERFILES>=parameters.txt, <OUTPUT>=parameters.csv,\
      <FILENAMECOLUMN>=source_file)

""",
        )


class Prtvol2Csv(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="PRTVOL2CSV",
            command=[
                shutil.which("prtvol2csv"),
                "--verbose",
                "--dir",
                "<DIR>",
                "--outputfilename",
                "<OUTPUTFILENAME>",
                "--yaml",
                "<REGIONS>",
                "--rename2fipnum",
                "--fipname",
                "<FIPNAME>",
                "<DATAFILE>",
            ],
            default_mapping={
                "<DIR>": "share/results/volumes",
                "<OUTPUTFILENAME>": "simulator_volume_fipnum.csv",
                "<REGIONS>": "",
                "<FIPNAME>": "FIPNUM",
            },
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description=prtvol2csv.DESCRIPTION,
            category="utility.eclipse",
            examples="""
.. code-block:: console

  FORWARD_MODEL PRTVOL2CSV(<DATAFILE>=<ECLBASE>, <REGIONS>=regions.yml, \
      <FIPNAME>=FIPNUM, <DIR>=., <OUTPUTFILENAME>=simulator_volume_fipnum.csv)

where ``ECLBASE`` is already defined in your ERT config, pointing to the Eclipse
basename relative to ``RUNPATH`` and ``regions.yml`` is a YAML file defining
the map from regions and/or zones to FIPNUM. The YAML file could be omitted in the
FORWARD_MODEL and specified directly in the Webviz config file, if the REGIONS argument
is not given a default value in the forward model job configuration.

The ``FIPNAME`` argument is by default set to ``FIPNUM``, but any FIP-vector can be
used. Ensure the PRT file has volume reports for the additional FIP-vector.

By using the ``rename2fipnum`` option, the column name would be set to FIPNUM in
the csv-file for any FIP-vector, as required by ``webviz-subsurface`` plugin
``VolumetricAnalysis``. This renaming is not needed for ``Webviz-Sumo``. An additional
column with the actual FIPNAME is included for information.

Using anything else than "." in the ``DIR`` argument is deprecated. To write to a CSV
file in a specific directory, add the path in the ``OUTPUTFILENAME`` argument.
The directory to export to must exist.
""",
        )


class RiWellmod(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="RI_WELLMOD",
            command=[
                shutil.which("ri_wellmod"),
                "<RI_PROJECT>",
                "<ECLBASE>",
                "-o",
                "<OUTPUTFILE>",
                "--msw",
                "<MSW>",
                *[f"<XARG{num}>" for num in range(12)],
            ],
            default_mapping={
                "<OUTPUTFILE>": "well_defs.sch",
                "<MSW>": "",
                **{f"<XARG{num}>": "--dummy" for num in range(12)},
            },
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description="""
``ri_wellmod`` is a utility to generate Eclipse well model definitions
(WELSPECS/WELSPECL, COMPDAT/COMPDATL, WELSEGS, COMPSEGS) using ResInsight. The script
takes as input a ResInsight project with wells and completions defined, in addition to
an Eclipse case (either an initialized case or an input case with grid and PERMX|Y|Z
and NTG defined in the GRDECL format).

.. note:: Well names specified as command line arguments are assumed to refer to the
   Eclipse well names, i.e., the completion export names as defined in the ResInsight
   wells project.
""",
            category="modelling.reservoir",
            examples="""
.. code-block:: console

 FORWARD_MODEL RI_WELLMOD(
    <RI_PROJECT>=<CONFIG_PATH>/../../resinsight/input/well_modelling/wells.rsp,
    <ECLBASE>=<ECLBASE>,
    <OUTPUTFILE>=<RUNPATH>/eclipse/include/schedule/well_def.sch)

 FORWARD_MODEL RI_WELLMOD(
    <RI_PROJECT>=<CONFIG_PATH>/../../resinsight/input/well_modelling/wells.rsp,
    <ECLBASE>=<ECLBASE>,
    <OUTPUTFILE>=<RUNPATH>/eclipse/include/schedule/well_def.sch,
    <MSW>="A2;A4;'R*'")

 FORWARD_MODEL RI_WELLMOD(
    <RI_PROJECT>=<CONFIG_PATH>/../../resinsight/input/well_modelling/wells.rsp,
    <ECLBASE>=<ECLBASE>,
    <OUTPUTFILE>=<RUNPATH>/eclipse/include/schedule/well_def.sch,
    <MSW>="A4",
    <XARG0>="--lgr",
    <XARG1>="A4:3;3;1")


.. warning:: Remember to remove line breaks in argument list when copying the
   examples into your own ERT config.


.. note:: More examples and options may be seen in the subscript docs for the script
   ``ri_wellmod``, just replace ',' by ';' and note that spaces cannot be part of
   argument strings, so you may need to use <XARGn> for the individual parts.

""",
        )


class Sunsch(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="SUNSCH",
            command=[
                shutil.which("sunsch"),
                "--verbose",
                "<config>",
            ],
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description=sunsch.DESCRIPTION,
            category="modelling.production",
            examples="""
.. code-block:: console

  FORWARD_MODEL SUNSCH(<config>=sunsch_config.yml)
""",
        )


class WelltestDpds(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="WELLTEST_DPDS",
            command=[
                shutil.which("welltest_dpds"),
                "<ECLBASE>",
                "<WELLNAME>",
                "-n",
                "<BUILDUP_NR>",
                "--phase",
                "<PHASE>",
                "-o",
                "<OUTPUTDIRECTORY>",
                "--outfilessuffix",
                "<OUTFILESSUFFIX>",
                "--genobs_resultfile",
                "<GENOBS_RESULTFILE>",
            ],
            default_mapping={
                "<PHASE>": "OIL",
                "<OUTPUTDIRECTORY>": ".",
                "<OUTFILESSUFFIX>": "",
                "<BUILDUP_NR>": "1",
                "<GENOBS_RESULTFILE>": "None",
            },
        )

    @staticmethod
    def documentation() -> Optional[ForwardModelStepDocumentation]:
        return ForwardModelStepDocumentation(
            description=welltest_dpds.DESCRIPTION,
            category="modelling.reservoir",
            examples="""
Example for cases without HM:
-----------------------------
::

   FORWARD_MODEL WELLTEST_DPDS(<ECLBASE>, <WELLNAME>=DST_WELL)

   or

   FORWARD_MODEL WELLTEST_DPDS(<ECLBASE>, <WELLNAME>=OP_1, <PHASE>=GAS, <BUILDUP_NR>=1,
                 <OUTPUTDIRECTORY>=dst, <OUTFILESSUFFIX>=OP_1)

Example for cases with HM:
--------------------------
::

   FORWARD_MODEL WELLTEST_DPDS(<ECLBASE>, <WELLNAME>=OP_1, <PHASE>=GAS, <BUILDUP_NR>=2,
                 <OUTPUTDIRECTORY>=dst, <OUTFILESSUFFIX>=OP_1_1,
                 <GENOBS_RESULTFILE>=OP_1_dpdt_bu2_saphir.txt )

Then set-up of GEN_DATA can be
::

   GEN_DATA DPDT_SIM INPUT_FORMAT:ASCII REPORT_STEPS:1
            RESULT_FILE:dpdspt_lag2_genobs_OP_1_%d_2

result_file corresponds to dpdspt_lag2_genobs_<WELLNAME>_%d_<BUILDUP_NR>

.. warning:: Remember to remove line breaks in argument list when copying the
   examples into your own ERT config.
""",
        )


@ert_plugin(name="Subscript")
def installable_forward_model_steps() -> list[type[ForwardModelStepPlugin]]:
    return [
        CasegenUpcars,
        CheckSwatinit,
        Csv2Ofmvol,
        CsvStack,
        EclCompress,
        Ecldiff2Roff,
        Eclgrid2Roff,
        Eclinit2Roff,
        Eclrst2Roff,
        GravSubsMaps,
        GravSubsPoints,
        InterpRelperm,
        MergeRftErtobs,
        MergeUnrstFiles,
        Ofmvol2Csv,
        Params2Csv,
        Prtvol2Csv,
        RiWellmod,
        Sunsch,
        WelltestDpds,
    ]
