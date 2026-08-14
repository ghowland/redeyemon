#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Configure: Database: Top Level configuration of ALL database kinds: Master config

These same steps must be applied to all databases.  This wraps those steps
so that we only need to implement specific database functionality, and it
can be wrapped in a repeatable framework, with unlimited configuration
possibilities inside the structure.  Yummy koolaid.
"""


import os
import sys

import config_util

# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def CreateDatabaseInstancesThatDontExist(db_id):
  # The instances we create, we return
  created_instances = {}
  
  database = site_control.GetDatabase(db_id)
  db_kind = site_control.GetDatabaseKind(database['kind'])
  
  # Get Database Instance requirements (how many of what type we need)
  instance_requirements = site_control.GetDatabaseInstanceRequirements(db_id)
  log('Database: %s  Instance Requirements: %s' % (database['name'], instance_requirements))
  
  # If we have to create instances
  if instance_requirements:
    # Process each instance kind separately, they are different kinds of
    #   instances for this one DB kind (such as Write Masters and Read Replicas)
    for (instance_kind_type_name, (instance_kind_id, instance_count)) in instance_requirements.items():
      log('Kind: %s  Count: %s' % (instance_kind_id, instance_count))
      instance_kind = site_control.GetDatabaseKindInstanceKind(instance_kind_id)
      
      log('Database %s: Requires %d instances of instance_kind: %s: %s' % \
          (database['name'], instance_count, db_kind['name'],
           instance_kind['name']))
      
      # Create the database instances
      for count in range(0, instance_count):
        # Add's the database instance, AND creates an initialized storage entry
        new_instance_id = site_control.AddDatabaseInstance(db_id, instance_kind_id)
        
        # Save the new instance
        created_instances[new_instance_id] = site_control.GetDatabaseInstance(new_instance_id)
  
  return created_instances


def HandleProvisioningForDbSetsForDbsThatNeedInstancesAndAssignTheirNewMachinesToDatabaseInstances(required_db_instances, site=site_control.SITE_DEFAULT):
  """Thats what she said.
  
  Handles all the provisioning for a pool where pool.db_set != NULL.
  
  Args:
    required_db_instances: dict, key is db.id(int), value is a dict, keyed on
        db_instance.id(int), with values as the db_instance field data.
  """
  # Create machines needed for the DB sets, not the individual DBs.  Align up
  #   the same kind of DBs on the same machines.  So Write Masters go together,
  #   and so do Read Replicas.  Use KIND_INSTANCE_KIND to segregate machines!
  for db_id in required_db_instances:
    # Get Database and Set data
    database = site_control.GetDatabase(db_id)
    db_set = site_control.GetDatabaseSet(database['set'])
    
    # Get all the pools controlled by this db_set.  We do them all, thats the
    #   way things are.  Pools are controlled by db_set, and since db_set could
    #   be assigned to more than one pool, then that pool is it's own version
    #   of db_set, and the databases will all be controlled the same way.
    #NOTE(g): That means having the same db_set on more than one pool should be
    #    a warning, but since the data is there, let's do it and complain.
    pools = site_control.GetPoolsControlledByDatabaseSet(database['set'])
    
    # All pools will need a machine for this db_set's required machines
    #   The obvious misconfiguration is here, but Im allowing it anyway.
    #   The GetPoolsControlledByDatabaseSet() sends a REM critical log message
    #   about this problem.
    for pool_id in pools:
      pool = site_control.GetPool(pool_id)
      
      # Loop through all the instances we need machines for
      for (instance_id, instance) in required_db_instances[db_id].items():
        # Get a machine in this pool that can be assigned to this DB Instance
        existing_usable_machine = site_control.GetPoolMachineAvailableForDatabaseInstance(pool_id, instance['id'])
        
        # If we found an existing machine, use it
        if existing_usable_machine:
          machine = existing_usable_machine
        
        # Else, we have to provision a new machine for this DB Instance
        else:
          #DEBUG: skip provisioning, just log it.  I dont want to test this now.
          if 1: ###### DEBUG ####
            log('DEBUG ::: : :Provision new machine for pool: %s' % pool_id)
            continue
          else:#DEBUG: Remove this indent, provisioning should happen here.
            # Provision a single machine, and return it's machine data
            machine = site_control.ProvisionSingleMachine(pool_id)
            
            # If we failed to provision
            if machine == None:
              log('Failed to provision machine for pool: %s  Database Instance: %s' % (pool_id, instance['id']), logging.CRITICAL)
              continue
        
        
        # Update the Instance with the new Machine
        instance['machine'] = machine['id']
        
        # Update the Instance status to Allocated
        instance['status'] = 2
        
        # Save the instance back into Site Control
        log('Assigning Database Instance %s: Machine: %s' % (instance['id'], machine['id']))
        site_control.UpdateData('db_instance', instance['id'], instance)
        
        # Update the instance's storage as well
        storage = site_control.GetStorage(instance['mount_storage'])
        storage['mount_machine'] = machine['id']
        site_control.UpdateData('storage', storage['id'], storage)



def Configure(site=site_control.SITE_DEFAULT):
  """Configure all db_set managed pools.  This is how databases work in REM.
  
  If you want databases, then you set them up in db, and you make a db_set,
  and put one or more dbs in it.  Then you make a pool and mark it's db_set,
  then that pool's machines are managed by this function wrapper.
  """
  # Keyed by db.id, this keeps track of how many of which kind_instance_kinds
  #   are needed.
  required_db_instances = {}
  
  # Get the databases
  dbs = site_control.GetDatabases()
  
  # Get all our machines
  machines = site_control.GetMachines(site=site)
  
  # Get DB instances
  for db_id in dbs:
    # Get all the instances for this db
    instances = site_control.GetDatabaseInstances(db_id)
    
    # Check that all their machines are there
    for (instance_id, instance) in instances.items():
      # If this instance is not in our machine list, or it is Decommissioned
      if instance['machine'] not in machines or machines[instance['machine']]['status'] == 7:
        # We need a new machine to handle this missing one, we are handling
        #   provisioning for our pool
        if db_id not in required_db_instances:
          required_db_instances[db_id] = {}
        
        # Store this instance as required for provisioning
        log('Existing: Instance requires provisioning: %s' % instance)
        required_db_instances[db_id][instance['id']] = instance
    
    # Create all the database instances that dont already exist
    new_instances = CreateDatabaseInstancesThatDontExist(db_id)
    
    # Add the newly created instances to the provisioning requirements
    for instance_id in new_instances:
      # We need a new machine to handle this missing one, we are handling
      #   provisioning for our pool
      if db_id not in required_db_instances:
        required_db_instances[db_id] = {}
      
      # Store this instance as required for provisioning
      log('New: Instance requires provisioning: %s' % instance_id)
      required_db_instances[db_id][instance_id] = new_instances[instance_id]
  
  # Provision any machines that need it
  #TODO(g): Implement this after I see the data is working.  I dont want to nuke
  #   my SCMaster test machine.
  if 1:
    #NOTE(g): This is the best description for a complex function Ive ever
    #   written.  Too bad it's horrible long and ugly.  Im leaving it for
    #   now because this is a complex topic and Im not going to break it up
    #   into a ton of functions so it has "good structure".  This whole storage
    #   thing is a major complexity at this point in the project and simple
    #   is best, and right now more structure is more complexity than longer
    #   functions and function names.  When things stabilize I expect this to
    #   change and grow larger into more robust code.  Test cases would be a
    #   good time to add this (test cases arent in now, because this is running
    #   against operational environment, until it WORKS test cases are going
    #   to make development unbarely slow, so holding off).
    HandleProvisioningForDbSetsForDbsThatNeedInstancesAndAssignTheirNewMachinesToDatabaseInstances(required_db_instances, site=site)
  else:
    #debug
    #TODO(g): Remove
    import pprint
    print 'Required Instances:'
    pprint.pprint(required_db_instances)
  
  #NOTE(g): After machines have been provisioned, the master is done.
  #   It will allocate them as normal, then when they start up, they will run
  #   config_db_local.py, which will configure their Database/Storage the rest
  #   of the way.
  return


def main(args=None):
  Configure()


if __name__ == '__main__':
  main(sys.argv[1:])

