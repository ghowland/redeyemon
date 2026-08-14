#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: RPC wrapper for Site Control data

This is the wrapper for getting our data through RPC.  We also use this to
populate web_render.py template text files, so there is a standard for how to
format text template files, because all the data is available in standard
hierarchical dicts, which are created here.

This will package all our relational table data for any given high level data
(pool, machine, service, site, etc), and all corresponding data will be present
so that only 1 rpc_site_control.py request is needed to get all the data we
would need to do inspections in a script through RPC, or to format some text
for Web representation.
"""


import os


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def UpdateDictWithPrefix(container, data, prefix):
  """Updates the container dict with keys from data, with an appeneded prefix."""
  for key in data:
    container[str(prefix) + str(key)] = data[key]


def RpcGetPools(site=site_control.SITE_DEFAULT):
  """Returns all the pools, for all the sites.  Keyed on pool.name.
  
  If you care about only one, strip them out yourself.
  """
  pools = {}
  
  pool_names = site_control.GetPools(site=site)
  
  # Populate the pools dict with our own version of Pool data, which is more
  #   complete for RPC uses.
  for name in pool_names:
    pools[name] = RpcGetPool(pool_names[pool].pool_id)
  
  return pools


def RpcGetPool(pool_id, render_status=True):
  """Returns a hierarchial dict of a pool and it's sub-information."""
  # Make a new dict, as were going to modify this data
  pool = site_control.GetPool(pool_id)
  if not pool:
    log('Pool not found: %s' % pool_id)
    return None
  
  pool = dict(pool)
  
  # Get the pool's child data, and add it in underscore notation, so it is legal
  #   for python string formatting.
  
  # Site
  site = site_control.GetSite(pool['site'])
  UpdateDictWithPrefix(pool, site, 'site_')
  
  # Hardware Image
  image = site_control.GetHardwareImage(pool['hardware_image'])
  UpdateDictWithPrefix(pool, image, 'hardware_image_')
  
  # Hardware Kind
  kind = site_control.GetHardwareKind(pool['hardware_kind'])
  UpdateDictWithPrefix(pool, kind, 'hardware_kind_')
  
  # Services, add IDs as a list
  pool['services'] = site_control.GetPoolServices(pool_id)
  
  # Machines, add IDs as a list
  pool['machines'] = site_control.GetPoolMachineList(pool_id, status=None)
  
  # Get a list of our child pools, if we have any
  pool['child_pools'] = []
  sql = "SELECT * FROM pool WHERE parent_pool = %d" % pool_id
  result = Query(sql)
  for item in result:
    pool['child_pools'].append(item['id'])
  
  # Databases attached with db_set to this pool
  pool['databases'] = []
  if pool['db_set']:
    db_set_dbs = site_control.GetDatabaseSetDatabases(pool['db_set'])
    for db_id in db_set_dbs:
      pool['databases'].append(db_id)
  
  # Stores attached with storage_set to this pool
  pool['storages'] = []
  if pool['storage_set']:
    #TODO(g): Create this function when it's time to use.  Not available yet
    #   Leaving it so it will break when used, so we know to fix it.  Clever?
    storage_set_storages = site_control.GetStorageSetStorages(pool['storage_set'])
    for storage_id in storage_set_storages:
      pool['storages'].append(storage_id)
  
  # Get the site_data_center actual name
  pool['site_data_center_name'] = site_control.GetMachineDataCenterFromSiteDataCenter(pool['site_data_center'])['name']
  
  # Get all the machine statuses
  pool['machine_statuses'] = ''
  if pool['machines']:
    for machine_id in pool['machines']:
      pool['machine_statuses'] += '%s ' % site_control.WebRender_Machine_Status(machine_id)
  
  # Add the Status Image for this pool.  Used to drop icons of how this pool
  #   is doing, status-wise.
  if render_status:
    pool['status_image'] = site_control.WebRender_Pool_Status(pool_id)
  
  return pool


def RpcGetDatabase(db_id, render_status=True):
  """Returns a hierarchial dict of a database and it's sub-information."""
  # Make a new dict, as were going to modify this data
  database = site_control.GetDatabase(db_id)
  if not database:
    log('Database not found: %s' % db_id)
    return None
  database = dict(database)
  
  # Add Database Kind fields
  kind = site_control.GetDatabaseKind(database['kind'])
  UpdateDictWithPrefix(database, kind, 'kind_')
  
  # List all the DB instance ids
  database['instances'] = site_control.GetDatabaseInstances(db_id)
  database['instances_write'] = site_control.GetDatabaseInstances(db_id, write_only=True)
  database['instances_read'] = site_control.GetDatabaseInstances(db_id, read_only=True)
  
  # Add the Status Image for this database.  Used to drop icons of how this
  #   database is doing, status-wise.
  if render_status:
    database['status_image'] = site_control.WebRender_Database_Status(db_id)
  
  # Get our db_set, if present
  if database['set']:
    db_set = site_control.GetDatabaseSet(database['set'])
    UpdateDictWithPrefix(database, db_set, 'set_')
  
  return database


def RpcGetDatabaseInstance(instance_id, render_status=True):
  """Returns a hierarchial dict of a DB instance and it's sub-information."""
  # Make a new dict, as were going to modify this data
  instance = site_control.GetDatabaseInstance(instance_id)
  if not instance:
    log('Database Instance not found: %s' % instance_id)
    return None
  instance = dict(instance)
  
  # Add Database Kind Instance Kind fields
  kind = site_control.GetDatabaseKindInstanceKind(instance['kind'])
  UpdateDictWithPrefix(instance, kind, 'kind_')
  
  # Add Database Instance Status
  status = site_control.GetDatabaseInstanceStatus(instance['status'])
  UpdateDictWithPrefix(instance, status, 'status_')
  
  # Add Database
  database = site_control.GetDatabase(instance['db'])
  UpdateDictWithPrefix(instance, database, 'db_')
  
  # Add Machine
  if instance['machine']:
    machine = site_control.GetMachine(instance['machine'])
    UpdateDictWithPrefix(instance, machine, 'machine_')
  else:
    instance['machine_name'] = ''
  
  # Add Storage
  if instance['mount_storage']:
    storage = site_control.GetStorage(instance['mount_storage'])
    UpdateDictWithPrefix(instance, storage, 'mount_storage_')
  else:
    instance['mount_storage_name'] = ''
  
  # Add the Status Image for this instance.  Used to drop icons of how this
  #   instance is doing, status-wise.
  if render_status:
    instance['status_image'] = site_control.WebRender_DatabaseInstance_Status(instance_id)
  
  return instance


def RpcGetService(service_id, render_status=True):
  """Returns a hierarchial dict of a database and it's sub-information."""
  # Make a new dict, as were going to modify this data
  service = site_control.GetService(service_id)
  if not service:
    log('Service not found: %s' % service_id)
    return None
  service = dict(service)
  
  # Add Config
  service['service_config'] = site_control.GetServiceConfig(service_id)
  UpdateDictWithPrefix(service, service['service_config'], 'config_')
  
  # Add State
  service['service_state'] = site_control.GetServiceStateAll(service_id)
  UpdateDictWithPrefix(service, service['service_state'], 'state_')
  
  # Add Scripts
  service['scripts'] = site_control.GetServiceScripts(service_id)
  
  # Add Pools
  service['pools'] = site_control.GetServicePools(service_id)
  
  # Add Machines
  service['machines'] = site_control.GetServiceMachines(service_id)
  
  
  # Add the Status Image for this service.  Used to drop icons of how this
  #   service is doing, status-wise.
  if render_status:
    service['status_image'] = site_control.WebRender_Service_Status(service_id)
  
  return service


def RpcGetMachine(machine_id, render_status=True):
  """Returns a hierarchial dict of a database and it's sub-information."""
  # Make a new dict, as were going to modify this data
  machine = site_control.GetMachine(machine_id)
  if not machine:
    log('Machine not found: %s' % machine_id)
    return None
  machine = dict(machine)
  
  # Get list of pools this machine is in
  machine['pools'] = site_control.GetMachinePools(machine_id)
  
  # If we have a pool, add all out data for it
  if machine['pools']:
    # Save our actual (parent) pool_id
    machine['pool'] = machine['pools'][0]
    
    # Get it and format it's data
    if machine['pool']:
      pool = site_control.GetPool(machine['pool'])
      UpdateDictWithPrefix(machine, pool, 'pool_')
  
  # Else, we dont know what pool we are in, so say so
  else:
    log('This machine does not have any pools: %s' % machine_id, logging.CRITICAL)
    machine['pool'] = None
  
  # Site
  site = site_control.GetSite(machine['site'])
  UpdateDictWithPrefix(machine, site, 'site_')
  
  # Get the site_data_center actual name
  machine['site_data_center_name'] = site_control.GetMachineDataCenterFromSiteDataCenter(machine['site_data_center'])['name']
  
  # Add Database Kind Instance Kind fields
  kind = site_control.GetHardwareKind(machine['hardware_kind'])
  UpdateDictWithPrefix(machine, kind, 'hardware_kind_')
  
  # Add Database Kind Instance Image fields
  image = site_control.GetHardwareImage(machine['hardware_image'])
  UpdateDictWithPrefix(machine, image, 'hardware_image_')
  
  # Add Service list of ids
  machine['services'] = site_control.GetMachineServices(machine_id)
  
  # Add the Status Image for this machine.  Used to drop icons of how this
  #   machine is doing, status-wise.
  if render_status:
    machine['status_image'] = site_control.WebRender_Machine_Status(machine_id)
  
  return machine


def RpcGetStorage(storage_id, render_status=True):
  """Returns a hierarchial dict of a storage and it's sub-information."""
  # Make a new dict, as were going to modify this data
  storage = site_control.GetStorage(storage_id)
  if not storage:
    log('Storage not found: %s' % storage_id)
    return None
  storage = dict(storage)
  
  # Add Status
  status = site_control.GetStorageStatus(storage['status'])
  UpdateDictWithPrefix(storage, status, 'status_')
  
  # Add the Status Image for this storage.  Used to drop icons of how this
  #   storage is doing, status-wise.
  if render_status:
    storage['status_image'] = site_control.WebRender_Storage_Status(storage_id)
  
  # Add Machine
  if storage['mount_machine']:
    machine = site_control.GetMachine(storage['mount_machine'])
    UpdateDictWithPrefix(storage, machine, 'mount_machine_')
  else:
    storage['mount_machine_name'] = ''
  
  # Add Handler Stack
  handler_stack = site_control.GetStorageHandlerStack(storage['handler_stack'])
  UpdateDictWithPrefix(storage, handler_stack, 'handler_stack_')
  
  # Get the handler stack name
  storage['handler_stack_name'] = site_control.GetStorageHandlerStackName(storage['handler_stack'])
  
  #TODO(g): Implement later.  Storage sets arent needed immediately, do this
  #   for Monitoring pool once all the database stuff works.
  ## Get our db_set, if present
  #if storage['set']:
  #  db_set = site_control.GetStorageSet(storage['set'])
  #  UpdateDictWithPrefix(storage, db_set, 'set_')
  
  return storage


def RpcGetStorageVolume(volume_id, render_status=True):
  """Returns a hierarchial dict of a volume and it's sub-information."""
  # Make a new dict, as were going to modify this data
  volume = site_control.GetStorageVolume(volume_id)
  if not volume:
    log('Storage Volume not found: %s' % volume_id)
    return None
  volume = dict(volume)
  
  # Add Status
  status = site_control.GetStorageVolumeStatus(volume['status'])
  UpdateDictWithPrefix(volume, status, 'status_')
  
  # Add Machine
  if volume['machine']:
    machine = site_control.GetMachine(volume['machine'])
    UpdateDictWithPrefix(volume, machine, 'machine_')
  else:
    machine['machine_name'] = ''
  
  # Add Storage
  if volume['storage']:
    storage = site_control.GetStorage(volume['storage'])
    UpdateDictWithPrefix(volume, storage, 'storage_')
  else:
    log('Volume Storage is missing: Volume: %s  Storage: %s' % \
        (volume_id, volume['storage']), logging.CRITICAL)
    machine['storage_name'] = ''
  
  
  # Add the Status Image for this storage.  Used to drop icons of how this
  #   storage is doing, status-wise.
  if render_status:
    volume['status_image'] = site_control.WebRender_StorageVolume_Status(volume_id)
  
  return volume


def RpcGetStorageHandler(handler_id, render_status=True):
  """Returns a hierarchial dict of a handler and it's sub-information."""
  # Make a new dict, as were going to modify this data
  handler = site_control.GetStorageHandler(handler_id)
  if not handler:
    log('Storage Handler not found: %s' % handler_id)
    return None
  handler = dict(handler)
  
  # Add Config Script
  if handler['script_config']:
    script = site_control.GetScript(handler['script_config'])
    UpdateDictWithPrefix(handler_stack, script, 'script_config_')
  else:
    handler['script_config_name'] = ''
  
  # Add Verify Script
  if handler['script_verify']:
    script = site_control.GetScript(handler['script_verify'])
    UpdateDictWithPrefix(handler_stack, script, 'script_verify_')
  else:
    handler['script_verify_name'] = ''
  
  # Add Monitor Script
  if handler['script_monitor']:
    script = site_control.GetScript(handler['script_monitor'])
    UpdateDictWithPrefix(handler_stack, script, 'script_monitor_')
  else:
    handler['script_monitor_name'] = ''
  
  # Add Repair Script
  if handler['script_repair']:
    script = site_control.GetScript(handler['script_repair'])
    UpdateDictWithPrefix(handler_stack, script, 'script_repair_')
  else:
    handler['script_repair_name'] = ''
  
  # Add Decommission Script
  if handler['script_decommission']:
    script = site_control.GetScript(handler['script_decommission'])
    UpdateDictWithPrefix(handler_stack, script, 'script_decommission_')
  else:
    handler['script_decommission_name'] = ''
  
  return handler


def RpcGetStorageHandlerStack(handler_stack_id, render_status=True):
  """Returns a hierarchial dict of a handler_stack and it's sub-information."""
  # Make a new dict, as were going to modify this data
  handler_stack = site_control.GetStorageHandlerStack(handler_stack_id)
  if not handler_stack:
    log('Storage Handler Stack not found: %s' % handler_stack_id)
    return None
  handler_stack = dict(handler_stack)
  
  # Add the Storage Handler data
  handler = site_control.GetStorageHandler(handler_stack['storage_handler'])
  UpdateDictWithPrefix(handler_stack, handler, 'storage_handler_')
  
  # Give ourselves a name
  handler_stack['name'] = handler_stack['storage_handler_name']
  
  # Add Config Info Script
  if handler_stack['script_config_info']:
    script = site_control.GetScript(handler_stack['script_config_info'])
    UpdateDictWithPrefix(handler_stack, script, 'script_config_info_')
  else:
    handler_stack['script_config_info_name'] = ''
  
  # If we have a stack parent, get them
  if handler_stack['stack_parent']:
    stack_parent = RpcGetStorageHandlerStack(handler_stack['stack_parent'])
    UpdateDictWithPrefix(handler_stack, stack_parent, 'stack_parent_')
  else:
    handler_stack['stack_parent_name'] = ''
  
  # Add all the Storages that use this Handler Stack
  handler_stack['storages'] = site_control.GetStorageHandlerStackStorages(handler_stack_id)
  
  return handler_stack


def RpcGetDatabaseSet(db_set_id, render_status=True):
  """Returns a hierarchial dict of a db_set and it's sub-information."""
  # Make a new dict, as were going to modify this data
  db_set = site_control.GetDatabaseSet(db_set_id)
  if not db_set:
    log('Database Set not found: %s' % db_set_id)
    return None
  db_set = dict(db_set)
  
  # Add databases: list of ids
  db_set['databases'] = site_control.GetDatabaseSetDatabases(db_set_id).keys()
  
  # Add pools: list of ids
  db_set['pools'] = site_control.GetDatabaseSetPools(db_set_id).keys()
  
  return db_set

