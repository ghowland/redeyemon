"""
code_python

Import python modules to execute procblock Code with this library.

TODO(g): Ensure output PYC files are unique and never clobber each other.
"""


import imp
import os
import sys

sys.path.append('../')
from shared import log as logging
from shared.log import log


def GetPythonScriptModule(script_filename):
  """Will return a Python module for this script_id, or None."""
  # Get the script file name for this item
  #log('Script: %s' % (script_filename))
  
  # Get the name and path, we need them seperate
  name = os.path.basename(script_filename)
  path = os.path.dirname(script_filename)
  
  # Split the suffix off the name
  if name.endswith('.py'):
    name = name[:-3]
  else:
    # Skip this one, but report it as a critical failure
    log('Script is not a python text file or is improperly named: %s' % \
        script_filename, logging.CRITICAL)
    return None
  
  # Open a file handle to this file
  try:
    fp = open(script_filename, 'r')
  
  except IOError, e:
    log('Error loading Python script: %s' % e, logging.CRITICAL)
    
    return None
  
  # Add the path of this module to our python import path, in case there are
  #   additional modules it wants to import from it's path location
  sys.path.append(path)
  
  # imp.load_module needs this suffix description information that
  #   imp.getsuffixes() would return, but the documentation was weird, so
  #   Im just forcing it to be this which is the only thing I want to be
  #   valid anyway.  Fail if it's not.
  suffix_description = ('.py', 'r', imp.PY_SOURCE)
  
  try:
    try:
      # Import this script, it should be a python script
      script_module = imp.load_module(name, fp, path, suffix_description)
      
      return script_module
    
    except ImportError, e:
      log('Failed to import script: %s: %s' % \
          (os.path.abspath(script_filename), e), logging.CRITICAL)
    except Exception, e:
      log('Failed to import script for non-import reasons: %s: %s' % \
          (script_filename, e), logging.CRITICAL)
  
  finally:
    # Close the file handle whether there was an exception or not
    fp.close()
    
  
  # Failed
  return None

