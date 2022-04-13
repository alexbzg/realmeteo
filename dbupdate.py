#!/usr/bin/python
#coding=utf-8
from rmconfig import rmconfig, appPath
from rmdb import rmdb

from os import listdir, path
import json, psycopg2, sys

conf = rmconfig()
sitePath = conf.get( 'site', 'path' )
citiesPath = sitePath + '/.cities'

for cityId in listdir( citiesPath ):

    cityPath = citiesPath + '/' + cityId + '/'
    for stationNo in listdir( cityPath ):
        if path.isdir( cityPath + stationNo ):
            stationPath = cityPath + stationNo + '/'
            station = json.load( open( stationPath + 'station.json' ) )
            if station.has_key('skip_db_update'):
                continue
            curPath = station['current_path']
            if ( curPath.startswith( '/' ) ):
                curPath = sitePath + curPath
            else:
                curPath = stationPath + curPath
            data = json.load( open( curPath ) )

            fields = [ k for k in data['current'].keys() if k != 'epoch' ]
            sql = "insert into data (station_id, ts," + \
                    ', '.join( fields ) + """) 
                    values ( """ + str(station['dbid']) + ', ' + \
                    "timestamp 'epoch' + %(epoch)s * interval '1 second', " + \
                    ', '.join( [ '%(' + x + ')s' for x in fields ] ) + ")"
            cur = rmdb.conn.cursor()
            try:
                cur.execute( sql, data['current'] )
                rmdb.commit()
            except psycopg2.Error, e:
                rmdb.conn.rollback()
                if not 'duplicate key' in e.pgerror:
                    sys.stderr.write( curPath + '\n' )
                    sys.stderr.write( "Params: " )
                    print >>sys.stderr, data['current']
                    if e.pgerror:
                        sys.stderr.write(  e.pgerror )



