#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Database Function: MySQL: Shutdown

Create this database, or ensure it is properly set up.
"""


import sys


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def Execute(data=None, state=None):
  """"""
  if 'instance_id' not in data:
    return site_control.IncorrectExecuteArgs('instance_id key is found in data')
  
  instance_id = data['instance_id']
  
  instance = site_control.GetDatabaseInstance(instance_id)
  
  print 'Shutdown the database for this db_instance:'
  print instance



def main(args=None):
  if not args:
    args = {}
  
  # If we have the db_instance.id arg
  if len(args) == 1:
    instance_id = int(args[0])
    
    # Execute the function
    result = Execute({'instance_id':instance_id})
    
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
