#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Determine Floating IP: Internal DNS
"""

import os

import rem_scripts.config.config_util as config_util

# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def Determine():
  """Determine is intelligent and looks over our current data and decides.

  Whatever this particular script is meant to do, it's output will be used in
  a fashion that is going to choose something.  For instance, the floating
  IP address for DNS or our Edge.
  """
  # Temporary: Always use the Site Control master.  Makes it easy for now.
  if 1:
    master_ip = rem_ec2.GetMasterIp()
    
    sql = "SELECT * FROM machine WHERE ip_internal = '%s'" % SanitizeSQL(master_ip)
    machine = Query(sql)
    
    if machine:
      # Return the Site Master's machine name
      return machine[0]['name']
    else:
      return None
  
  ## This is another method, but right now this is always on the Site Master
  ##   machine, so I'll keep this to use it later, but just use the Site Master
  ##   machine now
  #if 0:
  #  # Get the lowest machine_id in the DNS pool, and select it, so it is steady
  #  #TODO(g): Currently this is in the Database pool, but this should be on
  #  #   the Site Master pool, right?
  #  DNS_POOL = 5#TODO(g): Should this be hard coded?  Maybe easiest/best.
  #  machines = site_control.GetPoolMachineList(DNS_POOL)
  #
  #  if machines:
  #    lowest_machine_id = min(machines)
  #
  #    machine = site_control.GetMachine(lowest_machine_id)
  #
  #    return machine['name']
  #  else:
  #    return ''


def main():
  output = Determine()
  print output



if __name__ == '__main__':
  logging.Disable()

  main()