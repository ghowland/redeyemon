#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Storage Create Volume: Local Filesystem

Create the storage_volume entry for a volume.
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
    return site_control.IncorrectExecuteArgs('storage_id key is not found in data')
  
  # Get our storage
  storage_id = data['storage_id']
  storage = site_control.GetStorage(storage_id)
  handler_stack = site_control.GetStorageHandlerStack(storage['handler_stack'])
  log('Provisioning Creating storage_volume: Storage: %s' % storage['name'])
  
  # Get all the volumes we have (includes new volumes)
  volumes = site_control.GetStorageVolumes(storage_id)
  
  #TODO(g): LATER: Check out what kind of volume needs to be created.  Shouldnt
  #   need to check that this is needed, but will be obvious if there is a
  #   complex logic to determining each volume.
  pass
  
  # Prep the data
  size_gb = storage['size_gb']
  order = 0
  
  # Create the volume
  volume_id = site_control.StorageVolumeCreate_Actual(storage_id, order, size_gb)
  
  log('Created volume: %s for Storage: %s' % (volume_id, storage_id))
  
  return volume_id
  


def main(args=None):
  if not args:
    args = {}
  
  # If we have the db_instance.id arg
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
  #TODO(g): P
  main(sys.argv[1:])
