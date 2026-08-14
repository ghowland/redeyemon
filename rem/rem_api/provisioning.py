#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Provisioning
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def ProvisioningRequired(site=site_control.SITE_DEFAULT):
  """Returns how many machines, per pool, are required for provisioning now.

  Returns: Dict, key = str, pool name, value = int, count of required machines
  """
  pools = site_control.GetPools()

  required = {}

  for pool_name in pools:
    pool = pools[pool_name]
    
    RecalculatePoolSize(pool['id'], site=site)
    count = ProvisioningRequired_ByPool(pool['id'], site=site)

    if count:
      required[pool_name] = count

  return required


def ProvisioningRequired_ByPool(pool_id, site=site_control.SITE_DEFAULT):
  """Returns the number of machines this pool requires to be at goal levels.

  Returns: int, count of required machines
  """
  pool = site_control.GetPool(pool_id, site=site)

  # Clean up non-Provisioned Pool Machines if this pool has them and is not
  #   a parent_pool rider pool
  if not pool['parent_pool']:
    # Delete any non-Provisioned machines, we provision our own machines.
    #TODO(g): This is going to happen ALL THE TIME for no reason, its only to
    #   catch the SINGLE case of something flipping a machine from parent_pool
    #   to not, and then what happens with these informational phantom
    #   pool_machine entries?  So we have to protect against that.  I do it
    #   everywhere I touch them, like in GetPoolMachineList(), etc.  I think
    #   this challenge of keeping this problem from occurring is worth the
    #   great data placement in the tables, where Pool-Machine related data
    #   can be stored.  DNS is just the start most likely.
    sql = "DELETE FROM pool_machine WHERE pool = %d AND provisioned = 0" % pool['id']
    Query(sql)

  # If this pool has a parent, then it doesnt get a say, return 0
  if pool['parent_pool']:
    return 0

  # If goal is not set, they arent getting any machines
  if pool['machine_goal'] == None:
    return 0

  # If there is no total, then they need all their machines (we know goal!=NULL)
  if pool['machine_total'] == None:
    return pool['machine_goal']

  # If the total is not the same as the goal, then return the difference
  #NOTE(g): All updating of this is left to the control scripts, so that this
  #   remains a simple process, and the decisions behind it can be as complex
  #   as you like.
  if pool['machine_total'] != pool['machine_goal']:
    return pool['machine_goal'] - pool['machine_total']


def ProvisionMachines(site=site_control.SITE_DEFAULT):
  log('ProvisionMachines')

  # Get provisioning requirements
  provisioning = ProvisioningRequired()

  # Provision enough machines for the required pools, in our sites
  for pool_name in provisioning:
    count = provisioning[pool_name]
    
    # Get pool info
    pool = site_control.GetPoolByName(pool_name, site=site)
    
    # Get pool provisioning information
    info = site_control.GetPoolProvisioningInfo(pool['id'])
    
    # If we need a positive number: Get our new machines
    if count > 0:
      # Get the zone from our site_data_center info
      zone = site_control.GetMachineDataCenterFromSiteDataCenter(info['site_data_center'])['name']
      
      # Get the instance_type from our hardware_kind
      instance_type = site_control.GetHardwareKind(info['hardware_kind'])['name']
      
      # Provision the machines
      log('Provision for pool %s: %s machines: Zone=%s: Type=%s' % (pool_name, count, zone, instance_type))
      new_machines = rem_ec2.ProvisionMachineInstances(info['ami'], info['security_key'],
                                               count, zone, instance_type)
      
      # If we didnt get any, but we were supposed to
      if not new_machines:
        log('No new machines created for pool %s.  Should be %s machines.' % \
            (pool_name, count), logging.ERROR)
      
      # Add all of our machines
      for machine_name in new_machines:
        machine = new_machines[machine_name]
        
        # Set the site
        machine['site'] = site
        
        # Replace zone with site_data_center
        machine['site_data_center'] = site_control.GetSiteDataCenterByName(machine['zone'])['id']
        
        # Add the hardware_kind
        machine['hardware_kind'] = info['hardware_kind']
        
        log('Adding new machine to pool: %s: %s' % (pool_name, machine_name))
        site_control.AddNewMachineToPool(pool['id'], machine)
    
    # Else, if this is a negative number, get rid of our least desired machines
    elif count < 0:
      # Get number of machines to decomm
      decomm_count = abs(count)
      log('Decommision for pool %s: %s machines' % (pool_name, decomm_count))
      
      # Get the number of currently decommissioned machines in this pool
      currently_decommissioned_machines = site_control.GetPoolMachineList(pool['id'], status=7)
      
      # Subtract the current number of machines in decomm state from the number
      #   remaining to decomm
      decomm_count -= len(currently_decommissioned_machines)
      
      # If we no longer need to decomm machines, continue on to the next pool
      if decomm_count <= 0:
        log('Decommision for pool %s: %s machines: Already decommissioned, skipping' % \
            (pool_name, decomm_count))
        continue
      
      # Get Least desired machines.  Short words fail me.
      worst_machine_ids = GetPoolLeastDesiredMachines(pool['id'])
      
      #NOTE(g): I mark them for Decomm now, before I do it, because it's by
      #   this point decided.  If anything should fail in this attempt, or
      #   an Exception stops execution, I still want this machine out of
      #   the counted usable machines.  It will be cleaned up later if not now.
      worst_machine_names = []
      for worst_machine_id in worst_machine_ids:
        machine = site_control.GetMachine(worst_machine_id)
        worst_machine_names.append(machine['name'])
        
        # This machine has been Decommissioned!
        SetMachineStatus(worst_machine_id, 7)
      
      # Get the machines to decommission
      decomm_machines = worst_machine_names[:decomm_count]
      
      # Decommission these machines
      if decomm_machines:
        rem_ec2.DecommissionInstances(decomm_machines)


def AllocateMachines():
  """Once machines have been Provisioned(1), we still dont have their IP or other
  information.  This will collect that information and move the machines to
  an Installing(3) state."""
  log('Allocate Machines')

  # Get all our EC2 instances
  instances = rem_ec2.GetInstances()

  # If we failed to get any instances (EC2 error), return and we'll try again
  if instances == None:
    return

  # Get all our machines with status Requested(1)
  machines = site_control.GetMachines(status=1)

  # Try to get them working
  for machine_id in machines:
    machine = site_control.GetMachine(machine_id)
    
    # If we found a machine that hasnt been updated yet, and it now has
    #   information available to us
    if machine['ip_internal'] == None and machine['name'] in instances and \
        instances[machine['name']]['ip_internal']:
      # Get the EC2 instance dict
      instance = instances[machine['name']]
      log('Instance: %s' % instance['name'])
      
      # Get the IP/DNS/etc information from the instance information
      machine['ip_internal'] = instance['ip_internal']
      machine['ip_external'] = instance['ip_external']
      machine['dns_public'] = instance['dns_external']
      machine['dns_private'] = instance['dns_internal']
      
      # Escalate the Status to Allocated
      machine['status'] = 2
      
      # Update the machine with it's new data
      site_control.UpdateData('machine', machine['id'], machine)
    
    # Else, we have an IP for this machine, but it's different, if this machine
    #   exists
    elif machine['name'] in instances and machine['ip_internal'] != None and \
        machine['ip_internal'] != instances[machine['name']]['ip_internal']:
      # Update this machines data
      log('Updating machine data.  Internal IP changed: %s != %s' % \
          (machine['ip_internal'], instances[machine['name']]['ip_internal']))
      
      # Get the IP/DNS/etc information from the instance information
      machine['ip_internal'] = instance['ip_internal']
      machine['ip_external'] = instance['ip_external']
      machine['dns_public'] = instance['dns_external']
      machine['dns_private'] = instance['dns_internal']
      
      # Update the machine with it's new data
      site_control.UpdateData('machine', machine['id'], machine)


def RecalculatePoolSize(pool_id, site=site_control.SITE_DEFAULT):
  """Will recalculate the pool sizes."""
  pool = site_control.GetPool(pool_id, site=site)

  # Get all the machines listed in this pool
  sql = "SELECT * FROM pool_machine WHERE pool = %d" % pool['id']
  pool_machine_result = Query(sql)
  machine_total = len(pool_machine_result)

  # Get active machines
  sql = "SELECT machine.* FROM machine, pool_machine WHERE pool_machine.pool = %s AND pool_machine.machine = machine.id AND machine.status = 5" % pool['id']
  active_machines = Query(sql)
  machine_active = len(active_machines)

  # Get provisioned machines
  #TODO(g): For now we provision right to 2, but 1 is traditional, so do both
  sql = "SELECT machine.* FROM machine, pool_machine WHERE pool_machine.pool = %d AND pool_machine.machine = machine.id AND machine.status IN (1, 2)" % pool['id']
  just_provisioned_machines = Query(sql)
  machine_provisioned = len(just_provisioned_machines)

  # Update the pool sizes
  sql = "UPDATE pool SET machine_total = %d, machine_active = %d, machine_provisioned = %d WHERE id = %d" % \
        (machine_total, machine_active, machine_provisioned, pool['id'])
  Query(sql)

  log('Pool %s: Total=%s  Active=%s  Provisioned=%s' % \
      (pool['name'], machine_total, machine_active, machine_provisioned))

  return (machine_total, machine_active, machine_provisioned)


