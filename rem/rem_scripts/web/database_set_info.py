#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Web: Render: Database Set Info
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
    return '"id" not specified in args.  No Database Set specified.'
  else:
    db_set_id = int(data['id'])
  
  log('Database Info: %s' % db_set_id)
  
  body = ''
  
  body += site_control.WebRender_DatabaseSet(db_set_id)
  body += '<br>\n'
  
  # Format the page data
  db_set = site_control.GetDatabaseSet(db_set_id)
  if db_set:
    format_data = {'page_body':body, 'page_title':'Database Set: %s' % db_set['name']}
  else:
    format_data = {'page_body':body}
  
  # Format the template for output
  output = site_control.WebTemplateFormat(data['_template'], format_data)
  
  return output

