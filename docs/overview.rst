Overview
========

Here is a summary of the scripts included in this package and how they can
be used.

========================  ===  =================  ============
Script                    CLI  ERT Forward Model  ERT Workflow
========================  ===  =================  ============
bjobsusers                ✅   ⛔️                 ⛔️
casegen_upcars            ✅   ⛔️                 ⛔️
check_swatinit            ✅   ✅                 ⛔️
convert_grid_format [*]_  ✅   ✅                 ⛔️
csv2ofmvol                ✅   ✅                 ⛔️
csv_merge                 ✅   ⛔️                 ✅
csv_stack                 ✅   ✅                 ✅
eclcompress               ✅   ✅                 ⛔️
ecldiff2roff              ✅   ✅                 ⛔️
fmu_copy_revision         ✅   ⛔️                 ⛔️
fmuobs                    ✅   ⛔️                 ✅
interp_relperm            ✅   ✅                 ⛔️
merge_rft_ertobs          ✅   ✅                 ⛔️
merge_unrst_files         ✅   ✅                 ⛔️
ofmvol2csv                ✅   ✅                 ⛔️
pack_sim                  ✅   ⛔️                 ⛔️
params2csv                ✅   ✅                 ✅
presentvalue              ✅   ⛔️                 ⛔️
prtvol2csv                ✅   ✅                 ⛔️
restartthinner            ✅   ⛔️                 ⛔️
ri_wellmod                ✅   ✅                 ⛔️
rmsecl_volumetrics        ✅   ⛔️                 ⛔️
runrms                    ✅   ⛔️                 ⛔️
sector2fluxnum            ✅   ⛔️                 ⛔️
summaryplot               ✅   ⛔️                 ⛔️
sw_model_utilities        ✅   ⛔️                 ⛔️
sunsch                    ✅   ✅                 ⛔️
vfp2csv                   ✅   ⛔️                 ⛔️
welltest_dpds             ✅   ✅                 ⛔️
========================  ===  =================  ============

.. [*] ``convert_grid_format`` is the script that contains functionality
   for the ``ECLGRID2ROFF``, ``ECLINIT2ROFF``, and ``ECLRST2ROFF`` forward
   models.
