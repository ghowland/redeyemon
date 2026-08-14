#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
SQL Query wrapper

Never cache.  This is fairly low volume and always important to be accurate.
"""

import MySQLdb
import MySQLdb.cursors
import time
import threading
import os
import sys


import log as logging
from log import log


#NOTE(g): Unusual import:
#
#   import rem_api.cloud.rem_ec2 as rem_ec2
#
#   The above line in __Connect(), because of a Python circular import issue.
#   Normally it would be up here at the top.


#NOTE(g): No options are necessary, because this process MUST be automated.
#   How will this work?  Check using DNS and this machines IPs in the


#TODO(g): Get the database list, and always use the write-master.  This is
#   site control, and must be accurate and distributed.
#TODO(g):SECURITY:CRITICAL: Move this to YML file, and ensure it is 600 or fail
DATABASE_NAME = 'site_control'
DATABASE_HOST = None #NOTE(g): This must be automatically assigned to the Master
DATABASE_USER = 'site_control'
DATABASE_PASSWORD = 'rem_insecure' #TODO(g):SECURITY:CRITICAL:  REMOVE.  CHANGE.

# Need this to test the DB connection, before we try to connect.  No point
#   wasting time for the connection to fail.
DATABASE_PORT = 3306

# Maximum number of times to retry
MAX_RETRIES = 3


# A single connection object, and cursor, to the system control DB
CONNECTION = None
CONNECTION_CURSOR = None

#DEBUG_QUERY_COUNT = 0 #DEBUG, count the queries done, track down a bug


# MySQLdb is not thread safe, so Im just locking it so only one query gets
#   through at a time.  We are low traffic, so this is not important,
#   reliability is important.  Not worth making connection/cursor pool.
MYSQL_EXECUTION_LOCK = threading.Lock()

# Use this to make sure we only request 1 connection at a time
MYSQL_CONNECTION_LOCK = threading.Lock()


class SiteMasterUnavailable(Exception):
  """The Site Master database is unavailable, reasons unknown, but it cannot
  be connected to.
  """


def Query(sql, dict_values=None, commit=None):
  """Executes a SQL query and returns the result.

  INSERT: New row id number (only one)
  DELETE: Rows deleted
  UPDATE: Rows updated
  SELECT: List of dicts, keyed on field names as specified in SELECT
  """
  global CONNECTION
  cursor = _GetCursor()

  # Must acquire the cursor AFTER we get the connection, or failure stays locked
  global MYSQL_EXECUTION_LOCK
  MYSQL_EXECUTION_LOCK.acquire()

  # Figure out force commit.  If no commit was specified, this is not a
  #   forced commit.
  if commit == None:
    commit = True
    force_commit = False
  else:
    force_commit = True

  if dict_values:
    sql_full = sql % dict_values
  else:
    sql_full = sql

  #global DEBUG_QUERY_COUNT #DEUBG
  #DEBUG_QUERY_COUNT += 1
  #log('Query %s: %s' % (DEBUG_QUERY_COUNT, sql_full))

  retries = 0
  errors = []
  while retries < MAX_RETRIES:
    retries += 1

    try:
      cursor.execute(sql, dict_values)

    except MySQLdb.OperationalError, e:
      errors.append(e)

      # If this is an early retry failure, just try it again, it may heal
      if retries <= MAX_RETRIES - 2:
        log('Query: Early retry failure(%d): %s: %s' % (retries, e, sql_full))
        ResetConnection()
        continue

      # Else, If this is a repeat failure, reconnect and try again
      elif retries <= MAX_RETRIES - 1:
        log('Query: Repeat retry failure(%d): %s: %s' % (retries, e, sql_full))
        ResetConnection()
        continue

      # Actually fail
      if e[0] == 2013:
        raise Exception('MySQL Operational Error: 2013: Temporary loss of connection: %s' % sql_full)
      elif e[0] == 2003:
        raise Exception('MySQL Operational Error: 2003: Cant connect to host: %s' % sql_full)
      # Database was lost, reconnect
      elif e[0] == 2006:
        raise Exception('MySQL Operational Error: 2006: Database lost connection: %s' % sql_full)
      # This is a bad SQL call probably, report it
      else:
        raise Exception('MySQL error: Bad SQL: %s: %s' % (sql_full, e))

    except MySQLdb.ProgrammingError, e:
      # If this is an early retry failure, just try it again, it may heal
      if retries <= MAX_RETRIES - 2:
        errors.append(e)
        log('Query: Early retry failure(%d): %s: %s' % (retries, e, sql_full))
        continue

      # Else, If this is a repeat failure, reconnect and try again
      elif retries <= MAX_RETRIES - 1:
        errors.append(e)
        log('Query: Repeat retry failure(%d): %s: %s' % (retries, e, sql_full))
        ResetConnection()
        continue

      raise Exception('MySQL error: Programming error: %s: %s' % (sql_full, e))

    except Exception, e:
      raise Exception('MySQL error: Unhandled exception: %s: %s' % (sql_full, e))

    # Figure out whether we need to commit.  Anything that changes data.
    if sql.lower().split(' ')[0] in ('insert', 'update', 'alter', 'delete', 'create'):
      commit_possible = True
    else:
      commit_possible = False

    # Wastefully commit, not worth typing the logic for the traffic of site control
    #   commit: Whether to commit at all
    #   commit_possible: whether this is a command that could use a commit
    #   force_commit: The calling function actually asked for a commit, not
    #     commiting by default.
    #     Will commit, even on a SELECT, because it's forced.
    if commit and (commit_possible or force_commit):
      CONNECTION.commit() # MySQL legacy

    # If this was an insert
    if sql.lower().startswith('insert'):
      result = cursor.lastrowid
    # Else, get the row results
    else:
      result = cursor.fetchall()

    # Release our execution lock
    MYSQL_EXECUTION_LOCK.release()

    return result


def ResetConnection():
  """Resets all our connection info, because the connection was no good."""
  global CONNECTION
  global CONNECTION_CURSOR

  CONNECTION = None
  CONNECTION_CURSOR = None

  # Give a little time for any DB problems to be worked out
  time.sleep(0.1)

  # Try to connect again
  _Connect()

  # Give a little time for any DB problems to be worked out
  time.sleep(0.1)



def _GetCursor():
  """Returns a MySQL cursor to the write-master database.

  Will handle all connection creation procedures, so other functions
  can be ignored.  Can simply do a Query and ignore this though, left for
  programmers discretion.
  """
  _Connect()

  global CONNECTION_CURSOR

  return CONNECTION_CURSOR


def _Connect():
  """Can ignore this and just call GetCursor.  This establishes a connection
  if one doesnt exist, and returns the new/existing connection object.

  Returns: connection object (success) or None (failure).
  """
  global CONNECTION
  global CONNECTION_CURSOR
  global MYSQL_CONNECTION_LOCK
  
  MYSQL_CONNECTION_LOCK.acquire()
  if not CONNECTION or not CONNECTION_CURSOR:
    #TODO(g): Must make sure all exceptions release this before leaving
    __Connect()
  MYSQL_CONNECTION_LOCK.release()

  return CONNECTION



def _PortListeningTest(host, port=DATABASE_PORT):
  """Test that the port is listening.  Returns boolean of success."""
  #log('Testing database: %s:%s' % (host, port))
  # Give it 5 seconds
  TIMEOUT = 5
  import socket
  s = socket.socket()
  s.settimeout(TIMEOUT)
  try:
    s.connect((host, port))
    s.shutdown(1)
    #log('Testing database: %s:%s: Success' % (host, port))
    return True # Success!

  except Exception, e:
    #log('Testing database: %s:%s: Failed' % (host, port))
    return False # Failure...


def __Connect():
  """Internal only.  This actually connects to the MySQL db."""
  #log('Connecting...')
  global CONNECTION
  global CONNECTION_CURSOR

  global DATABASE_NAME
  global DATABASE_HOST
  global DATABASE_USER
  global DATABASE_PASSWORD
  
  global MYSQL_CONNECTION_LOCK

  # If no database host has been set yet, we have to get the master IP from S3
  if DATABASE_HOST == None:
    # Get the Master IP from S3, and set it as our host.  This will work
    #   unless the Master is dead, in which case we will shift to the
    #   Master Election process automatically once we fail later.
    # Cloud
    # Because of a circular import, I have to do this last
    import rem_api.cloud.rem_ec2 as rem_ec2
    master_ip = rem_ec2.GetMasterIp()
    DATABASE_HOST = master_ip

  #TODO(g): Get Write-Master connect info via started process
  database = DATABASE_NAME
  host = DATABASE_HOST
  user = DATABASE_USER
  password = DATABASE_PASSWORD

  # Test the database is listening first, to not waste time
  db_listening = _PortListeningTest(host)
  if not db_listening:
    msg = 'Database not listening: %s' % host
    #log(msg)
    raise SiteMasterUnavailable(msg)

  errors = []

  for attempt in range(0, MAX_RETRIES):
    try:
      log('Connecting to database: %s.%s (%s)' % (host, database,
                                                  os.path.basename(sys.argv[0])))
      connection = MySQLdb.connect(host=host, db=database, user=user, passwd=password)
    except MySQLdb.OperationalError, e:
      errors.append(e)

      # Rest and loop, if it's not the last one
      if attempt < MAX_RETRIES-1:
        time.sleep(0.1)
        continue
      else:
        # Can't connect to MySQL server on 'hostname', DNS Resolve or server down.
        if e[0] == 2003:
          MYSQL_CONNECTION_LOCK.release() # Ensure the connection lock is released
          raise Exception('MySQL Cant connect: %s' % errors[-1])
        if e[0] == 1045:
          MYSQL_CONNECTION_LOCK.release() # Ensure the connection lock is released
          raise Exception('MySQL password is incorrect: %s' % errors[-1])
        else:
          MYSQL_CONNECTION_LOCK.release() # Ensure the connection lock is released
          raise Exception('MySQL: Unhandled failure: %s' % errors[-1])
    except Exception, e:
      errors.append(e)

      # Rest and loop, if it's not the last one
      if attempt < MAX_RETRIES-1:
        time.sleep(0.1)
        continue
      else:
        MYSQL_CONNECTION_LOCK.release() # Ensure the connection lock is released
        raise Exception('MySQL errored out: %s' % errors[-1])

  #log('Saving database connection')
  CONNECTION = connection
  CONNECTION_CURSOR = connection.cursor(MySQLdb.cursors.DictCursor)


def GetSchema():
  """Returns a dict of tables with a dict of fields.

  NOTE(g): This is only useful for Unity internal processes.  All Unity
      operations use the Unity schema, not this.  Not adding this function
      to the Database Cursor objects intentionally, so it is not used.
  """
  sql = "SHOW TABLES"
  tables = Query(sql)

  schema = {}

  for table in tables:
    table_name = table.values()[0]

    # Create the schema table
    schema[table_name] = {}

    sql = "DESC %s" % table_name
    fields = Query(sql)

    # Get all the field names
    for field in fields:
      # Ensure all the keys are lower cased
      keys = field.keys()
      for key in keys:
        if key.lower() != key:
          field[key.lower()] = field[key]
          del field[key]

      # Fix up the fields
      if field['key'] == 'PRI':
        field['type_option'] = 'Primary Key'
      else:
        field['type_option'] = None

      if field['default'] != '':
        field['default'] = field['default']
      else:
        field['default'] = None

      # Split out the type from the type size, if present
      if '(' in field['type']:
        # Erase any second words from the type, like 'unsigned'.  I dont care
        field['type'] = field['type'].split(' ')[0]

        # Evaluate the type name and size
        type_name = field['type'].split('(', 1)[0]
        if ',' not in field['type']:
          type_size = int(field['type'].split('(', 1)[1][:-1])
        else:
          type_size = int(field['type'].split('(', 1)[1][:-1].split(',')[0])

        field['type'] = type_name
        field['type_size'] = type_size
      else:
        field['type_size'] = None

      # Save the field in the table
      schema[table_name][field['field']] = field

  return schema


def SanitizeSQL(text):
  return str(text).replace("'", "''").replace("\\", "\\\\")


def ConvertTimeToEpoch(datetime_value):
  return time.mktime(datetime_value.timetuple())


def RunMysqlCommand(mysql_command):
  """When the database isnt configured yet, so we need to run MySQL commands
  from the command line.
  """
  #TODO(g): Move this someplace better.
  MYSQL_BINARY = '/usr/bin/mysql'

  # Ensure wildcard chars are escaped
  #mysql_command = mysql_command.replace("*", "\*")

  cmd = '''/bin/echo "%s" | %s''' % (mysql_command, MYSQL_BINARY)
  log('RunMysqlCommand: %s' % cmd)
  os.system(cmd)





if __name__ == '__main__': #TEST
  print Query('SELECT * FROM pool')
