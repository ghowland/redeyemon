#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Web: Render: Pool Info
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def Execute(data, state):
  """Execute this view's render script."""
  if 'id' not in data:
    return '"id" not specified in args.  No Pool specified.'
  else:
    pool_id = int(data['id'])
  
  log('Pool Info: %s' % pool_id)
  
  body = ''
  
  body += site_control.WebRender_Pool(pool_id)
  body += '<br>\n'
  
  # Format the page data
  pool = site_control.GetPool(pool_id)
  format_data = {'page_body':body, 'page_title':'Pool: %s' % pool['name']}
  
  # Format the template for output
  output = site_control.WebTemplateFormat(data['_template'], format_data)
  
  return output

