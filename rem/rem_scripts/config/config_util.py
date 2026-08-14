#!/usr/bin/python


#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Config Utilities

Common functions and data needed by config scripts, to keep them minimum.

Smaller and simpler is easier to modify without defects.
"""



import time
import os
import subprocess


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


# Local relative path to the template text files
TEMPLATE_PATH = '../templates/'


def RunCommand(command):
  """Wrap it, for easy maintenance."""
  #os.system(command)
  pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
  status = pipe.wait()


def LoadTemplate(template):
  """Load a template."""
  global TEMPLATE_PATH

  filename = TEMPLATE_PATH + template

  data = open(filename).read()

  return data


def SaveFile(filename, data):
  """Saves a file in the safest way we can."""
  # Diff the temp and current final file, if they are the same, then abort
  #   saving or backing up, it is not necessary
  if os.path.isfile(filename):
    current_data = open(filename).read()

    if current_data == data:
      log('SaveFile: %s: Skipping, same.' % filename)
      return False

  log('SaveFile: %s' % filename)

  # Save the output
  #TODO(g): Two-stage this.  Necessary for any race conditions?  I dont think so...
  backup_filename = '%s.%s' % (filename, GetTimeStamp())

  temp_filename = '%s.tmp' % filename

  # Save this file to temp position, so it's ready to be moved (fastest operation)
  open(temp_filename, 'w').write(data)

  # Back up copy of the old data with timestamp
  if os.path.isfile(filename):
    os.system('/bin/mv %s %s' % (filename, backup_filename))

  # Move the new data from the temp file to the correct final file
  os.system('/bin/mv %s %s' % (temp_filename, filename))

  return True


def PrintTestTemplate(filename, data):
  """A test_template was given to a config file, so we cant save the data.
  
  Args:
    filename: string, the name that the file WOULD be saved as
    data: string, the data that WOULD be saved int the filename file
  """
  print '----------------------------------------------------------------------'
  print 'File: %s' % filename
  print '----------------------------------------------------------------------'
  print data
  print '----------------------------------------------------------------------'
  print


def GetTimeStamp(minutes=True, seconds=True):
  """Gets time stamps, for use in dating backup files and other things."""
  (year, month, day, hour, minute, second, _, _, _) = time.localtime()

  if seconds:
    output = '%02d%02d%02d%02d%02d%02d' % (year, month, day, hour, minute, second)
  elif minutes:
    output = '%02d%02d%02d%02d%02d' % (year, month, day, hour, minute)
  else:
    output = '%02d%02d%02d%02d' % (year, month, day, hour)

  return output
