#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Web: Render: Storage Info
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def Execute(data, state):
  """Execute this view's render script."""
  
  logging.SetLogFile('/usr/local/site_control/web_scripts.log')
  log('Starting')
  
  if 'id' not in data:
    return '"id" not specified in args.  No Storage specified.'
  else:
    storage_id = int(data['id'])
  
  log('Storage Info: %s' % storage_id)
  
  body = ''
  
  body += site_control.WebRender_Storage(storage_id)
  body += '<br>\n'
  
  # Format the page data
  storage = site_control.GetStorage(storage_id)
  if storage:
    format_data = {'page_body':body, 'page_title':'Storage: %s' % storage['name']}
  else:
    format_data = {'page_body':body}
  
  # Format the template for output
  output = site_control.WebTemplateFormat(data['_template'], format_data)
  
  return output

