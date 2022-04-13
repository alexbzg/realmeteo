#!/usr/bin/python
#coding=utf-8
from rmconfig import rmconfig, appPath
from rmdb import rmdb
from rmutils import logEx, jsonEncodeExtra, loadJSON

from os import listdir, path
import json, psycopg2, sys, jinja2, math, pytz, pytils, argparse
from datetime import datetime
#from operator import attrgetter


def jsonFilter( data ):
    return json.dumps( data, ensure_ascii = False, \
            default = jsonEncodeExtra )

class TemplateEnv():

    def __init__( self ):
        conf = rmconfig()
        sitePath = conf.get( 'site', 'path' )
        self.templateEnv = jinja2.Environment( \
                loader = jinja2.FileSystemLoader( sitePath + '/.tmplts/jinja' ) )
        self.templateEnv.filters['json'] = jsonFilter

    def applyTemplate( self, args, outFile, **data ):
        titles = { 'current': 'Реальная погода', 'history': 'Архив погоды' }
        template = self.templateEnv.get_template( args['template'] + \
                ( '_t' if args['t'] else '' ) + '.html' )
        data['template_type'] = args['template']
        data['test'] = args['t']
        outFile.write( template.render( **data ).replace( u'\ufeff', '' ).encode( 'utf-8' ) ) 

rmtemplates = TemplateEnv()
