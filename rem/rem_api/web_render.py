#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Web: Render the Site Control data

These are default methods of rendering the SC data (pools, machines, etc).

It still uses the ./rem/web/templates/ text files, but everything is already
done so any web script can grab a default item and render it into a page in
some specific place without having to think about how to render it this time.

There can be several default renderings, just use default args to modify,
or make new functions.  All flexbility here.  Add more text template files to
fill in data.
"""


import os


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def GetWebRenderTemplate(name):
  """Returns the template text, or None if the file isnt found."""
  #TODO(g): Unhardcode this path
  WEB_TEMPLATE_PATH = '/usr/local/site_control/rem/web/templates/%s'
  
  # Get the full path name
  full_path = WEB_TEMPLATE_PATH % name
  
  # If the path exists, load and return the text
  if os.path.isfile(full_path):
    try:
      output = open(full_path).read()
    except Exception, e:
      log('Couldnt load the file "%s": %s' % (full_path, e), logging.CRITICAL)
      return None
    
    return output
  
  # Else, the file wasnt found
  else:
    return None


def _RenderHeader(template, header_data):
  """For Line-type rendering, this reduces repeated code."""
  # Format the template, non-destructively.  (Keep unused format strings and %s)
  header = site_control.WebTemplateFormat(template, header_data)
  
  # Re-format to be a header
  header = '<thead>\n%s</thead>\n' % header
  header = header.replace('<td>', '<th>')
  header = header.replace('</td>', '</th>')
  
  return header


