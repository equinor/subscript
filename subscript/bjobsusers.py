#!/usr/bin/env python2.7
#
# Print list of users running on cluster, sorted by 
# number of jobs.
# 
# Author: vkip
# Based on: bash-fu by havb

import subprocess, string, re, pandas

def get_jobs(status='RUN'):
    cmd = "bjobs -u all | grep %s | awk '{print $2,$6;}'" % (status)
    rex = re.compile('.*(\d+)\*.*')
    slines = [ string.split(l) for l in string.split( string.strip( subprocess.check_output(cmd, shell=True)), sep='\n' ) ]
    if len(slines[0])<1:
        data = pandas.DataFrame(columns=('user','ncpu'))
    else:
        data = [ [uname, 1 if rex.match(hname) is None else int(rex.match(hname).group(1))] for (uname,hname) in slines ]
    return pandas.DataFrame(data, columns=('user','ncpu')).groupby('user').sum().sort_values('ncpu', ascending=False)
    
def userinfo(u):
    cmd = "finger %s | head -n 1" % (u)
    retval = u
    try:
        line = string.strip( subprocess.check_output(cmd, shell=True) )
        rex = re.compile('.*Login:\s+(.*)\s+Name:\s+(.*)\s+\((.*)\).*')
        [u2, uname, org] = [ string.strip(x) for x in rex.match(line).groups() ]
        retval =  "%s (%s) (%s)" % (uname, org, u)
    except AttributeError:
        pass

    return retval

def show_status(status='RUN', title='Running', umax=10):
    df = get_jobs(status).iloc[:umax]
    print "%s jobs:" % (title)
    print "--------------"
    for u,n in df.iterrows():
        print n[0], userinfo(u)
    print "- - - - - - - - - - -"
    print "Total: %d" % (df['ncpu'].sum())

show_status('RUN', 'Running')
print ""
show_status('PEND', 'Pending')


    

