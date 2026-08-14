#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Storage
"""

import os


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


# Storage Config: Action suggestions after storage has been configured
#TODO(g): Im putting in differentiated statuses, so in the future we can return
#   different results for each.  I probably wont do that on the first pass.
#   More visibility into what is going on is better though, and micro-state
#   changes can be added to db_instance_status to track detailed config activity.
####STORAGE_STATUS__ACTIVE = 0
####STORAGE_STATUS__CREATING = 1
####STORAGE_STATUS__RESTORING = 2
####STORAGE_STATUS__TESTING = 3
####STORAGE_STATUS__FAILED = 4

## ^^^------   TODO(g): Remove these once I switch things to use the real status below...



# Storage status
STORAGE_STATUS__INITIALIZED = 1
STORAGE_STATUS__REQUESTED = 2
STORAGE_STATUS__ASSIGNED = 3
STORAGE_STATUS__REASSIGNING = 4
STORAGE_STATUS__MOUNTED = 5
STORAGE_STATUS__REPAIRING = 6
STORAGE_STATUS__VERIFIED = 7
STORAGE_STATUS__ACTIVE = 8


# Storage volume status (only tracks what we need to know about the volume)
#NOTE(g): Volumes do not get configured, or turn Active, once they are assigned
#   that is the extent of their configuring.  Then stuff happens on top of
#   their assigned device.
STORAGE_VOLUME_STATUS__INITIALIZED = 1
STORAGE_VOLUME_STATUS__REQUESTED = 2
STORAGE_VOLUME_STATUS__ASSIGNED = 3
STORAGE_VOLUME_STATUS__CONFIGURED = 4
STORAGE_VOLUME_STATUS__VERIFIED = 5
STORAGE_VOLUME_STATUS__ACTIVE = 6
STORAGE_VOLUME_STATUS__REPAIRING = 7
STORAGE_VOLUME_STATUS__DECOMMISSIONED = 8
STORAGE_VOLUME_STATUS__PAUSED = 9


def GetStorage(storage_id):
  """Returns storage field data dict."""
  sql = "SELECT * FROM storage WHERE id = %d" % storage_id
  result = Query(sql)
  if result:
    return result[0]
  else:
    log('Storage not found: %s' % storage_id, logging.CRITICAL)
    return None


def GetStorageHandlerStack(handler_stack_id):
  """Returns storage_handler_stack field data dict.  None if not found"""
  sql = "SELECT * FROM storage_handler_stack WHERE id = %d" % handler_stack_id
  result = Query(sql)
  if result:
    return result[0]
  else:
    log('Storage Handler Stack not found: %s' % handler_stack_id, logging.CRITICAL)
    return None


def GetStorageHandler(handler_id):
  """Returns storage_handler field data dict."""
  sql = "SELECT * FROM storage_handler WHERE id = %d" % handler_id
  result = Query(sql)
  if result:
    return result[0]
  else:
    log('Storage Handler not found: %s' % handler_id, logging.CRITICAL)
    return None


def GetStorageHandlerFunction(handler_id, function_name):
  """There can be many functions in a function name, so return them all.
  
  Returns: None or dict
  """
  function_result = None
  
  # Get the handler's function info, if available
  sql = "SELECT * FROM storage_handler_function WHERE handler = %d AND name = '%s'" % \
        (handler_id, SanitizeSQL(function_name))
  result = Query(sql)
  
  # If this handler has this function
  if result:
    return result[0]
  else:
    return None


def GetStorageConfig(storage_id, name):
  """Returns the value of this storage_config value, None if NULL or not found.
  
  Returns: string or list of strings, if it has multiple entries
  """
  storage = GetStorage(storage_id)
  
  # If we dont have this storage
  if storage == None:
    log('Storage not found: %s' % storage_id, logging.CRITICAL)
    return None
  
  sql = "SELECT * FROM storage_config WHERE storage = %d AND name = '%s' ORDER BY value_order" % \
        (storage_id, SanitizeSQL(name))
  result = Query(sql)
  
  # If we dont have this result, return None
  if not result:
    return None
  
  # Else, If it's just one value, return it
  elif len(result) == 1:
    # If the value_order field was not set (NULL), then this is a normal value
    if result[0]['value_order'] == None:
      return result[0]['value']
    
    # Else, value_order was set.  We are expecting a list, even if its only one
    else:
      return list(result[0]['value'])
  
  # Else, if it's a list, return the list
  else:
    values = []
    
    for item in result:
      values.append(item['value'])
    
    return values


def SetStorageConfig(storage_id, name, value, value_order=None):
  """Allow setting the storage configuration variable.
  
  TODO(g): Allow setting lists, into config data.  Just delete our all previous
      variable entries and then create a new list.
  """
  storage = GetStorage(storage_id)
  
  # If we dont have this storage
  if storage == None:
    log('Storage not found: %s' % storage_id, logging.CRITICAL)
    return False
  
  # If this is a list value, not supported yet
  if type(value) in (list, tuple):
    #TODO(g): Delete all current entries, and insert these one by one, in order
    log('TODO(g): Support list values for Storage State.  Not set: %s: %s = %s' % (storage['name'], name, value))
    return False
  
  # Else, if this is a single item
  else:
    # Find out if this state variable already exists
    if value_order == None:
      sql = "SELECT * FROM storage_config WHERE storage = %d AND name = '%s'" % \
            (storage_id, SanitizeSQL(name))
    else:
      sql = "SELECT * FROM storage_config WHERE storage = %d AND name = '%s' AND value_order = %d" % \
            (storage_id, SanitizeSQL(name), value_order)
    result = Query(sql)
    
    # If the config variable already exists, update it
    if result:
      cur_id = result[0]['id']
      
      if value_order == None:
        sql = "UPDATE storage_config SET value = '%s', updated = NOW() WHERE id = %d" % (SanitizeSQL(value), cur_id)
      else:
        sql = "UPDATE storage_config SET value = '%s', value_order = %d, updated = NOW() WHERE id = %d" % (SanitizeSQL(value), value_order, cur_id)
      
      Query(sql)
      log('Updated Storage Config (%s): %s = %s' % (storage['name'], name, value))
      return True
    
    # Else, if this is a new variable
    else:
      if value_order == None:
        sql = "INSERT INTO storage_config (storage, name, value, updated) VALUES " + \
              "(%d, '%s', '%s', NOW())" % (storage_id, SanitizeSQL(name), SanitizeSQL(value))
      else:
        sql = "INSERT INTO storage_config (storage, name, value, value_order, updated) VALUES " + \
              "(%d, '%s', '%s', %d, NOW())" % (storage_id, SanitizeSQL(name), SanitizeSQL(value), value_order)
      
      result_id = Query(sql)
      log('Created Storage Config (%s): %s = %s (%d)' % (storage['name'], name, value, result_id))


def GetStorageState(storage_id, name):
  """Returns the value of this storage_state value (str), None if NULL or not found."""
  storage = GetStorage(storage_id)
  
  # If we dont have this storage
  if storage == None:
    log('Storage not found: %s' % storage_id, logging.CRITICAL)
    return None
  
  sql = "SELECT * FROM storage_state WHERE storage = %d AND name = '%s'" % \
        (storage_id, SanitizeSQL(name))
  result = Query(sql)
  
  # If we didnt have this state, return None
  if not result:
    return None
  else:
    return result[0]['value']


def SetStorageState(storage_id, name, value):
  """Sets a storage state variable value.  Returns boolean, success."""
  storage = GetStorage(storage_id)
  
  # If we dont have this storage
  if storage == None:
    log('Storage not found: %s' % storage_id, logging.CRITICAL)
    return False
  
  # Find out if this state variable already exists
  sql = "SELECT * FROM storage_state WHERE storage = %d AND name = '%s'" % \
        (storage_id, SanitizeSQL(name))
  result = Query(sql)
  
  # If the state variable already exists, update it
  if result:
    cur_id = result[0]['id']
    sql = "UPDATE storage_state SET value = '%s', updated = NOW() WHERE id = %d" % (SanitizeSQL(value), cur_id)
    Query(sql)
    log('Updated Storage State (%s): %s = %s' % (storage['name'], name, value))
    return True
  
  # Else, if this is a new variable
  else:
    sql = "INSERT INTO storage_state (storage, name, value, updated) VALUES " + \
          "(%d, '%s', '%s', NOW())" % (storage_id, SanitizeSQL(name), SanitizeSQL(value))
    result_id = Query(sql)
    log('Created Storage State (%s): %s = %s (%d)' % (storage['name'], name, value, result_id))


def GetStorageVolume(volume_id):
  """Returns the field dict for this storage_volume.  None if not found."""
  sql = "SELECT * FROM storage_volume WHERE id = %d" % volume_id
  result = Query(sql)
  
  if result:
    return result[0]
  else:
    return None


def GetStorageVolumeLowestEmptyOrder(storage_id):
  """Returns the lowest empty id for the storage's volume order."""
  lowest_empty_order = 0
  
  # Get all the storage volumes for this storage
  sql = "SELECT * FROM storage_volume WHERE storage = %d ORDER BY storage_order" % storage_id
  result = Query(sql)
  
  for item in result:
    # If we have this storage_order, then increment our lowest empty order
    if item['storage_order'] == lowest_empty_order:
      lowest_empty_order += 1 # Push it forward until it doesnt match a place
  
  # Return our lowest non-matched volume storage order
  return lowest_empty_order


def GetStorageVolumeHighestUsedOrder(storage_id):
  """Returns the highest used id for the storage's volume order.
  
  Returns int or None if no volumes exist.
  """
  # Get all the storage volumes for this storage
  sql = "SELECT * FROM storage_volume WHERE storage = %d ORDER BY storage_order DESC LIMIT 1" % storage_id
  result = Query(sql)
  
  # If we have a result, its the highest order number used, return it
  if result:
    result[0]['storage_order']
  
  # Else, no result
  else:
    return None


def StorageAssignToMachine(machine_id):
  """Assign this storage to the machine in the DB, and in EC2.
  
  Mark as status=Allocated(2)
  """
  #TODO(g):...
  pass #DB failover will do this, as will setting up an-new storage item


def AssignStorageVolumeToMachine(volume_id, machine_id):
  """"""
  #TODO(g):...
  pass#...


def RemoveStorageVolume(storage_id, volume_id):
  """Removes the storage_volume.id from EC, then from Site Control."""
  #TODO(g):...
  #NOTE(g): Will attempt to remove from EC2, even if gone from EC2 no big deal
  #   and that way we can treat a couple of cases the same way.
  pass#...


def RebuildStorage(storage_id):
  """Rebuilds the storage, formatting it and readying it.  If a restore can
  be done from backups, it is done.
  """
  #TODO(g): Why would this happen here?  This should happen in the Config
  #   script and call Storage Function "CreateVolumeFromSnapshot" directly.
  #   Call "Restore", which wraps "CreateVolumeFromSnapshot", so we can add
  #   other backend methods easier.
  
  
  #TODO(g):...  Call script_repair, and then
  #TODO(g): if the device hasnt been set up initially yet, ignore, becasue its
  #   going through setup phases
  pass#...


def GetStorageConfigInfo(storage_id):
  """Get this from the handler_stack storage_handler_stack.script_config_info.
  
  Running that script returns a dictionary, which we return.
  """
  # Get the Storage
  storage = GetStorage(storage_id)
  
  # Get the Storage's Handler Stack
  handler_stack = GetStorageHandlerStack(storage['handler_stack'])
  
  # Get the config_info id
  script_id = handler_stack['script_config_info']
  
  #TODO(g): This doesnt give me what I want.  Is there a way to get a python
  #   dict or something from thing?  It outputs a YAML file which I can read
  #   in, something?  I like the YAML file actually...  Then parse in the YAML
  #   file
  config_info = run_script.RunScript(script_id)
  
  #...
  raise Exception('Not FINISHED!  Figure out how to get a dictionary out of this...')
  #...
  
  config_info = {'machine':machine_id, 'volume_count':count, 'volume_size':size,
                 'mount_path_final':mount_path, }
  
  #return#... todo...
  
  
def SetStorageStatus(storage_id, status):
  """Set the storage status."""
  log('Setting storage status: Storage: %s:  Status: %s' % (storage_id, status))
  
  sql = "UPDATE storage SET status = %d WHERE id = %d" % (status, storage_id)
  Query(sql)


def SetStorageVolumeStatus(volume_id, status):
  """Set the storage status."""
  log('Setting storage volume status: Storage Volume: %s:  Status: %s' % (volume_id, status))
  
  sql = "UPDATE storage_volume SET status = %d WHERE id = %d" % (status, volume_id)
  Query(sql)


def GetStorageVolumeStatus(status):
  """Returns field data from storage_volume, or None if not found."""
  sql = "SELECT * FROM storage_volume_status WHERE id = %d" % status
  result = Query(sql)
  
  if result:
    return result[0]
  else:
    return None


def GetStorageStatus(status):
  """Returns field data from storage, or None if not found."""
  sql = "SELECT * FROM storage_status WHERE id = %d" % status
  result = Query(sql)
  
  if result:
    return result[0]
  else:
    return None


def GetStorageHandlerStackStackList(stack_id, stack_list=None):
  """Returns a list of storage_handler_stack.ids, from the top element in the
  stack to the bottom (last).
  """
  if not stack_list:
    stack_list = []
  
  # Get the current stack
  cur_stack = GetStorageHandlerStack(stack_id)
  
  # Add it to our stack list
  stack_list.append(cur_stack['id'])
  
  # If we have a parent stack, add it to this stack_list
  if cur_stack['stack_parent']:
    # Recurse until we have no more parents
    GetStorageHandlerStackStackList(cur_stack['stack_parent'], stack_list=stack_list)
  
  return stack_list


def GetStorageHandlerStackName(stack_id):
  """Returns handler stack name (string).
  
  This is a compound of all the stack layers' handler's names.
  """
  # Get our stack list
  stack_list = GetStorageHandlerStackStackList(stack_id)
  
  name = ''
  for cur_stack_id in stack_list:
    cur_stack = GetStorageHandlerStack(cur_stack_id)
    cur_handler = GetStorageHandler(cur_stack['storage_handler'])
    
    # Add the join, if we already have items
    if name:
      name += ' on '
    
    # Append the current handler name
    name += cur_handler['name']
  
  return name


def GetStorageVolumes(storage_id):
  """Returns a dict of storage volumes, keyed on storage_volume.id"""
  volumes = {}
  
  sql = "SELECT * FROM storage_volume WHERE storage = %d" % storage_id
  result = Query(sql)
  
  for item in result:
    volumes[item['id']] = item
  
  return volumes


def GetStorageVolumeList(storage_id):
  """Returns a list of ints: storage_volume.id"""
  volumes = []
  
  sql = "SELECT * FROM storage_volume WHERE storage = %d ORDER BY storage_order" % storage_id
  result = Query(sql)
  
  for item in result:
    volumes.append(item['id'])
  
  return volumes


def GetStorageHandlerStackStorages(handler_stack_id):
  """Returns a dict with all the storages that use this stack, keyed on id."""
  storages = {}
  
  sql = "SELECT * FROM storage WHERE handler_stack = %d" % handler_stack_id
  result = Query(sql)
  
  for item in result:
    storages[item['id']] = item
  
  return storages


def GetStorageHandlerStackFunctionScriptList(storage_id, function_name):
  """Get a stack script list, defaults to up stack.
  
  Functions go from top to bottom.
  
  Args:
    upwards: boolean, True==Return the stack as Bottom to Top.
  
  Returns: list of ints, script.id, meant to be executed in the ordered returned
  """
  # Scripts, meant to be executed in the ordered returned
  enter_scripts = []
  exit_scripts = []
  
  # Get the list of handlers from the stack, this is what we need
  handler_list = GetStorageHandlerList(storage_id)
  
  # Add all the functions of this name for each of the handlers
  for handler in handler_list:
    handler_function = site_control.GetStorageHandlerFunction(handler['id'],
                                                              function_name)
    
    # If we have functions for this handler, add them to our enter/exit scripts
    if handler_function:
      if handler_function['script_enter']:
        enter_scripts.append(handler_function['script_enter'])
      
      if handler_function['script_exit']:
        exit_scripts.append(handler_function['script_exit'])
  
  # Reverse the exit scripts, so we can run them Bottom-Up
  exit_scripts.reverse()
  
  # Build our final script list, by going Top-Down on enter, and Bottom-Up on
  #   exit.  This is the order ALL Storage Functions are executed, as it gives
  #   us the control over locking higher layers before doing a low layer
  #   operation, and unlocking coming out, so operations can be automatic.
  #   This is important for Backup, which will perform Snapshots, where the
  #   block data needs to be consistent per block or the backup is corrupt.
  scripts = enter_scripts + exit_scripts
  
  return scripts


def StorageFunctionRun(storage_id, function_name):
  """Run this Storage function.  Takes care of all the details.
  
  Storage Functions do not return anything because that is too complicated with
  the number of scripts they are running.  They can log their execution, and
  change the state of things, and we can query their state afterwards.
  
  Anything could change after a function runs, so best to just run it, then
  update all the data you are concerned about and test it's state.
  
  Because this is an operational system, there is no real test cases.  As we
  change things, the site will adapt accordingly.
  
  Returns: None
  """
  log('Storage Function (%s): Run: %s [%s]' % (storage_id, function_name, stack.Mini(4)))
  
  # Get the scripts we need to execute
  scripts = GetStorageHandlerStackFunctionScriptList(storage_id, function_name)
  
  log('Storage Function Script Stack: %s' % scripts)
  
  # Execute each of the scripts in sequence
  for script_id in scripts:
    module = site_control.GetScriptPythonModule(script_id)
    
    # Execute the script
    log('Storage: %s:  Executing script: %s' % (storage_id, module))
    module.Execute({'storage_id':storage_id})
  

def GetStorageHandlerList(storage_id):
  """Returns a list of storage_handler field dicts for this storage.
  
  Returns the handlers in the order they are stacked, with the top stack element
  returns first[0], and the bottom element last[-1].
  """
  handlers = []
  
  storage = GetStorage(storage_id)
  
  # Get the Storage's handlers
  cur_stack_id = storage['handler_stack']
  
  # Get our handler stack (without recursion)
  while cur_stack_id != None:
    # Get the stack data
    handler_stack = GetStorageHandlerStack(cur_stack_id)
    
    # Get the Storage Handler
    handler = GetStorageHandler(handler_stack['storage_handler'])
    
    # Add this handler to our list
    handlers.append(handler)
    
    # Set the current stack ID to our stack parent.  When it's None, we stop.
    cur_stack_id = handler_stack['stack_parent']
  
  return handlers


def StorageVolumeProvisionGeneric(storage_id, required_volume_count):
  """This handles all the volume provisioning once we know the required volumes.
  
  storage_handler_stack.script_provision will call this function, once it has
  determined how many volumes this 
  """
  storage = GetStorage(storage_id)
  handler_stack = GetStorageHandlerStack(storage['handler_stack'])
  
  # Get all the volumes we have (includes new volumes)
  volumes = site_control.GetStorageVolumes(storage_id)
  
  # If we dont have enough volumes
  if len(volumes) < required_volume_count:
    # Creating 
    for count in range(0, required_volume_count - len(volumes)):
      log('Creating volume for Storage: %s: Create Count: %s' % (storage_id, count))
      
      # Create the volumes
      site_control.StorageVolumeCreate(storage_id)
  
  # Else, if we have too many volumes
  elif len(volumes) > required_volume_count:
    log('Too many Storage Volumes.  Case not handled: Storage %s.  Cannot operate on this storage until this is fixed.' % storage_id, logging.CRITICAL)
    return
  else:
    log('Correct number of volumes: %s == %s' % (required_volume_count, len(volumes)))
  
  
  # Execute the Provision Request script
  log('Running Provision Script')
  site_control.ExecuteScript(handler_stack['script_provision'],
                             {'storage_id':storage_id}, {})


def StorageVolumeCreate(storage_id):
  """Create a new volume entry for this storage."""
  storage = GetStorage(storage_id)
  handler_stack = GetStorageHandlerStack(storage['handler_stack'])
  
  # Execute the Volume Create
  #NOTE(g): This has to be unique per Handler Stack, we have no idea how to
  #   divide up the size_gb among volumes or anything else.  Each Hander Stack
  #   top stack item needs to deal with it itself.
  volume_id = site_control.ExecuteScript(handler_stack['script_create_volume'],
                                         {'storage_id':storage_id}, {})
  
  log('Storage: %s  New Volume: %s' % (storage_id, volume_id))
  return volume_id


def StorageVolumeCreate_Actual(storage_id, order, size_gb):
  """Creates the storage_volume entry for StorageVolumeCreate.  Not called
  directly, except from storage_handler_stack.script_create_volume scripts.
  
  Returns the new storage_volume.id
  """
  storage = GetStorage(storage_id)
  
  sql = "INSERT INTO storage_volume (storage, storage_order, size_gb, machine) VALUES " + \
        "(%d, %d, %d, %d)" % (storage_id, order, size_gb, storage['mount_machine'])
  volume_id = Query(sql)
  
  return volume_id


def IsStorageConfigurationComplete(storage_id):
  """Test all of the handler stack values.  If they are all 100, its complete."""
  storage = GetStorage(storage_id)
  
  # Any failure proves this false
  is_complete = True
  
  stack_list = GetStorageHandlerStackStackList(storage['handler_stack'])
  
  # Process each storage_handler_stack.id
  for handler_stack_id in stack_list:
    handler_stack = GetStorageHandlerStack(handler_stack_id)
    
    # Create the storage state key
    state_key = 'config_%(name)s' % handler_stack
    
    state_complete = GetStorageState(storage_id, state_key)
    
    # If this handler is not 100 (all states are strings, or None), not complete
    if state_complete != '100':
      log('Storage Configuration is not complete: %s=%s' % (state_key, state_complete))
      is_complete = False
      break
  
  # Verify the configured volumes made a good mounted storage device
  if is_complete == True:
    # Mark any volumes that were "Assigned"(3) to "Configured"(4)
    volumes = GetStorageVolumes(storage_id)
    for (volume_id, volume) in volumes.items():
      # If this volume was "Assigned"
      if volume['status'] == 3:
        # Set it to "Configured"
        volume['status'] = 4
        site_control.UpdateData('storage_volume', volume_id, volume)
  
  return is_complete


def StorageConfigure(storage_id):
  """Configure this storage.
  
  Everything is generic, specifies are called out to.
  """
  storage = GetStorage(storage_id)
  handler_stack = site_control.GetStorageHandlerStack(storage['handler_stack'])
  
  
  log('Configuring Storage: %s: Status: %s' % (storage['name'], storage['status']))
  
  # Ensure we have volumes
  #TODO(g): This should really be done in the set up process, this is the wrong
  #   place, but Im trying to get this done quickly.  Clean up later.
  volumes = GetStorageVolumes(storage_id)
  if not volumes:
    log('No volumes found, provisioning...')
    
    # Provision the volumes this Storage needs
    site_control.ExecuteScript(handler_stack['script_provision'],
                               {'storage_id':storage_id}, {})
  
  # If this storage is just Initialized, or Requested (pending assignment)
  if storage['status'] in (site_control.STORAGE_STATUS__INITIALIZED,
                           site_control.STORAGE_STATUS__REQUESTED):
    # Request the storage volumes: Run the script_provision script
    site_control.ExecuteScript(handler_stack['script_provision_request'],
                               {'storage_id':storage_id}, {})
  
  
  # If this storage has been Assigned to a machine
  if storage['status'] == site_control.STORAGE_STATUS__ASSIGNED:
    # Configure the storage volumes, they have been assigned
    #NOTE(g): Assigned storage is always NEW, so, it will need to be
    #   initialized.  Storage that is being re-assigned or re-created
    #   will use the Repairing status, not Assigned/Requested.
    
    # Run "Configure" function
    log('Running Configure Function')
    site_control.StorageFunctionRun(storage_id, "Configure")
    
    # Test if the storage stack is configured
    complete = site_control.IsStorageConfigurationComplete(storage_id)
    
    # If we are complete update the storage, mark storage Configured
    if complete:
      #TODO(g): CRITICAL: This short-cuts everything below.  I dont like the
      #   current system of storage/volume statuses.  They need to be totally
      #   re-worked to put a lot more complexity in storage and maybe remove
      #   an item or two from volume.  I think I overloaded volume and stripped
      #   storage last time, and I need another pass.  No point doing the
      #   rest of these until this is done.
      site_control.SetStorageStatus(storage_id, site_control.STORAGE_STATUS__MOUNTED)
  
  
  # If this storage has been Mounted on a machine
  if storage['status'] == site_control.STORAGE_STATUS__MOUNTED:
    # Set the mount_path for this storage, from the top handle_stack.name's
    #   storage_config value
    handler_stack = GetStorageHandlerStack(storage['handler_stack'])
    mount_path = GetStorageConfig(storage_id, handler_stack['name'])
    storage['mount_path'] = mount_path
    site_control.UpdateData('storage', storage_id, storage)
    
    # Verify that this storage was properly configured
    log('Verify storage: %s' % storage_id)
    site_control.StorageFunctionRun(storage_id, "Verify") # Sets state internally
  
  
  
  # If this storage has been Mounted on a machine
  if storage['status'] == site_control.STORAGE_STATUS__VERIFIED:
    # Snapshot the storage we just mounted
    #TODO(g): Only do this for NEW storage in the future, otherwise its a waste
    #   as we just restored from a snapshot...  But for now, simple and fast.
    log('Snapshot storage: %s' % storage_id)
    site_control.StorageFunctionRun(storage_id, "Snapshot")
    
    # Activate the storage!
    site_control.SetStorageStatus(storage_id, site_control.STORAGE_STATUS__ACTIVE)
  
  #TODO(g): CRITICAL: Turn all of the below back on after I re-work statuses,
  #   site_control.STORAGE_STATUS__MOUNTED is stupid for a final test.  Active 
  #   is the right way to do it, with Paused, Repairing and other states that
  #   reflect both the storage and when underlaying volumes are doing something.
  
  ## If this storage is Configured
  #if storage['status'] == site_control.STORAGE_STATUS__CONFIGURED:
  #  # Verify the storage
  #  
  #  # Run "Verify" function
  #  log('Running Verify Function')
  #  site_control.StorageFunctionRun(storage_id, "Verify") # Sets state internally
  #
  #
  ## If this storage is Verified
  #if storage['status'] == site_control.STORAGE_STATUS__VERIFIED:
  #  # Activate!
  #  
  #  # If we have an Activate function, run it.  If not, no problem.
  #  site_control.StorageFunctionRun(storage_id, "Activate") # Fire and forget
  #  
  #  
  #  #TODO(g): Anything here?  Any more state to save or anything?  The final
  #  #   stack's handler's device should be written into the slot?  We know
  #  #   this anyway, since we generate it, so it will be formatted.  Nothing
  #  #   to do here I think.  Could still copy it I guess...  Worth doing.
  #  
  #  # Active it
  #  log('Activating')
  #  site_control.SetStorageStatus(site_control.STORAGE_STATUS__ACTIVE)
  #
  #
  ## If this storage is Active
  #if storage['status'] == site_control.STORAGE_STATUS__ACTIVE:
  #  pass # Do nothing...  Monitoring is done elsewhere.
  #
  #
  ## If this storage is Repairing
  #if storage['status'] == site_control.STORAGE_STATUS__REPAIRING:
  #  # Check if the right things are happening, if they arent happening,
  #  #   start them happening, if they are happening wait, if they happened
  #  #   then set to Configured, so we will verify it
  #  #TODO(g): Later.
  #  pass#todo...
  #
  ## If this storage is Decomissioned
  #if storage['status'] == site_control.STORAGE_STATUS__DECOMMISSIONED:
  #  # Run a decommussion function, when it's ready it will clean up
  #  site_control.StorageFunctionRun(storage_id, "Decommission")
  #
  ## If this storage is Paused
  #if storage['status'] == site_control.STORAGE_STATUS__PAUSED:
  #  pass # Do nothing...  This has to be manually un-paused


def GetStorageVolumeAvailableLocalDevice():
  # Possible names
  names = ['/dev/sdf', '/dev/sdf', '/dev/sdg', '/dev/sdh', '/dev/sdj',
           '/dev/sdk', '/dev/sdl']
  
  # Go through the names, and return the first one that doesnt already exist
  for name in names:
    if not os.path.exists(name):
      return name
  
  return None


def StorageVolumeCloudProvision(volume_id):
  """Sets up everything for the Cloud provision call, and requests it.
  
  Returns the raw dict object returned from the Cloud call, or None if failed.
  """
  volume = GetStorageVolume(volume_id)
  machine = site_control.GetMachine(volume['machine'])
  
  # Create the args
  #TODO(g): EC2 is stupid.  It doesnt allow me to set MY OWN device names,
  #   I can only use theirs.  No point setting this.  I can just symlink theirs
  #   once it's created.  Which I will do.  Then the symlink can be updated
  #   as the underlaying device changes, still.  EBS's volume becomes a private
  #   storage_state entry, and the symlink becomes the actual?
  #
  #   No, this is all a bad idea.  It makes monitoring harder and stuff.  Just
  #   leave the default and accept it will change.  We're dynamic.
  #   Remove this when theres no more thoughts of and on this subject...
  #device = '/dev/ebs_%s_%s' % (volume['storage'], volume_id)
  
  # Get the next available device name (EC2 limits you)
  device = GetStorageVolumeAvailableLocalDevice()
  
  machine_data_center = site_control.GetMachineDataCenterFromSiteDataCenter(machine['site_data_center'])
  zone = machine_data_center['name']
  
  #TODO(g): Cloud wrapper later.
  rem_volume = rem_ec2.CreateVolume(volume['size_gb'], zone, machine=machine['name'], machine_device=device)
  
  # Update the storage_volume entry with this assignment data
  #NOTE(g): Important not to do this all at once, so it CreateVolume fails,
  #   we dont have this information saved yet.  Confuses things.
  volume = GetStorageVolume(volume['id'])
  volume['status'] = 3 # Assigned
  volume['zone'] = zone
  volume['volume_id'] = rem_volume['volume_id']
  volume['machine_device'] = device
  volume['machine_data_center'] = machine_data_center['id']
  site_control.UpdateData('storage_volume', volume['id'], volume)
  
  return rem_volume
