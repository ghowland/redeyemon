#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Storage Provision: EBS -> LVM -> ext3

Provision volumes for this configuration.
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
  
  log('Provisioning Request: EBS: Storage: %s' % storage['name'])
  
  # Get all the volumes we have (includes new volumes)
  volumes = site_control.GetStorageVolumes(storage_id)
  
  if not volumes:
    log('No storage volumes: %s' % storage_id)
  else:
    log('Volume Count: %s: %s' % (len(volumes), volumes))
  
  # Check our volumes for being Assigned to machines
  for (volume_id, volume) in volumes.items():
    log('Volume: %s: %s' % (volume_id, volume))
    
    # If this volume is Initialized or Requested
    if volume['status'] == 1:
      # Request cloud storage volumes be provided
      #NOTE(g): Wraps calling the cloud functions and storing the results
      log('Provisioning volume from cloud: %s' % volume_id)
      site_control.StorageVolumeCloudProvision(volume_id)
      
      # Update the volume, it may be Requested already (skips a wait-cycle)
      volume = site_control.GetStorageVolume(volume_id)
    
    # If this volume is Requested (Not elif on purpose)
    if volume['status'] == 2:
      log('Checking if volume is Assigned yet: %s' % volume_id)
      
      # Get the cloud volume information (dont use cache, block until we get it)
      cloud_volume = site_control.GetCloudVolume(volume_id, no_cache_and_block=True)
      
      # If this volume is now mounted
      if 'attachment_status' in cloud_volume and \
          cloud_volume['attachment_status'] == 'attached':
        # Mark the volume as Assigned, so we can continue configuration
        log('Volume is now Assigned: %s' % volume_id)
        site_control.SetStorageVolumeStatus(volume_id, 3)
  
  # Get all the volumes, updated
  volumes = site_control.GetStorageVolumes(storage_id)
  
  # If we dont have any volumes yet, then the storage isnt mounted, and there
  #   is a problem.
  if not volumes:
    log('EBS request made it to the end of provision with no volumes in the DB.', logging.CRITICAL)
    return None
  
  # Else, process the volumes
  else:
    # Any non-assigned volume falsifies this
    all_assigned = True
    
    # When all the volumes are status=Assigned(3), then the storage=Assigned(3)
    for (volume_id, volume) in volumes.items():
      # If this isnt assigned, fail
      if volume['status'] != 3:
        all_assigned = False
        break
    
    # If all our Volumes are Assigned, then the Storage is Assigned
    if all_assigned:
      site_control.SetStorageStatus(storage_id, site_control.STORAGE_STATUS__ASSIGNED)


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
