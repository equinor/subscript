Folder:  subscript/tests/testdata_prtvol2csv
This folder contains test data for testdata_prtvol2csv.py

Print files (.PRT) from Eclipse, 
made with RPTSOL keyword with FIP=2 and FIP=3,
and in addition FIPRESV for reservoir volumes.

Both PRT files have reservoir volumes.
One additional FIP vector in the second file, named FIPZON.

DROGON_FIPNUM.PRT       - Eclipse version 2022.2, FIP=2 (FIPNUM only, 4 reports)
DROGON_FIPZON.PRT       - Eclipse version 2022.2, FIP=3 (all FIP-vectors)
DROGON_INACTIVE_FIPNUM.PRT -  with FIPNUM 5 as inactive
DROGON_NO_INITIAL_BALANCE.PRT       - Eclipse version 2025.1, FIP=2 (FIPNUM only, no initial BALANCE report)
                                    first BALANCE report after 6 months, no RESERVOIR VOLUMES reports
DROGON_NO_INITIAL_BALANCE_FLOW.PRT  - OPM Flow version 2025.10-pre, no initial BALANCE report
                                    FIP=3 (FIP*, all FIP vectors, one RESERVOIR VOLUMES report)
