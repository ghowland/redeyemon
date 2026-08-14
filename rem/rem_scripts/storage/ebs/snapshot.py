#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Storage Function: EBS: Snapshot

Snapshot the EBS volume
"""


import sys


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def Execute(data=None, state=None):
  """Returns Boolean, successful snapshot invoked of all volumes."""
  if 'storage_id' not in data:
    return site_control.IncorrectExecuteArgs('storage_id key is not found in data')
  
  # Get our storage
  storage_id = data['storage_id']
  storage = site_control.GetStorage(storage_id)
  
  # Prove this false
  all_snapshots_succeeded = True
  
  # Snapshot each volume
  volumes = site_control.GetStorageVolumes(storage_id)
  for (volume_id, volume) in volumes.items():
    log('Snapshotting volume: %(volume_id)s  %(machine_device)s   %(size_gb)s' % volume)
    
    # Snapshot this volume
    success = rem_ec2.SnapshotVolume(volume['volume_id'], 'Storage: %d  Volume: %d' % (storage_id, volume_id))
    
    if success:
      log('Snapshot successful: %s  Volume: %s' % (storage_id, volume_id))
    else:
      log('Snapshot failed: %s  Volume: %s' % (storage_id, volume_id))
      all_snapshots_succeeded = False
  

  #TODO(g): Block here until all the snapshots are done, so that we can unfreeze
  #   and it's all atomic.
  pass #TODO...

  
  # If all our snapshots succeeded, then we succeeded
  if all_snapshots_succeeded:
    return True
  else:
    return False




def main(args=None):
  if not args:
    args = {}
  
  # If we have the db_instance.id arg
  if len(args) == 1:
    db_instance_id = int(args[0])
    
    # Execute the function
    result = Execute({'db_instance_id':db_instance_id})
    
    # If there was a problem... (This is really just an example, pointless here)
    if isinstance(result, site_control.IncorrectExecuteArgs):
      print 'Incorrect args...'
      sys.exit(0)
  
  else:
    print 'usage: %s db_instance.id' % sys.argv[0]
    
    sys.exit(1)


if __name__ == '__main__':
  #TODO(g): P
  main(sys.argv[1:])
