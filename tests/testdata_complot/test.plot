DATAFILE
-- The eclipse data file (without .DATA) only the file name
   tests/data/TEST
/

WELLFILE
-- The schedule/well file, which contains WELSEGS and COMPSEGS
   tests/data/aicd_wrftplt.sch
/

OUTPUTFILE
-- If you want to export it in a csv file then fill this with the name of the file
-- leave it blank if you dont want to export output file
   'tests/data/df_export.csv'
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
   WELL           1               2-36               37-71                     1*            1
/







