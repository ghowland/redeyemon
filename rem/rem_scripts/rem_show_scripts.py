#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
REM: Shows scripts that are running on this machine, their run information
and when they last ran.
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *

import pprint


def ShowMahcineScripts(machine_id=None):
  """Prints about about pool, based on args.
  """
  # If we dont have anything, get them both
  if not machine_id:
    # Get this machine
    machine_id = site_control.GetThisMachineId()
  
  # Get our machine
  machine = site_control.GetMachine(machine_id)
  
  # Print the machine info
  print 'Machine:'
  #TODO(g): Make an easy way to print out info for machines and pools and shit.  Text, HTML or HTML-edit should be easy to specify.
  pprint.pprint(machine)
  print
  print 'Is Site Master: %s' % site_control.IsThisMachineSiteMaster()
  print
  
  # Get all the scripts on this machine
  service_scripts = site_control.GetMachineServiceScripts(machine_id)
  for script_id in service_scripts:
    script = site_control.GetScript(script_id)
    
    services = []
    for service_script_id in service_scripts[script_id]:
      service_script = site_control.GetServiceScript(service_script_id)
      if service_script['service'] not in services:
        service = site_control.GetService(service_script['service'])
        service_text = '%s (%s)' % (service['name'], service_script['service'])
        services.append(service_text)
    
    print 'Script: %s (%s):  File=%s:  Services=(%s)\n    %s' % \
          (script['name'], script_id, script['path_relative_script'],
           ', '.join(services), script['info'])
  
  #TODO(g): Show all the last run scripts on this machine.  10?  20?  Options...
  SHOW_LAST_RUNS = 10


def main():
  #TODO(g): Create options that allow us to specify machines, so we can browse
  #   around from any machine
  ShowMahcineScripts(machine_id=None)


if __name__ == '__main__':
  logging.Disable()
  
  main()
