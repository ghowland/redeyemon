#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Storage Function: LVM: Configure

Configure the volumes for LVM: Linux Volume Manager
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
  
  #TODO(g): Make this dynamic based on the Handler-Stack
  if site_control.GetStorageState(storage_id, 'config_ebs') != '100':
    log('Cannot configure LVM until EBS is configured')
    return None
  
  # Get the current state of this configuration
  config_state = site_control.GetStorageState(storage_id, 'config_lvm')
  
  # If this is not configured yet
  if config_state != '100':
    # Convert config_state to an integer, so we can test it
    try:
      config_state = int(config_state)
    except:
      config_state = 0
    
    log('Configuring Storage: LVM: %s  Config state: %s' % (storage['name'], config_state))
    
    volumes = site_control.GetStorageVolumes(storage_id)
    
    # If we have more than one volume, fail
    #TODO(g): Implement multi-volume solutions.  Can stripe or mirror without RAID
    if len(volumes) > 1:
      log('LVM is only set up to handle one(1) volume currently.  Modify before %d volumes will work: %s' % (len(volumes), storage_id), logging.CRITICAL)
      return None
    
    # Get the only volume (by it's volume_id)
    #TOOD(g): Handle multiple volumes...
    volume = volumes[volumes.keys()[0]]
    
    # Create the Physical Volume device
    #TODO(g): Unhard-code paths.  Do a discovery for all binaries to keep paths
    #   absolute when running scripts (to avoid environment problems that
    #   could arise without knowing they will break the automation...)
    if config_state < 10:
      # Force Physical Volume creation, to overwrite any previous info
      cmd = '/usr/sbin/pvcreate -ff -y %s' % volume['machine_device']
      (status, output, output_error) = run_script.Run(cmd)
      if status == 0:
        config_state = 10
        site_control.SetStorageState(storage_id, 'config_lvm', config_state) # 10%
        log('Physical Volume: Created')
      else:
        log('Physical Volume: Failed: %s' % output_error, logging.ERROR)
        return None
    else:
      log('Physical Volume: Already Created')
    
    # Create the Volume Group (physical extent: 16MB)
    if config_state < 20:
      cmd = '/usr/sbin/vgcreate -s 16M lvm_vg_%s %s' % (storage_id, volume['machine_device'])
      (status, output, output_error) = run_script.Run(cmd)
      if status == 0:
        config_state = 20
        site_control.SetStorageState(storage_id, 'config_lvm', config_state) # 20%
        log('Volume Group: Created: lvm_vg_%s' % storage_id)
      else:
        log('Volume Group: Failed: %s' % output_error, logging.ERROR)
        return None
    else:
      log('Volume Group: Already Created: lvm_vg_%s' % storage_id)
    
    # Create the Logical Volume device.  Use all free space, and name lvm_%(storage_id)s
    if config_state < 30:
      cmd = '/usr/sbin/lvcreate -l 100%%FREE lvm_vg_%s -n lvm_%s' % (storage_id, storage_id)
      (status, output, output_error) = run_script.Run(cmd)
      if status == 0:
        config_state = 30
        site_control.SetStorageState(storage_id, 'config_lvm', config_state) # 30%
        log('Logical Volume: Created: lvm_%s' % storage_id)
      else:
        log('Logical Volume: Failed: %s' % output_error, logging.ERROR)
        return None
      
    else:
      log('Logical Volume: Already Created: lvm_%s' % storage_id)
    
    # Save the LVM device in the Storage's config
    if config_state < 40:
      site_control.SetStorageConfig(storage_id, 'lvm', '/dev/lvm_vg_%s/lvm_%s' % (storage_id, storage_id))
      config_state = 40
      site_control.SetStorageState(storage_id, 'config_lvm', config_state) # 40%
    
    
    # If we have done everything, mark this as Configured
    if config_state >= 40:
      site_control.SetStorageState(storage_id, 'config_lvm', 100) # 100%
  
  # Else, this is already configured
  else:
    log('Already Configured Storage: LVM: %s  Config state: %s' % (storage['name'], config_state))
  

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
