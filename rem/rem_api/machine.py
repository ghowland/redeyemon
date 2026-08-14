#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Machine
"""


import yaml
import time


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *

#import rem_util
#print rem_util
#print dir(rem_util)
#import rem_util.query.SanitizeSQL as SanitizeSQL
#import rem_util.query.Query as Query


# This is the local cache of the last configuration this machine had.  If this
#   file doesnt exist, this is a new machine
MACHINE_LOCAL_CACHE_YAML = '/usr/local/site_control/rem_machine_cache.yaml'



def GetMachine(machine_id):
  """Returns the field data of the machine specified."""
  if type(machine_id) != int:
    try:
      machine_id = int(machine_id)
    except TypeError, e:
      log('Invalid machine_id: %s: %s' % (machine_id, stack.Mini(4)))
      raise e

  sql = "SELECT * FROM machine WHERE id = %d" % machine_id
  result = Query(sql)

  if not result:
    log('Machine not found: %s: %s' % (machine_id, stack.Mini(5)), logging.ERROR)
    return None
  else:
    # Add the status name, it's something people want to know
    machine = dict(result[0])
    machine['status_name'] = GetMachineStatus(machine['status'])['name']
    return machine


def GetMachines(status=None, site=site_control.SITE_DEFAULT):
  """Returns a dict of sites, keyed by their name, with their field data is
  values.
  """
  # If a site is specified, even default, only get those machines
  if site != None:
    # If we wants all the machines (dont care about status)
    if status == None:
      sql = "SELECT * FROM machine WHERE site = %d ORDER BY name" % site
    
    # Else, just the machines with the specified status
    else:
      sql = "SELECT * FROM machine WHERE site = %d AND status = %d ORDER BY name" % (site, status)
  
  # Else, get all machines, regardless of site
  #NOTE(g): Typically we want to restrict machines per site, so that sites get
  #   handled in their own way, but this function is also needed for cross-site
  #   machine processors, like for monitoring.  So allow getting ALL machines.
  else:
    # If we wants all the machines (dont care about status)
    if status == None:
      sql = "SELECT * FROM machine ORDER BY name"
    
    # Else, just the machines with the specified status
    else:
      sql = "SELECT * FROM machine WHERE status = %d ORDER BY name" % status

  result = Query(sql)

  machines = {}

  for item in result:
    machines[item['id']] = item # By id

  return machines


def GetMachinesByNames(status=None, site=site_control.SITE_DEFAULT):
  """Returns a dict, keyed on machine.name, value is field data of machine."""
  machines = GetMachines(status=status, site=site)
  
  # Put the machines into a dict by their instance name
  data = {}
  for machine_id in machines:
    machine = machines[machine_id]
    data[machine['name']] = machine
  
  return data


def DeleteMachine(machine_id, reason=None):
  log('Deleting machine from site control: %s' % machine_id)
  
  # Get the machine so we can use it's data later
  machine = GetMachine(machine_id)
  
  #TODO(g): Use cascading delete, is it a good match with this schema?  Could
  #   always add the stragglers manually...
  
  
  # Delete tables with foreign key constraints on machine
  # Pool machines
  sql = "DELETE FROM pool_machine WHERE machine = %d" % machine_id
  Query(sql)
  
  # DB instances
  sql = "DELETE FROM db_instance WHERE machine = %d" % machine_id
  Query(sql)
  
  # Remove floating IP assignment, clear the machine
  sql = "UPDATE floating_ip SET machine = NULL WHERE machine = %d" % machine_id
  Query(sql)
  
  # Remove storage volume assignment, the storage persistents, its assignment
  #   is gone
  sql = "UPDATE storage_volume SET machine = NULL WHERE machine = %d" % machine_id
  Query(sql)
  
  # Remove all RRD entries, no longer important
  sql = "DELETE FROM machine_rrd WHERE machine = %d" % machine_id
  Query(sql)
  
  # Remove all machine state fields, no longer important
  sql = "DELETE FROM machine_state WHERE machine = %d" % machine_id
  Query(sql)
  

  # Foreign Key constraints are now satisfied...
  
  # Delete the machine itself
  sql = "DELETE FROM machine WHERE id = %d" % machine_id
  Query(sql)
  
  # Save this machine as a terminated machine.  We keep track of them so we
  #   can relate machine_error_log entries with them.
  #   If worked beause the machine_id has no foreign key, we know when that
  #   machine launched, and when it terminated, so logs in between that time
  #   for that number will always be correct.  Plus, numbers just go up.
  log('Terminating: %s: %s' % (machine_id, machine))
  if machine:
    if reason:
      sql = "INSERT INTO terminated_machine (machine, time_launch, time_terminate, reason, hardware_kind) VALUES " + \
            "(%d, '%s', NOW(), '%s', %d)" % \
            (machine_id, time_launch, SanitizeSQL(reason), machine['hardware_kind'])
    else:
      sql = "INSERT INTO terminated_machine (machine, time_launch, time_terminate, hardware_kind) VALUES " + \
            "(%d, '%s', NOW(), %d)" % (machine_id, machine['time_launch'], machine['hardware_kind'])
    terminated_id = Query(sql)
    log('Terminated Machine added: %s' % terminated_id)
  else:
    log('Couldnt find machine from id (%d), could not add to terminated_machine list.', logging.CRITICAL)


def RemoveMachine(machine_id):
  """Removes this machine from our DB and pools."""
  DeleteMachine(machine_id)
  
  ##TODO(g): Remove after testing.  This is much less than I think we need to do
  #log('RemoveMachine: %s' % machine_id)
  #
  #sql = "DELETE FROM pool_machine WHERE machine = %d" % machine_id
  #Query(sql)
  #
  ## Constrants make this the last to be deleted
  #sql = "DELETE FROM machine WHERE id = %d" % machine_id
  #Query(sql)

  return True


def GetMachineDNSNames(machine_id):
  """Get all the names this machine is known by, as a sorted list."""
  sql = "SELECT * FROM pool_machine WHERE machine = %d ORDER BY dns_public" % machine_id
  result = Query(sql)
  
  names = []
  
  for item in result:
    names.append(item['dns_public'])
  
  return names


def MachineInstallsRequired(site=site_control.SITE_DEFAULT):
  """Look at how many machines we need in our site to install.

  Returns: list of ints, machine.id
  """
  # Get all the machines for this site
  sql = "SELECT machine.* FROM machine, pool, pool_machine WHERE pool.site = %d AND pool_machine.pool = pool.id AND machine.id = pool_machine.machine" % site
  result = Query(sql)

  installs = []

  # If this is a machine that needs installing
  for item in result:
    if item['status'] == 2:
      installs.append(item['id'])

  return installs


def MachineVerifiesRequired(site=site_control.SITE_DEFAULT):
  """Look at how many machines we need in our site, to verify proper install
  and configuration.

  Returns: list of ints, machine.id
  """ 
  # Get all the machines for this site
  sql = "SELECT machine.* FROM machine, pool, pool_machine WHERE pool.site = %d AND pool_machine.pool = pool.id AND machine.id = pool_machine.machine" % site
  result = Query(sql)

  installs = []

  # If this is a machine that needs verifying
  for item in result:
    if item['status'] == 4:
      installs.append(item['id'])

  return installs


def MachineDecommissionRequired(site=site_control.SITE_DEFAULT):
  """Look at how many machines we need in our site.

  Returns: list of ints, machine.id
  """
  # Get all the machines for this site
  sql = "SELECT machine.* FROM machine, pool, pool_machine WHERE pool.site = %d AND pool_machine.pool = pool.id AND machine.id = pool_machine.machine" % site
  result = Query(sql)

  installs = []

  # If this is a machine that needs decommissioning
  for item in result:
    if item['status'] == 7:
      installs.append(item['id'])

  return installs


def GetMachineByName(name, depth=0):
  """Returns the machine with this name, or None."""
  #log('Starting: %s  (Depth=%s)' % (name, depth))

  # If we've been given a bad name, report our caller
  if name == None:
    log('Machine Name passed is invalid: None.  %s' % stack.Mini(4))
    return None

  # Limit retries, fail with None if over the limit.
  MAX_DEPTH = 2
  if depth >= MAX_DEPTH:
    log('Max depth exceeded: %s' % depth)
    return None

  # Get the machines name
  sql = "SELECT * FROM machine WHERE name = '%s'" % SanitizeSQL(name)
  try:
  #if 1:
    #log('Query: %s' % sql)
    result = Query(sql)

  #TODO(g): Try letting this Exception bubble up, see if that works better...

  # The Site Master database is unavailable, so start the master election process
  except query.SiteMasterUnavailable, e:
    log('Site Master: Unavailable', logging.CRITICAL)
    raise e
  
  #TODO(g): This is one of the places we will see a failure of being able to
  #   find the master server.  If this fails, call. IsSiteControlAvailable to
  #   ensure the site is really up and take measures if not.
  except Exception, e:
    log('Failed, will check Site Control availability: %s' % e[0], logging.INFO)
    # This is an issue that may be caused by the site being down, check...
    site_control.IsSiteControlAvailable()

    # Try again.  We block recursive looping with depth
    log('Try to get our name again, recurse.')
    return GetMachineByName(name, depth=depth+1)

  # If we didnt find a machine, Site Control doesnt know about it
  if not result:
    log('Machine not found: %s' % name)
    return None # This machine is off the grid.

  machine = result[0]
  
  #log('Found machine: %s (%s)' % (machine['name'], machine['id']))#Useful in early stage startup debugging, but too noisy!
  return machine


def GetThisMachineId():
  """Returns the machine.id for this machine.  Returns None if not found."""
  #TODO(g): This causes a loop, calling IsSiteControlAvailable, whic tries
  #   to get the machine configuration.  This function is called too frequently
  #   to perform this task, so it'll have to be tested in a different way.
  if 0:
    # Ensure we have Site Control access.  This is a primary command, so must
    #   always be available
    if not site_control.IsSiteControlAvailable():
      raise Exception('REM: Site Control not available, cant determine machine_id')

  # Get the EC2 machine instance name
  ec2_name = rem_ec2.GetMachineName()

  # Get the machine, by it's name
  machine = GetMachineByName(ec2_name)

  if not machine:
    log('Machine not found: %s' % ec2_name)
    return None
  else:
    return machine['id']


def SetMachineState(machine_id, state_name, value):
  """Sets a machine state value.  Creates it if doesnt exist."""
  sql = "SELECT * FROM machine_state WHERE machine = %d AND name = '%s'" % \
        (machine_id, SanitizeSQL(state_name))
  result = Query(sql)

  # If it already exists, update it
  if result:
    machine_state = result[0]

    sql = "UPDATE machine_state SET value = '%s', updated = NOW() WHERE id = %d" %\
          (SanitizeSQL(value), machine_state['id'])
    Query(sql)
    
    log('Updated Machine State: %s: %s = %s' % (machine_id, state_name, value))

  # Else, its new, create it
  else:
    sql = "INSERT INTO machine_state (machine, name, value, updated) VALUES (%d, '%s', '%s', NOW())" % \
          (machine_id, SanitizeSQL(state_name), SanitizeSQL(value))
    Query(sql)
    
    log('Created Machine State: %s: %s = %s' % (machine_id, state_name, value))


def GetMachineState(machine_id, state_name):
  """Returns the machine state.  None if it doesnt exist or is NULL."""
  sql = "SELECT * FROM machine_state WHERE machine = %d AND name = '%s'" % \
        (machine_id, SanitizeSQL(state_name))
  result = Query(sql)

  if not result:
    return None
  else:
    return result[0]['value']


def LoadMachineConfigurationLocalCache():
  """Loads the locally cached YAML file for our Configuration data.

  Returns: dict if successful, None if failed
  """
  # Read the YAML file for this config
  try:
    config_data = yaml.load(open(MACHINE_LOCAL_CACHE_YAML, 'rb').read())
  except IOError, e:
    config_data = None

  return config_data


def GetMachinePoolPrimary(machine_id):
  """Returns dict, field data of specified machine's primary pool (or None)."""
  # Get the pool this machine is in, so we can get all it's services
  sql = "SELECT * FROM pool_machine WHERE machine = %d AND provisioned = 1" % machine_id
  result = Query(sql)
  if not result:
    return None
  else:
    pool = site_control.GetPool(result[0]['pool'])
    return pool


def GetMachinePools(machine_id):
  """Returns a list of pool.ids that run on this machine.
  
  The parent pool is always listed first.  Any pools after the first are child
  pools of the first pool.
  """
  pools = []

  # Get the pool this machine is in, so we can get all it's services
  sql = "SELECT * FROM pool_machine WHERE machine = %d AND provisioned = 1" % machine_id
  result = Query(sql)
  if not result:
    return []

  # Else, we got a result, so use it
  else:
    pool_id = Query(sql)[0]['pool']
    pools.append(pool_id)

  # Get all the pools that call this pool parent (slave-pools)
  sql = "SELECT * FROM pool WHERE parent_pool = %d" % pool_id
  result = Query(sql)

  # Get all the pools that use this pool to manage their machines
  for item in result:
    pools.append(item['id'])

  return pools


def GetMachineRrds(machine_id):
  """Returns a list of ints, rrd.id.  Dupes of rrd.ids are not allowed."""
  #TODO: ...  Get all the rrds, and scripts we're going to run to collect
  #   rrd info, and fields, so we have the order of output.  Should be
  #   text parsable output, as its going directly into an RRD Update command
  #   line call, and will be done in field order.  YAY!
  #
  #   This is used for both the RPC local collector, and the Mon rrd collector
  #   which knows which machines to connect to, because they have rrds to
  #   collect data on.   Perfect circle!  Same code/data.

  # Get all the RRDs that SHOULD be on the machine (by services)
  machine_services = GetMachineServices(machine_id)

  # Get all the RRDs for these services
  machine_services_rrds = site_control.GetRrdsByServiceList(machine_services)

  # Get all the RRDs that are on the machine
  sql = "SELECT * FROM machine_rrd WHERE machine = %d" % machine_id
  result = Query(sql)
  machine_rrds = []
  for item in result:
    machine_rrds.append(item['rrd'])

  # Compare machine_services_rrd against machine_rrds (goal vs actual)
  #TODO(g): Later will find RRDs we dont need and delete them.  (Manual override flag?)
  missing_rrds = []
  for rrd_id in machine_services_rrds:
    if rrd_id not in machine_rrds:
      missing_rrds.append(rrd_id)

  # If we are missing any RRDs, create them, and run this call again, and return
  #   those results
  if missing_rrds:
    # Add missing RRDs
    for rrd_id in missing_rrds:
      #TODO(g): Mark service later.  We always know it, we always need it, mark
      #   it.  If multiple services use it, just mark the first?
      #NOTE(g): Path will be filled in by the Mon: RRD collector
      log('GetMachineRrds %d: Adding missing RRD: %s' % (machine_id, rrd_id))
      sql = "INSERT INTO machine_rrd (machine, rrd) VALUES (%d, %d)" % (machine_id, rrd_id)
      Query(sql)

    # Call this functoin again, now that we added them, and let it return
    #   properly.  Shouldnt recurse out of control, as it will only do it when
    #   we are legitimately missing RRDs.  Could recurse if we dont add them
    #   properly, but not worrying about that.
    return GetMachineRrds(machine_id)

  return machine_rrds


def GetMachineServiceScripts(machine_id):
  """Returns a dict of all the scripts that run for this machine.

  Returns: dict, key=script.id, value=list of ints, service_script.id
  """
  scripts = {}

  machine = GetMachine(machine_id)

  services = GetMachineServices(machine_id)

  #log('GetMachineServiceScripts %s: services: %s' % (machine_id, services))

  for service_id in services:
    service_scripts = site_control.GetServiceScripts(service_id)

    # Add all the scripts
    for script_id in service_scripts:
      # Get our list of service_script instances for this script
      service_script_ids = service_scripts[script_id]

      # Loop over each service script for this item, they have their own
      #   schedules
      for service_script_id in service_script_ids:
        # Get the service_script field data
        service_script = site_control.GetServiceScript(service_script_id)

        # If this script runs on any machine status, or on this machine's current
        if service_script['run_on_machine_status'] in (None, machine['status']):
          # Create the list if this script doesnt already have the script_id
          if script_id not in scripts:
            scripts[script_id] = []

          # Now append all their services script instances
          scripts[script_id] += service_scripts[script_id]

  return scripts


def GetMachineServices(machine_id):
  """Returns a list of service.ids that run on this machine."""
  services = []

  # Get the pool this machine is in, so we can get all it's services
  sql = "SELECT * FROM pool_machine WHERE machine = %d" % machine_id
  result = Query(sql)
  if not result:
    return services#[]

  # Else, we got a result, so use it
  else:
    pool_id = result[0]['pool']

  # Get the services for this pool
  pool_services = site_control.GetPoolServices(pool_id)
  services += pool_services

  # Get all the pools that call this pool parent (slave-pools)
  sql = "SELECT * FROM pool WHERE parent_pool = %d" % pool_id
  result = Query(sql)

  # Get all the pools that use this pool to manage their machines
  for item in result:
    # Get all the services for these child-pools and add them
    child_services = site_control.GetPoolServices(item['id'])
    services += child_services

  return services


def GetMachineSite(machine_id):
  """Returns the site.id for the machine.id"""
  machine = GetMachine(machine_id)

  return machine['site']


def GetMachineStatus(status):
  """Returns the machine_status field data for this status.  None is not found."""
  sql = "SELECT * FROM machine_status WHERE id = %d" % status
  result = Query(sql)
  
  if result:
    return result[0]
  else:
    return None


def GetMachineStatusName(status):
  """Returns textual name of a machine status code."""
  sql = "SELECT * FROM machine_status WHERE id = %d" % status
  result = Query(sql)

  return result[0]['name']


def MachineReinstall(machine_id):
  """When monitoring detects a machine is not working, the first step to
  dealing with the problem is to re-install and configure everything.

  Next step is to decommission it, and let a new instance try again, fresh Image.
  """
  log('MachineReinstall: %s' % machine_id)
  # Send this machine back to the "Allocated" status, so it will be reinstalled
  UpdateData('machine', machine_id, {'status':2})


def LogMachineError(machine_id, text):
  """Logs a machine error into our DB, so we can know about all our errors."""
  log('LogMachineError: %s: %s' % (machine_id, text))

  sql = "INSERT INTO log_machine_error (machine, value, occurred) VALUES (%d, '%s', NOW())" % \
        (machine_id, SanitizeSQL(text))
  Query(sql)


def SaveMachineConfigurationLocalCache(config_data):
  """Saves the locally cached YAML file for our Configuration data."""
  log('Saving Config Data: %s' % MACHINE_LOCAL_CACHE_YAML)
  # Write the YAML file for this config
  open(MACHINE_LOCAL_CACHE_YAML, 'wb').write(yaml.dump(config_data))


def SetMachineStatus(machine_id, status):
  """Sets a machine's status."""
  if site_control.GetMasterMachineId() == machine_id and status == 7:
    log('Will not set the Site Control Master machine to Decomissioned: %s' % stack.Mini(5))
    return
  
  machine = GetMachine(machine_id)
  data = dict(machine)
  data['status'] = status
  site_control.UpdateData('machine', machine_id, data)


LAST_TIME_RECONFIGURED = 0
def ConfigureLocalMachine(site_config=None):
  """Reconfigures this local machine, updating latest Site Control data.

  This is the first thing that happens when a REM Client starts up, and
  will happen periodically (site_config->run_delay_machine_reconfigure) and
  when site-wide changes are made all machinse will be alerted with RPC.

  The site_config is for reducing work, if we have it to pass in.  No need
  to keep requesting it.
  """
  log('Starting')
  global LAST_TIME_RECONFIGURED

  machine_id = GetThisMachineId()

  # If we dont already have our site_config info, get it
  if not site_config:
    site_config = site_control.GetSiteConfig(GetMachineSite(machine_id))

  # Get our delay time between reconfigs to protect against DoS
  dos_protect_time = int(site_config['run_delay_machine_reconfigure'])

  # Stop any flood that might occur on reconfiguring this machine by
  #   having a buffer time between reconfigs
  if LAST_TIME_RECONFIGURED + dos_protect_time > time.time():
    log('ConfigureLocalMachine: DoS protect.  Not reconfiguring.')
    return

  # Store latest invocation time
  LAST_TIME_RECONFIGURED = time.time()

  # Get all the services on this machine
  services = GetMachineServices(machine_id)

  # For each service, run the config_script
  for service_id in services:
    # Get the configuration script for this service
    service = site_control.GetService(service_id)

    # If we have a config script for this service
    if service['script_config']:
      # Run this script, block on each script, as they may try to modify common
      #   system files
      run_script.RunScript(service['script_config'])

  log('Finished')


def AddNewMachine_ThisOne(site=site_control.SITE_DEFAULT):
  """Add's the current machine to Site Control.  Returns new machine_id.

  Returns: int, new machine_id
  """
  # Get the machine information from EC2
  instance = rem_ec2.GetMachineInstance()

  if instance == None:
    log('Could not get this machines instance.  Likely EC2 failure.')
    return None

  # Get the site data center for this machine
  site_data_center = site_control.GetSiteDataCenterFromRawDataCenterName(instance['data_center'])

  # Get the Hardware Image id
  hardware_image_id = site_control.GetHardwareImageByName(instance['ami'])['id']

  # Create a machine's data set
  machine = {
    'name':instance['name'],
    'site':site,
    'site_data_center':site_data_center,
    'hardware_kind':1, #TODO(g): How do I change this with EC2 provisioning?  I dont see an option.  Look up in docs.
    'hardware_image':hardware_image_id,
    'dns_public':instance['dns_external'],
    'dns_private':instance['dns_internal'],
    'ip_internal':instance['ip_internal'],
    'ip_external':instance['ip_external'],
    }

  # Add this machine, and return it's machine.id
  machine_id = _AddNewMachine(machine, site=site)

  return machine_id


def AddNewMachineToPool(pool_id, machine, site=site_control.SITE_DEFAULT):
  """Add this machine to the pool.

  Returns: int, pool_machine.id, or None in case of this pool already being full
  """
  # Recalculate the pool size to ensure we have the latest numbers
  site_control.RecalculatePoolSize(pool_id, site=site)
  
  # Get the pool data, includes sizing info
  pool = site_control.GetPool(pool_id, site=site)

  # Ensure this pool doesnt already have enough machines
  if pool['machine_total'] >= pool['machine_goal']:
    log('Trying to add a machine when the goal is already met.  Decomissioning: %s' % machine['name'], logging.ERROR)
    # Decommission this isntance we shouldnt have made
    rem_ec2.DecommissionInstances([machine['name']])
    return None
  
  log('Starting')
  # Create a machine entry
  machine_id = _AddNewMachine(machine, site=site)

  # Link the Machine to pool
  sql = "INSERT INTO pool_machine (pool, machine) VALUES (%s, %s)" % (pool['id'], machine_id)
  pool_machine_id = Query(sql)

  log('AddNewMachineToPool: %s' % pool_machine_id)

  # Recalculate the number of machines in this pool
  site_control.RecalculatePoolSize(pool_id, site=site)

  return pool_machine_id


def _AddNewMachine(machine, site=site_control.SITE_DEFAULT):
  """Adds this machine data to our Site Control DB.
  
  Dont call this directly, it should be called by AddNewMachineToPool()
  """
  log('Starting: %s' % machine)

  # Copy machine, so we can add fields without modifying the original
  data = dict(machine)
  data['site'] = site

  # Convert the hardware_image.name to .id
  data['hardware_image'] = site_control.GetHardwareImage(data['hardware_image'])['id']

  # If this machine data has DNS and IP information, save it
  #NOTE(g): Use dns_private because public is unavailable when it has a
  #   Floating IP on EC2.  dns_private should always be available.
  if data['dns_private'] and 'ip_internal' in data and data['ip_internal']:
    #NOTE(g): This machine is status=Allocated, because we have it's DNS and IPs
    sql = "INSERT INTO machine (name, site, site_data_center, hardware_kind, hardware_image, status, dns_public, dns_private, ip_internal, ip_external, time_launch) VALUES " +\
          "('%(name)s', %(site)s, %(site_data_center)s, %(hardware_kind)s, %(hardware_image)s, 2, '%(dns_public)s', '%(dns_private)s', '%(ip_internal)s', '%(ip_external)s', NOW())" % data

  # Else, If this machine data has DNS information, save it
  elif data['dns_private']:
    sql = "INSERT INTO machine (name, site, site_data_center, hardware_kind, hardware_image, status, dns_public, dns_private, time_launch) VALUES " +\
          "('%(name)s', %(site)s, %(site_data_center)s, %(hardware_kind)s, %(hardware_image)s, 1, '%(dns_public)s', '%(dns_private)s', NOW())" % data

  # Else, save without any DNS information yet (typical)
  else:
    sql = "INSERT INTO machine (name, site, site_data_center, hardware_kind, hardware_image, status, time_launch) VALUES " +\
          "('%(name)s', %(site)s, %(site_data_center)s, %(hardware_kind)s, %(hardware_image)s, 1, NOW())" % data

  machine_id = Query(sql)
  log('Added: %s' % machine_id)

  return machine_id






def ProvisionSingleMachine(pool_id):
  """Provision a single machine, do all the follow up work involved adding to SC
  
  NOTE(g): Provisioning a single machine is not very efficient in a number of
      ways.  Fix this later.  Right now it is simplifying this process, and
      thats more important than treating EC2 right or doing it as rapidly
      as possible (sequential EC2 calls are SLOW).
  """
  #TODO(g): Unhardcode this once we change how handleprovisioning works.
  REQUESTED_COUNT = 1
  
  # Get the pool
  pool = site_control.GetPool(pool_id)
  
  # Get the zone from our site_data_center info
  zone = site_control.GetMachineDataCenterFromSiteDataCenter(pool['site_data_center'])['name']
  
  # Get the instance_type from our hardware_kind
  instance_type = site_control.GetHardwareKind(pool['hardware_kind'])['name']
  
  hardware_image = site_control.GetHardwareImage(pool['hardware_image'])
  ami = hardware_image['name']
  security_key = hardware_image['keypair']
  
  # Provision the machines
  log('Provision for pool %s: %s machines: Zone=%s: Type=%s' % (pool['name'], REQUESTED_COUNT, zone, instance_type))
  new_machines = rem_ec2.ProvisionMachineInstances(ami, security_key, REQUESTED_COUNT,
                                           zone, instance_type)
  
  # If we didnt get any, but we were supposed to
  if not new_machines:
    log('No new machines created for pool %s.  Should be %s machines.' % \
        (pool_name, count), logging.ERROR)
    return None
  
  # Else, we got our machine data, return it
  else:
    # Save the machine data
    machine = new_machines[0]
    
    # Set the site
    machine['site'] = pool['site']
    
    # Replace zone with site_data_center
    machine['site_data_center'] = site_control.GetSiteDataCenterByName(machine['zone'])['id']
    
    # Add the hardware_kind
    machine['hardware_kind'] = pool['hardware_kind']
    
    # Add this new machine to our Pool
    log('Adding new DB machine to pool: %s: %s' % (pool['name'], machine['name']))
    new_machine_id = site_control.AddNewMachineToPool(pool_id, machine, site=pool['site'])
    
    # Get the final version of machine to return, with our id field and defaults
    final_machine = GetMachine(new_machine_id)
    
    return final_machine



def GetMachineDatabaseInstances(machine_id):
  """Returns a list of ints, db_instance.ids, assigned to this machine."""
  instances = []
  
  sql = "SELECT * FROM db_instance WHERE machine = %d" % machine_id
  result = Query(sql)
  
  for item in result:
    instances.append(item['id'])
  
  return instances



def GetMachineStorages(machine_id):
  """"""
  #TODO(g):...
  pass#...


def GetMachineStorageVolumes(machine_id):
  """"""
  #TODO(g):...
  pass#...



def GetMachineDatabaseInstancesWhoseStorageIsntConfigured(machine_id):
  """Get all the database instances on this machine who dont yet have storage
  configured.
  
  Returns: dict, key=int, database_instance.id, value=dict, table field data
  """
  instances = {}
  
  sql = "SELECT * FROM db_instance WHERE machine = %d" % machine_id
  result = Query(sql)
  
  for item in result:
    instances[item['id']] = item
  
  return instances

