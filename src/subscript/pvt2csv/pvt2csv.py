#!/usr/bin/env python
#
# pvt22csv
# 
# Usage:
#   pvt2csv <pvtfile1> [<pvtfile2>] ... 
#
# Parses Eclipse 100 PVT input files into CSV files suitable
# for analysis in Pandas and/or Spotfire
#
# Haavard Berland, DPN OTE PTC MOD MW, April 2017, havb@statoil.com

import pandas
import re
import argparse

import resscript.header as header

header.compose("pvt2csv.py", 
               "April 2017", 
               ["Havard Berland"], 
               ["havb@statoil.com"], 
               ["Access help with -h"], 
               "Convert Eclipse 100 PVT files into CSV files")

parser = argparse.ArgumentParser()
parser.add_argument("pvtfiles", nargs="+", help="PVT files containing PVT keywords")
parser.add_argument("-o", "--output", type=str, help="name of output csv file", default="pvt.csv")
args = parser.parse_args()

columnnames = { 
    'DENSITY' : ['pvtnum', 'oildensity', 'waterdensity', 'gasdensity'],
    'PVTW'    : ['pvtnum', 'pressure', 'volumefactor', 'compressibility', 'viscosity', 'viscosibility'],
    'PVTO'    : ['pvtnum', 'GOR', 'pressure', 'volumefactor', 'viscosity'],
    'PVTG'    : ['pvtnum', 'pressure', 'Rv', 'volumefactor', 'viscosity'], 
    'PVDG'    : ['pvtnum', 'pressure', 'volumefactor', 'viscosity'],
    'ROCK'    : ['pvtnum', 'pressure', 'compressibility']
    } 

# Used for parsing, to check if a string can be parsed as a floating point number
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


tables_each_file = []
for filename in args.pvtfiles:
    print " ** Parsing", filename

    lines = open(filename).readlines()

    # Strip newlines, comments and empty lines:
    lines = [x.strip() for x in lines]
    lines = [x.split('--')[0] for x in lines]
    lines = [x for x in lines if x!=""]

    # Now we go through the file with a state machine holding which keyword is active

    active_ecl_keyword = ''
    current_GOR = 0
    current_Pg = 0


    density_df = pandas.DataFrame(columns = columnnames['DENSITY'])
    pvtw_df    = pandas.DataFrame(columns = columnnames['PVTW'])
    pvto_df    = pandas.DataFrame(columns = columnnames['PVTO'])
    pvtg_df    = pandas.DataFrame(columns = columnnames['PVTG'])
    pvdg_df    = pandas.DataFrame(columns = columnnames['PVDG'])
    rock_df    = pandas.DataFrame(columns = columnnames['ROCK'])


    ecl_keyword_re = re.compile("^[A-Z]+\s*.*")
    unknownkeywordwarning = False
    for line in lines:
        

        # Changing to next keyword?
        if ecl_keyword_re.match(line):
            active_ecl_keyword = line.split(' ')[0]
            current_pvtnum = 1
            unknownkeywordwarning = False
            continue  #Hope user has not written more data on the keyword line.
            
        if active_ecl_keyword == 'DENSITY':
            # Check if we have a record with three numbers:
            if map(is_number, line.split()[0:3]) == [True, True, True] and line.split()[3] == '/':
                density_df.loc[len(density_df)+1] = [current_pvtnum] + map(float, line.split()[0:3])
                current_pvtnum += 1
                continue  # If we forget this continue, the script will think we did not understand the keyword
        
        if active_ecl_keyword == 'PVTW':
            if map(is_number, line.split()[0:5]) == [True, True, True, True, True] and line.split()[5] == '/':
                pvtw_df.loc[len(pvtw_df)+1] = [current_pvtnum] + map(float, line.split()[0:5])
                current_pvtnum += 1
                continue
            
            # Item 5 (dCw - viscosibility) is sometimes skipped, then it is defaulted to zero.
            if map(is_number, line.split()[0:4]) == [True, True, True, True] and line.split()[4] == '/':
                pvtw_df.loc[len(pvtw_df)+1] = [current_pvtnum] + map(float, line.split()[0:4]) + [ 0.0 ]
                current_pvtnum += 1
                continue
        
        if active_ecl_keyword == 'PVTO':
            # Special consideration for undersaturated oil must be done.

            # 4 numbers on a line is a new GOR.
            if map(is_number, line.split()[0:4]) == [True, True, True, True]: 
                current_GOR = float(line.split()[0])
                pvto_df.loc[len(pvto_df)+1] = [current_pvtnum] + map(float, line.split()[0:4])
                continue

            # 3 numbers and trailing slash or not means to use the current_GOR (undersaturated line)
            if map(is_number, line.split()[0:3]) == [True, True, True]:
                pvto_df.loc[len(pvto_df)+1] = [current_pvtnum, current_GOR] + map(float, line.split()[0:3])
                continue

        # Single slash means go to the next PVTNUM
        if line.split()[0] == '/':
            current_pvtnum += 1
            continue
            
        if active_ecl_keyword == 'PVTG':
            # Special consideration for undersaturated oil must be done.

            # 4 numbers is a new GOR
            if map(is_number, line.split()[0:4]) == [True, True, True, True]: 
                current_Pg = float(line.split()[0])
                pvtg_df.loc[len(pvtg_df)+1] = [current_pvtnum] + map(float, line.split()[0:4])
                continue

            # 3 numbers and trailing slash or not means to use the current_GOR (undersaturated line)
            if map(is_number, line.split()[0:3]) == [True, True, True]:
                pvtg_df.loc[len(pvtg_df)+1] = [current_pvtnum, current_Pg] + map(float, line.split()[0:3])
                continue

        if active_ecl_keyword == 'PVDG':
            # 3 numbers and no trailing slash 
            if map(is_number, line.split()[0:3]) == [True, True, True]:
                pvdg_df.loc[len(pvdg_df)+1] = [current_pvtnum] + map(float, line.split()[0:3])
                continue
            
        if active_ecl_keyword == 'ROCK':
            # 2 numbers and trailing slash
            if map(is_number, line.split()[0:2]) == [True, True] and line.split()[2] == '/':
                rock_df.loc[len(rock_df)+1] = [current_pvtnum] + map(float, line.split()[0:2])
                current_pvtnum += 1
                continue


        print "Info: Keyword " + active_ecl_keyword + " ignored. Unknown or unsupported syntax."
        unknownkeywordwarningprinted = True

    density_df['keyword'] = "DENSITY"
    pvto_df['keyword'] = "PVTO"
    pvtg_df['keyword'] = "PVTG"
    pvtw_df['keyword'] = "PVTW"
    pvdg_df['keyword'] = "PVDG"
    rock_df['keyword'] = "ROCK"

    file_df = pandas.concat([density_df, pvto_df, pvtg_df, pvtw_df, pvdg_df, rock_df], sort=False)
    
    file_df['filename'] = filename
    
    tables_each_file.append(file_df)

allfiles_df = pandas.concat(tables_each_file)
allfiles_df.to_csv(args.output, index=False)

            
                
                       
    
