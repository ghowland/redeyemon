#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Web: Render the Site Control data: Service

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


def WebRender_Service(service_id):
  """Render this service from it's RpcGetService() data."""
  # Get our base rendering data
  service = site_control.RpcGetService(service_id)
  if not service:
    msg = 'Service not found: %s' % service_id
    log(msg)
    return msg
  
  # Make our own data, to match to the template
  data = dict(service)
  
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
  
  # Add Pools
  data['pool_info'] = ''
  if data['pools']:
    pools = list(data['pools'])
    pools.sort() # Ensure they are always in the same order
    for pool_id in pools:
      if pool_id == pools[0]:
        data['pool_info'] += site_control.WebRender_Pool_Line(pool_id, print_header=True)
      else:
        data['pool_info'] += site_control.WebRender_Pool_Line(pool_id)
  
  # Get the template
  template = GetWebRenderTemplate('render/service.txt')
  
  # Format the template, non-destructively.  (Keep unused format strings and %s)
  output = site_control.WebTemplateFormat(template, data)
  
  return output


def WebRender_Service_Line(service_id, table_row=True, print_header=False):
  """Render this service from it's RpcGetService() data, on a single line."""
  # Get our base rendering data
  service = site_control.RpcGetService(service_id)
  
  if not service:
    msg = 'Service not found: %s' % service_id
    log(msg)
    return msg
  
  # Make our own data, to match to the template
  data = dict(service)
  
  # Get the template
  template = GetWebRenderTemplate('render/service_line.txt')
  
  # Format the template, non-destructively.  (Keep unused format strings and %s)
  output = site_control.WebTemplateFormat(template, data)
  
  # If we want to print the header too
  if print_header:
    # Create custom header data for this template
    header_data = {'name':'Service', 'id':'', 'init_service':'Init Service',
                   'status_image':''}
    
    # Render the header
    header = _RenderHeader(template, header_data)
    
    # Append the header
    output = header + output
  
  return output


def WebRender_Service_Status(service_id):
  """Render just a status item (16x16 image, can have popup) for this item."""
  output = ''
  
  # Get the RPC synthesized data, without status (cause thats us, loop)
  service = site_control.RpcGetService(service_id, render_status=False)
  
  if not service:
    log('Service not found: %s' % service_id)
    return '<img src="/static/images/candle.png" title="Not Found">'
  
  #TODO(g): Figure out how to gauge service status later.  Lots can be done here
  output += '<a href="service?id=%(id)s"><img src="/static/images/led_white.png" border=0 title="TODO(g): WebRender_Service_Status"></a>' % service
  
  return output
