#!/usr/bin/python
#coding=utf-8

from rmconfig import rmconfig, appPath
from rmutils import logEx, jsonEncodeExtra, loadJSON
import json
from os import listdir, path

conf = rmconfig()
sitePath = conf.get( 'site', 'path' )
citiesPath = sitePath + '/.cities'

for cityId in listdir( citiesPath ):

    cityPath = citiesPath + '/' + cityId + '/city.json'
    city = loadJSON( cityPath )
    if city:
        city['sh_name'] = city['name']
        with open( cityPath, 'w' ) as fjsCity:
            fjsCity.write( json.dumps( city, ensure_ascii = False ).encode( 'utf8' ) )
       
