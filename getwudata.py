#!/usr/bin/python
#coding=utf-8
import urllib2
from rmconfig import rmconfig, appPath
from os import listdir, path
import json, logging
from subprocess import Popen, PIPE
import sys

conf = rmconfig()
fcPath = conf.get( 'site', 'path' ) + '/.forecast'
tReqURL = conf.get( 'forecast', 'request_url' )
delimeter = ''
jqCmd = 'jq -f ' + appPath + '/forecast.jq'


for station in listdir( fcPath ):
    fcStationPath = fcPath + '/' + station
    fcJSONPath = fcStationPath + '/forecast.json'
    reqURL = tReqURL.format( station )
    try:
        oJson = urllib2.urlopen( reqURL ).read()
    except Exception as e:
        print "Error loading " + reqURL
        print e.strerror
        continue
    with open( fcStationPath + '/orig.json', 'w' ) as jsonFile:
        jsonFile.write( oJson )
    pJq = Popen( jqCmd, shell = True, stdin = PIPE, stdout = PIPE, stderr = PIPE )
    pJq.stdin.write( oJson )
    ( tJson, errors ) = pJq.communicate()
    if errors:
        print fcStationPath
        print errors
    if tJson:
        data = json.loads( tJson )
        try:
            if int( data['current']['epoch'] ) > int( data['forecast']['daily'][1]['epoch'] ) + 2 * 24 * 3600:
                continue
            with open( fcStationPath + '/forecast.json', 'w' ) as jsonFile:
                jsonFile.write( tJson )
        except Exception as e:
            logging.exception( "Error checking data: " + station )


