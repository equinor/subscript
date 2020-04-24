# -*- coding: utf-8 -*-
"""
Created on Tue Apr 09 09:23:58 2019

@author: IARI
"""


WBABOUT = """
About WellBuilder
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------

This is a program which model actual well completion for Eclipse.
This script generates all necessary keywords for Eclipse simulation according to the actual well completion description.
This job was previously performed by a script called icd_helper. However, the icd_helper script can only model limited completion designs.

WellBuilder has better functionalities than icd_helper such as follow:
    
1. icd_helper assumes that completed cells are isolated (no annular flow). This case is only applicable for a well with gravel pack annulus
   or a well with packers separating the grid cells. WellBuilder, on the other hand, can handle various well completion scenarios e.g.
   gravel pack annulus, open annulus, annulus with packers at arbitrary locations, a combination of annulus filled with gravel pack, open annulus or with packers.
   
2. WellBuilder can also model a partial completion joint. A screen joint with partial completion means that it contains  a portion of blank pipes. 
   This will not give impacts if the annulus is open, but if the annulus is filled with gravel pack (no annular flow) then 
   the fluid will flow only from the reservoir section adjacent to the screen section/micro annulus.
   WellBuilder models this phenomenon by reducing the transmissibility factor of the cell.
   
3. WellBuilder can model new generation of inflow control devices such as DAR, AICV and ICVs technology.

Oslo 2019
Ibnu Hafidz Arief
iari@equinor.com
+47 907 326 89

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        """

WBHELP = """
        
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        
Execute WellBuilder with the following command
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
WellBuilder -help -about -i input.case -s ../include/schedule/input.wells -p ../include/props/pvt.inc -o ../include/schedule/output.wells -figure    
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Required:
---------
-i      : followed by full definition of a WellBuilder case file (with extension)
-s      : followed by full definition of a schedule file (which contains basic COMPDAT, COMPSEGS and WELSEGS) (required if it is not specified in the case file)
-p      : followed by full definition of a pvt file (required if it is not specified in the case file)

Optional:
---------    
-help   : how to run the program
-about  : about WellBuilder
-o      : followed by full definition of  WellBuilder output file
-figure : ask the program to generate a pdf file which contains the well's schematic diagram

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        """

WBVERSION = "1.0"
