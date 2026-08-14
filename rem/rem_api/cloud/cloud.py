#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Cloud

This wraps all the cloud specific module functions, so that we are cloud neutral
inside Site Control code.  This will eventually be the only module that calls
functions inside of rem_ec2.py (and others as we add clouds).  The type of cloud
is determined based on the data involved (machine, volumes, floating IPs, etc),
and then call the proper module function.

In this way we can also wrap cloud specific features, and even make up for
missing cloud features with some other configuration (even setting up
automated pool creation to handle services that dont exist in a desired target
cloud).  Thats all future possibilities, but good that we have that level of
control to handle whatever requirements may arise in this brave new world.


TODO(g): Caching will work well here.  Machines and volumes wont be hopping
    clouds, ever.
    
    Use table cloud_cache.  It is set up to cache commands, or other keyed data,
    and can then store all our EC2 commands very easily, and allow client
    machines to access the cache data directly from EC2
    
    We will ALWAYS refresh the cache within it's time, and sometimes earlier on
    no_cache_and_block (which should be in all cloud.py args), so that critical
    ops dont have to fail or delay because we are still cached.
    
    no_cache_and_block will also block on that call, so that it is sure to get
    the latest answer (unless the command fails, then the old result is returned)
    for continuinty's sake, and we throw 
    
"""


# REM libraries
import site_control

import rem_ec2
import rem_home_cloud #NOTE(g): Not yet implemented.


# Imports that are used directly...
from rem_ec2 import SnapshotVolume


def LogCloudAPIFailure(info):
  """Whenever we have a Cloud failure, we need to log it so we can detect how
  things are breaking by saving state about it, and then running logic against
  it.
  
  Between those things we will be able to come up with automated solutions to
  cloud failures, where perhaps all the machines are still working, but the API
  to find out information about them is gone.
  
  TODO(g): In later multi-cloud environments, this may be a good time to start
  ramping up the Disaster Recovery Cloud environment, so that if this current
  cloud provider fails any more (or there are already other failures that)
  havent been detected yet (like loss of traffic), we are ready to fail to
  another cloud quickly and this served as an early warning sign.
  """
  
  #TODO(g): This...


def GetCloudVolume(volume_id, no_cache_and_block=False):
  """Returns the data we have on the Cloud's Storage Volume, or None."""
  volume = site_control.GetStorageVolume(volume_id)
  
  # Get the volumes
  volumes = GetCloudVolumes(no_cache_and_block=no_cache_and_block)
  
  if volume['volume_id'] in volumes:
    return volumes[volume['volume_id']]
  else:
    return None
  


def GetCloudVolumes(no_cache_and_block=False):
  """Returns all the data we have from the Cloud.
  
  TODO(g): Add caching through Site Control Master database.
  """
  # Get the volumes
  volumes = rem_ec2.GetVolumes()
  
  return volumes
  
