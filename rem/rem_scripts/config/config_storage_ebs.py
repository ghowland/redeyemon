#TODO(g): This module has never been used, but has some examples, so keeping it
#   for now.  I wrote this as a prototype, but then re-wrote it differently.

##!/usr/bin/python
#
#
##Author: Geoff Howland
##Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
##Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License
#
#"""
#Storage Handler: Config: EBS
#
#Handles all configuration aspects for EBS.
#
#This includes provisioning EBS volumes, attaching them to machines, and
#ensuring all the data is aligned between EC2 and Site Control.
#"""
#
#
## REM libraries
#import site_control
#import run_script
#from rem_api import cloud as rem_ec2
#from rem_util import *
#
#
#def Configure():
#  """Ensure this machine's EBS volumes are all configured correctly.
#  
#  NOTE(g): Each machine should take care of it's own assignments, so that we
#      know they were actually capable of doing so.  If they aren't capabale of
#      doing that, they can't be trusted to run storage.
#  """
#  # Get this machine's ID
#  machine_id = site_control.GetThisMachineId()
#  
#  # Get all the storages for this machine
#  storages = site_control.GetMachineStorages(machine_id)
#  
#  # For each storage on this machine
#  for storage_id in storages:
#    # Get the storage
#    storage = site_control.GetStorage(storage_id)
#    
#    # Check all the volumes are on this machine
#    volumes = site_control.GetMachineStorageVolumes(machine_id)
#    
#    # Ensure all current volumes are assigned to the correct machine
#    for volume_id in volumes:
#      volume = GetStorageVolume(volume_id)
#      
#      # Verify that it is on the correct machine
#      if volume['machine'] != machine_id:
#        # Assign this volume to this machine
#        site_control.AssignStorageVolumeToMachine(volume_id, machine_id)
#    
#    # Get the EC2 storage volumes
#    ec2_volumes = rem_ec2.GetStorageVolumes()
#    
#    # Collect all the assigment information from EC2 and update any differences
#    #   in Site Control (this means the mount device name: EC2EBS->local)
#    for volume_id in volumes:
#      volume = GetStorageVolume(volume_id)
#      
#      # If this volume has been cleaned out of EC2, we have to deal with a
#      #   missing volume.
#      if volume['volume_id'] not in ec2_volumes:
#        # This will get rid of it, we'll add it again later belome
#        site_control.RemoveStorageVolume(storage_id, volume['volume_id'])
#      
#      # Else, the volume is in EC2
#      else:
#        # If the volume is not marked active in EC2
#        #TODO(g): Figure out that test...
#        if 0:#...
#          # This will get rid of it, we'll add it again later belome
#          site_control.RemoveStorageVolume(storage_id, volume['volume_id'])
#        
#        # Get the EC2 volume information
#        ec2_volume = ec2_volumes[volume['volume_id']]
#        
#        # If we have differing device information, update Site Control
#        if ec2_volume['machine_device'] != volume['machine_device']:
#          # Update the machine device path name, using EC2 as authoritive
#          site_control.UpdateData('storage_volume', volume_id,
#                                  {'machine_device':ec2_volume['machine_device']})
#          
#          # Rebuild the storage, the device volume change
#          site_control.RebuildStorage(storage_id)
#    
#    
#    # -- Update from EC2 again.  We may have just made changed above.
#    
#    # Check all the volumes are on this machine
#    volumes = site_control.GetMachineStorageVolumes(machine_id)
#    
#    # Get the EC2 storage volumes
#    ec2_volumes = rem_ec2.GetStorageVolumes()
#    
#    
#    # Get the storage configuration info, so we can compare ideal to reality
#    #config_info = {'machine':machine_id, 'volume_count':total,
#    #               'volume_size':size_each, 'mount_path_final':mount_path}
#    config_info = site_control.GetStorageConfigInfo(storage_id)
#    
#    
#    # Ensure that we have all the volumes we want
#    #NOTE(g):CRITICAL: If the number of volumes changes, it's because someone
#    #   manually did something, so it is expected something drastic is going
#    #   to happen in our automated system.  This is it, the storage will be
#    #   corrected, and if data cant be recovered due to format incompatibility
#    #   then the new device configuration will be left blank on format and
#    #   an alert will be sent for humans to restore data to the new volume
#    #   manually.
#    if len(volumes) != config_info['volume_count']:
#      # Add the number of volumes we dont have
#      add_count = config_info['volume_count'] - len(volumes)
#      
#      # If we have too many volumes, get how many we are extra, and remove the
#      #   last ones in the storage.
#      if add_count < 0:
#        # Number of volumes to remove
#        remove_count = abs(add_count)
#        
#        # Remove the highest volume in our storage_volumes, until we are right
#        for count in range(len(volumes)-1, remove_count, -1):
#          site_control.RemoveStorageVolume(storage_id, volumes[count])
#        
#        # Rebuild the storage after this change
#        site_control.RebuildStorage(storage_id)
#      
#      # Else, we are adding more volumes to our storage
#      else:
#        # Add the volumes
#        for count in range(len(volumes), add_count):
#          # Get the lowest available order in the volume set
#          order = site_control.GetStorageVolumeLowestEmptyOrder(storage_id)
#          
#          # Add the volume to the specified order in the volume set
#          #NOTE(g): This automatically assigns the proper machine
#          new_volume_id = site_control.AddStorageVolume(storage_id, order=order)
#        
#        # Rebuild the storage after this change
#        site_control.RebuildStorage(storage_id)
#    
#    
#    # -- Update from EC2 again.  We may have just made changed above.
#    
#    # Check all the volumes are on this machine
#    volumes = site_control.GetMachineStorageVolumes(machine_id)
#    
#    # Get the EC2 storage volumes
#    ec2_volumes = rem_ec2.GetStorageVolumes()
#    
#    
#    # Ensure all the volumes are of the right size
#    for volume_id in volumes:
#      volume = site_control.GetStorageVolume(volume_id)
#      
#      # Track whether we remove anything
#      removed_volume = False
#      
#      # If there is a mismatch in size in this volume
#      if volume['size_gb'] != ec2_volumes['size_gb']:
#          site_control.RemoveStorageVolume(storage_id, volumes[count])
#          removed_volume = True
#      
#      # If we removed a volume (or more), rebuild the storage
#      if removed_volume:
#        # Rebuild the storage after this change
#        site_control.RebuildStorage(storage_id)
#
