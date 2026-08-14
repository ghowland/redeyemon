#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Database Function: MySQL: Create

Create this database, or ensure it is properly set up.
"""


import sys
import os


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def Execute(data=None, state=None):
  """"""
  if 'instance_id' not in data:
    return site_control.IncorrectExecuteArgs('db_instance_id key is found in data')
  
  instance_id = data['instance_id']
  
  instance = site_control.GetDatabaseInstance(instance_id)
  
  print 'Create the database for this db_instance:'
  print instance
  
  ## Commands to build a database on the storage, symlink and import SQL
  #mkdir /mnt/storage_39/mysql
  #mkdir /mnt/storage_39/mysql/databasename
  #echo 'create database databasename;' | mysql -u root
  #mv /var/lib/mysql/databasename/* /mnt/storage_39/mysql/databasename/
  #rmdir /var/lib/mysql/databasename
  #ln -s /mnt/storage_39/mysql/databasename /var/lib/mysql/databasename
  #chown -R mysql:mysql /mnt/storage_39/mysql/databasename/
  #mysql -u root databasename < ../site_control.sql

  storage = site_control.GetStorage(instance['mount_storage'])
  db = site_control.GetDatabase(instance['db'])

  # Create paths
  mysql_path = '%s/mysql' % storage['mount_path']
  db_path = '%s/%s' % (mysql_path, db['name'])

  # Make a directory for mysql databases on this storage, if it doesnt exist
  if not os.path.isdir(mysql_path):
    log('Making MySQL path: %s' % mysql_path)
    os.mkdir(mysql_path)

  # Create the database in it's normal /var/lib/mysql path
  cmd = "echo 'create database %s;' | mysql -u root" % db['name']
  log('Creating database: %s' % cmd)
  (status, output, output_error) = run_script.Run(cmd)
  if status != 0:
    log('Failed: %s' % output)
    log('Failed, Errors: %s' % output_error)
    return
  
  # Move the database files from the /var/lib/mysql/ database path, to it's
  #   storage's path
  cmd = "mv /var/lib/mysql/%s %s" % (db['name'], db_path)
  log('Moving database to storage: %s' % cmd)
  (status, output, output_error) = run_script.Run(cmd)
  if status != 0:
    log('Failed: %s' % output)
    log('Failed, Errors: %s' % output_error)
    return
  
  # Symlink the storage path with database files to the /var/lib/mysql database
  #   path, so MySQL sees the database exists again
  cmd = "ln -s %s /var/lib/mysql/%s" % (db_path, db['name'])
  log('Moving database to storage: %s' % cmd)
  (status, output, output_error) = run_script.Run(cmd)
  if status != 0:
    log('Failed: %s' % output)
    log('Failed, Errors: %s' % output_error)
    return
  
  # Import the test database
  #TODO(g): Get the config specified database...
  cmd = "mysql -u root %s < /usr/local/site_control/site_control.sql" % db['name']
  log('Import database: %s' % cmd)
  log('TODO(g): Get the config specified database...', logging.CRITICAL)
  (status, output, output_error) = run_script.Run(cmd)
  if status != 0:
    log('Failed: %s' % output)
    log('Failed, Errors: %s' % output_error)
    return



def main(args=None):
  if not args:
    args = {}
  
  # If we have the db_instance.id arg
  if len(args) == 1:
    instance_id = int(args[0])
    
    # Execute the function
    result = Execute({'instance_id':instance_id})
    
    # If there was a problem... (This is really just an example, pointless here)
    if isinstance(result, site_control.IncorrectExecuteArgs):
      print 'Incorrect args...'
      sys.exit(0)
  
  else:
    print 'usage: %s db_instance.id' % sys.argv[0]
    
    sys.exit(1)


if __name__ == '__main__':
  #TODO(g): P
  main(sys.argv[1:])
