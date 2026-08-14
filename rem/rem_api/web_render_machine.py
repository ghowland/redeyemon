#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Web: Render the Site Control data: Machines

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


def WebRender_Machine(machine_id):
  """Render this machine from it's RpcGetMachine() data."""
  # Get our base rendering data
  machine = site_control.RpcGetMachine(machine_id)
  if not machine:
    msg = 'Machine not found: %s' % machine_id
    log(msg)
    return msg
  
  # Make our own data, to match to the template
  data = dict(machine)
  
  # Render our services
  data['service_info'] = ''
  if data['services']:
    services = list(data['services'])
    services.sort() # Ensure they are always in the same order
    for service_id in services:
      if service_id == services[0]:
        data['service_info'] += site_control.WebRender_Service_Line(service_id, print_header=True)
      else:
        data['service_info'] += site_control.WebRender_Service_Line(service_id)
  
  # Render our pools
  data['pool_info'] = ''
  if data['pools']:
    pools = list(data['pools'])
    pools.sort() # Ensure they are always in the same order
    for pools_id in pools:
      if pools_id == pools[0]:
        data['pool_info'] += site_control.WebRender_Pool_Line(pools_id, print_header=True)
      else:
        data['pool_info'] += site_control.WebRender_Pool_Line(pools_id)
  
  # Get the template
  template = GetWebRenderTemplate('render/machine.txt')
  
  # Format the template, non-destructively.  (Keep unused format strings and %s)
  output = site_control.WebTemplateFormat(template, data)
  
  return output


def WebRender_Machine_Line(machine_id, table_row=True, print_header=False):
  """Render this machine from it's RpcGetMachine() data, on a single line."""
  # Get our base rendering data
  machine = site_control.RpcGetMachine(machine_id)
  
  if not machine:
    msg = 'Machine not found: %s' % machine_id
    log(msg)
    return msg
  
  # Make our own data, to match to the template
  data = dict(machine)
  
  # Get the template
  template = GetWebRenderTemplate('render/machine_line.txt')
  
  # Format the template, non-destructively.  (Keep unused format strings and %s)
  output = site_control.WebTemplateFormat(template, data)
  
  # If we want to print the header too
  if print_header:
    # Create custom header data for this template
    header_data = {'name':'', 'id':'', 'site_data_center_name':'Zone',
                   'hardware_kind_name':'Hardware',
                   'hardware_image_name':'Image', 'status_image':''}
    
    # Render the header
    header = _RenderHeader(template, header_data)
    
    # Append the header
    output = header + output
  
  return output


def WebRender_Machine_Status(machine_id):
  """Render just a status item (16x16 image, can have popup) for this item."""
  output = ''
  
  # Get the RPC synthesized data, without status (cause thats us, loop)
  machine = site_control.RpcGetMachine(machine_id, render_status=False)
  if not machine:
    log('Machine not found: %s' % machine_id)
    return '<img src="/static/images/candle.png" title="ERROR: Not Found">'
  
  # If this Instance is Active
  if machine['status'] == 5:
    #TODO(g): Add popup with BRIEF machine info: Green
    output += '<a href="machine?id=%(id)s"><img src="/static/images/led_green.png" border=0 title="%(status_name)s"></a>' % machine
  
  # Else, if this Instance is in configuration: Yellow
  elif machine['status'] in (2, 3, 4):
    output += '<a href="machine?id=%(id)s"><img src="/static/images/led_yellow.png" border=0 title="%(status_name)s"></a>' % machine
  
  # Else, if this Instance is in request/allocation: White
  elif machine['status'] == 1:
    output += '<a href="machine?id=%(id)s"><img src="/static/images/led_white.png" border=0 title="%(status_name)s"></a>' % machine
  
  # Else, if this Instance is paused or in decomm: Red
  elif machine['status'] == 8:
    output += '<a href="machine?id=%(id)s"><img src="/static/images/led_red.png" border=0 title="%(status_name)s"></a>' % machine
  
  # Else, WTF is this?  Blue
  else:
    log('Unhandled status: %s' % instance['status'])
    output += '<a href="machine?id=%(id)s"><img src="/static/images/led_blue.png" border=0 title="%(status_name)s"></a>' % machine
  
  return output


