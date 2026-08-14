#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Database
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


# The db_instance_status.  _instance left off for brevity.
DB_STATUS_INITIALIZED = 1
DB_STATUS_ALLOCATED = 2
DB_STATUS_CONFIGURED_STORAGE = 3
DB_STATUS_CONFIGURING = 4
DB_STATUS_CONFIGURED = 5
DB_STATUS_VERIFIED = 6
DB_STATUS_ACTIVE = 7
DB_STATUS_REPAIRING = 8


def GetDatabases():
  """Returns a dict of all the Databases in this site.
  
  NOTE(g): We do not need to restrict Databases by site, because Pools already
      do this for us.
  """
  databases = {}
  
  sql = "SELECT * FROM db"
  result = Query(sql)
  
  for item in result:
    databases[item['id']] = item
  
  return databases


def AddDatabase(name, kind, storage_size_gb, info=None, replica_goal=None,
                set=None):
  """Add a database to our system.  Use EnforceDatabase() to handle maintenance."""
  # Our dynamic fields and their values
  fields = []
  values = []
  
  # Add dynamic fields
  if info:
    fields.append("info")
    values.append("'%s'" % SanitizeSQL(info))
  if replica_goal:
    fields.append("replica_goal")
    values.append(str(replica_goal))
  if set:
    fields.append("set")
    values.append(str(set))
  
  # Create field and value strings
  fields_str = ', '.join(fields)
  values_str = ', '.join(values)
  
  # Create the full dynamic SQL statement
  sql = "INSERT INTO db (name, kind, storage_size_gb%s) VALUES " % fields_str
  sql += "('%s', %d, %d%s)" % (SanitizeSQL(name), kind, storage_size_gb,
                               values_str)
  
  # Insert (None if failed)
  database_id = Query(sql)
  
  return database_id


def AddDatabaseInstance(db_id, instance_kind_id):
  """Add an instance for this database, of instance_kind.id.
  
  This also creates an initialized(basically empty) storage entry, which will
  be filled out with a status and stuff on configuration, not now.
  """
  database = GetDatabase(db_id)
  
  instance_kind = GetDatabaseKindInstanceKind(instance_kind_id)
  
  # Create the entry, without storage
  sql = "INSERT INTO db_instance (db, kind, is_writable) VALUES " + \
        "(%d, %d, %d)" % (db_id, instance_kind_id, instance_kind['is_writable'])
  instance_id = Query(sql)
  
  # If we couldnt create this database instance, its a critical failure
  if instance_id == None:
    log('Could not create that database: %s: Instance kind of: %s' % (db_id, instance_kind_id), logging.CRITICAL)
    return None
  
  # Prepare the storage data
  storage_name = 'db_%d_%d' % (db_id, instance_id)
  size_gb = database['storage_size_gb']
  handler_stack = instance_kind['storage_handler_stack']
  
  # Create the storage
  sql = "INSERT INTO storage (name, size_gb, handler_stack) VALUES " + \
        "('%s', %s, %d)" % (SanitizeSQL(storage_name), size_gb, handler_stack)
  storage_id = Query(sql)
  
  # Save the storage we have created
  sql = "UPDATE db_instance SET mount_storage = %d WHERE id = %d" % \
        (storage_id, instance_id)
  Query(sql)
  log('Storage %d assigned to db_instance %d' % (storage_id, instance_id))
  
  # Return the new db_instance.id
  return instance_id


def GetDatabaseSet(db_set):
  """Returns a dict with the db_set field info.  Returns None if not found.
  """
  sql = "SELECT * FROM db_set WHERE id = %d" % db_set
  result = Query(sql)
  
  # If it failed, fail loudly
  if not result:
    log('Could not find db_set: %s' % db_set, logging.CRITICAL)  
    return None
  
  # Else, return our fields
  else:
    return result[0]


def GetDatabaseSetInstances():
  """"""
  


def GetDatabaseSetPools(db_set):
  """Returns a dict, keyed on pool.id(int), value is pool field data."""
  pools = {}
  
  sql = "SELECT * FROM pool WHERE db_set = %d" % db_set
  result = Query(sql)
  
  # Build the list of db.ids
  for item in result:
    pools[item['id']] = item
  
  return pools


def GetDatabaseSetDatabases(db_set):
  """Returns a dict, keyed on db.id(int), value is db field data"""
  dbs = {}
  
  sql = "SELECT * FROM db WHERE `set` = %d" % db_set
  result = Query(sql)
  
  # Build the list of db.ids
  for item in result:
    dbs[item['id']] = item
  
  return dbs


def GetDatabase(db_id):
  """Returns the database fields.  None if not found."""
  sql = "SELECT * FROM db WHERE id = %d" % db_id
  result = Query(sql)
  
  if result:
    return result[0]
  else:
    return None


def GetDatabaseKind(db_kind):
  """Get database kind info, or None if failed."""
  sql = "SELECT * FROM db_kind WHERE id = %d ORDER BY id" % db_kind
  result = Query(sql)
  
  if result:
    return result[0]
  else:
    return None


def GetDatabaseKindInstanceKinds(db_kind):
  """Returns a list of instance_kinds, in order of their importance.
  
  Returns: List of dicts, field data for db_kind_instance_kind
  """
  sql = "SELECT * FROM db_kind_instance_kind WHERE kind = %d ORDER BY importance_count" % db_kind
  result = Query(sql)
  
  instance_kinds = []
  
  for item in result:
    instance_kinds.append(item)
  
  return instance_kinds


def GetDatabaseKindInstanceKind(db_kind_instance_kind):
  """Returns the field data for the Instance Kind.  None if failed."""
  sql = "SELECT * FROM db_kind_instance_kind WHERE id = %d" % db_kind_instance_kind
  result = Query(sql)
  
  if result:
    return result[0]
  else:
    log('Couldnt find db_kind_instance_kind.id: %s' % db_kind_instance_kind, logging.CRITICAL)
    return None


def GetDatabaseInstances(db_id, write_only=False, read_only=False,
                         write_master_only=False, status=None):
  """Returns all the instances for this databases.
  
  By default returns instances of all status.  Specify to get only Active.
  
  Returns: dict, key is int, db_instance.id, value is db_instance field data
  """
  sql = "SELECT * FROM db_instance WHERE db = %d" % db_id
  result = Query(sql)
  
  instances = {}
  
  for item in result:
    # Get the db_kind_instance_kind info
    instance_kind = GetDatabaseKindInstanceKind(item['kind'])
    if instance_kind == None:
      log('Bad instance kind (None) for DB instance: %s' % item)
      continue
    
    # Skip if we only want writable, and this isnt
    if write_only and not instance_kind['is_writable']:
      continue
    
    # Skip if we only want read-only, and this is writable
    if read_only and instance_kind['is_writable']:
      continue
    
    # Skip if we only want write masters (more than one if sharded) and this
    #   isnt
    if write_master_only and not item['is_write_master']:
      continue
    
    # If a status was specified and this isnt it
    if status and item['status'] != status:
      continue
    
    # Add this instance, it passes our gauntlet
    instances[item['id']] = item
  
  return instances


def GetDatabaseInstance(instance_id):
  """Returns dict of db_instance field data, or None if not found."""
  sql = "SELECT * FROM db_instance WHERE id = %d" % instance_id
  result = Query(sql)
  
  if result:
    return result[0]
  else:
    log('Couldnt find Database Instance: %s' % instance_id, logging.CRITICAL)
    return None


def GetDatabaseInstanceStatus(status):
  """Returns dict with db_instance_status field data."""
  sql = "SELECT * FROM db_instance_status WHERE id = %d" % status
  result = Query(sql)
  
  if result:
    return result[0]
  else:
    log('Couldnt find Database Instance Status: %s' % status, logging.CRITICAL)
    return None


def GetDatabaseConfig(db_id, name):
  """Returns the value of this db_config value, None if NULL or not found.
  
  Returns: string or list of strings, if it has multiple entries
  """
  database = GetDatabase(db_id)
  
  # If we dont have this database
  if database == None:
    log('Database not found: %s' % db_id, logging.CRITICAL)
    return None
  
  sql = "SELECT * FROM db_config WHERE db = %d AND name = '%s' ORDER BY value_order" % \
        (db_id, SanitizeSQL(name))
  result = Query(sql)
  
  # If we dont have this result, return None
  if not result:
    return None
  
  # Else, If it's just one value, return it
  elif len(result) == 1:
    return result[0]['value']
  
  # Else, if it's a list, return the list
  else:
    values = []
    
    for item in result:
      values.append(item['value'])
    
    return values


def SetDatabaseConfig(db_id, name, value):
  """Allow setting the database configuration variable.
  
  TODO(g): Allow setting lists, into config data.  Just delete our all previous
      variable entries and then create a new list.
  """
  database = GetDatabase(db_id)
  
  # If we dont have this database
  if database == None:
    log('Database not found: %s' % db_id, logging.CRITICAL)
    return False
  
  # If this is a list value, not supported yet
  if type(value) in (list, tuple):
    #TODO(g): Delete all current entries, and insert these one by one, in order
    log('TODO(g): Support list values for Database State.  Not set: %s: %s = %s' % (database['name'], name, value))
    return False
  
  # Else, if this is a single item
  else:
    # Find out if this state variable already exists
    sql = "SELECT * FROM db_config WHERE db = %d AND name = '%s'" % \
          (db_id, SanitizeSQL(name))
    result = Query(sql)
    
    # If the config variable already exists, update it
    if result:
      cur_id = result[0]['id']
      sql = "UPDATE db_config SET value = '%s', updated = NOW() WHERE id = %d" % (SanitizeSQL(value), db_id)
      Query(sql)
      log('Updated Database Config (%s): %s = %s' % (database['name'], name, value))
      return True
    
    # Else, if this is a new variable
    else:
      sql = "INSERT INTO db_config (db, name, value, updated) VALUES " + \
            "(%d, '%s', '%s', NOW())" % (db_id, SanitizeSQL(name), SanitizeSQL(value))
      result_id = Query(sql)
      log('Created Database Config (%s): %s = %s (%d)' % (database['name'], name, value, result_id))


def GetDatabaseState(db_id, name):
  """Returns the value of this db_state value (str), None if NULL or not found."""
  database = GetDatabase(db_id)
  
  # If we dont have this database
  if database == None:
    log('Database not found: %s' % db_id, logging.CRITICAL)
    return None
  
  sql = "SELECT * FROM db_state WHERE db = %d AND name = '%s' ORDER BY value_order" % \
        (db_id, SanitizeSQL(name))
  result = Query(sql)
  
  # If we didnt have this state, return None
  if not result:
    return None
  else:
    return result[0]['value']


def SetDatabaseState(db_id, name, value):
  """Sets a database state variable value.  Returns boolean, success."""
  database = GetDatabase(db_id)
  
  # If we dont have this database
  if database == None:
    log('Database not found: %s' % db_id, logging.CRITICAL)
    return False
  
  # Find out if this state variable already exists
  sql = "SELECT * FROM db_state WHERE db = %d AND name = '%s'" % \
        (db_id, SanitizeSQL(name))
  result = Query(sql)
  
  # If the state variable already exists, update it
  if result:
    cur_id = result[0]['id']
    sql = "UPDATE db_state SET value = '%s', updated = NOW() WHERE id = %d" % (SanitizeSQL(value), db_id)
    Query(sql)
    log('Updated Database State (%s): %s = %s' % (database['name'], name, value))
    return True
  
  # Else, if this is a new variable
  else:
    sql = "INSERT INTO db_state (db, name, value, updated) VALUES " + \
          "(%d, '%s', '%s', NOW())" % (db_id, SanitizeSQL(name), SanitizeSQL(value))
    result_id = Query(sql)
    log('Created Database State (%s): %s = %s (%d)' % (database['name'], name, value, result_id))


def GetDatabaseBackupLast(count=1):
  """Retries a list of the field dicts of db_backup.  Goes back count entries."""
  sql = "SELECT * FROM db_backup ORDER BY created DESC LIMIT %d" % count
  result = Query(sql)
  
  # Return the list of our latest backups
  return result


def BackupStart(instance_id, machine_id, path, relay_log, relay_position):
  """Start up a backup.  Returns new backup_id.  None if failed."""
  instance = GetDatabaseInstance(instance_id)
  
  # If we dont have this database
  if instance == None:
    log('Database Instance not found: %s' % instance_id, logging.CRITICAL)
    return False
  
  # Get the database too
  database = GetDatabase(instance['db'])
  
  # Create the backup entry
  sql = "INSERT INTO db_backup (instance, machine, created, path, relay_log, relay_position) VALUES " + \
        "(%d, %d, NOW(), '%s', '%s', %d)" % \
        (instance_id, machine_id, SanitizeSQL(path), SanitizeSQL(relay_log),
         relay_position)
  backup_id = Query(sql)
  log('Database Backup Started: %s: Instance %s: On machine: %s' % \
      (database['name'], instance_id, machine_id))
  
  return backup_id


def BackupFinished(backup_id):
  """Mark this backup as finished.  Updates the backup to finished."""
  sql = "UPDATE db_backup SET finished = NOW() WHERE id = %d" % backup_id
  Query(sql)


def GetDatabaseFunctionScript(db_kind, name):
  """Returns the script.id for this db_kind's named function.  Fail == None."""
  sql = "SELECT * FROM db_kind_function WHERE kind = %d AND name = '%s'" % \
        (db_kind, SanitizeSQL(name))
  result = Query(sql)
  
  # Return the script.id or None
  if result:
    return result[0]['script']
  else:
    return None


def GetDatabaseInstanceDatabaseKind(instance_id):
  """Returns db_kind.id(int) for the db this instance is an instance of."""
  instance = GetDatabaseInstance(instance_id)
  
  db = GetDatabase(instance['db'])
  
  return db['kind']


def DatabaseFunctionRun(instance_id, function_name):
  """Run this Database function.  Takes care of all the details.
  
  Database Functions do not return anything because that is too complicated with
  the number of scripts they are running.  They can log their execution, and
  change the state of things, and we can query their state afterwards.
  
  Anything could change after a function runs, so best to just run it, then
  update all the data you are concerned about and test it's state.
  
  Because this is an operational system, there is no real test cases.  As we
  change things, the site will adapt accordingly.
  
  Returns: None
  """
  log('Database Function (%s): Run: %s [%s]' % (instance_id, function_name, stack.Mini(4)))
  
  instance = GetDatabaseInstance(instance_id)
  db_kind = GetDatabaseInstanceDatabaseKind(instance_id)
  
  script_id = GetDatabaseFunctionScript(db_kind, function_name)
  
  log('Database Function Script: %s' % script_id)
  
  # If we got a script
  if script_id:
    # Get the module
    module = site_control.GetScriptPythonModule(script_id)
    
    # Execute the script
    log('Database Instance: %s:  Executing script: %s' % (instance_id, module))
    module.Execute({'instance_id':instance_id})
  else:
    log('Database Function Missing Script: DB Kind: %s  Function: %s' % \
        (instance['kind'], function_name), logging.CRITICAL)


def GetDatabaseInstancesOnMachine(machine_id):
  """Returns a dict, keyed on db_instance.id, value is field data."""
  sql = "SELECT * FROM db_instance WHERE machine = %d" % machine_id
  result = Query(sql)
  
  instances = {}
  
  for item in result:
    instances[item['id']] = item
  
  return instances


def SetDatabaseInstanceStatus(instance_id, status):
  """Sets a db_instance.status to specified."""
  instance = GetDatabaseInstance(instance_id)
  
  log('Changing Database Instance Status: %s: Status: %s -> %s  (%s)' % \
      (instance_id, instance['status'], status, stack.Mini(4)))
  
  # Update the status
  instance['status'] = status
  
  # Update the data
  site_control.UpdateData('db_instance', instance_id, instance)


def GetDatabaseInstanceKindCount(db_id, kind_instance_kind_id):
  """Returns int, the number of database instances for this DB and Instance Kind
  """
  sql = "SELECT * FROM db_instance WHERE db = %d AND kind = %d" % \
        (db_id, kind_instance_kind_id)
  result = Query(sql)
  
  count = len(result)
  
  return count


def GetDatabaseInstanceRequirements(db_id):
  """Returns a dict, keyed are db_kind_instance_kind.id, value is number of
  instances that need to be created, in total, to have enough instances to
  satisfy the db's db_kind's specification.
  """
  database = GetDatabase(db_id)
  
  log('Database: %s' % database)
  
  # Get the database kind
  kind = GetDatabaseKind(database['kind'])
  
  # Get our provisioning requirements
  #TODO(g): When sharding is implemented, this routine will need be altered.
  instance_kinds = GetDatabaseKindInstanceKinds(database['kind'])
  
  # Divide the instance kinds into reads and writes
  write_kinds = []
  read_kinds = []
  for instance_kind in instance_kinds:
    if instance_kind['is_writable']:
      write_kinds.append(instance_kind)
    else:
      read_kinds.append(instance_kind)
  
  # Take the first write and read as the Write Master and read replica, these
  #   are already sorted by importance_count, so they should be in a good order,
  #   even though this is a ridiculously simple algorithm.  Improve later as
  #   needed.
  if write_kinds:
    write_master_kind = write_kinds[0]
  else:
    log('Couldnt find a write master database kind: %s' % db_id, logging.CRITICAL)
    write_master_kind = None
  
  if read_kinds:
    read_replica_kind = read_kinds[0]
  else:
    log('Couldnt find a read-replica database kind: %s' % db_id) # Non-critical
    read_replica_kind = None
  
  # Create the required data
  required = {}
  
  # A single write-master for this database: tuple of kind_instance_kind_id and count
  if write_master_kind:
    #TODO(g): Sharding will change this
    write_master_kind_count = 1
    
    # Get the current number of instances for this kind
    existing_instances = GetDatabaseInstanceKindCount(db_id, write_master_kind['id'])
    
    # Reduce required count by existing count
    log('Database Write-Master Requirements: %s:  Ideal: %s  Existing: %s' % (database['name'], write_master_kind_count, existing_instances))
    write_master_kind_count -= existing_instances
    
    # Add the count required
    required['write_master_kind'] = (write_master_kind['id'], write_master_kind_count)
  
  # As many read-replicas as our goal states: tuple of kind_instance_kind_id and count
  if read_replica_kind:
    #NOTE(g): Manually set for now.  This will eventually have scripts to adjust
    #   the goal dynamically on monitoring performance results.
    read_replica_kind_count = database['replica_goal']
    
    # Get the current number of instances for this kind
    existing_instances = GetDatabaseInstanceKindCount(db_id, read_replica_kind['id'])
    
    # Reduce required count by existing count
    log('Database Read-Replica Requirements: %s:  Ideal: %s  Existing: %s' % (database['name'], read_replica_kind_count, existing_instances))
    read_replica_kind_count -= existing_instances
    
    required['read_replica_kind'] = (read_replica_kind['id'], read_replica_kind_count)
  
  log('Required:\n%s' % required)#Debug
  
  return required




if __name__ == '__main__': #TEST
  
  # Database tests
  if 1:
    AddDatabase('Test', 1, 20, 'Testing... 123', 2)
    pass
