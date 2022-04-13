#!/usr/bin/python
#coding=utf-8
from lxml import etree
import urllib2
from rmconfig import rmconfig, appPath
from rmtemplates import rmtemplates
from rmutils import loadJSON
from os import listdir, path
import json

conf = rmconfig()
siteRoot = conf.get( 'site', 'path' )
citiesPath = siteRoot + '/.cities'
forecastPath = siteRoot + '/.forecast'
citiesList = [ [], [] ]

for cityId in listdir( citiesPath ):

    cityPath = citiesPath + '/' + cityId + '/'
    cityObj = json.load( open( cityPath + 'city.json' ) )
    cityObj['stations'] = []
    for station in listdir( cityPath ):
        stationPath = cityPath + station
        if path.isdir( stationPath ):
            stationObj = loadJSON( stationPath + '/station.json' )
            if stationObj and stationObj.has_key('number'):
                cityObj['stations'].append( stationObj )
                curPath = stationObj['current_path']
                if ( curPath.startswith( '/' ) ):
                    curPath = siteRoot + curPath
                else:
                    curPath = stationPath + '/' + curPath
                curJSON = loadJSON( curPath )
                if curJSON:
                    stationObj['current'] = curJSON['current']
    cityObj['stations'] = sorted( cityObj['stations'], \
            key = lambda station: int( station['number'] ) )

    with open( cityPath + 'city.json', 'w' ) as jsCity:
        jsCity.write( json.dumps( cityObj, ensure_ascii = False ).encode( 'utf8' ) )

    if cityObj.has_key( "noindex" ) or not cityObj['stations']:
	    continue

    cityBr = {}
    cityBr['name'] = cityObj['name']
    cityBr['id'] = cityObj['id']
    cityBr['stations'] = cityObj['stations']
    cityBr['foreign'] = cityObj['foreign']
    cityBr['sun'] = cityObj['astro']['sun']
    fcJSON = loadJSON( siteRoot + '/' + cityObj['forecast_path'] )
    if fcJSON:
        cityBr['icon'] = fcJSON['current']['icon']
   
    citiesList[ 1 if cityBr['foreign'] else 0 ].append( cityBr )

citiesList = [ sorted( cityType, key = lambda city : city['name'] ) \
        for cityType in citiesList  ]
for cityType in citiesList:
    curLetter = ''
    for city in cityType:
        if city['name'][0] != curLetter:
            curLetter = city['name'][0]
            city['firstLetter'] = True

with open( siteRoot + '/index.html', 'w' ) as indexHTML:
    rmtemplates.applyTemplate( {'template': 'index', 't': False },\
            indexHTML, cities = citiesList )

with open( conf.get( 'site', 'path' ) + '/index.json', 'w' ) as jsIndex:
    jsIndex.write( json.dumps( { 'cities': [ citiesList ] }, ensure_ascii = False ).encode( 'utf8' ) )

