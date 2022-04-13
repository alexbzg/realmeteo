#!/usr/bin/python
#coding=utf-8

from rmconfig import rmconfig, appPath
from rmutils import logEx, jsonEncodeExtra, loadJSON


from PIL import Image, ImageDraw, ImageFont
from os import listdir, path
import json, sys, jinja2
from datetime import datetime



conf = rmconfig()
sitePath = conf.get( 'site', 'path' )
citiesPath = sitePath + '/.cities'
infImgPath = sitePath + '/.images/informers/'
iconPath = sitePath + '/.images/weather_icons/'
templateEnv = jinja2.Environment( \
        loader = jinja2.FileSystemLoader( sitePath  ) )
template = templateEnv.get_template( 'informers.json' )
infSettings = json.loads( template.render() ) 



def evalText( text, data ):
    t = False
    try:
        t = text.format( **data )
    except KeyError as e:
        pass
    except Exception as e:
#        print data
        print text
        print str(e)
        pass
    return t

def drawText( draw, data, el ):
    text = evalText( el['text'], data )
    if not text:
        return
    fontsize = el['font']['size']
    font = ImageFont.truetype( infImgPath + '/fonts/' + el['font']['file'],\
            fontsize )
    size = draw.textsize( text, font )
    if el.has_key( 'maxsize' ):
        while size[0] > el['maxsize']:
            fontsize -= 1
            font = ImageFont.truetype( infImgPath + '/fonts/' + el['font']['file'],\
                    fontsize )
            size = draw.textsize( text, font )
    x, y = el['xy']
    if el.has_key( 'align' ): 
        if el['align'][0] == 'middle':
            x -= size[0] / 2
        elif el['align'][0] == 'right':
            x -= size[0]
        if el['align'][1] == 'bottom':
            y -= size[1] 
    draw.text( ( x, y ), text, font = font, fill = tuple( el['colour'] ) )

def drawIcon( im, data, el ):
    icon = evalText( el['icon'], data )
    if not icon:
        return
    prefix = "wind" if el.has_key( 'wind' ) and el['wind'] else ''
    try:
        iconIm = Image.open( '{0}{1}x{1}/{2}.png'.format( iconPath + prefix, el['size'], icon ) )
        x, y = el['xy']
        im.paste( iconIm, box = ( x, y, x + el['size'], y + el['size'] ), mask = iconIm )
    except IOError as e:
        pass
        

if not infSettings:
    sys.exit()

for cityId in listdir( citiesPath ):

    cityPath = citiesPath + '/' + cityId + '/'
    for stationNo in listdir( cityPath ):
        stationPath = cityPath + stationNo
        if path.isdir( stationPath ):
            data = loadJSON( cityPath + '/' + stationNo + '/data.json' )
            if not data: 
                continue
            for infS in infSettings:
                im = Image.open( infImgPath + infS['background'] )
                draw = ImageDraw.Draw( im )

                for el in infS['elements']:
                    if el['type'] == 'text':
                        drawText( draw, data, el )
                    elif el['type'] == 'icon':
                        drawIcon( im, data, el )

                im.save( stationPath + '/' + infS['filename'], infS['format'] )





