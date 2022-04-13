#!/usr/bin/python
#coding=utf-8
from rmconfig import rmconfig, appPath
from rmdb import dbConn
from rmutils import toEpoch

import psycopg2, pytz, re, base64, logging  
from datetime import datetime
from urlparse import parse_qs

logging.basicConfig( level = logging.DEBUG,
        format='%(asctime)s %(message)s', 
        filename='/var/log/realmeteo/uwsgi.log',
        datefmt='%Y-%m-%d %H:%M:%S' )
logging.debug( "restart" )


def bytes2int( bytes, neg = False ):
    mult = 1
    result = 0
    for char in bytes:
        result += ( ord( char ) - ( 255 if neg else 0 ) ) * mult
        mult *= 256
    return result


def application(env, start_response):
    rmdb = dbConn()

    def getStationData( clientID ):
        data = rmdb.fetch( \
            """select id, (select tz from cities where cities.id = city ) 
                from stations where client_id = %s""",\
            ( clientID, ) )
        if data:
            return data[0]
        else:
            return False

    if env['PATH_INFO'] == '/.scripts/client/sync.php':
        start_response('200 OK', [('Content-Type','text/html')])

        clientID = parse_qs( env['QUERY_STRING'] )['station'][0]
        stationData = getStationData( clientID )
        if stationData:
            stationID, tzID = stationData
            tz = pytz.timezone( tzID )
            lastTS = rmdb.getValue( \
                "select to_char( (ts at time zone 'UTC') at time zone '" + tzID + \
                "', 'DD.MM.YY HH24:MI' ) from data where station_id = %s " + \
                "order by ts desc limit 1",\
                ( stationID, ) )
            now = datetime.now( tz ).strftime( '%m%d%H%M%Y' )
            return now + '\n' + ( lastTS if lastTS else '' ) + '\n' 
        else:
            return "Wrong station!"
    elif env['PATH_INFO'] == '/.scripts/client/getdata.php':
        start_response('200 OK', [('Content-Type','text/html')])
        try:
            reqSize = int( env.get( 'CONTENT_LENGTH', 0 ) )
        except:
            reqSize = 0
        reqBody = env['wsgi.input'].read( reqSize )
        reqParsed = parse_qs( reqBody )
        stationData = getStationData( reqParsed['station'][0] )
        tz = pytz.timezone( stationData[1] )
        utc = pytz.utc
        if stationData:
            data = base64.decodestring( reqParsed['data'][0] )
#            with open('/var/www/realmeteo/getdata.debug', 'w') as debugFile:
#                debugFile.write( data  )
#            return 'OK'

            dataLength = len( data ) / 52
            records = []
            co = 0
            while co < dataLength:

                record = {}
                recData = data[co * 52 : ( co + 1 ) * 52]

                dateData = bytes2int( recData[:2] )
                year = dateData / 512 + 2000
                if year < 2015:
                    co += 1
                    continue
                month = ( dateData % 512) / 32
                day = dateData % 32
                timeData = bytes2int( recData[2:4] )                              
                hour = timeData / 100 
                minute = timeData % 100
                dt = datetime( year, month, day, hour, minute )

                temp = float( bytes2int( recData[4:6] ) )
                if temp == 32767:
                    temp = None
                else:
                    temp = ( temp / 10 - 32 ) * 5 / 9
                    if temp > 100:
                        temp = float( bytes2int( recData[4:6], True ) );
                        temp = (temp / 10 - 32) * 5 / 9;
                record['temperature'] = temp

                record['pcp_hr'] = float( bytes2int( recData[10:12] ) ) * 28.8

                pressure = float( bytes2int( recData[14:16] ) ) * 0.0254
                if pressure < 700 or pressure > 800:
                    pressure = None
                record['pressure'] = pressure

                solarrad = bytes2int( recData[16:18] )
                if solarrad == 32767:
                    solarrad = None
                record['solar_rad'] = solarrad

                humid = ord( recData[23] )
                record['humidity'] = None if humid == 255 else humid

                def windSpeed( char ):
                    speed = ord(char)
                    return None if speed == 255 else speed * 0.44704
                record['wind_speed_avg'] = windSpeed( recData[24] )
                record['wind_speed_hi'] = windSpeed( recData[25] )

                winddirs = ('N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', \
                    'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW')
                winddir = ord( recData[27] )
                record['wind_dir'] = None if winddir == 255 else winddirs[winddir]
                
                record['uv'] = ord( recData[28] )
                record['uv'] = None if record['uv'] == 255 else \
                        float( record['uv'] ) / 10
            
                record['epoch'] = toEpoch( tz.localize( dt ).astimezone( \
                        utc ).replace( tzinfo = None ) )
                record['station_id'] = str( stationData[0] )
                logging.debug( stationData )
                logging.debug( record )
                rmdb.insertWeatherRecord( record )

                co += 1

            return 'OK'
        else:
            return 'Wrong station!'

