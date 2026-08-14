#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Web: Render the Site Control data: Pool

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


def WebRender_Pool(pool_id):
  """Render this pool from it's RpcGetPool() data."""
  # Get our base rendering data
  pool = site_control.RpcGetPool(pool_id)
  
  if not pool:
    msg = 'Pool not found: %s' % pool_id
    log(msg)
    return msg
  
  # Make our own data, to match to the template
  data = dict(pool)
  
  # Get the template
  template = GetWebRenderTemplate('render/pool.txt')
  
  # If this pool is a Child Pool
  if pool['parent_pool']:
    data['parent_pool_info'] = '<b>Parent Pool:</b> <a href="pool?id=%d">%s</a><br>' % \
        (pool['parent_pool'], site_control.GetPool(pool['parent_pool'])['name'])
  else:
    data['parent_pool_info'] = '<b>Child Pools:</b><br>\n'
    
    data['parent_pool_info'] += '<table width="100%">\n'
    
    # Look for child pools instead
    child_pools = site_control.GetPoolChildPools(pool_id)
    child_pools.sort() # Ensure they are always in the same order
    for child_pool_id in child_pools:
      if child_pool_id == child_pools[0]:
        data['parent_pool_info'] += site_control.WebRender_Pool_Line(child_pool_id, print_header=True)
      else:
        data['parent_pool_info'] += site_control.WebRender_Pool_Line(child_pool_id)
    
    data['parent_pool_info'] += '</table>\n'
  
  # Add Machines
  data['machine_info'] = ''
  if data['machines']:
    machines = list(data['machines'])
    machines.sort() # Ensure they are always in the same order
    for machine_id in machines:
      if machine_id == machines[0]:
        data['machine_info'] += site_control.WebRender_Machine_Line(machine_id, print_header=True)
      else:
        data['machine_info'] += site_control.WebRender_Machine_Line(machine_id)
  
  # If this pool is DB Set controlled
  data['pool_db_storage_info'] = ''
  if pool['db_set']:
    db_set = site_control.GetDatabaseSet(pool['db_set'])
    
    # Label our data set
    data['pool_db_storage_info'] += '<b>Database Set:</b> <a href="database_set?id=%(id)s">%(name)s</a><br>\n' % db_set
    
    # Get our databases
    databases = site_control.GetDatabaseSetDatabases(pool['db_set'])
    
    # Open database table
    data['pool_db_storage_info'] += '<br><table width="80%">\n'
    
    # Add them to pool_db_storage_info
    keys = databases.keys()
    keys.sort() # Ensure the entries are always in the same order
    for db_id in keys:
      if db_id == keys[0]:
        data['pool_db_storage_info'] += site_control.WebRender_Database_Line(db_id, print_header=True)
      else:
        data['pool_db_storage_info'] += site_control.WebRender_Database_Line(db_id)
    
    # Close database table
    data['pool_db_storage_info'] += '</table>\n'
  
  elif pool['storage_set']:
    pass#TODO(g):...
  
  else:
    data['pool_db_storage_info'] = 'This pool is not controlled by database set or storage set.'
  
  # Add Services
  data['services'] = site_control.GetPoolServices(pool_id)
  data['services'].sort()
  data['service_info'] = ''
  for service_id in data['services']:
    if service_id== data['services'][0]:
      data['service_info'] += site_control.WebRender_Service_Line(service_id, print_header=True)
    else:
      data['service_info'] += site_control.WebRender_Service_Line(service_id)
  
  # Format the template, non-destructively.  (Keep unused format strings and %s)
  output = site_control.WebTemplateFormat(template, data)
  
  return output


def WebRender_Pool_Line(pool_id, table_row=True, print_header=False):
  """Render this pool from it's RpcGetPool() data, on a single line."""
  # Get our base rendering data
  pool = site_control.RpcGetPool(pool_id)
  
  if not pool:
    msg = 'Pool not found: %s' % pool_id
    log(msg)
    return msg
  
  # Make our own data, to match to the template
  data = dict(pool)
  
  # Get the template
  template = GetWebRenderTemplate('render/pool_line.txt')
  
  # Format the template, non-destructively.  (Keep unused format strings and %s)
  output = site_control.WebTemplateFormat(template, data)
  
  # If we want to print the header too
  if print_header:
    # Create custom header data for this template
    header_data = {'name':'', 'id':'', 'site_data_center_name':'Zone',
                   'hardware_kind_name':'Hardware',
                   'hardware_image_name':'Image',
                   'machine_goal':'Goal Size',
                   'machine_active':'Active Size',
                   'machine_statuses':'Machines', 'status_image':''
                   }
    
    # Render the header
    header = _RenderHeader(template, header_data)
    
    # Append the header
    output = header + output
  
  return output


def WebRender_Pool_Status(pool_id):
  """Render just a status item (16x16 image, can have popup) for this item."""
  output = ''
  
  # Get the RPC synthesized data, without status (cause thats us, loop)
  pool = site_control.RpcGetPool(pool_id, render_status=False)
  
  if not pool:
    log('Pool not found: %s' % pool_id)
    return '<img src="/static/images/candle.png" title="Not Found">'
  
  # Get our machines
  machines = pool['machines']
  
  # If all our machines are Active: Green
  if pool['machine_goal'] == pool['machine_active']:
    output += '<a href="pool?id=%(id)s"><img src="/static/images/led_green.png" border=0 title="All Machines Active"></a>' % pool
  
  # Else, if we have a goal for machines, but no active machines: Red
  elif pool['machine_goal'] > 0 and pool['machine_active'] == 0:
    output += '<a href="pool?id=%(id)s"><img src="/static/images/led_red.png" border=0 title="No Instances"></a>' % pool
  
  # Else, if we have a goal for machines, but some active machines: Yellow
  elif pool['machine_goal'] > 0 and pool['machine_active'] >= 1:
    output += '<a href="pool?id=%(id)s"><img src="/static/images/led_yellow.png" border=0 title="Not All Instances Active"></a>' % pool
  
  # Else, unknown
  else:
    log('Unknown status of Pool: %s' % pool_id)
    output += '<a href="pool?id=%(id)s"><img src="/static/images/led_white.png" border=0 title="Unknown Status"></a>' % pool
  
  return output


