#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Pool
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def GetPoolByName(name, site=site_control.SITE_DEFAULT):
  # If they are passing in a pool_id, warn them
  if type(name) == int:
    msg = 'Incorrect argument.  You want GetPoolById()'
    log(msg, logging.ERROR)
    raise Exception(msg)

  return GetPools(site=site)[name] #TODO(g): Optimization point.


def GetPool(pool_id, site=site_control.SITE_DEFAULT):
  return GetPoolById(pool_id, site=site)


def GetPools(site=site_control.SITE_DEFAULT, db_set=False, storage_set=False):
  """Returns a dict of pools, keyed by their name, with their fields data as
  values.

  TODO(g): If anything was going to be cached, this might, at least for a
      few seconds at a time.  Consider in the future...

  Returns: Dict, key = str, pool name, value = dict, pool field values
  """
  sql = 'SELECT * FROM pool WHERE site = %s ORDER BY name' % site
  result = Query(sql)

  pools = {}

  for item in result:
    # If we want only db_set pools, and this isnt a db_set pool
    if db_set and item['db_set'] == None:
      continue
    # If we want only storage_set pools, and this isnt a storage_set pool
    if storage_set and item['storage_set'] != storage_set:
      continue
    
    # Save the pool
    pools[item['name']] = item

  return pools


def GetPoolById(pool_id, site=site_control.SITE_DEFAULT):
  """Returns a pool by it's name, None if not found."""
  #TODO(g): Use site
  sql = "SELECT * FROM pool WHERE id = %d" % pool_id
  result = Query(sql)

  if not result:
    return None

  else:
    return result[0]


def GetPoolProvisioningInfo(pool_id, site=site_control.SITE_DEFAULT):
  """Returns a dict with all the provisioning information needed for this pool.
  """
  info = {}

  pool = GetPoolById(pool_id)

  image_name = site_control.GetHardwareImage(pool['hardware_image'])['name']

  info = {
    'ami':image_name,
    'security_key':site_control.GetSiteConfig(site=site)['ec2_security_key'],
    'hardware_kind':pool['hardware_kind'],
    'site_data_center':pool['site_data_center'],
  }

  return info


def GetPoolLeastDesiredMachines(pool_id):
  """Find all the machines for this pool. Only if parent_pool=None.

  This is used to Decommissinon machines.  Caring about the Most Desired
  machines is less interested, but reverse if needed.

  Returns: list of ints, machine.ids
  """
  pool = GetPoolById(pool_id)

  # If this is a child pool, it cant have undesirably machines, as it has none
  if pool['parent_pool']:
    return [] # Nothing

  # Get ALL the pool machines, not just the active ones
  pool_machines = GetPoolMachineList(pool_id, status=None)

  # Build points for each machine, for good things, starting from 0
  points = {}
  for machine_id in pool_machines:
    points[machine_id] = 0

  # Machines that cannot be in the list
  restricted_machines = []
  
  # Add the Site Control Master machine, we never want to remove it
  master_machine_id = site_control.GetMasterMachineId()
  if master_machine_id != None:
    restricted_machines.append(master_machine_id)

  # Check each machine in this pool, which is the master, etc, interesting
  #   things and then add points, return sorted list
  for machine_id in pool_machines:
    # If this is the Site Config master
    machine = site_control.GetMachine(machine_id)
    if machine['ip_internal'] == rem_ec2.GetMasterIp():
      points[machine_id] += 10000
      restricted_machines.append(machine_id)

    # 20 points per DB instance: Write-Master
    sql = 'SELECT id FROM db_instance WHERE machine = %d AND kind = 1' % machine_id
    points[machine_id] += 20 * len(Query(sql))

    # 10 points per DB instance
    sql = 'SELECT id FROM db_instance WHERE machine = %d' % machine_id
    points[machine_id] += 10 * len(Query(sql))

    # 10 points per Storage Volume
    sql = 'SELECT id FROM storage_volume WHERE machine = %d' % machine_id
    points[machine_id] += 10 * len(Query(sql))

  # Build a prioritized list with the highest points up top
  machines = []

  # Get a sorted point list, list of tuples (key, value)
  sorted_point_list = sorted(points.items())
  for (machine_id, points) in sorted_point_list:
    if machine_id not in restricted_machines:
      machines.append(machine_id)

  # Reverse the list to give the worst first
  machines.reverse()

  return machines


def GetPoolMachineList(pool_id, status=5):
  """Returns an ordered list of all the machines running this service.

  status: int, default is Active
  """
  machines = []

  pool = GetPoolById(pool_id)

  if not pool:
    log('Could not find pool: %s' % pool_id, logging.CRITICAL)
    return []

  # If this pool has it's own machines
  if not pool['parent_pool']:
    sql = "SELECT * FROM pool_machine WHERE pool = %d AND provisioned = 1 ORDER BY machine" % pool_id

  # Else, this pool has another pool as a parent manage it's machines
  else:
    #log('Pool %d using parent pool %s' % (pool_id, pool['parent_pool']))
    #NOTE(g): I am in fact CREATING these entries, with scripts/config_dns.py,
    #   but we do not use them in REM internally.  They are data for the DNS
    #   names we assign to each pool machine, and I think likely other
    #   pool-machine related data can be stored there as well, but we dont
    #   count those as machines.
    sql = "SELECT * FROM pool_machine WHERE pool = %d ORDER BY machine" % pool['parent_pool']
  result = Query(sql)

  for item in result:
    machine = site_control.GetMachine(item['machine'])

    # If no status was suppled, or this machine is in the write status
    if not status or status == machine['status']:
      machines.append(item['machine'])

  #log('Machine list: Pool %d: List: %s' % (pool_id, machines))

  return machines


def GetPoolServices(pool_id):
  """Returns a list of service.ids that run in this pool."""
  services = []

  # Get services attached to this pool
  sql = "SELECT * FROM pool_service WHERE pool = %d" % pool_id
  result = Query(sql)

  # Add them to our list
  for item in result:
    service_id = item['service']
    services.append(service_id)

    # Get their requirements
    required_services = site_control.GetServiceRequiredServices(service_id)

    # Add the requirements to our list
    services += required_services

  return services


def SetPoolMachineGoalSize(pool_id, count):
  """Sets the pool.machine_goal size.  Returns Boolean of success.
  
  Reasons for failure: This pool is has db_set or storage_set as non-NULL values.
      This means the control for the machine_goal size is left the DB or
      Storage configuration scripts, respectively.
  """
  pool = GetPool(pool_id)
  
  # If this pool is controlled by a db_set or storage_set, fail
  if pool['db_set'] or pool['storage_set']:
    return False
  
  # Update the goal size
  sql = "UPDATE pool SET machine_goal = %d WHERE id = %d" % (count, pool_id)
  Query(sql)
  
  return True


def GetPoolsControlledByDatabaseSet(db_set_id):
  """Returns a list of pool.ids that are controlled by this db_set.
  
  NOTE(g): Really only one pool should be controlled by a db_set, if there is
  more than one, we will complain because it is just doubling the db_set's
  macines for no reason, and then applying different labels to them.
  """
  #NOTE(g): Order by id so the list is deterministic.
  sql = "SELECT * FROM pool WHERE db_set = %d ORDER BY id" % db_set_id
  result = Query(sql)
  
  pools = []
  
  for item in result:
    pools.append(item['id'])
  
  # If we are misconfigured and more than one pool has this db_set, critical log
  if len(pools) > 1:
    db_set = site_control.GetDatabaseSet(db_set_id)
    log('There is more than one pool set to db_set %s (%d), this is a misconfiguration and goes against the design of pools, but allowed in data: Pools: %s' % \
        (db_set['name'], db_set_id, pools), logging.CRITICAL)
  
  return pools


def GetPoolsControlledByStorageSet(storage_set_id):
  """Returns a list of pool.ids that are controlled by this storage_set.
  
  NOTE(g): Really only one pool should be controlled by a storage_set, if there is
  more than one, we will complain because it is just doubling the storage_set's
  macines for no reason, and then applying different labels to them.
  """
  #NOTE(g): Order by id so the list is deterministic.
  sql = "SELECT * FROM pool WHERE storage_set = %d ORDER BY id" % storage_set_id
  result = Query(sql)
  
  pools = []
  
  for item in result:
    pools.append(item['id'])
  
  # If we are misconfigured and more than one pool has this db_set, critical log
  if len(pools) > 1:
    storage_set = site_control.GetStorageSet(storage_set_id)
    log('There is more than one pool set to storage_set_id %s (%d), this is a misconfiguration and goes against the design of pools, but allowed in data: Pools: %s' % \
        (storage_set['name'], storage_set_id, pools), logging.CRITICAL)
  
  return pools


def GetPoolChildPools(pool_id):
  """Returns a list of pool.id for pools that use this as a parent_pool."""
  pools = []
  
  sql = "SELECT * FROM pool WHERE parent_pool = %d" % pool_id
  result = Query(sql)
  
  for item in result:
    pools.append(item['id'])
  
  return pools


def GetPoolMachineAvailableForDatabaseInstance(pool_id, instance_id):
  """Returns a dict of machine field data, or None, if no machine found.
  
  The machine returned matches the specifications for the instance_id required,
  and does not already have an instance of this instance's database on it.
  """
  pool = GetPool(pool_id)
  instance = site_control.GetDatabaseInstance(instance_id)
  
  # Get all the machines in this pool (Active only, by default)
  machines = GetPoolMachineList(pool_id)
  
  # Check each of our machines, return a match's field data
  for machine_id in machines:
    # Get the machine data to test
    machine = site_control.GetMachine(machine_id)
    
    # Prove this isnt a match (any failed test does so)
    matched = True
    
    # Get the database instances on this machine
    machine_db_instances = site_control.GetMachineDatabaseInstances(machine_id)
    for machine_db_instance_id in machine_db_instances:
      machine_db_instance = site_control.GetDatabaseInstance(machine_db_instance_id)
      
      # If thie machine instance is in the same Database as our target instance
      if machine_db_instance['db'] == instance['db']:
        matched = False # Cant put more than one instance of the same DB on a machine
    
    # If we match, no tests failed, return the machine data for assigning this
    #   instance to run on it.  Storage will be assigned to this machine, etc.
    if matched:
      return machine
    
  
  # Didnt find a matching machine.  Failed.
  return None