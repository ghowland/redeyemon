#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Machine: Decommission

If EC2 has removed an instance from our instance list, remove the machine and
referencing table entries.

If EC2 has marked a machine as Terminated in our instance list, remove the
machine and referencing table entries.

If a machine exists and it's status is Decomissioned(7), then tell EC2 to remove it.
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def Decommission():
  """Configure our local machine."""
  # Get EC2's list of our instances, show all, even terminated and shuttingd-down
  instances = rem_ec2.GetInstances(all=True)
  
  # If we failed to get any instances, return because we cant do our job
  if instances == None:
    return
  
  # Decommission all the machines left in Decommissioned state in Site Control,
  #   but not removed from EC2.
  #NOTE(g): This was done when they were put into Decommissioned, but maybe
  #   EC2 will fail, and this will catch that by repeating until successful
  decommissioned_machines = {} # List of strings, instance names
  
  # Compare our machines to instances, any missing machines or EC2 marked
  #   as terminated, then remove the machines from Site Control as they are gone
  machines = site_control.GetMachines(status=None) # Get all the machines
  for (machine_id, machine) in machines.items():
    # If we cant find this machine in instances, remove the machine
    if machine['name'] not in instances:
      log('Found missing machine to remove: %s' % machine['name'])
      site_control.DeleteMachine(machine_id)
      decommissioned_machines[machine['name']] = machine['id']
    
    # Else, If the instance has been marked in EC2 as Terminated (or Shutting Down)
    elif instances[machine['name']]['ec2_state'] in ('terminated', 'shutting-down'):
      log('Found terminated machine to remove: %s' % machine['name'])
      # Remove the machine, its been terminated (or being shut down)
      decommissioned_machines[machine['name']] = machine['id']
    
    # Else, found
    else:
      #log('Found machine %s in instances: %s' % (machine['name'], instances[machine['name']]))
      pass
  
  # Get the master machine ID, never decomission this
  master_machine_id = site_control.GetMasterMachineId()
  
  # Get machines marked for decomissioning
  machines = site_control.GetMachines(status=7)
  # Process our machines
  for (machine_id, machine) in machines.items():
    # If this isnt the Site Control Master machine
    if machine_id != master_machine_id:
      log('Found machine marked for decomm: %s(%s)' % (machine['name'], machine_id))
      decommissioned_machines[machine['name']] = machine['id']
  
  # Decomission all the marked machines
  rem_ec2.DecommissionInstances(decommissioned_machines.keys())
  
  # Remove all the machines from our DB
  decommed = False
  for (machine_name, machine_id) in decommissioned_machines.items():
    if machine:
      log('Deleting machine: %s (%s)' % (machine_name, machine_id))
      site_control.DeleteMachine(machine_id)
      decommed = True
  
  # If we decommissioned machines, try to provision them now to save time
  if decommed:
    log('Just decommissioned machines, trying to provision immediately to save time.')
    site_control.ProvisionMachines()


def main():
  Decommission()


if __name__ == '__main__':
  main()
