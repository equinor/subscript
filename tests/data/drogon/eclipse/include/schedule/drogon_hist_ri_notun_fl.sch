-- Producers
-- INCLUDE
--   '$RIWPATH/55_33-A-1_UnifiedCompletions_ECLIPSE' /
-- INCLUDE
--   '$RIWPATH/55_33-A-2_UnifiedCompletions_ECLIPSE' /
-- INCLUDE
--   '$RIWPATH/55_33-A-3_UnifiedCompletions_ECLIPSE' /
-- INCLUDE
--   '$RIWPATH/55_33-A-4_UnifiedCompletions_ECLIPSE' /
-- INCLUDE
--   '$RIWPATH/55_33-A-4_UnifiedCompletions_MSW_ECLIPSE' /	

-- -- Injectors
-- INCLUDE
--   '$RIWPATH/55_33-A-5_UnifiedCompletions_ECLIPSE' /
-- INCLUDE
--   '$RIWPATH/55_33-A-6_UnifiedCompletions_ECLIPSE' /

-- -- RFT wells
-- INCLUDE
--   '$RIWPATH/RFT_55_33-A-2_UnifiedCompletions_ECLIPSE' /
-- INCLUDE
--   '$RIWPATH/RFT_55_33-A-3_UnifiedCompletions_ECLIPSE' /
-- INCLUDE
--   '$RIWPATH/RFT_55_33-A-4_UnifiedCompletions_ECLIPSE' /
-- INCLUDE
--   '$RIWPATH/RFT_55_33-A-5_UnifiedCompletions_ECLIPSE' /
-- INCLUDE
--   '$RIWPATH/RFT_55_33-A-6_UnifiedCompletions_ECLIPSE' /

INCLUDE
  '../include/schedule/ri_wells.inc' /
--  '$RIWPATH/../ri_wells.inc' /

COMPORD
  '*' INPUT /
/

GRUPTREE
  'OP'      'FIELD' /
  'RFT'     'FIELD' /
  'WI'      'FIELD' /
/

WCONHIST
  'R_A*' SHUT ORAT 0 /
	'A1'  SHUT ORAT 0 /
	'A2'  SHUT ORAT 0 /
	'A3'  SHUT ORAT 0 /
	'A4'  SHUT ORAT 0 /
/

WCONINJH
  'A5' WATER SHUT 0 /
  'A6' WATER SHUT 0 /
/

WRFTPLT
--WELL    RFT   PLT   SEG
 'R_A2'   YES    NO    NO /
 'R_A3'   YES    NO    NO /
 'R_A4'   YES    NO    NO /
 'R_A5'   YES    NO    NO /
 'R_A6'   YES    NO    NO /
/

-- TUNING
-- -- TSINIT       TSMAXZ     TSMINZ     TSMCHP     TSFMAX     TSFMIN     TSFCNV     TFDIFF     THRUPT     TMAXWC
--           1         30         1*         1*         1*         1*         1*         1*         1*          1 /
-- -- TRGTTE       TRGCNV     TRGMBE     TRGLCV     XXXTTE     XXXCNV     XXXMBE     XXXLCV     XXXWFL
--          1*         1*         1*         1*         1*         1*         1*         1*         1* /
-- -- NEWTMX       NEWTMN     LITMAX     LITMIN     MXWSIT     MXWPIT
--          12          1         50          1         50         50 /

-- WSEGITER
--   200 20 /


RPTRST
 BASIC=4 FREQ=5 FLOWS NORST=1 FLORES /

DATES
 5 JAN 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV  3999.9895 0.01046396   563278.5    1*         1*         1*         1* /
/

DATES
 1 FEB 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98828 0.01173127  562930.75    1*         1*         1*         1* /
/

DATES
 1 MAR 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98804 0.01194996 559445.875    1*         1*         1*         1* /
/

WRFTPLT
--WELL    RFT   PLT   SEG
 'R_A2'   YES    NO    NO /
/

DATES
 10 MAR 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98804 0.01190207 555478.938    1*         1*         1*         1* /
 'A2'    OPEN  RESV 3998.90845 1.09144855 557876.625    1*         1*         1*         1* /
/

DATES
 30 MAR 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98804 0.01198202   552904.5    1*         1*         1*         1* /
 'A2'    OPEN  RESV 3998.86108 1.13892972   549982.5    1*         1*         1*         1* /
/

DATES
 1 APR 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98779 0.01214723 550678.438    1*         1*         1*         1* /
 'A2'    OPEN  RESV  3998.8457 1.15427291     541520    1*         1*         1*         1* /
/

DATES
 28 APR 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98779 0.01225858 549805.688    1*         1*         1*         1* /
 'A2'    OPEN  RESV 3998.81396 1.18605173 552031.063    1*         1*         1*         1* /
/

WRFTPLT
--WELL    RFT   PLT   SEG
 'R_A5'   YES    NO    NO /
/

DATES
 1 MAY 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98779  0.0122888 548860.438    1*         1*         1*         1* /
 'A2'    OPEN  RESV 3998.03076 1.96926403 564362.813    1*         1*         1*         1* /
/

DATES
 8 MAY 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98779 0.01216489 548021.313    1*         1*         1*         1* /
 'A2'    OPEN  RESV 3252.84009  133.61795 473783.719    1*         1*         1*         1* /
/

WCONINJH
--WELL  PHASE OP/SH       RATE        BHP        THP   VFP         CTL
 'A5'   WATER  OPEN       8000         1*         1*    1*    4*  RATE /
/

DATES
 1 JUN 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98804 0.01204866     548309    1*         1*         1*         1* /
 'A2'    OPEN  RESV 2367.14575 266.190521 363896.875    1*         1*         1*         1* /
/

DATES
 2 JUN 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98804 0.01201871  548413.25    1*         1*         1*         1* /
 'A2'    OPEN  RESV 2320.37622 288.573303 360967.719    1*         1*         1*         1* /
/

DATES
 8 JUN 2018 /
/

-- 25kg over 1 day with rate 8000 Sm3/d
WTRACER
-- 55_33-A-5
 A5  WT1  3.125 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98804 0.01199211 548500.938    1*         1*         1*         1* /
 'A2'    OPEN  RESV 2289.13623 308.386627 359407.906    1*         1*         1*         1* /
/

DATES
 9 JUN 2018 /
/

WTRACER
-- 55_33-A-5
 A5  WT1  0.0 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98804 0.01192498  548690.75    1*         1*         1*         1* /
 'A2'    OPEN  RESV 2214.33887  361.36554 352996.844    1*         1*         1*         1* /
/

DATES
 22 JUN 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98828 0.01183807 548896.313    1*         1*         1*         1* /
 'A2'    OPEN  RESV 2094.41846 432.391632 337377.563    1*         1*         1*         1* /
/

DATES
 30 JUN 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98828 0.01180832 548954.438    1*         1*         1*         1* /
 'A2'    OPEN  RESV 2048.48755 455.179474 330013.531    1*         1*         1*         1* /
/

RPTSCHED
  FIP=2 WELLS=0 /

RPTRST
 BASIC=2 DEN ROCKC RPORV RFIP FLOWS NORST=1 FLORES /

DATES
 1 JLY 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98828 0.01179739 548974.875    1*         1*         1*         1* /
 'A2'    OPEN  RESV 2031.80225 462.899078 327175.094    1*         1*         1*         1* /
/

RPTSCHED
  FIP=0 WELLS=0 /

RPTRST
 BASIC=0 /

DATES
 3 JLY 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98828 0.01175203 549050.188    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1972.14526  489.42215 316306.188    1*         1*         1*         1* /
/

WRFTPLT
--WELL    RFT   PLT   SEG
 'R_A3'   YES    NO    NO /
/

DATES
 13 JLY 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98828  0.0116675 549117.813    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1868.56238  528.61499 297787.156    1*         1*         1*         1* /
 'A3'    OPEN  RESV 3999.31543 0.68449342 538145.313    1*         1*         1*         1* /
/

DATES
 1 AUG 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98853 0.01158203   548983.5    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1755.96851 566.594543 276263.594    1*         1*         1*         1* /
 'A3'    OPEN  RESV 3999.25903 0.74095553 643722.688    1*         1*         1*         1* /
/

DATES
 25 AUG 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98853 0.01153841  548822.75    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1700.40942 585.502686 265439.063    1*         1*         1*         1* /
 'A3'    OPEN  RESV 3999.18701 0.81295449  792995.25    1*         1*         1*         1* /
/

DATES
 1 SEP 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98853 0.01152227 548699.563    1*         1*         1*         1* /
 'A2'    OPEN  RESV  1673.7832 592.851868 260747.391    1*         1*         1*         1* /
 'A3'    OPEN  RESV 3999.14185 0.85803682 906019.438    1*         1*         1*         1* /
/

DATES
 12 SEP 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98853  0.0115139  548602.25    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1657.58813 596.955322 258068.734    1*         1*         1*         1* /
 'A3'    OPEN  RESV  3999.1123  0.8875308 968189.875    1*         1*         1*         1* /
/

WRFTPLT
--WELL    RFT   PLT   SEG
 'R_A4'   YES    NO    NO /
/

DATES
 14 SEP 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98853 0.01150873 548504.688    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1645.29175 599.732788   255998.5    1*         1*         1*         1* /
 'A3'    OPEN  RESV 3999.09644 0.90362561 997838.625    1*         1*         1*         1* /
/

DATES
 22 SEP 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98853 0.01152343 548149.063    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1626.75391 603.420715 252895.531    1*         1*         1*         1* /
 'A3'    OPEN  RESV 3999.08569 0.91430873 1008678.88    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3998.38892 1.61111939 563054.438    1*         1*         1*         1* /
/

DATES
 1 OCT 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98853 0.01155542 547511.625    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1613.70776 605.397339 250939.563    1*         1*         1*         1* /
 'A3'    OPEN  RESV 3999.08179 0.91823024 1017155.94    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3999.95972  0.0403567 563274.313    1*         1*         1*         1* /
/

DATES
 5 OCT 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98828 0.01163088 545342.875    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1591.12781 606.189514 247795.703    1*         1*         1*         1* /
 'A3'    OPEN  RESV 3777.78418  4.2843914  951957.75    1*         1*         1*         1* /
 'A4'    OPEN  RESV  3999.9624 0.03755065 560799.938    1*         1*         1*         1* /
/

DATES
 1 NOV 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98828 0.01170644 543627.375    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1572.55859 604.647705 244998.625    1*         1*         1*         1* /
 'A3'    OPEN  RESV 3045.47925 43.6984138     634619    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3999.96362 0.03634704 556413.813    1*         1*         1*         1* /
/

DATES
 7 NOV 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98828  0.0117292 542560.625    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1566.90198 602.699707 243777.234    1*         1*         1*         1* /
 'A3'    OPEN  RESV 2701.05176 101.172859 513934.938    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3999.96411 0.03595892 553765.375    1*         1*         1*         1* /
/

WRFTPLT
--WELL    RFT   PLT   SEG
 'R_A6'   YES    NO    NO /
/

DATES
 17 NOV 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98828 0.01179661 540130.063    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1565.26575 604.899658 241281.734    1*         1*         1*         1* /
 'A3'    OPEN  RESV  2219.9353 236.568481 387707.531    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3999.96484 0.03527188 549732.188    1*         1*         1*         1* /
/

WCONINJH
--WELL  PHASE OP/SH       RATE        BHP        THP   VFP         CTL
 'A6'   WATER  OPEN       8000         1*         1*    1*    4*  RATE /
/

DATES
 1 DEC 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98804 0.01189484 539077.625    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1569.52502 609.066956 239856.453    1*         1*         1*         1* /
 'A3'    OPEN  RESV   2057.927 365.239075 331354.938    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3999.96558 0.03441242   547079.5    1*         1*         1*         1* /
/

DATES
 7 DEC 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98804 0.01191988   538717.5    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1575.09509   611.5578 239684.672    1*         1*         1*         1* /
 'A3'    OPEN  RESV 2047.55322 437.422668 313483.906    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3999.96606 0.03394911 545709.813    1*         1*         1*         1* /
/

DATES
 15 DEC 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98804 0.01193314 538344.375    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1579.28296 613.164856 239770.344    1*         1*         1*         1* /
 'A3'    OPEN  RESV 2053.37891 479.771881 305594.563    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3999.96606 0.03393355  544903.25    1*         1*         1*         1* /
/

DATES
 17 DEC 2018 /
/

-- 25kg over 1 day with rate 8000 Sm3/d
WTRACER
-- 55_33-A-6
 A6  WT2  3.125 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98804 0.01193703 538357.188    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1580.43945 613.587463 239824.484    1*         1*         1*         1* /
 'A3'    OPEN  RESV 2055.34253 490.308105 303893.031    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3999.96606 0.03394502 544701.375    1*         1*         1*         1* /
/

DATES
 18 DEC 2018 /
/

WTRACER
-- 55_33-A-6
 A6  WT2  0.0 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98804  0.0119545     537822    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1585.92114 615.672913 240243.672    1*         1*         1*         1* /
 'A3'    OPEN  RESV 2043.35376 538.115967 294207.313    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3999.96606 0.03402502   543742.5    1*         1*         1*         1* /
/

DATES
 28 DEC 2018 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98804  0.0119719 537098.625    1*         1*         1*         1* /
 'A2'    OPEN  RESV   1590.974 617.852173 240821.938    1*         1*         1*         1* /
 'A3'    OPEN  RESV 2007.26196 583.371704 283031.125    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3999.96582 0.03413038 542760.063    1*         1*         1*         1* /
/

DATES
 1 JAN 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98804 0.01201329 535818.625    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1597.97302 624.054993 242629.469    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1894.48682 699.640198 262325.219    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3999.94653 0.05334856 540320.563    1*         1*         1*         1* /
/

DATES
 1 FEB 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.98804 0.01208858  534385.75    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1599.77429 631.468323 244210.297    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1770.22449  823.12207 244940.281    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3988.39844 11.6017036 536168.125    1*         1*         1*         1* /
/

DATES
 9 FEB 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3999.45435 0.54581445 534102.375    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1596.56909  637.50769 244581.859    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1701.36377 890.289673 237416.234    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3840.16724 159.832825 514144.969    1*         1*         1*         1* /
/

DATES
 1 MAR 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3990.43262 9.56739998 534361.813    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1591.50525 643.636475 244510.141    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1648.13306 942.891907  232253.25    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3700.73901 299.260986 493920.125    1*         1*         1*         1* /
/

DATES
 9 MAR 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3975.66675 24.3333054 535467.813    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1586.30164 648.548462 244196.609    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1613.81042 976.811768 229299.531    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3585.63306 414.366852 477575.594    1*         1*         1*         1* /
/

DATES
 22 MAR 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3962.34814 37.6518288 539551.813    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1579.90356 653.899536 243660.813    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1577.11768  1009.1441 226502.719    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3492.67798 507.322021 464625.813    1*         1*         1*         1* /
/

DATES
 1 APR 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3927.69873 72.3012695  558563.25    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1566.57153 663.982178 242298.438    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1516.32544 1058.49939 223575.719    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3351.13452 648.865417 445306.563    1*         1*         1*         1* /
/

DATES
 1 MAY 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV          0          0          0    1*         1*         1*         1* /
 'A2'    OPEN  RESV          0          0          0    1*         1*         1*         1* /
 'A3'    OPEN  RESV          0          0          0    1*         1*         1*         1* /
 'A4'    OPEN  RESV          0          0          0    1*         1*         1*         1* /
/

WCONINJH
--WELL  PHASE OP/SH       RATE        BHP        THP   VFP         CTL
 'A5'   WATER  OPEN          0         1*         1*    1*    4*  RATE /
 'A6'   WATER  OPEN          0         1*         1*    1*    4*  RATE /
/

DATES
 4 MAY 2019 /
/

DATES
 5 MAY 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3876.40869 123.591362 566482.563    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1597.29724 687.544739 249163.391    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1522.07056 1152.00049 225040.703    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3193.48315 806.516846 425859.156    1*         1*         1*         1* /
/

WCONINJH
--WELL  PHASE OP/SH       RATE        BHP        THP   VFP         CTL
 'A5'   WATER  OPEN       8000         1*         1*    1*    4*  RATE /
 'A6'   WATER  OPEN       8000         1*         1*    1*    4*  RATE /
/

DATES
 24 MAY 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV  3848.2085 151.791382 589391.625    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1549.68604 684.721924 242150.813    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1449.44714  1136.4281 226563.031    1*         1*         1*         1* /
 'A4'    OPEN  RESV 3120.33276 879.667175 415393.188    1*         1*         1*         1* /
/

DATES
 1 JUN 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3827.82935 172.170761 606056.125    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1533.81604  691.15863 239458.703    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1421.28906 1147.63147 227867.219    1*         1*         1*         1* /
 'A4'    OPEN  RESV  3064.2334 935.766724 411152.906    1*         1*         1*         1* /
/

DATES
 14 JUN 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3804.16333 195.836624 624977.688    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1518.06494 699.196899 237365.031    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1391.61731 1166.80688 226561.578    1*         1*         1*         1* /
 'A4'    OPEN  RESV 2994.20337 1005.79657 403562.406    1*         1*         1*         1* /
/

DATES
 30 JUN 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3792.61279 207.387222 633460.813    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1511.03613 703.192017 236356.109    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1378.89795 1176.75281 225310.594    1*         1*         1*         1* /
 'A4'    OPEN  RESV 2936.14355 1063.85645 396648.281    1*         1*         1*         1* /
/

RPTSCHED
  FIP=2 WELLS=0 /

RPTRST
 BASIC=2 DEN ROCKC RPORV RFIP FLOWS NORST=1 FLORES /

DATES
 1 JLY 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3771.18213 228.817932 647367.938    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1498.30872 710.865356 234322.344    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1359.59937 1194.32544  222327.25    1*         1*         1*         1* /
 'A4'    OPEN  RESV 2789.32104 1210.67883 376566.563    1*         1*         1*         1* /
/

RPTSCHED
  FIP=0 WELLS=0 /

RPTRST
 BASIC=0 /

DATES
 27 JLY 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3749.53003 250.469894  660348.75    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1485.08545  718.83136 232329.516    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1342.22644 1211.48352 219064.281    1*         1*         1*         1* /
 'A4'    OPEN  RESV 2637.18457 1362.81543 355921.031    1*         1*         1*         1* /
/

DATES
 1 AUG 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3734.11816 265.881836 668258.813    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1475.77759 724.308838 231105.391    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1331.35535 1222.35339 216637.563    1*         1*         1*         1* /
 'A4'    OPEN  RESV 2574.37109 1425.62903 347602.375    1*         1*         1*         1* /
/

DATES
 16 AUG 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3710.44336 289.556641 684989.125    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1464.71655 730.747498 229724.594    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1319.03223 1234.10376 213869.063    1*         1*         1*         1* /
 'A4'    OPEN  RESV 2518.67578 1481.32422 340194.906    1*         1*         1*         1* /
/

DATES
 24 AUG 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3681.52246 318.477539  703226.25    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1458.29785 734.494995 228937.531    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1312.14063 1240.16052 212275.422    1*         1*         1*         1* /
 'A4'    OPEN  RESV 2492.52856 1507.47131 336840.688    1*         1*         1*         1* /
/

DATES
 1 SEP 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3638.32739 361.672699 721560.938    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1452.35522 738.021118 228205.406    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1305.78784 1245.32043 210830.109    1*         1*         1*         1* /
 'A4'    OPEN  RESV   2471.073 1528.92688 334120.563    1*         1*         1*         1* /
/

DATES
 6 SEP 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3510.09155 489.908569   737026.5    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1438.56433 746.250305     226473    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1291.68713 1255.00745 207513.453    1*         1*         1*         1* /
 'A4'    OPEN  RESV 2427.31128  1572.6886 328600.781    1*         1*         1*         1* /
/

DATES
 1 OCT 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3323.31592 676.684204 711349.313    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1418.99524 758.149902 223915.406    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1270.18689 1263.45288 202419.344    1*         1*         1*         1* /
 'A4'    OPEN  RESV 2369.31445 1630.68567 321294.375    1*         1*         1*         1* /
/

DATES
 19 OCT 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV  3234.2373 765.762756 686131.938    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1405.25696 767.045044 222038.656    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1255.01782 1267.71106 198723.328    1*         1*         1*         1* /
 'A4'    OPEN  RESV 2327.72632 1672.27356 315784.563    1*         1*         1*         1* /
/

DATES
 1 NOV 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV          0          0          0    1*         1*         1*         1* /
 'A2'    OPEN  RESV          0          0          0    1*         1*         1*         1* /
 'A3'    OPEN  RESV          0          0          0    1*         1*         1*         1* /
 'A4'    OPEN  RESV          0          0          0    1*         1*         1*         1* /
/

WCONINJH
--WELL  PHASE OP/SH       RATE        BHP        THP   VFP         CTL
 'A5'   WATER  OPEN          0         1*         1*    1*    4*  RATE /
 'A6'   WATER  OPEN          0         1*         1*    1*    4*  RATE /
/

DATES
 2 NOV 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3172.63916  827.36084 639673.563    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1416.68066 783.946289 223371.891    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1271.66711 1296.96948 195164.063    1*         1*         1*         1* /
 'A4'    OPEN  RESV 2303.01343 1696.98657 312427.031    1*         1*         1*         1* /
/

WCONINJH
--WELL  PHASE OP/SH       RATE        BHP        THP   VFP         CTL
 'A5'   WATER  OPEN       8000         1*         1*    1*    4*  RATE /
 'A6'   WATER  OPEN       8000         1*         1*    1*    4*  RATE /
/

DATES
 8 NOV 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3143.18604 856.814026 637083.563    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1399.19897 778.139771 222045.547    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1256.56067 1281.89771 195644.328    1*         1*         1*         1* /
 'A4'    OPEN  RESV 2275.78882 1724.21118 308180.813    1*         1*         1*         1* /
/

DATES
 16 NOV 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3087.55811 912.441833 625077.875    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1385.23218 783.118042 220022.281    1*         1*         1*         1* /
 'A3'    OPEN  RESV   1243.677 1279.53711     194675    1*         1*         1*         1* /
 'A4'    OPEN  RESV 2233.90869 1766.09143 301915.156    1*         1*         1*         1* /
/

DATES
 29 NOV 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 3048.02832 951.971619 614447.563    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1377.62744 787.372498 218735.344    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1237.11365 1280.48987 193865.547    1*         1*         1*         1* /
 'A4'    OPEN  RESV 2206.61792 1793.38196 298490.094    1*         1*         1*         1* /
/

DATES
 1 DEC 2019 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 2942.80933 1057.19067 581114.438    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1362.15857 798.075684 216617.672    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1223.29834 1286.81079 191095.203    1*         1*         1*         1* /
 'A4'    OPEN  RESV 2147.23511 1852.76477 290121.719    1*         1*         1*         1* /
/

DATES
 1 JAN 2020 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 2807.17383 1192.82605     536416    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1345.53455 811.305969 214192.484    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1209.65979 1296.30786 186902.813    1*         1*         1*         1* /
 'A4'    OPEN  RESV 2082.39502 1917.60498   281177.5    1*         1*         1*         1* /
/

DATES
 11 JAN 2020 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 2721.91187 1278.08826 506267.344    1*         1*         1*         1* /
 'A2'    OPEN  RESV   1334.755 821.127808 212483.375    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1201.00745 1303.75879 183629.844    1*         1*         1*         1* /
 'A4'    OPEN  RESV 2043.38013    1956.62 275790.656    1*         1*         1*         1* /
/

DATES
 31 JAN 2020 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 2674.17212 1325.82776 488282.219    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1328.47168 827.208435 211493.875    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1195.91907 1308.36646 181668.703    1*         1*         1*         1* /
 'A4'    OPEN  RESV 2021.94714 1978.05286 272838.125    1*         1*         1*         1* /
/

DATES
 1 FEB 2020 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 2648.99634 1351.00366 478628.844    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1325.18518 830.657471 210994.344    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1193.24023 1311.08765 180621.656    1*         1*         1*         1* /
 'A4'    OPEN  RESV  2011.3291  1988.6709 271421.344    1*         1*         1*         1* /
/

DATES
 8 FEB 2020 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 2593.17627 1406.82385   458543.5    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1318.93018 837.627258 210054.859    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1187.93066 1316.50732 178672.734    1*         1*         1*         1* /
 'A4'    OPEN  RESV 1992.20593 2007.79407 268881.219    1*         1*         1*         1* /
/

DATES
 21 FEB 2020 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 2525.94556 1474.05457 435413.625    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1312.76196 845.093811 209114.828    1*         1*         1*         1* /
 'A3'    OPEN  RESV  1182.4718 1322.10791 176763.719    1*         1*         1*         1* /
 'A4'    OPEN  RESV 1974.11804 2025.88196 266450.719    1*         1*         1*         1* /
/

DATES
 1 MAR 2020 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 2392.54443 1607.45544 390659.125    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1303.09399 859.976013 207572.094    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1172.33911 1332.95349 173565.016    1*         1*         1*         1* /
 'A4'    OPEN  RESV  1944.0498  2055.9502 262389.313    1*         1*         1*         1* /
/

DATES
 1 APR 2020 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 2289.25537 1710.74451 356367.281    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1296.56995 872.941589 206486.094    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1163.89807 1341.91687  171017.25    1*         1*         1*         1* /
 'A4'    OPEN  RESV 1920.26685 2079.73315 259165.734    1*         1*         1*         1* /
/

DATES
 4 APR 2020 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 2215.30371 1784.69629     335333    1*         1*         1*         1* /
 'A2'    OPEN  RESV  1294.0177 882.684143 206020.438    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1158.07861 1348.51318 169433.313    1*         1*         1*         1* /
 'A4'    OPEN  RESV 1904.13245 2095.86743 256960.078    1*         1*         1*         1* /
/

DATES
 24 APR 2020 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 2126.27124 1873.72876 311949.875    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1292.67358 894.752686 205741.719    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1151.78809 1356.39575 167820.391    1*         1*         1*         1* /
 'A4'    OPEN  RESV 1886.06848 2113.93164 254509.469    1*         1*         1*         1* /
/

DATES
 1 MAY 2020 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV          0          0          0    1*         1*         1*         1* /
 'A2'    OPEN  RESV          0          0          0    1*         1*         1*         1* /
 'A3'    OPEN  RESV          0          0          0    1*         1*         1*         1* /
 'A4'    OPEN  RESV          0          0          0    1*         1*         1*         1* /
/

WCONINJH
--WELL  PHASE OP/SH       RATE        BHP        THP   VFP         CTL
 'A5'   WATER  OPEN          0         1*         1*    1*    4*  RATE /
 'A6'   WATER  OPEN          0         1*         1*    1*    4*  RATE /
/

DATES
 2 MAY 2020 /
/

DATES
 5 MAY 2020 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 1762.09607 2237.90405 238855.703    1*         1*         1*         1* /
 'A2'    OPEN  RESV  1359.6792 940.251099 215853.172    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1195.63831 1449.67932 165997.781    1*         1*         1*         1* /
 'A4'    OPEN  RESV 1845.60669 2154.39331 249710.234    1*         1*         1*         1* /
/

WCONINJH
--WELL  PHASE OP/SH       RATE        BHP        THP   VFP         CTL
 'A5'   WATER  OPEN       8000         1*         1*    1*    4*  RATE /
 'A6'   WATER  OPEN       8000         1*         1*    1*    4*  RATE /
/

DATES
 15 MAY 2020 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 1880.98889 2119.01099 257948.125    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1318.06689  931.15979  211670.75    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1148.06421 1384.01355 167351.797    1*         1*         1*         1* /
 'A4'    OPEN  RESV 1881.04968 2118.95044 254340.547    1*         1*         1*         1* /
/

DATES
 1 JUN 2020 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 1800.71265 2199.28735 239597.391    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1312.44312  984.85498 210726.531    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1115.60596 1381.58081 165085.781    1*         1*         1*         1* /
 'A4'    OPEN  RESV 1846.33459 2153.66528 249336.297    1*         1*         1*         1* /
/

DATES
 27 JUN 2020 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV   1722.625   2277.375 224937.641    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1318.88147   1035.495 211451.516    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1100.93286 1387.04382 162808.797    1*         1*         1*         1* /
 'A4'    OPEN  RESV 1824.04443 2175.95557 246256.984    1*         1*         1*         1* /
/

DATES
 30 JUN 2020 /
/

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 1716.85278 2283.14722 223893.953    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1319.60852  1040.1532 211521.656    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1100.02966 1387.47205 162594.109    1*         1*         1*         1* /
 'A4'    OPEN  RESV 1822.49243 2177.50757 246058.859    1*         1*         1*         1* /
/

RPTSCHED
  FIP=2 WELLS=0 /

RPTRST
 BASIC=2 DEN ROCKC RPORV RFIP FLOWS NORST=1 FLORES /

DATES
 1 JLY 2020 /
/

--------------
SAVE
--------------

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    OPEN  RESV 1711.04138  2288.9585 222848.125    1*         1*         1*         1* /
 'A2'    OPEN  RESV 1320.36243 1044.99292 211598.484    1*         1*         1*         1* /
 'A3'    OPEN  RESV 1099.16235 1387.92432 162394.953    1*         1*         1*         1* /
 'A4'    OPEN  RESV 1820.97083  2179.0293 245861.344    1*         1*         1*         1* /
/

RPTSCHED
  FIP=0 WELLS=0 /

RPTRST
 BASIC=0 /

DATES
 2 JLY 2020 /
/

--------------
END
--------------

WCONHIST
--WELL  OP/SH   CTL       ORAT       WRAT       GRAT   VFP        ALQ        THP        BHP
 'A1'    SHUT  ORAT          0         1*         1*    1*         1*         1*         1* /
 'A2'    SHUT  ORAT          0         1*         1*    1*         1*         1*         1* /
 'A3'    SHUT  ORAT          0         1*         1*    1*         1*         1*         1* /
 'A4'    SHUT  ORAT          0         1*         1*    1*         1*         1*         1* /
/

WCONINJH
--WELL  PHASE OP/SH       RATE        BHP        THP   VFP         CTL
 'A5'   WATER  SHUT          0         1*         1*    1*    4*  RATE /
 'A6'   WATER  SHUT          0         1*         1*    1*    4*  RATE /
/
