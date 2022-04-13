#!/usr/bin/python
#coding=utf-8
from rmconfig import rmconfig, appPath
from os import listdir, path
from subprocess import Popen, PIPE
import string, random, logging, os

conf = rmconfig()
siteRoot = conf.get( 'site', 'path' )
cmdPath = siteRoot + '/.cmd'
logging.basicConfig( format = '%(asctime)s %(message)s', level = logging.INFO )
uscripts = { 'dbstations': 'dbFillStations.py', 'index': 'createIndex.py', 'astro': 'astro.py', \
        'test': 'update.py -t' }

for cmd in listdir( cmdPath ):

    if cmd == 'ftpclients':
        cmdUserAdd = 'useradd -s /usr/sbin/nologin -d {0}/.clients/{1} -m -g ftp -N realmeteo_{1}'
        cmdPasswd = 'passwd realmeteo_{0}'
        for user in open( cmdPath + '/ftpclients', 'r' ).readlines():
            user = user.rstrip( '\r\n' )
            pUserAdd = Popen( cmdUserAdd.format( siteRoot, user ), \
                    shell = True, stdout = PIPE, stderr = PIPE )
            ( out, err ) = pUserAdd.communicate()
            if pUserAdd.returncode != 0:
                logging.error( 'Error creating user realmeteo_' + user + \
                        ':\n' + err + '\n' )
            else:
                passwd = ''.join( random.SystemRandom().choice( string.ascii_letters + string.digits ) \
                        for _ in range(8) )
                pPasswd = Popen( cmdPasswd.format( user ), \
                        shell = True, stdin = PIPE, stdout = PIPE, stderr = PIPE )
                pPasswd.stdin.write( passwd + '\n' )
                pPasswd.stdin.write( passwd + '\n' )
                ( out, err ) = pPasswd.communicate()
                if pPasswd.returncode != 0 :
                    logging.error( 'Error setting password for user realmeteo_' + user + \
                            ':\n' + err + '\n' )
                else:
                    with open( '/etc/vsftpd.users', 'a' ) as vuFile:
                        vuFile.write( '\nrealmeteo_' + user )
                    logging.info( 'ftp user realmeteo_' + user + ' created, password: ' + passwd + \
                            '\n' )
        os.remove( cmdPath + '/ftpclients' )
    elif uscripts.has_key( cmd ):
        Popen( appPath + '/' + uscripts[cmd], shell = True ).communicate()
        logging.info( cmd + '\n' )
        os.remove( cmdPath + '/' + cmd  )
    

