#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Service Configure: Elastic Load Balancer

Load balances are our HTTP machines.
"""


import os
import sys

import config_util

# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def Configure():
  """Gets all the Active HTTP machines from site control and enforces them
  with the Elastic Load balancer.
  """
  #TODO(g): Hard coding...
  HTTP_POOL = 2
  
  # Status is Active(5) by default, but explicit as this is what were doing...
  machines = site_control.GetPoolMachineList(HTTP_POOL, status=5)
  
  # Get a list of instance names
  instances = []
  for machine_id in machines:
    machine = site_control.GetMachine(machine_id)
    
    instances.append(machine['name'])
  
  # Enforce these instances are on our 'web' Elastic Load Balancer
  log('Setting load balancer instances: %s' % instances)
  rem_ec2.SetLoadBalancerInstances('web', instances)


def main(args=None):
  Configure()



if __name__ == '__main__':
  main(sys.argv[1:])