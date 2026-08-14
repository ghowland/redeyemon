#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Web: Render: Machine Info
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def Execute(data, state):
  """Execute this view's render script."""
  if 'id' not in data:
    return '"id" not specified in args.  No Machine specified.'
  else:
    machine_id = int(data['id'])
  
  log('Machine Info: %s' % machine_id)
  
  body = ''
  
  body += site_control.WebRender_Machine(machine_id)
  body += '<br>\n'
  
  # Format the page data
  format_data = {'page_body':body}
  
  # If this machine is valid, add the title too
  machine = site_control.GetMachine(machine_id)
  if machine:
    format_data['page_title'] = 'Machine: %s' % machine['name']

  
  # Format the template for output
  output = site_control.WebTemplateFormat(data['_template'], format_data)
  
  return output
