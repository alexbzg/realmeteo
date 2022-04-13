#!/usr/bin/python
#coding=utf-8
from rmconfig import rmconfig, appPath
from rmutils import logEx, loadJSON, jsonEncodeExtra
from rmdb import rmdb, cursor2dicts
from shutil import copyfile

from os import listdir, path
import sys, json, os

conf = rmconfig()
sitePath = conf.get( 'site', 'path' )
citiesPath = sitePath + '/.cities/'
bPath = '/usr/local/realmeteo/.cities/'
cities = listdir( citiesPath ) if len( sys.argv ) < 2 else \
            ( sys.argv[1], )

for city in cities:
    copyfile( bPath + city + '/city.json', citiesPath + city + '/city.json' )

    


