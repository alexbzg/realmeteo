#!/usr/bin/python
#coding=utf-8
from rmconfig import rmconfig, appPath
from rmdb import rmdb
from rmutils import logEx, jsonEncodeExtra, loadJSON
from rmtemplates import rmtemplates

from os import listdir, path
import json, psycopg2, sys, jinja2, math, pytz, pytils, argparse
from datetime import datetime
#from operator import attrgetter


def jsonFilter( data ):
    return json.dumps( data, ensure_ascii = False, \
            default = jsonEncodeExtra )


conf = rmconfig()
sitePath = conf.get( 'site', 'path' )
citiesPath = sitePath + '/.cities'
argparser = argparse.ArgumentParser()
argparser.add_argument( '-t', action = 'store_true' )
argparser.add_argument( 'template', nargs = '?', default = 'current' )
args = vars( argparser.parse_args() )
postfix = '_t' if args['t'] else ''
extraLinks = loadJSON(sitePath + '/extraLinks.json')

for cityId in listdir( citiesPath ):

    cityPath = citiesPath + '/' + cityId + '/'
    city = loadJSON( cityPath + 'city.json' )
    if not city:
        continue
    tz = pytz.timezone( city['tz_name'] )

    stations = []
    stationsList = listdir( cityPath )
    stationsList.sort()
    for stationNo in stationsList:
        if path.isdir( cityPath + stationNo ):
            station = loadJSON( cityPath + '/' + stationNo + '/station.json' )
            if station:
                stations.append( station )

    for station in stations:        
        if not station.has_key('number'):
            print cityPath + '/' + stationNo + '/station.json: number not found'
            continue
        stationPath = cityPath + str( station['number'] ) + '/'
        history = loadJSON( stationPath + 'history.json' )
        if args['template'] == 'history' and not history:
            continue
        extData = { 'city': city, 'station': station, 'stations': stations,\
                'history': history, 'extra_links': extraLinks }
        if args['template'] == 'current':
            if city.has_key( 'forecast_path' ) and city['forecast_path']:
                forecast = loadJSON( sitePath + city['forecast_path'] )
                if forecast:
                    extData['forecast'] = forecast
                    tz = pytz.timezone( city['tz_name'] )
                    if extData['forecast'].has_key('daily'):
                        for day in extData['forecast']['forecast']['daily']:
                            dt = datetime.fromtimestamp( int( day['epoch'] ), tz )
                            day['day'] = dt.strftime( '%d' )
                            day['month'] = pytils.dt.ru_strftime( u'%B', \
                                inflected = True, date = dt )
            curPath = station['current_path']
            data = {}
            if ( curPath.startswith( '/' ) ):
                curPath = sitePath + curPath
            else:
                curPath = stationPath + curPath
            try:
                curJSON = loadJSON( curPath )
                if not curJSON:
                    continue

                data = curJSON['current']
                if station.has_key( 'import_data' ):
                    importPath = sitePath + station['import_data']['path']
                    importJSON = loadJSON( importPath )
                    if importJSON:
                        for field in station['import_data']['fields']:
                            data[field] = importJSON['current'][field]
                if station['current_path'].startswith( '/.forecast'):
                    elevation = curJSON['location']['elevation']
                    if elevation.endswith( ' ft' ):
                        elevation = float( elevation[:-3] ) * 0.3048
                    else:
                        elevation = float( elevation )
                    if elevation < 0:
                        elevation = 0
                    kt = 8000 * ( 1 + 0.00366 * data['temperature'] )
                    data['pressure'] = round( ( data['pressure'] * kt ) / \
                            ( elevation + kt ), 1 )


                if data.has_key( 'wind_speed_avg' ) and \
                    data['wind_speed_avg'] > 0 and data.has_key('wind_dir'): 
                    if data['wind_dir'] != 'V':
                        tabin = u'NESW'
                        tabout = u'СВЮЗ'
                        tabin = [ ord(char) for char in tabin ]
                        tt = dict(zip(tabin, tabout))
                        data['wind_dir_ru'] = \
                        data['wind_dir'].translate( tt )
                else:
                    data['wind_0'] = 0;

                dt = datetime.fromtimestamp( data['epoch'], tz )
                data['day'] = dt.strftime( '%d' )
                data['month'] = pytils.dt.ru_strftime( u'%B', \
                        inflected = True, date = dt )
                data['time'] = dt.strftime( '%H:%M' )
                data['year'] = dt.strftime( '%Y' )

                if ( city['astro']['moon']['phase'] == 0 ):
                    city['astro']['moon']['desc'] = u'новая'
                elif ( city['astro']['moon']['phase'] < 4 ):
                    city['astro']['moon']['desc'] = u'растущая'
                elif ( city['astro']['moon']['phase'] == 4 ):
                    city['astro']['moon']['desc'] = u'полная'
                else:
                    city['astro']['moon']['desc'] = u'убывающая'

                data['icon'] = forecast['current']['icon']
                n = not ( city['astro']['sun']['today']['rise'].has_key( 'up' ) \
                    and  city['astro']['sun']['today']['rise']['up'] == 'always' )
                for day in ( 'today', 'tomorrow' ):
                    for evt in ( 'rise', 'set' ):
                        if city['astro']['sun'][day][evt]['epoch'] != '-':
                            if data['epoch'] > city['astro']['sun'][day][evt]['epoch']:
                                n = not n
                            else:
                                break
                if n:
                    data['icon'] = 'night_' + data['icon']

                if data.has_key( 'humidity' ):
                    if (data['humidity'] < 0 or data['humidity'] > 100):
                        del data['humidity']
                    else:
                        data['humidity'] = int(round(data['humidity'], 0))
                

                if data.has_key('temperature') and data.has_key('wind_speed_avg') and \
                        data.has_key('humidity') and data['temperature'] != None and\
                        data['humidity'] != None and data['wind_speed_avg'] != None:
                    e = data['humidity'] * 0.06105 * math.exp( \
                        ( 17.27 * data['temperature'] ) / ( 237.7 + data['temperature'] ) )        
                    data['windchill'] = round( data['temperature'] + 0.33 * e - \
                            0.7 * data['wind_speed_avg'] - 4 )
                else:
                    data['windchill'] = None

                extData['current'] = data
                with open(  stationPath + '/data.json', 'w' ) as fData:
                    fData.write( json.dumps( extData, \
                        default = jsonEncodeExtra, \
                        ensure_ascii = False ).encode( 'utf8' ) )
               


            except Exception as ex:
                print "Error loading " + curPath
                logEx( ex )
                continue
                
            if not args['t'] and not station.has_key('clientid'): 
                if station.has_key( 'dbid' ):
                    data['station_id'] = str( station['dbid'] )
                    rmdb.insertWeatherRecord( data )
                else:
                    print 'No dbid ' + stationPath

        with open( stationPath + args['template'] + postfix + '.html', 'w' ) as fHTML:
            rmtemplates.applyTemplate( args, fHTML, **extData )

