#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
REM EC2 Commands
"""


import commands
import random
import os
import sys
import time

from rem_util import *

import run_script


# This is the bucket we put everything in.  Hard coded to the EC2 account
#TODO(g): Move into account details, still has to be hard coded here to include
#   for initial startup...
#
#   Put this into a YAML file that requires editting?  Yes, I like that.
#
S3_BUCKET = 'site_control_0'


# Script to get the local IP address
#TODO(g): This is not the best way to do this...  FIX
SCRIPT_GET_LOCAL_IP_INTERNAL='/usr/local/site_control/rem/rem_scripts/get_local_ip_internal'


def RunCommand(command):
  """Wrap this for maintenance."""
  (status, output) = commands.getstatusoutput(command)

  #log('EC2 Command (%s): %s\n%s' % (status, command, output))
  log('EC2 Command (%s): %s' % (status, command))

  return output


def RunCommandWithStatus(command):
  """Wrap this for maintenance."""
  (status, output) = commands.getstatusoutput(command)

  #log('EC2 Command (%s): %s\n%s' % (status, command, output))
  log('EC2 Command (%s): %s' % (status, command))

  return (status, output)


def OutputToDict(output, fields, key_field, delimiter='\t', default_dict=None):
  """Takes text output of a command, which have column based lines.

  Splits these lines and matches them with their field names in the fields
  dict (count:name), then keys each dict item on the key_field value
  """
  data = {}

  # Process all our instances (one per line)
  lines = output.split('\n')
  for line in lines:
    items = line.split('\t')

    instance_data = {}
    # Initialize the instance data with all the fields
    for key in fields:
      field = fields[key]
      instance_data[field] = None

    # If we have a default dictionary, start with it's data
    if default_dict:
      instance_data.update(default_dict)

    # Save fields by name for this instance's data
    for count in range(0, len(items)):
      if count in fields:
        instance_data[fields[count]] = items[count]

    data[instance_data[key_field]] = instance_data

  return data


def GetMachineName():
  """Returns this machine's EC2 instance name.  Returns None if not found."""
  instance = GetMachineInstance()

  # If we got it, return it
  if instance:
    #log('Name: %s' % instance['name'])
    return instance['name']

  # Else, we didnt find it, return None
  else:
    log('Couldnt find this machine', logging.ERROR)
    return None


def GetInstances(all=False):
  """Get the instances we have listed in EC2.
  
  Returns: Dict of instances on success, None on failure
  """
  #log('Get EC2 Instances.  Caller: %s' % stack.Mini(4))

  # Mapping of relevant field names to column order
  fields = {0:'ec2_reserve_type',
            1:'name',
            2:'ami',
            3:'dns_external',
            4:'dns_internal',
            5:'ec2_state',
            6:'ec2_security_group',
            7:'ami_launch_index',
            9:'machine_kind',
            10:'time_launch',
            11:'data_center',
            12:'ec2_product_code',
            15:'monitoring_status',
            16:'ip_external',
            17:'ip_internal'
  }

  # Run the command, get the output.  Dont show terminated instances
  if not all:
    cmd = 'ec2-describe-instances | grep -v terminated | grep -v shutting-down'
  else:
    cmd = 'ec2-describe-instances'
    
  # Run the script
  (status, output, output_error) = run_script.Run(cmd)
  
  log('ec2-describe-instance: %s: %s' % (status, str(output)[:20]))#DEBUG

  # If this command failed to run, then we cant act on it's data, return empty
  if status != 0:
    log('ec2-describe-instances failed: %s' % status, logging.ERROR)
    return None

  # Parse the output, using the fields, returns a dict keyed on the 'name' field
  data = OutputToDict(output, fields, 'name')

  # Purge non-instances from our data
  for item_key in data.keys():
    item = data[item_key]
    if data[item_key]['ec2_reserve_type'] != 'INSTANCE':
      #log('Deleting: %s' % data[item_key])
      del data[item_key]

  return data


def GetMachineInternalIp():
  """Gets this machine's internal IP address.

  Note: Uses shell script
  """
  # Get the local IP address.
  internal_ip = RunCommand(SCRIPT_GET_LOCAL_IP_INTERNAL)

  return internal_ip


CACHED_THIS_MACHINE_INSTANCE = None
CACHED_THIS_MACHINE_INSTANCE_LAST_UPDATE = 0
CACHED_THIS_MACHINE_INSTANCE_TIMEOUT = 30
def GetMachineInstance():
  """Returns the EC2 machine instance dict, for just this machine.  Or None.

  The dict is keyed on ip_internal, the value is a dict of Instance field data.
  """
  global CACHED_THIS_MACHINE_INSTANCE
  global CACHED_THIS_MACHINE_INSTANCE_LAST_UPDATE
  global CACHED_THIS_MACHINE_INSTANCE_TIMEOUT

  # If we have this cached
  if CACHED_THIS_MACHINE_INSTANCE:
    # Clear our cache if our last update has timed out
    if not (CACHED_THIS_MACHINE_INSTANCE_LAST_UPDATE + CACHED_THIS_MACHINE_INSTANCE_TIMEOUT > time.time()):
      #log('Cache cleared')
      CACHED_THIS_MACHINE_INSTANCE = None
      CACHED_THIS_MACHINE_INSTANCE_LAST_UPDATE = 0

    # Else, return the cached data
    else:
      #log('Cache returned: %s' % CACHED_THIS_MACHINE_INSTANCE)
      return CACHED_THIS_MACHINE_INSTANCE

  local_ip = GetMachineInternalIp()

  # Get all the instances
  instances = GetInstances()

  # No instances available
  if instances == None:
    log('No instances were found, so this machine could not be detected.  EC2 failure.', logging.ERROR)
    return None

  # Got through all the instances
  for name in instances:
    instance = instances[name]

    # If this machine matches in internal IP address, this is it
    if instance['ip_internal'] == local_ip:
      #log('Found: %s: %s' % (instance['name'], instance['ip_internal']))

      # Save the instance information, our machine isnt going anywhere.
      CACHED_THIS_MACHINE_INSTANCE = instance
      CACHED_THIS_MACHINE_INSTANCE_LAST_UPDATE = time.time()

      return instance

  # Couldnt find any...
  log('Not found: %s' % len(instances))
  return None


def ProvisionMachineInstances(ami, security_key, count, zone, instance_type):
  """Returns a dict of new machines, with their name as the key."""
  log('Provision machines: awi:%s seckey:%s count:%s zone:%s type:%s' % \
      (ami, security_key, count, zone, instance_type))

  # Mapping of relevant field names to column order
  fields = {0:'ec2_reserve_type',
            1:'name',
            2:'hardware_image',
            3:'ec2_state',
  }

  # Default data for our dictionary
  default_dict = {'name':None, 'zone':zone, 'instance_type':instance_type,
                  'hardware_image':ami, 'dns_public':None, 'dns_private':None}

  # Run the command, get the output
  cmd = 'ec2-run-instances %s -n %s -k %s -t %s -z %s' % \
        (ami, count, security_key, instance_type, zone)
  log('Command: %s' % cmd)
  output = RunCommand(cmd)
  log('Output: %s' % output)

  # If EC2 reports back this is a bad AMI
  if 'Client.InvalidAMIID.NotFound:' in output:
    log('The AMI was not found: %s' % ami, logging.CRITICAL)
    return {}

  # Parse the output, using the fields, returns a dict keyed on the 'name' field
  data = OutputToDict(output, fields, 'name', default_dict=default_dict)

  # Purge non-instances from our data
  for item_key in data.keys():
    item = data[item_key]
    if data[item_key]['ec2_reserve_type'] != 'INSTANCE':
      #log('Deleting: %s' % data[item_key])
      del data[item_key]

  return data


def DecommissionInstances(instance_names):
  """Decomissions a number of instances.   Takes a list of instance names."""
  log('Decommission instances: %s' % instance_names)

  # Mapping of relevant field names to column order
  fields = {0:'ec2_reserve_type',
            1:'name',
            2:'ec2_state_previous',
            3:'ec2_state_current',
  }

  # Run the command, get the output
  cmd = 'ec2-terminate-instances %s' % ' '.join(instance_names)
  output = RunCommand(cmd)


  # Parse the output, using the fields, returns a dict keyed on the 'name' field
  data = OutputToDict(output, fields, 'name')

  # Purge non-instances from our data
  for item_key in data.keys():
    item = data[item_key]
    if data[item_key]['ec2_reserve_type'] != 'INSTANCE':
      #log('Deleting: %s' % data[item_key])
      del data[item_key]

  #TODO(g): Test for immediate success with a machine state change in EC2

  return data


def _GetTempFileName():
  """Returns the name of a file that can be used for temporary writing."""
  #TODO(g): This needs to check and loop on found, and something needs to
  #   clean up old files, probably best to do it here too.
  name = '/tmp/rem_temp_%s' % random.randint(0, 10000)

  return name


def _RemoveTempFile(filename):
  """Removes the temp file."""
  os.unlink(filename)


def RunS3Command(command):
  """Wraps running an S3 command, because S3 is unreliable, we may be looping
  to try to recovery the data.
  """
  retries = 0
  MAX_RETRIES = 10

  #TODO(g): Put this someplace better.  Xplat later.
  S3_COMMAND = '/usr/bin/s3cmd --config=/root/.s3cfg'

  done = False
  while not done:
    (status, output) = RunCommandWithStatus('%s --force %s' % (S3_COMMAND, command))

    # If we are starting to see errors, start writing about it
    if retries > 0:
      log('RunS3Command: retries %s: %s: status %s: %s' % (retries, command, status, output))

    if status == 0:
      done = True

    if retries >= MAX_RETRIES:
      output = 'RunS3Command: Failed, maximum number of retry attempts(%s) exceeded:\n%s' % (MAX_RETRIES, output)
      done = True

    retries += 1

  return output


def S3Put(path, data, data_local_path=None):
  """The data is written to a temp data file, then stored in S3 at the path.
  The S3 bucket must already exist for this path.

  Args:
    path: str, the full path of the file in S3, but not in URL form.
          Example: /bucket/filename   Not: s3://bucket/filename
    data: binary data, will be stored as a binary object.  Ignored if using
      data_local_path.
    data_local_path: string or None(optional), if string this is the local
        absolute file path to the file to put in S3.
  """
  log('S3 Put: %s  (local=%s)' % (path, data_local_path))

  # If we are using our data to create a temp file and put it in S3
  if not data_local_path:
    # Write the data into a temp file
    filename = _GetTempFileName()
    f = open(filename, 'wb')
    f.write(data)
    f.close()
  
  # Else, the file already exists.  Put it in S3
  else:
    filename = data_local_path

  # Put this data into S3
  cmd = 'put %s %s' % (filename, path)
  RunS3Command(cmd)

  # Delete the temp file
  _RemoveTempFile(filename)


def S3Get(path, force=True, save_local_path=None):
  """The data is written to a temp data file, then stored in S3 at the path.
  The S3 bucket must already exist for this path.

  Args:
    path: str, the full path of the file in S3, but not in URL form.
          Example: /bucket/filename   Not: s3://bucket/filename
    force: boolean, default is True
    save_local_path: None or string, string is local path to store this data,
        so we dont have to save it manually if we want it on the local machine
  """
  log('S3 Get: %s  [%s: %s]' % (path, os.path.basename(sys.argv[0]), stack.Mini(3)))

  # Write the data into a temp file, if we're not saving it locally
  if not save_local_path:
    filename = _GetTempFileName()
  else:
    filename = save_local_path

  # Ensure path to filename exists (speed not an issue S3 is slow)
  try:
    os.makedirs(os.path.dirname(os.path.abspath(filename)))
  except OSError, e:
    pass # Expected, if the directory already exists

  # Put this data into S3
  if force:
    cmd = 'get --force %s %s' % (path, filename)
  else:
    cmd = 'get %s %s' % (path, filename)
  RunS3Command(cmd)

  # Read the data from the file
  data = open(filename).read()

  # Delete the temp file, if we're not saving it locally
  if not save_local_path:
    _RemoveTempFile(filename)

  return data


def S3Info(path):
  """Returns the time and size of the path file in a dict.  None if not found."""
  output = RunS3Command('ls %s' % path)
  
  # If it didnt find a file, return None
  if not output:
    return None
  
  # Get the timestamp and size
  (timestamp, size, _) = output.strip().split('  ', 2)
  data = {'time':timestamp, 'size':size, 'path':path}
  
  log('%s: %s: %s bytes' % (path, timestamp, size))
  
  return data


CACHED_MASTER_IP = None
CACHED_MASTER_IP_LAST_UPDATE = 0
CACHED_MASTER_IP_TIMEOUT = 30
def GetMasterIp(cache=True):
  """Gets the Master IP from S3."""
  #TODO(g): Put this someplaces better.  Note not URL, path.  Duplicate.
  S3_MASTER_IP = 's3://%s/master.ip' % S3_BUCKET

  global CACHED_MASTER_IP
  global CACHED_MASTER_IP_LAST_UPDATE
  global CACHED_MASTER_IP_TIMEOUT

  # If we have this cached, and we want cached data
  if cache and CACHED_MASTER_IP:
    # Clear our cache if our last update has timed out
    if not (CACHED_MASTER_IP_LAST_UPDATE + CACHED_MASTER_IP_TIMEOUT > time.time()):
      #log('Cache cleared')
      CACHED_MASTER_IP = None
      CACHED_MASTER_IP_LAST_UPDATE = 0

    # Else, return the cached data
    else:
      log('Cache returned: %s' % CACHED_MASTER_IP)
      return CACHED_MASTER_IP

  # Get the Master IP
  master_ip = S3Get(S3_MASTER_IP).strip()
  
  # Save it in Cache
  CACHED_MASTER_IP = master_ip

  return master_ip


def IsThisMachineMaster():
  """Returns boolean, if this machine is the Site Control Master."""
  local_ip = GetMachineInternalIp()
  master_ip = GetMasterIp()

  return local_ip == master_ip


def GetFloatingIpAssignment(floating_ip, name=None):
  """Get the instance that has this Elastic IP.

  Returns: str or None. str=success, machine_name.  None=fail, not found or not
      set
  """
  if name:
    log('Get Floating IP: %s: %s' % (floating_ip, name))
  else:
    log('Get Floating IP: %s' % floating_ip)

  cmd = '/opt/ec2-tools/ec2-tools/bin/ec2-describe-addresses'
  output = RunCommand(cmd)
  fields = {0:'type', 1:'ip', 2:'machine_name'}
  data = OutputToDict(output, fields, 'ip')

  # If the floating_ip wasnt found
  if floating_ip not in data:
    #TODO(g): How to differentiate between not found and not set?
    return None

  # Else, return the name
  else:
    return data[floating_ip]['machine_name']


def SetFloatingIpAssignment(floating_ip, instance_name):
  """Set the Elastic IP.  Returns boolean for success."""
  log('Set Floating IP: %s -> %s' % (floating_ip, instance_name))

  # Set it
  cmd = '/opt/ec2-tools/ec2-tools/bin/ec2-associate-address -i %s %s' % \
        (instance_name, floating_ip)
  log('Set Floating IP: %s' % cmd)
  os.system(cmd)

  # Test it
  new_floating_ip_instance_name = GetFloatingIpAssignment(floating_ip)

  # Succeeded?
  if new_floating_ip_instance_name == instance_name:
    return True
  else:
    return False


def GetLoadBalancerInstances(name):
  """Returns a dict of instances attached to this named load balancer.
  
  Keyed on instance name, with service information as value.
  """
  instances = {}
  
  # Get the data from EC2
  cmd = 'elb-describe-instance-health %s' % name
  output = RunCommand(cmd)
  
  # Parse the data
  lines = output.split('\n')
  
  for line in lines:
    line = line.strip()
    
    if line:
      # Collapse double spaces
      while '  ' in line:
        line = line.replace('  ', ' ')
      
      # Get cols
      try:
        (item_type, instance, status) = line.split(' ')
      except ValueError, e:
        continue # Bad line
      
      # Save in dict, if this is an instance
      if item_type == 'INSTANCE-ID':
        instances[instance] = status
      else:
        log('Unknown ELB item type: %s' % line, logging.ALERT)
  
  return instances


def _RemoveLoadBalancerInstances(name, instance_list):
  """Internal: Use SetLoadBalancerIntstances() to manage instances.
  
  This removes specific instances to the Load Balancer.
  """
  if not instance_list:
    log('No instances to add... (%s)' % name)
  else:
    log('Removing from Load Balancer: %s: %s' % (name, instance_list))
  
  # Create the instances string
  instances = ','.join(instance_list)
  
  # Call the command
  cmd = 'elb-deregister-instances-from-lb %s --instances %s' % (name, instances)
  result = RunCommand(cmd)
  log('Result: %s' % result)


def _AddLoadBalancerInstances(name, instance_list):
  """Internal: Use SetLoadBalancerIntstances() to manage instances.
  
  This adds specific instances to the Load Balancer.
  """
  if not instance_list:
    log('No instances to add... (%s)' % name)
  else:
    log('Adding to Load Balancer: %s: %s' % (name, instance_list))
  
  
  # Create the instances string
  instances = ','.join(instance_list)
  
  # Call the command
  cmd = 'elb-register-instances-with-lb %s --instances %s' % (name, instances)
  result = RunCommand(cmd)
  #log('Result: %s' % result)


def SetLoadBalancerInstances(name, instance_list):
  """Enforces that a list of instance names is set on this named load balancer.
  
  Will add or remove names, depending on what is currently in the list.
  """
  # Get all the instances currently on the list
  current_instances = GetLoadBalancerInstances(name).keys()
  
  # Remove these instances
  remove_instances = []
  
  # Mark all instances in current, but not in instance list to be removed
  for instance in current_instances:
    if instance not in instance_list:
      remove_instances.append(instance)
  
  # Remove all the instances
  if remove_instances:
    _RemoveLoadBalancerInstances(name, remove_instances)
  
  # Mark the instances in our list that are not in current to be added
  add_instances = []
  for instance in instance_list:
    if instance not in current_instances:
      add_instances.append(instance)
  
  # Add all the instances
  if add_instances:
    _AddLoadBalancerInstances(name, add_instances)
  
  # Get all the instances, AGAIN, as we've changed things
  current_instances = GetLoadBalancerInstances(name)
  
  # If any instances are marked as OutOfService, or not InService, force
  #   them back into service.  This is EC2 saving resources by immediately
  #   pulling machines from service on 503.
  for (instance, status) in current_instances.items():
    # Redundantly stating our cases, just to document them, first will always hit
    if status != 'InService' or status == 'OutOfService':
      SetLoadBalanceInstanceInService(name, instance)


def SetLoadBalanceInstanceInService(name, instance):
  """Set this load balancer instance to InService.
  
  NOTE(g): ELB doesnt have a way to do this.  Im just removing the entry and
      re-adding it.  To get ELB not to do this, better health checks must be
      configured.
  
  TODO(g): Set up better automatic health checks so that this isnt necessary.
  """
  log('ELB %s: Force ELB to list instance %s as InService' % (name, instance))
  _RemoveLoadBalancerInstances(name, [instance])
  _AddLoadBalancerInstances(name, [instance])
  


def GetVolumes():
  """Returns EBS volumes."""
  volumes = {}
  
  # Get the data from EC2
  #TODO(g): Remove full path hard code.  It failed default path for some reason
  cmd = '/opt/ec2-tools/ec2-tools/bin/ec2-describe-volumes'
  output = RunCommand(cmd)
  
  # Parse the data
  lines = output.split('\n')
  
  for line in lines:
    line = line.strip()
    
    if line:
      # Collapse double spaces
      while '  ' in line:
        line = line.replace('  ', ' ')
      
      # Get cols
      try:
        cols = line.split(' ')
        item_type = cols[0]
      except ValueError, e:
        continue # Bad line
      
      # Save in dict, if this is a volume
      if item_type == 'VOLUME':
        (_, volume_id, size_gb, zone, status, creation_time) = cols
        
        # Create the volume entry and populate it
        volumes[volume_id] = {}
        volumes[volume_id]['size_gb'] = size_gb
        volumes[volume_id]['zone'] = zone
        volumes[volume_id]['status'] = status
        volumes[volume_id]['create_time'] = creation_time
        
        # Set this, just so if it's not attached we know this field exists
        volumes[volume_id]['machine'] = None
      
      # Else, if this is an attachment statement (about a Volume)
      elif item_type == 'ATTACHMENT':
        (_, volume_id, machine, device_path, status, creation_time) = cols
        
        if volume_id in volumes:
          # Save our attachement data
          volumes[volume_id]['machine'] = machine
          volumes[volume_id]['device_path'] = device_path
          volumes[volume_id]['attachment_status'] = status
          volumes[volume_id]['attachment_create_time'] = status
        
        else:
          log('Attachment found WITHOUT a volume.  Bad data: %s\n\n%s' % (line, lines), logging.CRITICAL)
      
      else:
        log('Unknown Volume result line type: %s' % line, logging.ALERT)
  
  return volumes


def DeleteVolume(volume_id):
  """Delete this EBS volume."""
  #TODO(g): Remove full path hard code.  It failed default path for some reason
  log('Deleting volume: %s' % volume_id)
  cmd = '/opt/ec2-tools/ec2-tools/bin/ec2-delete-volume %s' % volume_id
  RunCommand(cmd)


def AttachVolume(volume_id, machine, device=None):
  """Attach an EBS volume to a machine."""
  log('Attaching Volume %s to Machine at %s: %s' % (volume_id, machine, device))
  if device:
    cmd = 'ec2-attach-volume %s --instance %s --device %s' % \
          (volume_id, machine, device)
  else:
    cmd = 'ec2-attach-volume %s --instance %s' % (volume_id, machine)
  
  # Attach the EBS volume to a machine
  output = RunCommand(cmd)
  log('\n'+output)


def DetachVolume(volume_id, force=False):
  """Attach an EBS volume to a machine."""
  log('Detaching volume %s' % volume_id)
  if not force:
    cmd = 'ec2-detach-volume %s' % volume_id
  else:
    cmd = 'ec2-detach-volume %s --force' % volume_id
  
  # Detach the EBS volume
  output = RunCommand(cmd)
  log('\n'+output)
  

def CreateVolume(size_gb, zone, machine=None, machine_device=None, from_snapshot=None):
  """Create an EBS volume. Returns an EBS volume dict.
  
  Fields in volume dict: volume_id, size_gb, zone, status, create_time
  """
  log('Create volume: %s %s %s %s %s' % (size_gb, zone, machine, machine_device, from_snapshot))
  
  if not from_snapshot:
    #TODO(g): Remove full path hard code.  It failed default path for some reason
    cmd = '/opt/ec2-tools/ec2-tools/bin/ec2-create-volume --size %d --availability-zone %s' % (size_gb, zone)
  else:
    #TODO(g): Remove full path hard code.  It failed default path for some reason
    cmd = '/opt/ec2-tools/ec2-tools/bin/ec2-create-volume --size %d --availability-zone %s --snapshot %s' % \
          (size_gb, zone, snapshot)
  
  # Request the EBS volume
  (status, output, output_error) = run_script.Run(cmd)
  
  log('\nCommand: %s \n%s' % (cmd, output))
  
  # If the command succeeded
  if status == 0:
    # Parse the data
    lines = output.split('\n')
    if lines:
      line = lines[0]
      
      # Collapse double spaces
      while '  ' in line:
        line = line.replace('  ', ' ')
      
      #Cols:
      #VOLUME  vol-4ee51f27    50              us-east-1d      creating        2009-12-10T07:46:05+0000
      
      # Get cols
      try:
        cols = line.replace('\t', ' ').split(' ')
        item_type = cols[0]
      except ValueError, e:
        log('No output.  Failure: %s' % output, logging.ALERT)
        return None
      
      # Set up the volume data
      volume = {'volume_id':cols[1], 'size_gb':cols[2], 'zone':cols[3],
                'status':cols[4], 'create_time':cols[5]}
      
      # If we have a machine, try to attach it now
      #if machine and machine_device:
      if machine:
        AttachVolume(volume['volume_id'], machine, machine_device)
      #TODO(g): Implement standards at REM.
      #elif machine:
      #  log('machine AND machine_device must be set.  We have standards at REM, and letting EC2 set our device names is not part of them.', logging.CRITICAL)
      
      # Return our machine info
      return volume
    
    # Else, the command fails, because theres no output
    else:
      log('Command failed: No output', logging.ERROR)
  
  # Else, the command fails
  else:
    log('Command failed: %s' % output, logging.ERROR)
    return None


def SnapshotVolume(volume_id, text):
  """Snapshot the EC2 volume specified by it's EC2 volume_id and text description.
  
  Returns: boolean, success
  """
  log('Snapshot Volume: %s %s' % (volume_id, text))
  
  #TODO(g): Remove full path hard code.  It failed default path for some reason
  cmd = '/opt/ec2-tools/ec2-tools/bin/ec2-create-snapshot %s -d "%s"' % \
        (volume_id, text[:255]) # Description max length=255
  
  # Request the EBS volume
  (status, output, output_error) = run_script.Run(cmd)
  
  log('\nCommand: %s \n%s' % (cmd, output))
  
  # If the command succeeded
  if status == 0:
    return True
  else:
    return False


if __name__ == '__main__':
  local_ip = GetMachineInternalIp()
  print 'Local IP: %s' % local_ip

  instance = GetMachineInstance()
  print 'Instance: %s' % instance
