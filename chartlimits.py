#!/usr/bin/python
#coding=utf-8
from rmconfig import rmconfig, appPath
from rmutils import logEx, loadJSON, jsonEncodeExtra
from rmdb import rmdb, cursor2dicts

from os import listdir, path
import sys, json, os

conf = rmconfig()
sitePath = conf.get( 'site', 'path' )
param = 'pressure'
tslimit = '01.03.2016'
citiesPath = sitePath + '/.cities/'
cities = listdir( citiesPath ) if len( sys.argv ) < 2 else \
            ( sys.argv[1], )
sql = 'select min(' + param + '), max(' + param + \
        ' ) from data where station_id in ' + \
        '( select id from stations where city = %s ) and ts > \'' + \
        tslimit + '\''

for city in cities:
#for city in ( 'novosibirsk', ):
    cityPath = citiesPath + city
    cityJSON = json.load( open( cityPath + '/city.json' ) )    
    limits = list( rmdb.fetch( sql, ( city, ) )[0] )
    if not limits[0]:
        continue
#    limits[0] -= 5
#    limits[0] -= limits[0] % 5
#    limits[1] += 10
#    limits[1] -= limits[1] % 5
    cityJSON['chartlimits'] = { 'pressure': limits }
    with open( cityPath + '/city.json', 'w' ) as fjsCity:
        fjsCity.write( json.dumps( cityJSON, ensure_ascii = False ).encode( 'utf8' ) )

    


