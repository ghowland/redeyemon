#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Client to the REM Site Control database: Site Control API

The RPC server for the API uses this, as does the web page system, and CLI
tools.  It is the access to our data, and using this ensures the data is
changed with proper integrity checks and log all changes appropriately.

TODO(g): Cache all EC2 calls in Site Control database.  Protects against
    cascading problems around EC2 calls failing (like "Who Am I?"), also
    reduces CPU usage of REM on all systems except Site Control Master, because
    the Java processes to interact with EC2 are terribly innefficient and
    I havent found a comprehensive wrapped Web-API set, or done it myself.
    
    This also gives the advantage that all machines are GUARANTEED to see
    exactly the same state of the system that the master does, and allows the
    controlled machines to be less aware of problems EC2 may be having that the
    master can shield them from.
"""


import time
import yaml
import os


# Everyone includes all of these items, this is easiest kept here
SITE_DEFAULT = 1# Normal utilities


# We want what util has
from rem_util import *


# operator.itemgetter is new in Python 2.4
#  `itemgetter(index)(container)` is equivalent to `container[index]`
from operator import itemgetter


# ** Import all our API modules, including all their functions to have a grand
#   API all collection in a single module. **
from rem_api import *



if __name__ == '__main__': #TEST
  
  # Database tests
  if 1:
    AddDatabase('Test', 1, 20, 'Testing... 123', 2)
    pass
  
  # Old tests
  if 0:
    # Get the sites
    sites = GetSites()
    keys = sites.keys() ; keys.sort() ; print 'Sites: %s ' % keys
  
    # Get the pools
    pools = GetPools()
    keys = pools.keys() ; keys.sort() ; print 'Pools: %s ' % keys
  
    # Check what provisioning needs to occur
    provisioning = ProvisioningRequired()
    print 'Provisioning: %s' % provisioning
  
    # Get this Machine ID
    machine_id = GetThisMachineId()
    print 'Machine ID: %s' % machine_id
  
    # Get machine services
    machine_services = GetMachineServices(machine_id)
    machine_services.sort()
    print 'Machine services: %s' % machine_services
  
    # Get machine pools
    machine_pools = GetMachinePools(machine_id)
    print 'Machine pools: %s' % machine_pools
  
    # Get Machine
    machine = GetMachine(machine_id)
    print 'Machine: %s' % machine
  
    # Get machine service scripts
    machine_scripts = GetMachineServiceScripts(machine_id)
    #TODO(g): Write routine ScriptRunRequired_MachineService(machine_id, script_id, service_script_id)
    print 'Machine scripts: %s' % machine_scripts
  
    # Get machine RRDs
    machine_rrds = GetMachineRrds(machine_id)
    print 'Machine RRDs: %s' % machine_rrds

  # Get RRD 1
  if 0:
    print 'RRD #1:'
    import pprint
    pprint.pprint(GetRrd(1))

  #
