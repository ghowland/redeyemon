#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Storage Function: LVM: Unfreeze volume (All I/O ops are unblocked)

Unblocks all I/O ops for this LVM volume
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
  
  log('TODO(g): Storage:LVM:Unfreeze: Implement to protect snapshots')



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
      sys.exit(0)
  
  else:
    print 'usage: %s storage.id' % sys.argv[0]
    
    sys.exit(1)


if __name__ == '__main__':
  #TODO(g): P
  main(sys.argv[1:])
