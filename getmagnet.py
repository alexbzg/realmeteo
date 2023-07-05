#!/usr/bin/python
#coding=utf-8
from rmconfig import rmconfig, appPath
from rmutils import toEpoch

import json, re, urllib2
from datetime import datetime, timedelta
from dateutil.parser import parse

conf = rmconfig()
txt = urllib2.urlopen( conf.get( 'geomagnet', 'url' ) ).readlines()
reH = re.compile( '^NOAA Kp index breakdown (\w+ \d+)-(\w+ \d+) (\d\d\d\d)' )
reL = re.compile( '^(\d\d)-(\d\d)UT +(\d\.\d\d) .+ (\d\.\d\d) .+ (\d\.\d\d)' )
start = None
data = []
for line in txt:
    if not start:
        m = reH.match( line )
        if m:
            year = m.group( 3 )
            if m.group( 1 ).startswith( 'Dec' ) and m.group( 2 ).startswith( 'Jan' ):
                year = str( int( year ) - 1 )
            start = parse( m.group( 1 ) + ' ' + year )
    else:
        m = reL.match( line )
        if m:
            dt = start
            for c in range( 3 ):
                item = {}
                dt = start + timedelta( days = c )
                item['beginning'] = toEpoch( dt.replace( hour = int( m.group( 1 ) ) ) )
                item['end'] = item['beginning'] + 10800
                item['value'] = round(float( m.group( 3 + c ) ))
                data.append( item )

json.dump( data, open( conf.get( 'site', 'path' ) + '/geomagnet.json', 'w' ) )

