#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
REM: Show pool info, this machine, this machine's pools, list other pools.

Allow pool and machine_id to be specified.
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *

import pprint


def ShowPoolInfo(pool_id=None, machine_id=None):
  """Prints about about pool, based on args.
  """
  # If we dont have anything, get them both
  if not machine_id:
    # Get this machine
    machine_id = site_control.GetThisMachineId()
  
  # Get our machine
  machine = site_control.GetMachine(machine_id)
  
  # If we have a pool ID, just use that
  if pool_id:
    pools = [pool_id]
  
  # Else, get all the machine's pools
  else:
    pools = site_control.GetMachinePools(machine_id)
  
  # Print the machine info
  print 'Machine:'
  #TODO(g): Make an easy way to print out info for machines and pools and shit.  Text, HTML or HTML-edit should be easy to specify.
  pprint.pprint(machine)
  print
  print 'Is Site Master: %s' % site_control.IsThisMachineSiteMaster()
  print
  
  # Print the pool names and IDs
  for pool_id in pools:
    pool = site_control.GetPool(pool_id)
    print 'Pool: %s (%s)' % (pool['name'], pool_id)
    pprint.pprint(pool)
    print
  
  # Print the machine's services
  services = site_control.GetMachineServices(machine_id)
  for service_id in services:
    service = site_control.GetService(service_id)
    print 'Service: %s (%s): %s' % (service['name'], service_id, service['info'])
  
  # Print out all the pools, and what machine instance names and ids are in them
  print
  print 'Pools:'
  pools = site_control.GetPools()
  names = pools.keys()
  names.sort()
  for name in names:
    pool = pools[name]
    
    # Get all the machines in this pool
    machines = site_control.GetPoolMachineList(pool['id'], status=None)
    
    # Create a string about containing info on each machine
    output = ''
    for machine_id in machines:
      if output:
        output += ', '
      
      machine = site_control.GetMachine(machine_id)
      
      status = site_control.GetMachineStatus(machine['status'])
      output += '%s:%s(%s)' % (machine['name'], status['name'], machine_id)
    
    # Print the pool name, and it's machine info
    print '  %s: %s' % (name, output)
  


def main():
  #TODO(g): Create options that allow us to specify machines and pools
  #   so we can browse around from any machine
  ShowPoolInfo(pool_id=None, machine_id=None)


if __name__ == '__main__':
  logging.Disable()
  
  main()
