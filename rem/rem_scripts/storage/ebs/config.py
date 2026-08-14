#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Storage Function: EBS: Configure

Configure the volumes for EBS: Elastic Block Storage
"""


import sys


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def Execute(data=None, state=None):
  """"""
  if 'storage_id' not in data:
    return site_control.IncorrectExecuteArgs('storage_id key is found in data')
  
  storage_id = data['storage_id']
  
  storage = site_control.GetStorage(storage_id)
  
  # Get the current state of this configuration
  config_state = site_control.GetStorageState(storage_id, 'config_ebs')
  
  # If this is not configured yet
  if config_state != '100':
    log('Configuring Storage: EBS: %s  Config state: %s' % (storage['name'], config_state))
    
    # Store EBS volume device into storage_state, in our standardized
    #   format, so we have device names for all layers of the stack
    volumes = site_control.GetStorageVolumes(storage_id)
    for (volume_id, volume) in volumes.items():
      # Save each volume, specifying the storage_order as our value_order for
      #   the config
      site_control.SetStorageConfig(storage_id, 'ebs', volume['machine_device'], volume['storage_order'])
    
    # Mark this as configured
    site_control.SetStorageState(storage_id, 'config_ebs', 100)
  
  # Else, this is already configured
  else:
    log('Already Configured Storage: EBS: %s  Config state: %s' % (storage['name'], config_state))
  


def main(args=None):
  if not args:
    args = {}
  
  # If we have the storage.id arg
  if len(args) == 1:
    storage_id = int(args[0])
    
    # Execute the function
    result = Execute({'storage_id':storage_id})
    
    # If there was a problem... (This is really just an example, pointless here)
    if isinstance(result, site_control.IncorrectExecuteArgs):
      print 'Incorrect args...'
      print 'usage: %s storage.id' % sys.argv[0]
      sys.exit(0)
  
  else:
    print 'usage: %s storage.id' % sys.argv[0]
    sys.exit(1)


if __name__ == '__main__':
  main(sys.argv[1:])
