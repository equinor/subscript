#!/usr/bin/perl
#Extract Reservoir volumes from PRT file
#Writes data to a new file (user defined name)
#Volume data are output with a space seperator for compatibility with ert volume workflow jobs
#
#To run script: 
# >perl  extract_resvol_from_prtfile.pl <input_prt_file> <result_file>
 
#Author: Roger Nybo
 
# Roger Nybo - May 2016    Edited script to create correct input format for ert volume workflow job
#                          Now also adds a report line for non-present fipnum regions which will occur for inactive regions (0 volume)
#                          This will ensure a more robust, non-repeatable, set-up of the ert volume job config file
# Roger Nybo - Aug 2016    Edited script to extract reservoir volume data (note: add FIPRESV to Eclipse RPTSOL keyword)
#                          Output file will have 7 header lines (same as for script that extracts volumes at standard cond)
 
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
    if ($line =~ /^\s*:\s*RESERVOIR VOLUMES/)		#look for reservoir volume output
    {
	$check="found";
	print F_VOL "Reservoir volumes extracted from eclipse prt file:\n";	
	print F_VOL "$ARGV[0]\n";	
 
	while($line !~ /^\s*={40,}/) 	#Continue until end of res vol table
	{
	    $line=<F_PRT>;               
	    @data=split(':', $line  );   #Split line into elements seperated by colon (:)
 
	    print F_VOL "$data[1]  $data[2]  $data[3]  $data[4]  $data[5]  $data[6] \n";	
	}		
    }
}
 
 
 
 
#print status to screen	
print "\n------ Reservoir volume table was $check in the \"$ARGV[0]\" file\n";
 
if ($check !~ /not found/)
{
   print "------ and extracted volumes have been written to the file \"$ARGV[1]\"\n\n";
}
else
{
    print "------ Are you sure \"$ARGV[0]\" is a PRT file containing reservoir volume data?\n\n";
    print "------ Make sure the RPTSOL keyword is set up properly in your eclipse data file:\n";
    print "------ RPTSOL\n";
    print "------    FIP=2  'FIPRESV' /\n\n";
}
 
close(F_PRT);
close(F_VOL);
