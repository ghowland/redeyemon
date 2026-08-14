#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Machine: Configure

Second stage of brining a machine up.  Once a machine is Requested(1), we
have it's instance info, but not access info, because it hasnt been provisioned
by EC2 yet.  This runs to collect that connection information and then
set the machine's state to Allocated(2) to let to be Installed(3).

Configure: local files
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def Configure():
  """Configure our local machine."""
  machine_id = site_control.GetThisMachineId()
  machine = site_control.GetMachine(machine_id)

  # Get all the services on this machine
  services = site_control.GetMachineServices(machine_id)

  # Process our services
  for service_id in services:
    service = site_control.GetService(service_id)

    # Run the configuration script, if it's set
    if service['script_config']:
      script = site_control.GetScript(service['script_config'])
      log('Machine: %s(%s)  Service: %s(%s)  Script: %s(%s)' % \
          (machine['name'], machine_id, service['name'], service_id,
           script['name'], service['script_config']))
      (exit_code, output) = run_script.RunScript(service['script_config'])

  # If the machine was in Allocated state, we want to upgrade to installed.
  #NOTE(g): Dont mess with other states
  machine = site_control.GetMachine(machine_id)
  if machine['status'] == 2:
    # All our service configuration script have been run, this machine has been
    #   configured
    site_control.SetMachineStatus(machine_id, 3) # Installed!



def main():
  Configure()



if __name__ == '__main__':
  main()
