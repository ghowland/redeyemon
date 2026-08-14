#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Services
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def GetServices():
  """Returns a dict keyed on service.name with the service field data as value."""
  services = {}

  sql = "SELECT * FROM service"
  result = Query(sql)

  for item in result:
    services[item['name']] = item

  return services


def GetService(service_id):
  """Returns service.id's field data in dict."""
  sql = "SELECT * FROM service WHERE id = %d" % service_id
  item = Query(sql)[0]

  return item


def GetServiceByName(name):
  """Returns service.id's field data in dict, or None if not found."""
  sql = "SELECT * FROM service WHERE name = '%s'" % SanitizeSQL(name)
  result = Query(sql)

  if result:
    return result[0]
  else:
    return None


def GetServiceStateAll(service_id):
  """Returns a dict of all the state variables and their values."""
  state = {}
  
  sql = "SELECT * FROM service_state WHERE service = %d" % service_id
  result = Query(sql)
  
  for item in result:
    state[item['name']] = item['value']
  
  return state


def GetServiceScript(service_script_id):
  sql = "SELECT * FROM service_script WHERE id = %d" % service_script_id
  item = Query(sql)[0]

  return item


def SetServiceConfigField(service_id, field, value):
  """Sets Service Config field with a value."""
  sql = "SELECT * FROM service_config WHERE service = %d AND name = '%s'" % (service_id, SanitizeSQL(field))
  result = Query(sql)

  # If this is a new site_config field
  if not result:
    msg = 'Creating new service (%s) config field: %s = %s' % (service_id, field, value)
    log(msg, level=logging.LEVEL_WARN)
    sql = "INSERT INTO service_config (service, name, value, updated) VALUES (%d, '%s', '%s', NOW())" %\
          (service_id, SanitizeSQL(field), SanitizeSQL(value))
    result = Query()

  # Else, update the existing field's value
  else:
    log('Updated service (%s) config field: %s = %s' % (service, field, value))
    sql = "UPDATE service_config SET value = '%s', updated = NOW() WHERE id = %s" %\
          (SanitizeSQL(value), result[0]['id'])
    Query(sql)


def GetServiceConfigField(service_id, field):
  """Returns the value of the Site's config field."""
  sql = "SELECT * FROM service_config WHERE site = %d AND name = '%s'" % \
        (service_id, SanitizeSQL(field))
  result = Query(sql)

  # Return None of the value
  if not result:
    return None
  else:
    return result[0]['value']


def GetServiceConfig(service_id):
  """Returns all the configuration information for this service in a single dict."""
  data = {}

  # All value_ordering is handled by the SELECT query, dont bother trying
  #   to make it better after this, either the admin filled out this value_order
  #   per config field name correctly, or not.  If order matters, theyll fix it.
  sql = "SELECT * FROM service_config WHERE service = %d ORDER BY name, value_order" % service_id
  result = Query(sql)

  for item in result:
    # If this is a new field, add it's value as a single attribute
    if item['name'] not in data:
      # If value_order wasnt specified, its a value
      if item['value_order'] == None:
        data[item['name']] = item['value']
      
      # Else, we have value_order, so its a list
      else:
        data[item['name']] = list(item['value'])
    
    # Else, this field name already exists, so it is a list.  Convert if it's
    #   single, then append the value to the list.  Ordering is already complete
    else:
      # If the value is not already a list, turn it into one
      #TODO(g): Redundant?  Remove?  I added the value_order test.  Could it
      #   happen otherwise?  Should it?
      if type(data[item['name']]) != list:
        data[item['name']] = list(data[item['name']])
      
      # Append the new value
      data[item['name']].append(item['value'])

  return data


def GetServiceRequiredServices(service_id, depth=0):
  services = []

  # Limit recursion to maximum of 5
  if depth >= 5:
    return services

  # Get required services
  sql = "SELECT * FROM service_required_service WHERE parent = %d" % service_id
  result = Query(sql)

  for item in result:
    add_service = item['service']

    # Add the service to our required services
    if add_service not in services:
      services.append(add_service)

      # Get recursive services, is depth limited to 5
      services += GetServiceRequiredServices(add_service, depth=depth+1)

  return services



def GetServiceScripts(service_id):
  """Returns a dict of all of scripts that run for this service.

  Returns: dict, key=script.id, value=list of ints, service_script.id
  """
  scripts = {}

  sql = "SELECT * FROM service_script WHERE service = %d" % service_id
  result = Query(sql)

  for item in result:
    script_id = item['script']

    # Add the script_id to the scripts dict, if it doesnt exist
    if script_id not in scripts:
      scripts[script_id] = []

    # Add the service_script.id to the script_id list, so we know which
    #   instances of this script need to be run (timing information, these
    #   are what are actually called, the script is the root data)
    scripts[script_id].append(item['id'])

    #log('GetServiceScripts: service %s: script %s: service_script %s' % (service_id, script_id, item['id']))

  return scripts


def GetServiceRrds(service_id):
  """Gets all the RRDs required by this service."""
  rrds = []

  sql = "SELECT * FROM service_rrd WHERE service = %d" % service_id
  result = Query(sql)

  for item in result:
    rrds.append(item['rrd'])

  return rrds


def GetRrdsByServiceList(service_list):
  """Returns a list of all the rrd.ids for all the service.ids in the list.

  Returns: List of ints, rrd.ids
  """
  rrds = []

  # Get all the rrds for all the services in our list
  for service_id in service_list:
    service_rrds = GetServiceRrds(service_id)

    # Add all the rrds we dont already have
    for rrd_id in service_rrds:
      if rrd_id not in rrds:
        rrds.append(rrd_id)

  return rrds


def GetServicePools(service_id):
  """Returns a list of all the Pools that use this service."""
  pools = []
  
  sql = "SELECT * FROM pool_service WHERE service = %d" % service_id
  result = Query(sql)
  
  # Add all the pools, uniquely
  for item in result:
    if item['pool'] not in pools:
      pools.append(item['pool'])
  
  return pools


def GetServiceMachines(service_id):
  """Returns a list of all the Machines that use this service."""
  machines = []
  
  # Get all the pools we are used in
  pools = GetServicePools(service_id)
  
  # Get all the machines in these pools, and add them to our machine list
  for pool_id in pools:
    # Get all the machines
    pool_machines = site_control.GetPoolMachineList(pool_id, status=None)
    
    for machine_id in pool_machines:
      if machine_id not in machines:
        machines.append(machine_id)
  
  return machines


