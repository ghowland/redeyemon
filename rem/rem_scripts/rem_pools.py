#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
REM: Show all pools machines for navigation.
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *

import pprint


def PrintMachineConnectInfo(pool_id, machine):
  """Print this machines's connect info."""
  sql = "SELECT * FROM pool_machine WHERE pool = %d AND machine = %d" % \
        (pool_id, machine['id'])
  result = query.Query(sql)
  
  # If we didnt get a result, we cant talk about the DNS name
  if not result:
    pool_machine = None
  else:
    pool_machine = result[0]
  
  # Update the machine
  machine = dict(machine)
  
  # If we have the pool machine, show the DNS
  if pool_machine:
    machine['dns'] = pool_machine['dns_public']
    print '%(id)04s: %(name)s (%(status_name)s):  Public: %(dns_public)-43s IP Internal: %(ip_internal)-16s %(dns)s' % machine
  else:
    print '%(id)04s: %(name)s (%(status_name)s):  Public: %(dns_public)-43s IP Internal: %(ip_internal)-16s' % machine


def ShowAllPoolMachineConnectInfo():
  """Prints all the machine connection info for all the pools, so we know
  which machine is doing what.
  """
  # Print out the site information 
  this_machine_id = site_control.GetThisMachineId()
  
  # Test for failure
  if this_machine_id == None:
    print 'ERROR: Failed to acquire this machines machine_id.'
    return
  
  this_machine = site_control.GetMachine(this_machine_id)
  site = site_control.GetSiteById(this_machine['site'])
  print 'Site: %(name)s (%(url)s)' % site
  print
  
  pools = site_control.GetPools()
  pool_names = pools.keys()
  pool_names.sort()
  
  for pool_name in pool_names:
    print 'Pool: %s' % pool_name
    pool = pools[pool_name]
    
    machines = site_control.GetPoolMachineList(pool['id'], status=None)
    
    # Store our machines by active/not, so we can easily see what is going on
    active = {}
    not_active = {}
    for machine_id in machines:
      machine = site_control.GetMachine(machine_id)
      
      # If Active, save in our active dict
      if machine['status'] == 5:
        active[machine_id] = machine
      # Else, save in not-active
      else:
        not_active[machine_id] = machine
    
    # If we need to label these
    if not_active:
      print '  [Active Machines]'
    
    # Print out Active machines
    machine_ids = active.keys()
    machine_ids.sort() # Lowest ID first, always, so the list doesnt bounce around
    for machine_id in machine_ids:
      PrintMachineConnectInfo(pool['id'], active[machine_id])
    
    if not_active:
      print
      print '  [Non-Active Machines]'
      
    # Print out Active machines
    machine_ids = not_active.keys()
    machine_ids.sort() # Lowest ID first, always, so the list doesnt bounce around
    for machine_id in machine_ids:
      PrintMachineConnectInfo(pool['id'], not_active[machine_id])
    
    # Extra line between pools
    print 
  


def main():
  ShowAllPoolMachineConnectInfo()


if __name__ == '__main__':
  #logging.Disable()
  
  main()
