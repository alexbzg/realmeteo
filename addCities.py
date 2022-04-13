#!/usr/bin/python
#coding=utf-8

from rmconfig import rmconfig, appPath
import json
import csv
import os

conf = rmconfig()
f = False

fNewCities = open( '/var/www/realmeteo/cities.csv' )
dirCities = conf.get( 'site', 'path' ) + '/.cities/'
dirFc = conf.get( 'site', 'path' ) + '/.forecast/'

reader = csv.DictReader( fNewCities, ( 'name', 'prep', 'id', 'fc_id', 'aw_id' ) )

for city in reader:

    print city['id']

    if city['fc_id'][0] == 'I':
        city['fc_id'] = 'pws:' + city['fc_id']

    dirFcCity = dirFc + city['fc_id'] 

    if not os.path.isdir( dirFcCity ):
        os.mkdir( dirFcCity )
        continue

    if not os.path.isfile( dirFcCity + '/forecast.json' ):
        print city['id'] + ' no forecast received yet'
        continue
    
    dirCity = dirCities + city['id']
    station = {}
    if city['aw_id']:
        station['current_path'] = 'current.json'
        station['accuweather'] = city['aw_id']
    else:
        station['current_path'] = '/.forecast/' + city['fc_id'] + '/forecast.json'
    city['forecast_path'] = '/.forecast/' + city['fc_id'] + '/forecast.json'

    jsonFcCity = json.load( open( dirFcCity + '/forecast.json' ) )

    newCity = False

    if not os.path.isdir( dirCity ):
    
        city['tz_name'] = jsonFcCity['location']['tz_name']
        city['tz_offset'] = jsonFcCity['location']['tz_offset']
        city['stations'] = ( 1, )
        city['foreign'] = f
        station['number'] = 1
        os.mkdir( dirCity )
        newCity = True

    else:

        city = json.load( open( dirCity + '/city.json' ) )
        station['number'] = len( city[ 'stations' ] ) + 1
        city['stations'].append( station['number'] )

    station['coordinates'] = jsonFcCity['location']['coordinates']
    os.mkdir( dirCity + '/' + str( station['number'] ) )    
        
    with open( dirCity + '/city.json', 'w' ) as fjsCity:
        if newCity:
            json.dump( city, fjsCity, ensure_ascii = False )
        else:
            fjsCity.write( json.dumps( city, ensure_ascii = False ).encode( 'utf8' ) )

    with open( dirCity  + '/' + str( station['number'] ) + '/station.json', 'w' ) as fjsStation:
        json.dump( station, fjsStation )
       

    

