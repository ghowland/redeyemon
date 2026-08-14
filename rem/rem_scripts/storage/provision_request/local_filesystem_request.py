#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Storage Provision: Local Filesystem

No provisioning happens here, because this file system already exists.  We still
create a volume for it, so we can track what device it's on and then we can
match our performance graphing and other tests (disk space) to the service that
relies on this Storage.
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
  
  log('Provisioning Request: Local: Storage: %s' % storage['name'])
  
  # This volume is local, it is automatically Assigned.  Update status.
  site_control.SetStorageVolumeStatus(volume_id, 3)


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
