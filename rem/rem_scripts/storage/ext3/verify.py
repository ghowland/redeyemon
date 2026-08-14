#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Storage Function: ext3: Verify

Perform read and write operations, to test that the volume functions in a basic
way.
"""


import sys
import os


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
  
  # Any failure inside this block is a failure to verify
  try:
    log('Storage %s (%d): Verifying: Writing to a file.' % (storage['name'], storage_id))
    path = '%s/...test...' % storage['mount_path']
    open(path, 'w').write('Testing 123')
    
    content = open(path).read()
    
    # If we dont have the exact content we put in, fail
    if content != 'Testing 123':
      raise Exception('Read from written file test failed: %s' % path)
    
    # Delete the test file
    os.unlink(path)
    
    # We made it to the end, success
    success = True
  
  # Any exceptions, and verify fails
  except Exception, e:
    log('Storage %s (%d): Verify Failed: %s' % (storage['name'], storage_id, e),
        logging.ERROR)
    success = False
  
  
  # If we the tests were successful, set this Storage to Verified
  if success:
    site_control.SetStorageStatus(storage_id, site_control.STORAGE_STATUS__VERIFIED)
  
  # Else, the tests failed, Repair this Storage
  else:
    site_control.SetStorageStatus(storage_id, site_control.STORAGE_STATUS__REPAIRING)
  



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
