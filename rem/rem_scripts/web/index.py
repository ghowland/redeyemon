#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Web: Render: Index

Displays Pools and Services, as a basic dashboard.  Other things can be found
from these, and these wrap the things we are most interested in.
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def Execute(data, state):
  """Execute this view's render script."""
  #output = site_control.WebRenderOutput()
  
  logging.SetLogFile('/usr/local/site_control/web_scripts.log')
  
  body = ''
  
  # Get the site information
  #TODO(g): Switch to rpc_site_control get, so we have additional data
  site = site_control.GetSite(state.get('site', site_control.SITE_DEFAULT))
  
  # Paste this in
  body += '<h1>%s</h1>\n' % site['name']
  
  # Get all our pools
  pools = site_control.GetPools()
  pool_names = pools.keys()
  pool_names.sort()
  
  # Render our pools
  body += '<h2>Pools</h2>\n'
  body += '<div class="black_box" style="width: 80%;">\n'
  body += '<table width="100%">\n'
  for pool_name in pool_names:
    pool = site_control.GetPoolByName(pool_name)
    if pool_name == pool_names[0]:
      body += site_control.WebRender_Pool_Line(pool['id'], print_header=True)
    else:
      body += site_control.WebRender_Pool_Line(pool['id'])
  body += '</table>\n'
  body += '</div>\n'
  
  # Get our services
  services = site_control.GetServices()
  service_names = services.keys()
  service_names.sort()
  
  # Render our services
  body += '<br><h2>Services</h2>\n'
  body += '<div class="black_box" style="width: 50%;">\n'
  body += '<table width="100%">\n'
  for service_name in service_names:
    service = site_control.GetServiceByName(service_name)
    if service_name == service_names[0]:
      body += site_control.WebRender_Service_Line(service['id'], print_header=True)
    else:
      body += site_control.WebRender_Service_Line(service['id'])
  body += '</table>\n'
  body += '</div>\n'
  
  
  # Format the page data
  format_data = {'page_body':body}
  
  # Format the template for output
  output = site_control.WebTemplateFormat(data['_template'], format_data)
  
  return output

