#!/usr/bin/python
#coding=utf-8
from rmconfig import rmconfig, appPath
from os import listdir, path
import json
import ephem
from datetime import datetime, timedelta
import pytz
from rmutils import loadJSON

def toEpoch( dt ):
    return int( ( dt - datetime(1970,1,1)).total_seconds() )

def calc( o, body, dt ):
    r = { 'rise': { 'time': '-', 'epoch': '-' }, \
            'set':  { 'time': '-', 'epoch': '-' } }
    if dt:
        o.date = dt
        for evt in ( 'rise', 'set' ):
            try:
                ad = ( o.previous_rising( body ) if evt == 'rise' \
                        else o.next_setting( body ) ).datetime()
                r[evt] = { 'time': utc.localize( ad \
                        ).astimezone( tz ).strftime( '%H:%M' ), \
                        'epoch': toEpoch( ad ) }
            except ephem.AlwaysUpError:
                r[evt] = { 'time': '-', 'epoch': None, 'up': 'always' }
            except ephem.NeverUpError:
                r[evt] = { 'time': '-', 'epoch': None, 'up': 'never' }
    return r


conf = rmconfig()
citiesRoot = conf.get( 'site', 'path' ) + '/.cities'
utc = pytz.utc
date_utc = datetime.utcnow()
nnm = ephem.next_new_moon( date_utc ).datetime()
pnm = ephem.previous_new_moon( date_utc ).datetime()
moonphase = int(round(((date_utc-pnm).days/29.53058867)*8, 0))


for city in listdir( citiesRoot  ):
    cityRoot = citiesRoot + '/' + city
    cityJSfn = cityRoot + '/city.json'
    cityJS = loadJSON( cityJSfn  )
    if not cityJS:
        continue
    stationJS = loadJSON( cityRoot + '/1/station.json' )
    if not stationJS:
        continue
    tz = pytz.timezone( cityJS['tz_name'] )
    dt = datetime.now( tz ).replace( hour = 12, minute = 0 \
            ).astimezone( utc ).replace( tzinfo = None )
    o = ephem.Observer()
    o.lat, o.lon = [ str( x ) for x in stationJS['coordinates'] ]
    o.date = dt
    o.pressure = 0
    sun = ephem.Sun()
    moon = ephem.Moon(o)
    md = dt
    if "-" in str( moon.alt ):
        try:
            pr = o.previous_rising( moon ).datetime()
            pz = pr + ( pr - o.previous_setting( moon ).datetime() ) / 2
        except ephem.NeverUpError:
            pz = None
        try:
            nr = o.next_rising( moon ).datetime()
            nz = nr + ( nr - o.next_setting( moon ).datetime() ) / 2
        except ephem.NeverUpError:
            nz = None
        if not pz:
            md = nz
        elif not nz or dt - pz < nz - dt:
            md = pz
        else:
            md = nz
    astro = { 'moon': calc( o, moon, md ), \
            'sun': { 'today': calc( o, sun, dt ), \
                'tomorrow': calc( o, sun, dt + timedelta( days = 1 ) ) } }
    astro['moon']['phase'] = moonphase
    cityJS['astro'] = astro
    with open( cityJSfn, 'w' ) as cityJSf:
        cityJSf.write( json.dumps( cityJS, ensure_ascii = False ).encode( 'utf8' ) )


