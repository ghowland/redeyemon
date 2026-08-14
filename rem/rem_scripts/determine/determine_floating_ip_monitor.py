#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Determine Floating IP: Monitoring Graphs
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
  # Get the lowest machine_id in the Edge pool, and select it, so it is steady
  MONITOR_POOL = 10#TODO(g): Should this be hard coded?  Maybe easiest/best.
  machines = site_control.GetPoolMachineList(MONITOR_POOL)

  if machines:
    lowest_machine_id = min(machines)

    machine = site_control.GetMachine(lowest_machine_id)

    return machine['name']
  else:
    return ''



def main():
  output = Determine()
  print output



if __name__ == '__main__':
  logging.Disable()

  main()