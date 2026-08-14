#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Web: Render: Storage Handler Info
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
    return '"id" not specified in args.  No Storage Handler specified.'
  else:
    handler_id = int(data['id'])
  
  log('Storage Handler Info: %s' % handler_id)
  
  body = ''
  
  body += site_control.WebRender_StorageHandler(handler_id)
  body += '<br>\n'
  
  # Format the page data
  handler = site_control.GetStorageHandler(handler_id)
  if handler:
    format_data = {'page_body':body, 'page_title':'Storage Handler: %s' % handler['name']}
  else:
    format_data = {'page_body':body}
  
  # Format the template for output
  output = site_control.WebTemplateFormat(data['_template'], format_data)
  
  return output

