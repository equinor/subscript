
SUNSCH
======

Sunsch is a tool to build your final Schedule section to Eclipse. This can be done
through merging multiple partial Schedule files, or inserting small Schedule commands
at specific dates, possibly with templating included while inserting. Insertion
can be at absolute dates, or at relative dates to a start date.

.. argparse::
   :module: subscript.sunsch.sunsch
   :func: get_parser
   :prog: sunsch


Features in short
-----------------

- Configuration in YAML format
- Merging via DATE keyword
- Optional clipping any events before or after chosen start and end dates
- A "date grid" can be inserted. Daily, weekly, biweekly, monthly, bimonthly
  and yearly are supported. Monthly dates will be rounded to the first of
  every month.
- Insertion of small Schedule snippets, opening a well for example. Can
  be inserted either at dates relative a reference date, or at a specific date.
- Schedule snippets can have parameters that get values when inserted.
  This is similar to what one could achieve using DESIGN_KW, but with less
  temporary files.

When to use
------------

The tool is designed for FMU runs. It can be used both for the history section
and for prediction, but probably has its most relevant usage in sensitivities
for prediction. It will enable usage of the aging Schlumberger Schedule
application, in that the exported text file from Schlumberger Schedule can be
further processed with this tool. If RMS10/11 is in use already for well
planning and Schedule export, the need for this tool is less, and one should
possibly try not to use both unless needed.

Yaml file syntax
----------------

Write a configuration file in YAML format, describing which Schedule files you
are starting from and which you want to merge in, and any other directives to
insert at specific points in the Schedule file.

Start listing the files that should be included as is (merged by date)::

  files:
    - eclipse/include/schedule/initialfile.sch
    - eclipse/include/schedule/mergein.sch

to your configuration. This file normally starts with keywords for the Schedule
section except the DATES keyword, as the date is implicit through the START
keyword in your Eclipse deck.

In an FMU setting, the script should be run with the RUNPATH as the current
directory, so you would normally use paths relative to that (runpath is usually
``realization-*/iter-*``)

Then you add where the output should go, again relative to RUNPATH::

  output: eclipse/include/schedule/finalschedule.sch

This last filename is what needs to go into your templated Eclipse DATA-file.

You should add startdate to the configuration, it is supposed to be the same as
the START given to Eclipse. If there is anything before that date in any of the
input files or insert statements, that will be clipped away. Similarly for
enddate. You may also add refdate. This is only used for relative insertions of
Schedule snippets, so that you can say that some command should be inserted X
days after the refdate.

If you want explicit DATEs at regular intervals, you can use the date-grid feature::

  dategrid: yearly

This is in case the file you initialize from is empty, or does not already have
this. Together with enddate you can also use this to extend the dategrid in the
initial file.

The insert statement has more features. If files are supplied to the insert
statement, those files should not include the DATES keyword, because this is to
be generated. You can specify the date for where it should go in (dates in
ISO-format), or you can state how many days relative to the reference date. An
additional feature is to also substitute parameters in the inserted file (with
this you can use the same sch-file for say WCONPROD at multiple dates, but with
varying rates). The Schedule file to be inserted should then have ``<ORAT>`` (you
could also accomplish this using DESIGN_KW and producing many files to be
inserted, but doing it in this yaml file can allow for cleaner directories).

See the example below for how the insert statement is used.

YAML example
------------

.. code-block:: yaml

  startdate: 1995-06-01
  refdate: 2022-01-01
  enddate: 2030-12-01
  output: eclipse/include/schedule/schedule.sch
  files:
    - eclipse/include/schedule/history.sch
    - eclipse/include/schedule/receptionpressures.sch
  dategrid: monthly
  insert:
    -
      filename: iorwell1.sch
      date: 2020-01-01
    -
      filename: iorwell2.sch
      days: 100  # Relative to refdate
    -
      string: "WCONHIST\n A-5 OPEN ORAT 5000/\n/"
      days: 40
    -
      template: eclipse/include/schedule/prediction_existing_wells.sch
      days: 2
      substitute: { ORAT: 3000, GRAT: 400000}

ERT usage
---------

Sunsch is installed as a forward model in ERT. A typical configuration could look like::

  -- [ various DESIGN_KW statements producing input files to sunsch]
  FORWARD_MODEL DESIGN_KW(<template_file>=<CONFIG_PATH>/../input/templates/config_sunsch.tmpl, <result_file>=<RUNPATH>/sunsch_config.yml)
  FORWARD_MODEL SUNSCH(<config>=sunsch_config.yml)

(if you don't need to templatize your sunsch configuration, you can simplify)

Caveats
-------

- Any comments (starting with ``--`` in the source files) are lost in the final
  output. This is unfortunate, but hard to fix. It is related to the comments in
  input files not having a well-defined location in the final output.
- Any INCLUDE files that merged schedule files have, will be parsed and read.
  That means that the files must exist already and that paths must match up. The
  final output will not contain the INCLUDE statement, but its content. If you
  need INCLUDE statements in the final output that are not parsed (and can refer
  to not-yet-existing files), use a string insertion in the insert section.
- Some error in the Eclipse deck that Eclipse 100 accepts (missing / in some
  circumstances), will not be accepted by sunsch (only when using string
  insertion)
