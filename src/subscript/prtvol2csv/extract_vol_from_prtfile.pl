#!/usr/bin/perl
# Extract FIELD and FIPNUM volumes from PRT file at initial time step (day 0)
# Writes data to a new file (user defined name)
# Volume data are output with a space seperator for compatibility with ert volume workflow jobs
#
# To run script:
# > perl  extract_prt_file_vol.pl <input_prt_file> <result_file>

# Author: Roger Nybo

# Roger Nybo - May 2016    Edited script to create correct input format for ert volume workflow job
#                          Now also adds a report line for non-present fipnum regions which will occur for inactive regions (0 volume)
#                          This will ensure a more robust set-up of the ert volume job config file

#Simple check; have user entered 2 arguments?
if (!defined($ARGV[1]))
{
    print "\n--------------  Error! You need to enter 2 arguments \n";
    die "--------------  Syntax is: \>perl  extract_prt_file_vol.pl <input_prt_file> <result_file> \n\n";
}

#Open PRT file for reading
open(F_PRT,"<","$ARGV[0]");
#Open result file for writing
open(F_VOL,">","$ARGV[1]");


my $line;
my $line2;
my $region;
my @data;
my @vol;
my @vol_oil;
my @vol_wat;
my @vol_gas;
my $check = "not found";
my $region_counter = 0;
my $region_number = 0;

#Start reading from PRT-file
OUTER: while($line=<F_PRT>)
{
    if ($line =~ /^\s*\S*\s* ECHO OF INPUT DATA FOR RUN/)       #  Find line with run name info  \*\*\*\*\*\*\*\*
    {
        my @run_name=split(' +', $line  );                      # Split line into elements seperated by white spaces
        print F_VOL "Run name: $run_name[8]\n";                 # Write run name to output file
    }

    if ($line =~ /^\s*BALANCE  AT      0/)                      # Check if line starts with "  BALANCE  AT      0"  (2014.1 --> 6 spaces between AT and 0)
    {
        $check = "found";
        $line2=<F_PRT>;                                         # Read next line (--> $line2)

        # Write info and header
        print F_VOL $line;                                      # info (days)
        print F_VOL "$line2\n";                                 # info (date)

        print F_VOL "          :--------------- OIL    SM3  ---------------:::-- WAT    SM3  --:--------------- GAS    SM3  ---------------\n";
        print F_VOL "FIP-REGION:LIQUID:VAPOUR:TOTAL:TOTAL:FREE:DISSOLVED:TOTAL\n";


        $line=<F_PRT>;                                          # Read next line

        while($line !~ /^\s*BALANCE|^\s*Error summary/)         # Continue until next BALANCE (t>0) or until end of file if only one BALANCE in file
        {
            if ($line =~ /^\s*:\s*PAV =/)                       # FIPNUM info is found in line above this one (i.e. in previous line = $line2)
            {
                @data=split(':', $line2  );                     # Split previous line ($line2) into elements seperated by colon (:)
                $region="$data[1]";                             # Extract fip/field info
                @data=split(' +', $region );                    # Split text string into elements seperated by blanks
                $region="$data[1] $data[2] $data[3] $data[4] "; # and redefine string, now without long blank sections
		        if ($region =~ /^FIELD/)
                {
                    $region = "FIELD TOTALS REGION NaN ";       # make same format for field total as for fipnum regions - re ert vol workflow
                }
                    else
                    {
                        $region_number=$data[4];                # get fipnum region number. use to detect non-present fipnum regions (i.e. inactivated fipnum regions)
                        $region_counter = $region_counter + 1;
                    }
            }

            while ($region_counter < $region_number)
            {
                print F_VOL "FIPNUM REPORT REGION $region_counter    0    0   0    0   0    0   0  \n";  # print 0 values for any non-present fipnum regions
                    $region_counter = $region_counter + 1;
            }

            if ($line =~ /^\s*:CURRENTLY IN PLACE/)             #This is the line containing volumes
            {
                @vol=split(':', $line  );                   # Split line into elements seperated by colon (:)
                @vol_oil=split(' +', $vol[2]  );            # oil volumes (extract by splitting elements seperated by white spaces)
                @vol_wat=split(' +', $vol[3]  );            # water volume (extract by splitting elements seperated by white spaces)
                @vol_gas=split(' +', $vol[4]  );            # gas volumes (extract by splitting elements seperated by white spaces)

                if ($vol_oil[3] < 0.00001)                  # For older versions of e100: if Rv=0 it is reported blank instead of 0 under VAPOUR. Check for this and fix.
                {
                   $vol_oil[3]=$vol_oil[2];                 # Move total to third item
                   $vol_oil[2]=0;                           # Set second item to zero (vapour)
                }

                # Print fipnum region and volumes to file
                # print F_VOL "$region : $vol_oil[1] :  $vol_oil[2] : $vol_oil[3] :  $vol_wat[1] : $vol_gas[1] :  $vol_gas[2] : $vol_gas[3]  \n";
                # changed to space seperator - re ert vol workflow
                print F_VOL "$region   $vol_oil[1]    $vol_oil[2]   $vol_oil[3]    $vol_wat[1]   $vol_gas[1]    $vol_gas[2]   $vol_gas[3]  \n";
            }
            $line2=$line;   # Update $line2 (ready for next loop where it will act as the previous line)
            $line=<F_PRT>;  # Read next line
        }
    }
#    last OUTER if $line =~  /^\s*BALANCE  AT/;                 #End while if second BALANCE is found --> redundant (already taken care of in the inner while loop)
}

#print status to screen
print "\n------ A balance sheet at day 0 was $check in the \"$ARGV[0]\" file\n";

if ($check !~ /not found/)
{
   print "------ and extracted volumes has been written to the file \"$ARGV[1]\"\n\n";
}
else
{
    print "------ Are you sure \"$ARGV[0]\" is a PRT file containing any volume data?\n\n";
    print "------ Make sure the RPTSOL keyword is set up properly in your eclipse data file:\n";
    print "------ RPTSOL\n";
    print "------    FIP=2  'FIPRESV' /\n\n";
}

close(F_PRT);
close(F_VOL);
