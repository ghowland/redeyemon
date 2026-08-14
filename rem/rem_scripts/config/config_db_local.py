#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Configure: Database: Top Level configuration of ALL database kinds: Local config

This is the LOCAL configuration script for all database kinds.  This means
all kinds of databases are handled under this script.  This only configures
databases that will run on THIS machine.  The config_db_master.py script
ensured a machine would be created to managed it's database, and if this script
is running, that is us.

Create storage (from scratch, or snapshot/backup) if it does not exist or is
corrupt (fails read/write tests).

  CAUTION: Automated action is an option, turning it on can have unintended
  consequences if everything is not PERFECT, so use with caution.

This script configures ALL the databases on this machine, in a single invocation.
"""


import os
import sys

import config_util

# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def Configure(site=site_control.SITE_DEFAULT):
  """Configure the database instance on this machine to be Active: Ready to
  handle queries.
  """
  # Get this machines info
  machine_id = site_control.GetThisMachineId()
  machine = site_control.GetMachine(machine_id)
  
  # Get what db_set controlls this machine
  pool = site_control.GetMachinePoolPrimary(machine_id)
  db_set = site_control.GetDatabaseSet(pool['db_set'])
  dbs = site_control.GetDatabaseSetDatabases(pool['db_set'])

  # For each database, configure 
  for db_id in dbs:
    db = dbs[db_id]
    
    # What database instances runs on this machine
    instances = site_control.GetDatabaseInstancesOnMachine(machine_id)
    
    # Process each db_instance
    for (instance_id, instance) in instances.items():
      
      # Configure the storage, and find out what it thinks we should do next
      site_control.StorageConfigure(instance['mount_storage'])
      
      # Get the updated status
      storage = site_control.GetStorage(instance['mount_storage'])
      config_status = storage['status']
      
      # If nothing changed, continue to the next DB instance
      if config_status == site_control.STORAGE_STATUS__ACTIVE:
        
        # If the database was allocated, but waiting on storage to configure...
        if instance['status'] == site_control.DB_STATUS_ALLOCATED:
          # Just having the storage as active and us in allocate is enough.
          
          # Set the database status to Configured-Storage, time to Configure
          #   the database itself, now that the storage is ready
          site_control.SetDatabaseInstanceStatus(instance_id, site_control.DB_STATUS_CONFIGURED_STORAGE)
        
        
        #NOTE(g): These must EACH be if-statements, not if-elifs, or else we
        #   will not be able to chain through things that happen immediately
        
        
        # If the database was allocated, but waiting on storage to configure...
        if instance['status'] == site_control.DB_STATUS_CONFIGURED_STORAGE:
          # Configure this machine
          ConfigureDatabaseSetMachine(db_set, machine_id)
          
          # Get the database instance again, maybe we are configured
          instance = site_control.GetDatabaseInstance(instance_id)
        
        
        # If the database has been configured, verify it
        if instance['status'] == site_control.DB_STATUS_CONFIGURED:
          # Verification...
          VerifyDatabaseSetMachine(db_set, machine_id)
          
          # Get the database instance again, maybe we are verfied
          instance = GetDatabaseInstance(instance_id)
        
        
        # If the database was Verified, set it to Active!
        if instance['status'] == site_control.DB_STATUS_VERIFIED:
          # Activate
          site_control.SetDatabaseInstanceStatus(instance_id, site_control.DB_STATUS_ACTIVE)
      
      
      # Else, if the the storage is still being configured
      elif config_status in (site_control.STORAGE_STATUS__INITIALIZED,
                             site_control.STORAGE_STATUS__REQUESTED,
                             site_control.STORAGE_STATUS__ASSIGNED):
        log('Database Instance: %s: Storage Currently being Configured: %s' % \
            (instance_id, config_status))
      
      # Else, if the database is in a failed state
      elif config_status == site_control.STORAGE_STATUS__REPAIRING:
        log('Database Instance: %s: FAILED STATE', logging.ALERT)
        
        #TODO(g): Take corrective action here.  Restore from previous backup.
        #...
        pass#...
        #...


def VerifyDatabaseSetMachine(db_set, machine_id):
  """Very the database set on this machine."""
  # Get all the database instances for this db_set
  instances = site_control.GetDatabaseSetInstances(db_set)
  for (instance_id, instance) in instance.items():
    
    #TODO(g): Actual verify things.  Run the standard script, and the custom scripts.
    if 1:
      # Set this database instance to Verified
      site_control.SetDatabaseInstanceStatus(instance_id, site_control.DB_STATUS_VERIFIED)


def ConfigureDatabaseSetMachine(db_set, machine_id):
  """Configure this machine's database.
  
  TODO(g): Remove db_set, unless there is a good reason to keep it.  I think
      it's pointless though.  We should just configure ALL the DB instances on
      this machine, which is what we care about.  Which db_set they are in just
      determines which db_instances were created on this machine, so thats
      already been selected for...  I think.  So check, then remove it.
  """
  # Dont allow configuring of this machine from other machine's specs
  this_machine_id = site_control.GetThisMachineId()
  if machine_id != this_machine_id:
    log('Trying to configure a database for a different machine.', logging.CRITICAL)
    return
  
  # Get database instances on this machine
  instances = site_control.GetMachineDatabaseInstances(machine_id)
  
  # Process each of these instances
  for instance_id in instances:
    instance = site_control.GetDatabaseInstance(instance_id)
    
    # If this instance is Initiaziled
    if instance['status'] == site_control.DB_STATUS_INITIALIZED:
      # Try to get the machine for this instance
      machine = site_control.GetMachine(instance['machine'])
      
      # If the machine exists and it's in a configurable state (for storage)
      if machine and machine['status'] in (site_control.MACHINE_STATUS_ALLOCATED,
                                           site_control.MACHINE_STATUS_CONFIGURED,
                                           site_control.MACHINE_STATUS_VERIFIED,
                                           site_control.MACHINE_STATUS_ACTIVE):
        # Set this database to Allocated, we have a machine to put storage on!
        site_control.SetDatabaseInstanceStatus(instance_id, site_control.DB_STATUS_ALLOCATED)
        instance = site_control.GetDatabaseInstance(instance_id) # Refresh status
    
    # If this instance is Allocated
    if instance['status'] == site_control.DB_STATUS_ALLOCATED:
      # Attempt to configure storage
      #NOTE(g): This function will look at the storage state, and not run
      #   again if it is already being configured be a previous request.  So
      #   calling this multiple times is safe.
      site_control.DatabaseFunctionRun(instance['mount_storage'], 'ConfigureStorage')
      
      # Get the storage
      storage = site_control.GetStorage(instance['mount_storage'])
      
      # If the storage is Active, then our storage is configured.  Set the state
      if storage['status'] == site_control.STORAGE_STATUS__ACTIVE:
        site_control.SetDatabaseInstanceStatus(instance_id, site_control.DB_STATUS_CONFIGURED_STORAGE)
        instance = site_control.GetDatabaseInstance(instance_id) # Refresh status
    
    # If this instance has Configured Storage, configure the database
    if instance['status'] == site_control.DB_STATUS_CONFIGURED_STORAGE:
      #NOTE(g): This will set the status to Configuring internally, and then
      #   also set the status to Configured when it is complete.
      SYMLINK_PATH = '/var/rem/cloud/storage/VOLUME_NAME_HERE/DB_INSTANCE_NAME/DB_DATA_STUFF' # <--- use
      site_control.DatabaseFunctionRun(instance['id'], 'CreateDatabaseInstance')
    
    # If this instance is currently Configuring
    if instance['status'] == site_control.DB_STATUS_CONFIGURING:
      pass # Do nothing.  "CreateDatabaseInstance" DB Function handles this.
    
    
    # If this instance has been Configured
    if instance['status'] == site_control.DB_STATUS_CONFIGURED:
      # Verify the database
      success = site_control.DatabaseFunctionRun(instance['id'], 'VerifyDatabaseInstance')
      
      # If we succeeded, set this to Verified
      if success:
        site_control.SetDatabaseInstanceStatus(instance_id, site_control.DB_STATUS_VERIFIED)
        instance = site_control.GetDatabaseInstance(instance_id) # Refresh status
    
    # If this instance has been Verified
    if instance['status'] == site_control.DB_STATUS_VERIFIED:
      # Backup up the database, so we have a version to restore to, always.
      #NOTE(g): This only backs up instances that with is_writable=1.
      success = site_control.DatabaseFunctionRun(instance['id'], 'Backup')
      
      # Activate it
      site_control.SetDatabaseInstanceStatus(instance_id, site_control.DB_STATUS_ACTIVE)
      instance = site_control.GetDatabaseInstance(instance_id) # Refresh status
    
    # If this instance is Active
    if instance['status'] == site_control.DB_STATUS_ACTIVE:
      pass # Do nothing...  Monitoring happens separately.
    
    # If this instance is Repairing
    if instance['status'] == site_control.DB_STATUS_REPAIRING:
      #TODO(g): Add this later.
      #   This would call a Restore (BackupCreate).
      #   Who finds the problem state?  Monitoring?  Does this do something, or
      #     are other scripts handling it?  Still need to resolve this.
      pass#todo...
  


def main(args=None):
  Configure()


if __name__ == '__main__':
  main(sys.argv[1:])
  