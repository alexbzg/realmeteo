#!/usr/bin/python
#coding=utf-8
from rmconfig import rmconfig, appPath
from rmdb import rmdb
from os import listdir, path
from rmutils import loadJSON
import json

conf = rmconfig()
citiesPath = conf.get( 'site', 'path' ) + '/.cities'
citiesList = []

for cityId in listdir( citiesPath ):

    cityPath = citiesPath + '/' + cityId + '/'
    city = json.load( open( cityPath + 'city.json' ) )
    cityDB = rmdb.getObject( 'cities', \
            { 'id': city['id'], 'tz': city['tz_name'], 'name': city['name'],\
                'prep': city['prep'] } )
    for stationNo in listdir( cityPath ):
        if path.isdir( cityPath + stationNo ):
            station = loadJSON( cityPath + stationNo + '/station.json' )
            if not station or station.has_key( 'dbid' ):
                continue
            params = { 'no': station['number'], 'city': city['id'] }
            if station.has_key( 'clientid' ):
                params['client_id'] = station['clientid']
            stationDB = rmdb.getObject( 'stations', params )
            station['dbid'] = stationDB['id']

            with open( cityPath + stationNo + '/station.json', 'w' ) as jsStation:
                jsStation.write( json.dumps( station, ensure_ascii = False ).encode( 'utf8' ) )


