#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Sites
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def GetSites():
  """Returns a dict of sites, keyed by their name, with their field data is
  values.
  """
  sql = "SELECT * FROM site ORDER BY name"
  result = Query(sql)

  sites = {}

  for item in result:
    sites[item['name']] = item

  return sites


def GetSite(site_id):
  return GetSiteById(site_id)


def GetSiteByName(name):
  sites = GetSites()
  return sites[name]


def GetSiteById(site_id):
  sql = "SELECT * FROM site ORDER BY id = %d" % site_id
  site_data = Query(sql)[0]

  return site_data


def GetSiteDataCenterFromRawDataCenterName(data_center_name, site=site_control.SITE_DEFAULT):
  """Returns this site's data center for the specified raw data center name.

  Example: EC2 uses us-east-1a and us-east-1b.  So I map us-east-1a to
  machine_data_center.id=1 and us-east-1b to machine_data_center.id=2.

  Then the site_data_center maps these to an order, so that if
  (site_data_center.id=1)=1 and (site_data_center.id=2)=2, then the Primary
  data center (s_d_c=1) is us-east-1a and the Secondary data center (s_d_c=2)
  is us-east-1b.

  This allows us to have a permanently ordered list (machine_data_center)
  which we can add EC2, and later other cloud vendor, data centers to, and
  then an order in which to use those data centers for the site.

  Then pools created by the site_data_center, so that the same service can
  run in two different data centers with two different size goals.

  Example: The Database pool has 2 machines in the Primary data center, and
      1 machine in the Secondar data center, as a disaster recovery machine.


  Returns: None on failure.  int on success, site_data_center.id
  """
  # Get this machine data center's data
  #NOTE(g): Order by ID just to constrain a problem where someone double inputs
  #   data, Id rather not fail on that here by flip-flopping between them ever.
  sql = "SELECT * FROM machine_data_center WHERE name = '%s' ORDER BY ID" % SanitizeSQL(data_center_name)
  result = Query(sql)

  # If we dont have a machine, return None as failure
  if not result:
    log('No data center: %s' % data_center_name)
    return None

  # Get the site data center from this
  sql = "SELECT * FROM site_data_center WHERE site = %d AND machine_data_center = %d" % (site, result[0]['id'])
  result = Query(sql)

  # If we couldnt find this data center
  if not result:
    log('Found data center %s(%s), but couldnt find site_data_center match.' % data_center_name)
    return None

  # Return the site_data_center.id
  return result[0]['id']


def GetSiteByMachine(machine_id):
  """What site are we connected to?  If this machine doesnt exist, return None"""
  machine = site_control.GetMachine(machine_id)

  if machine:
    return machine['site']
  else:
    log('Machine doesnt exist: %s' % machine_id)
    return None


def GetSiteConfig(site=site_control.SITE_DEFAULT):
  """Returns all the configuration information for this site in a single dict."""
  data = {}

  # All value_ordering is handled by the SELECT query, dont bother trying
  #   to make it better after this, either the admin filled out this value_order
  #   per config field name correctly, or not.  If order matters, theyll fix it.
  sql = "SELECT * FROM site_config WHERE site = %d ORDER BY name, value_order" % site
  result = Query(sql)

  for item in result:
    # If this is a new field, add it's value as a single attribute
    if item['name'] not in data:
      data[item['name']] = item['value']

    # Else, this field name already exists, so it is a list.  Convert if it's
    #   single, then append the value to the list.  Ordering is already complete
    else:
      # If the value is not already a list, turn it into one
      if type(data[item['name']]) != list:
        data[item['name']] = list(data[item['name']])

      # Append the new value
      data[item['name']].append(item['value'])

  # Always save the site information, so it's easily accessable
  data['_site'] = site

  return data


def GetSiteConfigField(site, field):
  """Returns the value of the Site's config field."""
  sql = "SELECT * FROM site_config WHERE site = %d AND name = '%s'" % \
        (site, SanitizeSQL(field))
  result = Query(sql)

  # Return None of the value
  if not result:
    return None
  else:
    return result[0]['value']


def GetSiteDataCenterByName(name):
  """Return the site_data_center field data for the data center with this name.
  
  Returns None on failure, int on success.
  """
  sql = "SELECT * FROM machine_data_center WHERE name = '%s'" % SanitizeSQL(name)
  result = Query(sql)
  
  if result:
    machine_data_center = result[0]
    
    sql = "SELECT * FROM site_data_center WHERE machine_data_center"
    result = Query(sql)
    
    if result:
      return result[0]
  
  # Fail. Couldnt find anything
  return None


def SetSiteConfigField(site, field, value):
  """Sets Site Config field with a value.  Site must be specified, no defaults."""
  sql = "SELECT * FROM site_config WHERE site = %d AND name = '%s'" % (site, SanitizeSQL(field))
  result = Query(sql)

  # If this is a new site_config field
  if not result:
    msg = 'Creating new site (%s) config field: %s = %s' % (site, field, value)
    log(msg, level=logging.LEVEL_WARN)
    sql = "INSERT INTO site_config (site, name, value, updated) VALUES (%d, '%s', '%s', NOW())" %\
          (site, SanitizeSQL(field), SanitizeSQL(value))
    result = Query()

  # Else, update the existing field's value
  else:
    log('Updated site (%s) config field: %s = %s' % (site, field, value))
    sql = "UPDATE site_config SET value = '%s', updated = NOW() WHERE id = %s" %\
          (SanitizeSQL(value), result[0]['id'])
    Query(sql)


def GetMachineDataCenterFromSiteDataCenter(site_data_center_id):
  """Returns the machine_data_center field data, or None if not found."""
  sql = "SELECT * FROM site_data_center WHERE id = %d" % site_data_center_id
  result = Query(sql)
  
  if result:
    sql = "SELECT * FROM machine_data_center WHERE id = %d" % result[0]['machine_data_center']
    result = Query(sql)
    
    # Return the machine_data_center field data
    if result:
      return result[0]
  
  return None


