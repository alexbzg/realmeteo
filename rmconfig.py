#!/usr/bin/python
#coding=utf-8
import ConfigParser

appPath = "/usr/local/realmeteo"

def rmconfig():
    cp = ConfigParser.ConfigParser()
    cp.read( appPath + '/rm.conf' )
    return cp

