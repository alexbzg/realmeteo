#!/usr/bin/python
#coding=utf-8
from rmconfig import rmconfig, appPath
from rmutils import logEx, toEpoch, loadJSON, jsonEncodeExtra
from rmdb import rmdb, cursor2dicts

from os import listdir, path
import threading, sys, pytz, json, re, Queue, zipfile, os, logging
from datetime import datetime, timedelta
from string import maketrans
from dateutil.parser import parse
from lxml import etree

logging.basicConfig( level = logging.DEBUG,
        format='%(asctime)s %(message)s', 
        filename='/usr/local/realmeteo/getcurrent.log',
        datefmt='%Y-%m-%d %H:%M:%S' )


utc = pytz.utc
conf = rmconfig()
sitePath = conf.get( 'site', 'path' )
citiesPath = sitePath + '/.cities/'
dataQueue = Queue.Queue()
loadThreads = []
reL = re.compile( "^\s*(\S+): ['\"]?([^'\"]+)['\"]?\r?\n$" )
awPath = sitePath + '/.clients/accuweather/' 
awData = []
awZips = listdir( awPath )
for zip in awZips:
    if 'zip' in zip:
        zPath = awPath + zip
        try:
            zipfile.ZipFile( zPath ).extractall( awPath )
        except Exception:
            logging.exception( 'Error opening zip-file ' + zPath )
        os.remove( zPath )   
for file in listdir( awPath ):
    if not 'zip' in file:
        fPath = awPath + file
        dom = etree.parse( open( fPath ) )
        epoch = toEpoch( parse( dom.xpath( 'timestamp' )[0].text \
                ).replace( tzinfo = None ) )
        awData.append( ( dom, epoch ) )
        os.remove( fPath ) 


def load( src, params ):
    import urllib2
    try:
        params['data'] = urllib2.urlopen( src ).readlines()
    except Exception as ex:
        print "Error loading " + src
        logEx( ex )
    finally:
        dataQueue.put( params )

def toFloat( v, trim ):
    if 'n/a' in v or 'N/A' in v or len( v ) < trim:
        return None
    elif trim:
        return float( v[:-trim] )
    else:
        m = re.match( r'(\d+)\D*', v )
        if m:
            return float( m.group( 1 ) )
        else:
            return None

def toInt( v, trim ):
    if 'n/a' in v or 'N/A' in v or len( v ) < trim:
        return None
    else:
        return int( v[:-trim] )


def process( params ):

    def parseTS( v ):
        dt = params['tz'].localize( parse( v, \
                dayfirst = True, ignoretz = True, \
                tzinfos = params['tz'] ) ).astimezone( \
                utc ).replace( tzinfo = None )
        if params.has_key( 'timedelta' ):
            dt += timedelta( **params['timedelta'] ) 
        return toEpoch( dt )

    if params.has_key( 'data' ) and params['data']:
        try:
            data = {} 
            dataFl = False

            if params['template'] == 1 or params['template'] == 111 :
                dataP = {}
                for line in params['data']:
                    m = reL.match( line )
                    if m and m.group(2) != 'N/A':
                        dataP[ m.group(1) ] = m.group(2).translate( maketrans( ',', '.' ) )

                
                if dataP.has_key( 'WEATHER_TS' ):
                    data[ 'epoch' ] = parseTS( dataP['WEATHER_TS'] )
                
                if dataP.has_key( 'OUTSIDETEMP' ):
                    data[ 'temperature' ] = float( dataP[ 'OUTSIDETEMP' ] )
                if dataP.has_key( 'OUTSIDEHUMIDITY' ):
                    data[ 'humidity' ] = float( dataP[ 'OUTSIDEHUMIDITY' ] )
                if dataP.has_key( 'BAROMETER' ):                   
                    data[ 'pressure' ] = int( round( float( dataP[ 'BAROMETER' ] ) ) )
                if dataP.has_key( 'WINDDIRECTION' ):                   
                    data[ 'wind_dir' ] = dataP[ 'WINDDIRECTION' ]
                    if params['template'] == 111:
                        data[ 'wind_dir' ] = data[ 'wind_dir' ].translate( \
                                maketrans( 'NESW', 'SWNE' ) )
                if dataP.has_key( 'AVGWINDSPEED' ):                   
                    data[ 'wind_speed_avg' ] = float( dataP[ 'AVGWINDSPEED' ] )
                if dataP.has_key( 'HIWINDSPEED' ):                   
                    data[ 'wind_speed_hi' ] = float( dataP[ 'HIWINDSPEED' ] )
                if dataP.has_key( 'RAINRATE' ):                   
                    data[ 'pcp_hr' ] = dataP[ 'RAINRATE' ]
                dataFl = True

            elif params['template'] == 'weatherlink.com':                
                dom = etree.HTML( ''.join( params['data'] ) )
                data['epoch'] = parseTS( dom.xpath( "//td[ @class = 'summary_timestamp' ]" \
                        )[0].text[25:] ) 

                tempStr = dom.xpath( "//td[ @class = 'summary_data' " +
                        "and . = 'Outside Temp' ]/following-sibling::td[1]" )[0].text
                if 'F' in tempStr:
                    data['temperature'] = round( ( toFloat( tempStr, 2 ) - 32 ) / 1.8, 1 )
                else:
                    data['temperature'] = toFloat( tempStr, 2 )

                data['humidity'] = toInt( dom.xpath( "//td[ @class = 'summary_data' " +
                        "and . = 'Outside Humidity' ]/following-sibling::td[1]" )[0].text, 1 )

                pressureStr = dom.xpath( "//td[ @class = 'summary_data' " +
                        "and . = 'Barometer' ]/following-sibling::td[1]" )[0].text
                if 'hPa' in pressureStr:
                    data['pressure'] = int( round( float( pressureStr[:-3] ) * 0.75 ) )
                elif 'mb' in pressureStr:
                    data['pressure'] = int( round( float( pressureStr[:-2] ) * 0.75 ) )
                elif '"' in pressureStr:
                    data['pressure'] = int( round( float( pressureStr[:-1] ) * 25.4 ) )
                else:
                    data['pressure'] = int( round( toFloat( pressureStr, 2 ) )  )

                windDirStr = dom.xpath( "//td[ @class = 'summary_data' " +
                        "and . = 'Wind Direction' ]/following-sibling::td[1]" )[0].text
                if not 'n/a' in windDirStr:
                    data['wind_dir'] = windDirStr[:windDirStr.index( u'\xa0' )]

                if dom.xpath( "//td[ @class = 'summary_data' and . = 'Solar Radiation' ]" ):
                    data['solar_rad'] = toFloat( dom.xpath( "//td[ @class = 'summary_data' " +
                            "and . = 'Solar Radiation' ]/following-sibling::td[1]" )[0].text, 4 )
                    data['uv'] = toFloat( dom.xpath( "//td[ @class = 'summary_data' " +
                            "and . = 'UV Radiation' ]/following-sibling::td[1]" )[0].text, 6 )

                def windFromStr( v ):
                    if v == 'Calm':
                        return 0
                    if 'm/s' in v:
                        return toFloat( v, 4 )
                    if 'mph' in v:
                        return round( toFloat( v, 4 ) * 0.44704, 1 )
                    else:
                        return round( toFloat( v, 5 ) / 3.6, 1 )

                data['wind_speed_avg'] = windFromStr( dom.xpath( "//td[ @class = 'summary_data' " +
                        "and . = 'Average Wind Speed' ]/following-sibling::td[2]" )[0].text )
                windSpeedHiStr =  dom.xpath( "//td[ @class = 'summary_data' " +
                        "and . = 'Wind Gust Speed' ]/following-sibling::td[2]" )[0].text
                if not 'n/a' in windSpeedHiStr:
                    data['wind_speed_hi'] = windFromStr( windSpeedHiStr )
                data['pcp_hr'] = toFloat( dom.xpath( "//td[ @class = 'summary_data' " +
                        "and . = 'Rain' ]/following-sibling::td[1]" )[0].text, 7 )

                dataFl = True

            elif params['template'] == 'accuweather':
                data['epoch'] = params['data'][1]
                el = params['data'][0].xpath( 'location[ @code = "{0}" ]'.format( \
                    params['id'] ) )[0] 
                data['temperature'] = int( el.xpath( 'temp' )[0].text )
                data['humidity'] = int( el.xpath('rhumid' )[0].text )
                data['wind_dir'] = el.xpath( 'wind_dir' )[0].text
                data['wind_speed_avg'] = round( float( el.xpath( 'windspeed' )[0].text ) / 3.6, 1 )
                data['wind_speed_hi'] = round( float( el.xpath( 'gust' )[0].text ) / 3.6, 1 )
                data['pressure'] = round( float( el.xpath( 'pres' )[0].text ) * 7.5, 1 )
                dataFl = True

            elif params['template'] == 'weatherbit':
                data['epoch'] = params['data']['ts']
                data['temperature'] = params['data']['temp']
                data['humidity'] = params['data']['rh']
                data['wind_dir'] = params['data']['wind_cdir']
                data['wind_speed_avg'] = params['data']['wind_spd']
                data['pressure'] = round(params['data']['pres'] * 0.75, 1)
                data['uv'] = params['data']['uv']
                data['solar_rad'] = params['data']['solar_rad']
                if params['data'].has_key('snow') and params['data']['snow']:
                    data['pcp_hr'] = params['data']['snow']
                elif params['data'].has_key('precip') and params['data']['precip']:
                    data['pcp_hr'] = params['data']['precip']

                dataFl = True

            elif params['template'] == 'ekb2':
                dom = etree.HTML( ''.join( params['data'] ) )
                dataTxt = ( dom.xpath( '//div[ @id = "details" ]/div/pre/text()' ) )[4]
                reLekb = re.compile( \
                    r'(\d+/\d+/\d+ \d+:\d+) + \S+ +(\S+) +\S+ +\S+ +(\S+) +' + \
                    r'\S+ +\S+ +(\S+) +\S+ +\S+ +(\S+) +(\S+) +(\S+) +' + \
                    r'(\S+) +(\S+)', re.M )
                m = reLekb.search( dataTxt )
                if m:
                    data['epoch'] = parseTS( m.group( 1 ) )
                    data['temperature'] = float( m.group( 2 ) )
                    data['humidity'] = int( ( m.group( 3 ) )[:-1] )
                    data['pressure'] = int( m.group( 4 ) )
                    data['pcp_hr'] = float( m.group( 5 ) )
                    data['wind_speed_avg'] = float( m.group( 6 ) )
                    data['wind_speed_hi'] = float( m.group( 7 ) )
                    data['wind_dir'] = m.group( 8 )
                    dataFl = True
 

            if not data.has_key( 'epoch' ):
                raise Exception( 'No valid timestamp field' )

            if dataFl:
                json.dump( { 'current': data }, open( params['dest'], 'w' ),\
                        default = jsonEncodeExtra )

        except Exception as ex:
            logging.exception( "Eror building " + params['dest'] + '\n' + \
                "Error processing " + params['src'] )

cities = listdir( citiesPath ) if len( sys.argv ) < 2 else \
            ( sys.argv[1], )

for city in cities:
    stationsPath = citiesPath + city
    cityJSON = loadJSON( stationsPath + '/city.json' )
    if not cityJSON:
	    continue
    tz = pytz.timezone( cityJSON['tz_name'] )
    stations = listdir( stationsPath ) if len( sys.argv ) < 3 else \
            ( sys.argv[2], )
    for station in stations:
        stationPath = stationsPath + '/' + station
        if ( path.isdir( stationPath ) ):
                
            stationJSON = loadJSON(  stationPath + '/station.json' )
            if not stationJSON:
                continue

            if stationJSON.has_key( 'load_current' ):
                params = { 'template': stationJSON['load_current']['template'], \
                        'tz': tz, 'dest':  stationPath + '/current.json', 
                        'src': stationJSON['load_current']['path'] }
                if stationJSON['load_current'].has_key( 'timedelta' ):
                    params['timedelta'] = stationJSON['load_current']['timedelta']
                if stationJSON['load_current']['path'].startswith( 'http' ) or \
                        stationJSON['load_current']['path'].startswith( 'ftp' ):
                    t =  threading.Thread( target = load, args = \
                        ( stationJSON['load_current']['path'], params ) )
                    t.start()
                    loadThreads.append( t )
                else:
                    try:
                        params['data'] = open( stationJSON['load_current']['path'] \
                                ).readlines()
                        process( params )
                    except Exception as ex:
                        print "Error loading " +  stationJSON['load_current']['path']
                        logEx( ex )
            elif stationJSON.has_key( 'accuweather' ):
                id = stationJSON['accuweather']
                params = { 'template': 'accuweather', \
                        'tz': tz, 'dest':  stationPath + '/current.json', \
                        'src': 'accuweather | ' + id, 'id': id }
                for data in awData:
                    params['data'] = data
                    process( params )
            elif stationJSON.has_key('weatherbit'):
                id = stationJSON['weatherbit']
                params = { 'template': 'weatherbit', \
                        'tz': tz,\
                        'dest':  stationPath + '/current.json', \
                        'id': id}
                data = loadJSON(sitePath + '/.weatherbit/' + id + '/data.json')
                if data and data.has_key('current'):
                    params['data'] = data['current']
                    process( params )
            elif stationJSON.has_key( 'clientid' ):
                data = rmdb.getLastWeatherRecord( stationJSON['dbid'] )
                if data:
                    json.dump( { 'current': data }, \
                            open( stationPath + '/current.json', 'w' ),\
                            default = jsonEncodeExtra )




for t in loadThreads:
    t.join()

while not dataQueue.empty():
    process( dataQueue.get() )
 

