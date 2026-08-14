#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Web: Render the Site Control data: Database

rem_api.web_render.py is the main module.  Because there are so many methods
per data group they are being seperated into seperate modules.
"""


import os


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *

# Special web_render_* imports from web_render
from web_render import GetWebRenderTemplate
from web_render import _RenderHeader


def WebRender_Database(database_id):
  """Render this database from it's RpcGetDatabase() data."""
  # Get our base rendering data
  database = site_control.RpcGetDatabase(database_id)
  if not database:
    msg = 'Database not found: %s' % database_id
    log(msg)
    return msg
  
  # Make our own data, to match to the template
  data = dict(database)
  
  # Add Instances
  data['instance_info'] = ''
  if data['instances']:
    instances = list(data['instances'])
    instances.sort() # Ensure they are always in the same order
    for instance_id in instances:
      if instance_id == instances[0]:
        data['instance_info'] += site_control.WebRender_DatabaseInstance_Line(instance_id, print_header=True)
      else:
        data['instance_info'] += site_control.WebRender_DatabaseInstance_Line(instance_id)
  
  # Get the template
  template = GetWebRenderTemplate('render/database.txt')
  
  # Format the template, non-destructively.  (Keep unused format strings and %s)
  output = site_control.WebTemplateFormat(template, data)
  
  return output


def WebRender_Database_Line(db_id, table_row=True, print_header=False):
  """Render Database information, in a single line format.
  
  Line rendering functions should have the table_row/print_header args so that
  we can standardize on this.
  
  The first call to this should print the header if you want the header
  automatically produced.
  """
   # Get our base rendering data
  database = site_control.RpcGetDatabase(db_id)
  
  if not database:
    msg = 'Database not found: %s' % db_id
    log(msg)
    return msg
  
  # Make our own data, to match to the template
  data = dict(database)
  
  # Get the template
  template = GetWebRenderTemplate('render/database_line.txt')
  
  # Create a row instances status images
  data['instance_statuses'] = ''
  
  # Do the Write instances first
  for instance_id in data['instances_write']:
    # Add the instance status
    data['instance_statuses'] += '%s ' % WebRender_DatabaseInstance_Status(instance_id)
  
  # Do the Read instances next
  for instance_id in data['instances_read']:
    # Add the instance status
    data['instance_statuses'] += '%s ' % WebRender_DatabaseInstance_Status(instance_id)
  
  # Format the template, non-destructively.  (Keep unused format strings and %s)
  output = site_control.WebTemplateFormat(template, data)
  
  # If we want to print the header too
  if print_header:
    # Create custom header data for this template
    header_data = {'name':'Databases', 'id':'', 'info':'Info', 'kind_name':'Type',
                   'replica_goal':'Replicas', 'storage_size_gb':'Size GB',
                   'instance_statuses':'Instances', 'status_image':''}
    
    # Render the header
    header = _RenderHeader(template, header_data)
    
    # Append the header
    output = header + output
    
  
  return output


def WebRender_Database_Status(db_id):
  """Render just a status item (16x16 image, can have popup) for this item."""
  output = ''
  
  # Get the RPC synthesized data, without status (cause thats us, loop)
  database = site_control.RpcGetDatabase(db_id, render_status=False)
  
  if not database:
    log('Database not found: %s' % db_id)
    return '<img src="/static/images/candle.png" title="Not Found">'
  
  # Get our DB instances (easier label)
  instances = database['instances']
  
  # Get how many active instances we have
  active_instances = site_control.GetDatabaseInstances(db_id, status=7)
  
  # Get how many active instances we have
  repairing_instances = site_control.GetDatabaseInstances(db_id, status=8)
  
  # If we have no instances: Red
  if len(instances) == 0:
    output += '<a href="database?id=%(id)s"><img src="/static/images/led_red.png" border=0 title="No Instances"></a>' % database
  
  # Else, if some of our instances are being repaired: Red
  elif repairing_instances:
    output += '<a href="database?id=%(id)s"><img src="/static/images/led_red.png" border=0 title="Repairing Instances"></a>' % database
  
  # Else, if all our instances are Active: Green
  elif len(instances) == active_instances:
    output += '<a href="database?id=%(id)s"><img src="/static/images/led_green.png" border=0 title="No Instances"></a>' % database
  
  # Else, some of our instances are being configured: Yellow
  else:
    output += '<a href="database?id=%(id)s"><img src="/static/images/led_yellow.png" border=0 title="Configuring Instance(s)"></a>' % database
  
  return output


def WebRender_DatabaseInstance(instance_id):
  """Render this database instance from it's RpcGetDatabaseInstance() data."""
  # Get our base rendering data
  instance = site_control.RpcGetDatabaseInstance(instance_id)
  if not instance:
    msg = 'Database Instance not found: %s' % instance_id
    log(msg)
    return msg
  
  # Make our own data, to match to the template
  data = dict(instance)
  
  # Get the template
  template = GetWebRenderTemplate('render/database_instance.txt')
  
  # Format the template, non-destructively.  (Keep unused format strings and %s)
  output = site_control.WebTemplateFormat(template, data)
  
  return output


def WebRender_DatabaseInstance_Line(instance_id, table_row=True, print_header=False):
  """Render this instance from it's RpcGetDatabaseInstance() data, on a single line."""
  # Get our base rendering data
  instance = site_control.RpcGetDatabaseInstance(instance_id)
  
  if not instance:
    msg = 'Database Instance not found: %s' % instance_id
    log(msg)
    return msg
  
  # Make our own data, to match to the template
  data = dict(instance)
  
  # Get the template
  template = GetWebRenderTemplate('render/database_instance_line.txt')
  
  # Format the template, non-destructively.  (Keep unused format strings and %s)
  output = site_control.WebTemplateFormat(template, data)
  
  # If we want to print the header too
  if print_header:
    # Create custom header data for this template
    header_data = {'db_name':'Database', 'id':'', 'machine_name':'Machine',
                   'status_image':'', 'mount_storage':'',
                   'mount_storage_name':'Storage', 'status_name':'Status'
                   }
    
    # Render the header
    header = _RenderHeader(template, header_data)
    
    # Append the header
    output = header + output
  
  return output


def WebRender_DatabaseInstance_Status(instance_id):
  """Render just a status item (16x16 image, can have popup) for this item."""
  output = ''
  
  # Get the RPC synthesized data, without status (cause thats us, loop)
  instance = site_control.RpcGetDatabaseInstance(instance_id, render_status=False)
  
  if not instance:
    log('Database Instance not found: %s' % instance_id)
    return '<img src="/static/images/candle.png" title="Not Found">'
  
  # If this Instance is Active: Green
  if instance['status'] == 7:
    output += '<a href="database_instance?id=%(id)s"><img src="/static/images/led_green.png" border=0 title="%(status_name)s"></a>' % instance
  
  # Else, if this Instance is in configuration: Yellow
  elif instance['status'] in (2, 3, 4, 5, 6):
    output += '<a href="database_instance?id=%(id)s"><img src="/static/images/led_yellow.png" border=0 title="%(status_name)s"></a>' % instance
  
  # Else, if this Instance is in requested: White
  elif instance['status'] == 1:
    output += '<a href="database_instance?id=%(id)s"><img src="/static/images/led_white.png" border=0 title="%(status_name)s"></a>' % instance
  
  # Else, if this Instance is in repairs: Red
  elif instance['status'] == 8:
    output += '<a href="database_instance?id=%(id)s"><img src="/static/images/led_red.png" border=0 title="%(status_name)s"></a>' % instance
  
  # Else, WTF is this?  Blue
  else:
    log('Unhandled status: %s' % instance['status'])
    output += '<a href="database_instance?id=%(id)s"><img src="/static/images/led_blue.png" border=0 title="%(status_name)s"></a>' % instance
  
  return output


def WebRender_DatabaseSet(db_set_id):
  """Render this database db_set from it's RpcGetDatabaseSet() data."""
  # Get our base rendering data
  db_set = site_control.RpcGetDatabaseSet(db_set_id)
  if not db_set:
    msg = 'Database Set not found: %s' % db_set_id
    log(msg)
    return msg
  
  # Make our own data, to match to the template
  data = dict(db_set)
  
  # Get the template
  template = GetWebRenderTemplate('render/database_set.txt')
  
  # Add Pool info
  if data['pools']:
    data['pool_info'] = ''
    pools = data['pools']
    pools.sort() # Ensure the pools are always in the same order
    for pool_id in pools:
      pool = site_control.GetPool(pool_id)
      if pool_id == pools[0]:
        data['pool_info'] += site_control.WebRender_Pool_Line(pool_id, print_header=True)
      else:
        data['pool_info'] += site_control.WebRender_Pool_Line(pool_id)
  else:
    data['pool_info'] = 'This Database Set has no pools that it controls.  It is inert.'
  
  # Add Database info
  if data['databases']:
    data['database_info'] = ''
    databases = data['databases']
    databases.sort() # Ensure the pools are always in the same order
    for database_id in databases:
      if database_id == databases[0]:
        data['database_info'] += site_control.WebRender_Database_Line(database_id, print_header=True)
      else:
        data['database_info'] += site_control.WebRender_Database_Line(database_id)
  else:
    data['database_info'] = 'This Database Set has no databases.'
  
  # Format the template, non-destructively.  (Keep unused format strings and %s)
  output = site_control.WebTemplateFormat(template, data)
  
  return output
