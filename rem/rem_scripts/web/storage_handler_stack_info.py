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
    return '"id" not specified in args.  No Storage Handler Stack specified.'
  else:
    handler_stack_id = int(data['id'])
  
  log('Storage Handler Stacker Info: %s' % handler_stack_id)
  
  body = ''
  
  body += site_control.WebRender_StorageHandlerStack(handler_stack_id)
  body += '<br>\n'
  
  # Format the page data
  handler_stack = site_control.RpcGetStorageHandlerStack(handler_stack_id)
  if handler_stack:
    format_data = {'page_body':body, 'page_title':'Storage Handler Stack: %s' % handler_stack['storage_handler_name']}
  else:
    format_data = {'page_body':body}
  
  # Format the template for output
  output = site_control.WebTemplateFormat(data['_template'], format_data)
  
  return output

