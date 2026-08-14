#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Floating IPs
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def GetFloatingIps():
  """Returns a dict of floating_ip field data items, keyed on ip_address."""
  ips = {}

  sql = "SELECT * FROM floating_ip"
  result = Query(sql)

  for item in result:
    ips[item['ip_address']] = item

  return ips


def GetFloatingIpByIp(floating_ip):
  """Returns the data for one floating_ip address."""
  ips = GetFloatingIps()

  return ips[floating_ip]


def GetFloatingIpByName(name):
  """Returns a dict of floating_ip field data items, for the named Floating IP.
  
  Returns None if not found.
  """
  ips = {}

  sql = "SELECT * FROM floating_ip WHERE name = '%s'" % SanitizeSQL(name)
  result = Query(sql)

  if result:
    return result[0]
  else:
    return None
  


def GetFloatingIpCorrectMachineName(ip_data):
  """Gets the correct machine name to be on this floating_ip address.
  
  NOTE(g): Pass in IP data.  Getting it up from EC2 again is TOO SLOW!
  """
  # Get the IP address
  #ip_data = GetFloatingIpByIp(floating_ip)
  floating_ip = ip_data['ip_address']

  # Get the IP configuration script
  script_ip = ip_data['script_config']
  if script_ip:
    (exit_code, output) = run_script.RunScript(script_ip)
  else:
    log('No script found to configure Floating IP: %s' % \
        floating_ip, logging.ERROR)

  # The output is the correct machine name
  correct_machine_name = output

  return correct_machine_name


def ProvisionFloatingIps():
  log('ProvisionFloatingIps')

  # Get our floating ips
  floating_ips = GetFloatingIps()

  # Process our floating ips
  for floating_ip in floating_ips:
    ip = floating_ips[floating_ip]
    log('Processing: %s' % ip['name'])

    # Determine the correct machine for this floating_ip
    correct_machine_name = GetFloatingIpCorrectMachineName(ip).strip()

    log('Correct Machine: %s = %s' % (ip['name'], correct_machine_name))
    
    # Get the current floating machine assignment
    floating_ip_machine_name = rem_ec2.GetFloatingIpAssignment(floating_ip,
                                                               name=ip['name'])

    log('Current Machine: %s = %s' % (ip['name'], floating_ip_machine_name))
    
    # If this is not attached to the correct machine name, set it properly.
    #NOTE(g): correct_machine_name will be '' if one cant be found.  Test first.
    if correct_machine_name and floating_ip_machine_name != correct_machine_name:
      log('Setting Floating IP %s to machine: %s' % (floating_ip, correct_machine_name))
      rem_ec2.SetFloatingIpAssignment(floating_ip, correct_machine_name)
      
      # Update the floating_ip machine
      machine = site_control.GetMachineByName(correct_machine_name)
      sql = "UPDATE floating_ip SET machine = %d WHERE id = %d" % (machine['id'], ip['id'])
      Query(sql)
      
    elif correct_machine_name == '':
      log('No Active machines available for this Floating IP: %s' % floating_ip)

