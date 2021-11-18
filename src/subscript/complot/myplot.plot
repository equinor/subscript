
-- This is the plot file for the SegmentPlot routine


DATAFILE
-- The eclipse data file (without .DATA) only the file name
-- '/project/CommonPPL/WellBuilder/Test_cases/boxmodels/eclipse/model/2d_tilted/models/AICD_OA_WRFTPLT'
 '/project/byron2/mariner/resmod/ff/2019a/users/asuf/eclipse_apr2020_icd/eclipse/model/AMPJ-ICD-4V-4PK-TKLOV'
/

WELLFILE
-- The schedule/well file, which contains WELSEGS and COMPSEGS
-- '/project/CommonPPL/WellBuilder/Test_cases/boxmodels/eclipse/model/2d_tilted/schedule/aicd_oa_wrftplt.sch'
 '/project/byron2/mariner/resmod/ff/2019a/users/asuf/eclipse_apr2020_icd/eclipse/include/WellBuilder/ampj-icd-4v-4pk.sch'
/

OUTPUTFILE
-- If you want to export it in a csv file then fill this with the name of the file
-- leave it blank if you dont want to export output file
'df_export.csv'
/

INFORMATION
-- WELL : Specify the well name
-- LATERAL : the lateral branch number e.g. 1, 2, 3, etc.
-- TUBINGSEGMENT : Specify the number of the tubing segments (the first layer)
-- 		 : start_segment-end_segment
-- DEVICESEGMENT : Specify the number of the device segments (the second layer)
-- 		 : start_segment-end_segment
-- ANNULUSSEGMENT : Specify the number of the annulus segments (the third layer)
-- 		  : start_segment-end_segment0
-- DAYS : Specify the day of which you would like to see the results
-- DAYS : if you want to display multiple days then separate them with "-"
-- Any irrelevant columns e.g. annulus segment then fill with 1*

-- WELL     LATERAL      TUBINGSEGMENT       DEVICESEGMENT          ANNULUSSEGMENT        DAYS
-- WELL             1               2-36               37-71                  72-106           550
   AMPJ           1               2-48               49-95                  96-142          1000
/







