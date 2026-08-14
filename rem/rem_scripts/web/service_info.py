#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Web: Render: Service Info
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def Execute(data, state):
  """Execute this view's render script."""
  
  if 'id' not in data:
    return '"id" not specified in args.  No Service specified.'
  else:
    service_id = int(data['id'])
  
  log('Service Info: %s' % service_id)
  
  body = ''
  
  body += site_control.WebRender_Service(service_id)
  body += '<br>\n'
  
  # Format the page data
  service = site_control.GetService(service_id)
  format_data = {'page_body':body, 'page_title':'Service: %s' % service['name']}
  
  # Format the template for output
  output = site_control.WebTemplateFormat(data['_template'], format_data)
  
  return output

