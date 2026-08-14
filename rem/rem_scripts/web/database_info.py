#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Web: Render: Database Info
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
    return '"id" not specified in args.  No Database specified.'
  else:
    database_id = int(data['id'])
  
  log('Database Info: %s' % database_id)
  
  body = ''
  
  body += site_control.WebRender_Database(database_id)
  body += '<br>\n'
  
  # Format the page data
  database = site_control.GetDatabase(database_id)
  if database:
    format_data = {'page_body':body, 'page_title':'Database: %s' % database['name']}
  else:
    format_data = {'page_body':body}
  
  # Format the template for output
  output = site_control.WebTemplateFormat(data['_template'], format_data)
  
  return output

