#!/usr/bin/python
#coding=utf-8
from datetime import datetime
import decimal, json
from os import path


def toEpoch( dt ):
    return int( ( dt - datetime(1970,1,1)).total_seconds() )

def logEx( ex ):
    errstr = str( type(ex) ) + ' '
    if hasattr( ex, 'errstr' ):
        errstr += ex.errstr
    else:
        errstr += str( ex )
    print errstr

def jsonEncodeExtra( obj ):
    if isinstance( obj, decimal.Decimal ):
        return float( obj )
    raise TypeError( repr( obj ) + " is not JSON serializable" )

def loadJSON( pathJS ):
    if not path.isfile( pathJS ):
        print pathJS + " not found"
        return False
    try:
        r = json.load( open( pathJS ) )
        return r
    except Exception as ex:
        print "Error loading " + pathJS
        logEx( ex )
        return False

