#!/usr/bin/python
#coding=utf-8

import psycopg2, sys, logging

from rmconfig import rmconfig

def cursor2dicts( cur, keys = None ):
    if cur and cur.rowcount:
        colNames = [ col[0] for col in cur.description ]
        if cur.rowcount == 1 and not keys:
            return dict( zip( colNames, cur.fetchone() ) )
        else:
            if ( 'id' in colNames ) and keys:
                idIdx = colNames.index( 'id' )
                return dict( 
                        ( row[ idIdx ], dict( zip( colNames, row ) ) )
                        for row in cur.fetchall() )
            else:
                return [ dict( zip( colNames, row ) ) for
                        row in cur.fetchall() ]
    else:
        return False

class dbConn:
    weatherFields =  ( 'temperature', 'humidity',\
            'wind_dir', 'wind_speed_avg', 'wind_speed_hi', 'pressure',\
            'solar_rad', 'uv', 'pcp_hr' )

    def __init__( self ):
        connStr = ' '.join( 
                [ k + "='" + v + "'" 
                    for k, v in rmconfig().items( 'db' ) ] )
        try:
            conn = psycopg2.connect( connStr )
            conn.set_client_encoding( 'UTF8' )
            self.conn = conn
        except:
            sys.stderr.write( "No db connection!" )
            self = False

    def fetch( self, sql, params = None ):
        cur = self.conn.cursor()
        cur.execute( sql, params )
        if cur.rowcount:
            res = cur.fetchall()
            cur.close()
            return res
        else:
            cur.close()
            return False

    def execute( self, sql, params = None ):
        cur = self.conn.cursor()
        try:
            cur.execute( sql, params )
        except psycopg2.Error, e:
            sys.stderr.write( "Error executing: " + sql + "\n" )
            if params:
                sys.stderr.write( "Params: " )
                print >>sys.stderr, params
            if e.pgerror:
                sys.stderr.write(  e.pgerror )
                self.error = e.pgerror
            sys.stderr.flush()
            self.conn.rollback()
            return False
        return cur

    def getValue( self, sql, params = None ):
        res = self.fetch( sql, params )
        if res:
            return res[0][0]
        else:
            return False

    def commit( self ):
        self.conn.commit()

    def getObject( self, table, params, create = False, 
            never_create = False ):
        sql = ''
        cur = False
        if not create:
            sql = "select * from %s where %s" % (
                    table, 
                    " and ".join( [ k + " = %(" + k + ")s"
                        if params[ k ] != None 
                        else k + " is null"
                        for k in params.keys() ] ) )
            cur = self.execute( sql, params )
            if cur and not cur.rowcount:
                cur.close()
                cur = False
                if never_create:
                    return False
        if create or not cur:
            keys = params.keys()
            sql = "insert into " + table + " ( " + \
                ", ".join( keys ) + ") values ( " + \
                ', '.join( [ "%(" + k + ")s" for k in keys ] ) + \
                " ) returning *"
            cur = self.execute( sql, params )
        if cur:
            objRes = cursor2dicts( cur )
            cur.close()
            self.commit()
            return objRes
        else:
            return False

    def getMasterDetail( self, masterSQL, params, detailSQL, 
            detailFieldName = 'detail' ):
        data = cursor2dicts( self.execute( masterSQL, params ) )
        for row in data:
            row[ detailFieldName ] = cursor2dicts( 
                    self.execute( detailSQL, row ) )
        return data

    def updateObject( self, table, params ):
        paramString = ", ".join( [ k + " = %(" + k + ")s" 
            for k in params.keys() if k != "id" ] )
        if paramString != '':
            sql = "update " + table + " set " + paramString + \
                " where id = %(id)s returning *" 
            cur = self.execute( sql, params )
            if cur:
                objRes = cursor2dicts( cur )
                cur.close()
                self.commit()
                return objRes

    def deleteObject( self, table, id ):
        sql = "delete from " + table + " where id = %s" 
        self.execute( sql, ( id, ) ).close()
        self.commit()


    def insertWeatherRecord( self, data ):
        for field in self.weatherFields:
            if not data.has_key( field ):
                data[field] = None
        fieldsStr = 'ts'
        valuesStr = "timestamp 'epoch' + %(epoch)s * interval '1 second'"
        for field in self.weatherFields + ( 'station_id', ):
            fieldsStr += ', ' + field
            valuesStr += ', %(' + field + ')s'
        sql = "insert into data ( " + fieldsStr + " ) values ( " + valuesStr + ")"
      
      
        cur = self.conn.cursor()
        try:
            cur.execute( sql, data )
            self.conn.commit()


        except psycopg2.Error, e:
            self.conn.rollback()
            logging.exception( 'insert weather record error' )

    def getLastWeatherRecord( self, stationID ):
        sql = 'select ( extract( epoch from ts )::int / 600 ) * 600 as epoch, ' + \
                ', '.join( self.weatherFields ) + """ from data where station_id = %s
                order by ts desc limit 1;"""
        return cursor2dicts( self.execute( sql, ( stationID, ) ) )

rmdb = dbConn()


    
