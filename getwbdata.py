#!/usr/bin/python
#coding=utf-8
import urllib2
from os import listdir
import json
import logging
import argparse

from rmconfig import rmconfig
from rmutils import loadJSON

def convert_forecast(data):
    result = {}
    result['epoch'] = data['ts']
    result['icon'] = str(data['weather']['code'])
    if data.has_key('temp'):
        result['temperature'] = int(data['temp'])
    if data.has_key('max_temp'):
        result['temp_high'] = int(data['max_temp'])
    if data.has_key('min_temp'):
        result['temp_low'] = int(data['min_temp'])
    result['pop'] = data['pop']
    result['wind_dir'] = data['wind_cdir']
    result['pressure'] = round(data['pres'] * 0.75, 1)
    result['wind_speed'] = int(data['wind_spd'])
    return result

conf = rmconfig()
data_dir = conf.get('site', 'path') + '/.weatherbit'
api_url = conf.get('weatherbit', 'api_url')
api_key = conf.get('weatherbit', 'key')

forecast_length = {'daily': 10, 'hourly': 24}

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
            return rsp_json['data'][0] if len(rsp_json['data']) == 1\
                else rsp_json['data']
        else:
            return None

    data = loadJSON(data_filename)
    if not data:
        data = {'forecast': {}}
    if args.c:
        data['current'] = query(('current',))
        data['current']['icon'] = str(data['current']['weather']['code'])
    if args.d or args.o:
        forecast_type = 'daily' if args.d else 'hourly'
        forecast = query(('forecast', forecast_type))
        data['forecast'][forecast_type] = []
        for period in forecast:
            data['forecast'][forecast_type].append(convert_forecast(period))
        data['forecast'][forecast_type] = data['forecast'][forecast_type][:forecast_length[forecast_type]]

    with open(data_filename, 'w') as json_file:
        json_file.write(json.dumps(data))
