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
args = vars( argparser.parse_args() )
#templateEnv = jinja2.Environment( \
#        loader = jinja2.FileSystemLoader( sitePath + '/.tmplts/jinja' ) )
#templateEnv.filters['json'] = jsonFilter
templateType = 'history' if args['t'] else 'current'
#template = templateEnv.get_template( templateType + '.html' )


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
        stationPath = cityPath + str( station['number'] ) + '/'
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

            fields = [ k for k in data.keys() if k != 'epoch' ]
            sql = "insert into data (station_id, ts," + \
                    ', '.join( fields ) + """) 
                    values ( """ + str(station['dbid']) + ', ' + \
                    "timestamp 'epoch' + %(epoch)s * interval '1 second', " + \
                    ', '.join( [ '%(' + x + ')s' for x in fields ] ) + ")"


            with open( stationPath + templateType + '.html', 'w' ) as fHTML:

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
                data['date'] = pytils.dt.ru_strftime( u'%d %B %Y г.', \
                        inflected = True, date = dt )
                data['time'] = dt.strftime( '%H:%M' )

                if ( city['astro']['moon']['phase'] == 0 ):
                    city['astro']['moon']['desc'] = u'новая'
                elif ( city['astro']['moon']['phase'] < 4 ):
                    city['astro']['moon']['desc'] = u'растущая'
                elif ( city['astro']['moon']['phase'] == 4 ):
                    city['astro']['moon']['desc'] = u'полная'
                else:
                    city['astro']['moon']['desc'] = u'убывающая'

                if data.has_key('temperature') and data.has_key('wind_speed_avg') and \
                        data.has_key('humidity') and data['temperature'] != None and\
                        data['humidity'] != None and data['wind_speed_avg'] != None:
                    e = data['humidity'] * 0.06105 * math.exp( \
                        ( 17.27 * data['temperature'] ) / ( 237.7 + data['temperature'] ) )        
                    data['windchill'] = round( data['temperature'] + 0.33 * e - \
                            0.7 * data['wind_speed_avg'] - 4 )
                else:
                    data['windchill'] = None

#                fHTML.write( template.render( \
#                        city = city, station = station, current = data, \
#                        stations = stations, template_type = templateType ).encode( 'utf8' ) )
                rmtemplates.applyTemplate( templateType, fHTML, \
                        city = city, station = station, current = data, \
                        stations = stations )

        except Exception as ex:
            print "Error loading " + curPath
            logEx( ex )
            continue
               
        if not args['t'] and not station.has_key('clientid'):
            data['station_id'] = str( station['dbid'] )
            rmdb.insertWeatherRecord( data )



