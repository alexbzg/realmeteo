#!/usr/bin/python
#coding=utf-8
import urllib2
from os import listdir, path
import json
import logging
import argparse

from rmconfig import rmconfig, appPath
from rmutils import loadJSON

conf = rmconfig()
data_dir = conf.get('site', 'path') + '/.weatherbit'
api_url = conf.get('weatherbit', 'api_url')
api_key = conf.get('weatherbit', 'key')

parser = argparse.ArgumentParser()
parser.add_argument('-c', action="store_true")
parser.add_argument('-d', action="store_true")
parser.add_argument('-o', action="store_true")
args = parser.parse_args()

for entry in listdir(data_dir):
    entry_dir = data_dir + '/' + entry
    data_filename = entry_dir + '/data.json'

    def query(params):
        req_url = api_url.format('/'.join(params), entry, api_key)
        try:
            rsp = urllib2.urlopen(req_url).read()
        except Exception as e:
            logging.exception("Error loading " + req_url)
            logging.error(e.strerror)
            return None
        with open(entry_dir + '/' + '_'.join(params) + '.orig.json', 'w')\
            as json_file:
            json_file.write(rsp)
        rsp_json = json.loads(rsp)
        if rsp_json and rsp_json.has_key('data'):
            return rsp_json['data']
        else:
            return None

    data = loadJSON(data_filename)
    if not data:
        data = {'forecast': {}}
    if args.c:
        data['current'] = query(('current',))
    if args.d:
        data['forecast']['daily'] = query(('forecast', 'daily'))
    if args.o:
        data['forecast']['hourly'] = query(('forecast', 'hourly'))

    with open(data_filename, 'w') as json_file:
        json_file.write(json.dumps(data))
