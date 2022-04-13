#!/usr/bin/python
#coding=utf-8
from rmconfig import rmconfig, appPath
from rmdb import rmdb
from rmutils import toEpoch, jsonEncodeExtra, loadJSON

from os import listdir, path
from datetime import datetime
import json, decimal, pytz, argparse, os

argparser = argparse.ArgumentParser()
argparser.add_argument( '-a', action = 'store_true' )
argparser.add_argument( '-c', action = 'store_true' )
args = vars( argparser.parse_args() )

conf = rmconfig()
sitePath = conf.get( 'site', 'path' )
citiesPath = sitePath + '/.cities'

fields = ( 'temperature', 'humidity', 'pressure', 'wind_speed_avg', \
                    'wind_speed_hi', 'solar_rad', 'uv', \
                    '( pcp_hr / 36000 ) * %(interval)s' )
fieldNames = { '( pcp_hr / 36000 ) * %(interval)s': 'pcp' }
namedFields = [ fieldNames[f] if fieldNames.has_key(f) else f \
        for f in fields ]
nullRow = ( None, ) * len( fields )
interval = 1800 if args['a'] else 600
sqlTfield = '( extract( epoch from ts )::int / %(interval)s ) * %(interval)s' 
sql = 'select ' + sqlTfield + ' as t, ' + \
        ', '.join( [ 'round( avg( ' + f + ' ), 1 )' + \
        (' as ' + fieldNames[f] if fieldNames.has_key( f ) else '') \
        for f in fields ] ) + \
        """ from data 
            where station_id = %(dbid)s and """
sqlTsCondition = "extract( year from ts ) = %(year)s" if args['a'] else \
        "ts > ( now() - interval '24 hours' ) at time zone 'UTC'" 
sqlTail = " group by t order by t"
utc = pytz.utc
sqlParams = { 'interval': interval }
yearsSql = """select distinct extract( year from ts )::int as y 
                from data where station_id = %s
                order by y"""

for cityId in listdir( citiesPath ):

    cityPath = citiesPath + '/' + cityId + '/'
    city = loadJSON( cityPath + 'city.json' )
    if not city:
        print 'city.json not found!'
        continue
    tz = pytz.timezone( city['tz_name'] )
    for stationNo in listdir( cityPath ):
        if path.isdir( cityPath + stationNo ):
            stationPath = cityPath + stationNo + '/'
            station = loadJSON( stationPath + 'station.json' )
            if not station:
                print 'station.json not found!'
                continue
            if not station.has_key('dbid'):
                print 'dbid not found'
                continue

            def exportData( year, cont = True ):
                global sqlTsCondition
                data = None
                dstPath = stationPath + 'history/' + str( year ) + '.json' if year else \
                         stationPath + 'charts.json'
                if year:
                    sqlParams['year'] = year
                    if cont:
                        data = loadJSON( dstPath )
                if not data:
                    data = { 'interval': interval * 1000, \
                            'data': { f: [] for f in namedFields },
                            'flags': { f: False for f in namedFields } } 
                prev = None
                tmpSql = sql + sqlTsCondition
                if data.has_key( 'stop' ):
                    prev = data['stop']
                    tmpSql += " and " + sqlTfield + " > %(stop)s"
                    sqlParams['stop'] = data['stop']
                tmpSql += sqlTail
                sqlParams['dbid'] = station['dbid']

                for row in rmdb.execute( tmpSql, sqlParams ).fetchall():
                    t = row[0]

                    def addRow( row ):
                        for n in range(len(fields)):
                            data['data'][namedFields[n]].append( row[n] )
                            if not data['flags'][namedFields[n]] and row[n] != None and row[n] != 0:
                                data['flags'][namedFields[n]] = True

                    if prev:
                        while t - prev > interval:
                            addRow( nullRow )
                            prev += interval
                    else:
                        data[ 'start' ] = toEpoch( datetime.fromtimestamp( t, utc \
                                ).astimezone( tz ).replace( tzinfo = None ) ) * 1000
                    prev = t 
                    addRow( row[1:] )

                if year:
                    data['stop'] = prev
                else:
                    for f in namedFields:
                        if not data['flags'][f]:
                            data['data'][f] = None

                with open( dstPath, 'w' ) as jsData:
                    json.dump( data, jsData, default = jsonEncodeExtra )

            if args['a']:
                historyJSONpath = stationPath + 'history.json'
                if not path.exists( stationPath + 'history' ):
                    os.makedirs( stationPath + 'history' )
                historyJSON = loadJSON( historyJSONpath )
                if not historyJSON or args['c']:
                    historyJSON = []
                lastYear = historyJSON[-1] if historyJSON else None
                for yearRow in rmdb.execute( yearsSql, ( station['dbid'], ) ).fetchall():
                    year = yearRow[0]
                    if not lastYear or year >= lastYear:
                        exportData( year, year == lastYear )
                        if year != lastYear:
                            historyJSON.append( year )
                with open( historyJSONpath, 'w' ) as jsData:
                    json.dump( historyJSON, jsData, default = jsonEncodeExtra )
            else:
                exportData( None )

            



