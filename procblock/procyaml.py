"""
procyaml

Process YAML files to make them easier to write for procblock.

Specially, add __import_%(key)s tags, so we can embed YAML files inside of
each other, and order our data a bit more sanely.

ImportYaml() does the __import_ thing.

LoadYaml() does caching.  TODO(g): Mix this with that.
"""


import os
import yaml
import stat

import shared.stack

import shared.log as logging
from shared.log import log


# All YAML files we load can be cached and tested here
YAML_CACHE = {}
YAML_CACHE_TIME = {}


def LoadYaml(path):
  """Wraps loading of files, so they can be cached, and the cache can be
  updated.
  """
  global YAML_CACHE
  
  if type(path) != str:
    log('Path is not a string: %s: %s' % (stack.Mini(4), path), logging.ERROR)
  
  # If we have the path in cache, and the file change time hasnt changed,
  #   return the cached value
  if path in YAML_CACHE:
    if os.stat(path)[stat.ST_MTIME] == YAML_CACHE_TIME[path]:
      return YAML_CACHE[path]
  
  # Load data
  try:
    data = yaml.load(open(path, 'r').read())
  except TypeError:
    log('Failed to load YAML file: %s' % path, logging.ERROR)
    raise
  
  if data != None:
    # Cache data
    YAML_CACHE[path] = data
    YAML_CACHE_TIME[path] = os.stat(path)[stat.ST_MTIME]
  
  return data



def ImportYaml_ImportKey(data, cwd):
  """Recursive function to import keys into a YAML dictionary."""
  for key in data.keys():
    # If this key is an import key
    if key.startswith('__import__'):
      (_, import_key) = key.split('__import__', 1)
      
      log('Importing key: %s: %s' % (import_key, data[key]))
      
      #TODO(g): Process the filename, if it's not absolute, test local, and
      #   then localize off the filename's path
      import_filename = data[key]
      
      # If the import_filename is not an existing absolute or relative path
      if not os.path.isfile(import_filename):
        # If this is an absolute path, then we cant load it
        if import_filename.startswith('/'):
          raise Exception('ImportYaml: Cannot import key YAML: %s: %s: Absolute path file not found' % (key, import_filename))
        # Else, append on our 
        else:
          import_filename = '%s/%s' % (cwd, import_filename)
          
          if not os.path.isfile(import_filename):
            raise Exception('ImportYaml: Cannot import key YAML: %s: %s: Appending to current working directory failed' % (key, import_filename))
      
      # Import the YAML
      import_data = ImportYaml(import_filename, cwd=cwd)
      
      # Delete the import key rule, keep it clean
      del data[key]
      
      # If this key already exists, and is a dictionary, update
      if import_key in data and type(data[import_key]) == dict and type(import_data) == dict:
        data[import_key].update(import_data)
      
      # Else, overwright the key
      else:
        data[import_key] = import_data
    
    # Else, if this is a dictionary value, then run it through the importer too
    elif type(data[key]) == dict:
      
      ImportYaml_ImportKey(data[key], cwd)


def ImportYaml(filename, cwd=None):
  """Import this YAML file, and import recursively any sections marked with
  __import__name, where "name" will be updated as a dictionary, or replaced
  if not a dictionary.
  
  Args:
    filename: string, name of file to load
    cwd: string (optional), if present this is the current working directory
        of the first imported file
  
  Returns: data, typically a dictionary.  Contents of YAML file.
  """
  log('Importing YAML: %s' % filename)
  data = yaml.load(open(filename))
  
  if cwd == None:
    cwd = os.path.dirname(filename)
  
  # If the data is a dictionary, we need to check the keys for import rules
  if type(data) == dict:
    ImportYaml_ImportKey(data, cwd)
  #
  #else:
  #  print '  Type: %s' % type(data)
  
  return data
  