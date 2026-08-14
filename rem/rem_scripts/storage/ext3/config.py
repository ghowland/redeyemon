#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Storage Function: ext3: Configure

Configure the volumes for ext3

Format.
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
    return site_control.IncorrectExecuteArgs('storage_id key is found in data')
  
  storage_id = data['storage_id']
  
  storage = site_control.GetStorage(storage_id)
  
  #TODO(g): Make this dynamic based on the Handler-Stack
  if site_control.GetStorageState(storage_id, 'config_ebs') != '100':
    log('Cannot configure ext3 until EBS is configured')
    return None
  
  #TODO(g): Make this dynamic based on the Handler-Stack
  if site_control.GetStorageState(storage_id, 'config_lvm') != '100':
    log('Cannot configure ext3 until LVM is configured')
    return None
  
  
  # Get the current state of this configuration
  config_state = site_control.GetStorageState(storage_id, 'config_ext3')
  
  # If this is not configured yet
  if config_state != '100':
    # Convert config_state to an integer, so we can test it
    try:
      config_state = int(config_state)
    except:
      config_state = 0
    
    log('Configuring Storage: ext3: %s  Config state: %s' % (storage['name'], config_state))
    
    # Get the LVM device
    #TODO(g): Do this based on Handler-Stack, not hard-coded
    lvm_device = site_control.GetStorageConfig(storage_id, 'lvm')
    
    # Format the mount path
    mount_path = '/mnt/storage_%s' % storage_id
    
    # Format the device with ext3
    if config_state < 10:
      # Format the device with ext3 (ext2+journaling)
      cmd = '/sbin/mke2fs -j %s' % lvm_device
      (status, output, output_error) = run_script.Run(cmd)
      if status == 0:
        config_state = 10
        site_control.SetStorageState(storage_id, 'config_ext3', config_state) # 10%
        log('ext3: Formated')
      else:
        log('ext3: Failed to format: %s' % output_error, logging.ERROR)
        return None
    else:
      log('ext3: Already Formated')
    
    # Create the device mount directory
    if config_state < 20:
      # If the path doesnt already exist, create it
      if not os.path.isdir(mount_path):
        try:
          os.mkdir(mount_path)
        except Exception, e:
          log('Failed to make path: %s: %s' % (mount_path, e), logging.CRITICAL)
          return None
      
      config_state = 20
      site_control.SetStorageState(storage_id, 'config_ext3', config_state) # 20%
      log('ext3: Mount path created: %s' % mount_path)
    else:
      log('ext3: Mount path already created: %s' % mount_path)
    
    # Mount the device
    if config_state < 30:
      # Format the device with ext3 (ext2+journaling)
      cmd = '/bin/mount %s %s' % (lvm_device, mount_path)
      (status, output, output_error) = run_script.Run(cmd)
      if status == 0:
        # Save the mouth_path as ext3's configuration
        site_control.SetStorageConfig(storage_id, 'ext3', mount_path)
        config_state = 30
        site_control.SetStorageState(storage_id, 'config_ext3', config_state) # 20%
        log('ext3: Mounted: %s' % mount_path)
      else:
        log('Failed to mount device: %s' % output_error, logging.ERROR)
        return None
    else:
      log('ext3: Already Mounted: %s' % mount_path)
    
    # If we have done everything, mark this as Configured
    if config_state >= 30:
      site_control.SetStorageState(storage_id, 'config_ext3', 100) # 100%
      
      # Mark this Storage a Mounted
  
  # Else, this is already configured
  else:
    log('Already Configured Storage: ext3: %s  Config state: %s' % (storage['name'], config_state))
  
  


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
