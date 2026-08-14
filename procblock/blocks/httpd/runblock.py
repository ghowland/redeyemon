"""
******* OLD SKOOL:  Decomm this to use procblock ASAP.  This is just to get
    everything running very quickly so full iterations can happen, instead of
    working on one piece for a long time without having a full system
    running to test it.

Run Script Block

This library will take a ScriptBlock formatted list, and will process each
of the directives.

Directives include setting variables and running scripts, and can alternate
running scripts and setting output variables to create a flexible chain of
external scripts, which feed each other data, and have access to their
predecessors output, and the original input, and any session information.

This module is meant to be a general purpose way to run dynamic scripts
that are only specified in data, so they do not have to be part of a project.

The interface has been designed to maximize flexibility and simplicity to
load and invoke, while allowing arbitrary complexity to be hidden inside
the calling scripts and state.
"""


import os
import threading
import time
import subprocess
import imp
import sys

sys.path.append('../../')
import shared.log as logging
from shared.log import log


def Run(command):
  """Actually run the command on the local machine.  Blocks until complete.
  """
  #global ENVIRONMENT
  
  output_error = '' #Later, how to handle reading the timing stream between the two?  It's lost...

  #log('Run: %s' % command)

  #TODO(g): Remove when subprocess method works
  #(status, output, output_error) = os.popen3(command)

  # Subprocess is beautiful and finally makes this a pleasant experience!
  #   Imagine, OUTPUT, ERRORS and EXIT CODE!!!  Not exclusively choosing two!
  #   Newbs be rejoice in your ignorance.
  pipe = subprocess.Popen(command, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, shell=True)
  status = pipe.wait()
  output = pipe.stdout.read()
  output_error = pipe.stderr.read()
  
  # Close the pipes
  pipe.stderr.close()
  pipe.stdout.close()

  if status != 0:
    log('Non-Zero Exit Code: %s: %s' % (status, command), logging.INFO)

  return (status, output, output_error)


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


def ExecuteScript(python_script, data, chain_output, state, env=None):
  """Execute the specified script.  This will ensure it is imported, and
  re-imported if the code changes on the disk.
  
  TODO(g): Implement in-memory cache of md5-sums from the Manager, specifying
      the md5-sum of each script, and do not import if it is not the same.
      Instead, alert on a locally changed script.
  """
  
  # Import the Python Script module
  script_module = GetPythonScriptModule(python_script)
  
  if script_module == None:
    log('Failed to find python script: %s' % os.path.abspath(python_script), logging.ERROR)
    return
  
  # Execute the script, and return the data (which will update chain_output)
  try:
  #if 1:
    result = script_module.Execute(data, chain_output, state, env)
  except Exception, e:
    #TODO(g): Print the exception out here, so we keep all this data together,
    #   Im only doing it this less-optimal way (exception and python script
    #   are not in the same lines, and will be hard to see when threaded),
    #   because I havent baked Python 2.6 into the EC2 AMIs yet.
    log('Exception in script: %s: %s' % (python_script, e))
    raise
  
  return result


class RunScriptFailedCondition(Exception):
  """Failed to pass all "if" conditions."""


def RunScriptBlock(script_data, script_input, state, script_path_prefix=None):
  
  #log('%s %s'  % (script_data, script_path_prefix))
  
  # Misconfiguration
  if 'run' not in script_data:
    log('ERROR: No data to run!', logging.ERROR)
    return
  
  # If-Condition test
  if_passed = True
  if 'if' in script_data:
    for key in script_data['if']:
        # If this is an Local instance script
        if instance:
          if key not in instance:
            if_passed = False
            log('Script: IF FAIL: Key not found in instance: %s' % key)
          
          elif type(script_data['if']) == list:
            if instance[key] not in script_data['if'][key]:
              if_passed = False
              log('Script: IF FAIL: Instance var (%s) value not in list: %s not in %s' % (key, instance['key'], script_data['if'][key]))
        
        # Else, Manager script, user service data
        elif key not in service_data:
          if_passed = False
          log('Script: IF FAIL: Key not found in service_data: %s' % key)
        
        elif type(script_data['if'][key]) == list:
          if service_data[key] not in script_data['if'][key]:
            if_passed = False
            log('Script: IF FAIL: Key (%s) value (%s) not found in service_data value list: %s' % (key, service_data[key], script_data['if'][key]))
        
        elif service_data[key] != script_data['if'][key]:
          if_passed = False
          log('Script: IF FAIL: Key (%s) value (%s) does not equal service_data value: %s' % (key, service_data[key], script_data['if'][key]))
    
    # Return if the IF failed
    if not if_passed:
      raise RunScriptFailedCondition("Conditions to run were not met.  Not run.")
  
  
  # Get the script data, to pass to the functions
  data = script_data.get('data', {})
  
  # Update data with our script_input
  data.update(script_input)
  
  # This dictionary is passed along to each script, and gets updated with the
  #   result, so we can chain outputs, using them as inputs for the next
  #   script, and having a very rich data set of collected results by the end
  #   of executing the chain
  chain_output = {}
  
  # Time the script started
  start_time = time.time()
  
  #print 'Run Script Execute: %s   (Instance: %s   Count: %s)' % (script, instance_name, script_run_count)
  
  # Execute the chain of scripts
  for item in script_data['run']:
    
    # If this is a script
    if 'script' in item:
      
      # Get the python script
      python_script = item['script']
      
      # If we have a script prefix, and this isnt an absolute path, prefix it
      if script_path_prefix and not python_script.startswith('/'):
        python_script = '%s/%s' % (script_path_prefix, python_script)
      
      # Execute the script, get the result to update chain_output
      result = ExecuteScript(python_script, data, chain_output, state, env=None)
      
      # Update chain_output with result
      if type(result) == dict:
        chain_output.update(result)
      else:
        log('Python Script Execute did not return dict: %s: %s' %
            (python_script, result), logging.ERROR)
    
    
    # Else, if we are 
    elif 'set' in item:
      # Set all the keypairs specified into our data
      for (key, value) in item['set'].items():
        # Update the data, we are using
        data[key] = value
    
    
    # Else, if we are Changing Directories
    elif 'cd' in item:
      dir = item['cd']
      
      # Check if any of our script_input keys are variables here
      found = False
      for key in script_input:
        if '%%(%s)' % key in dir:
          found = True
          break
      
      # If we found a script_input variable, then expand the variables
      if found:
        dir = dir % script_input
      
      #TODO(g): NOTTHREADSAFE: Is this safe to do outside of a child thread?
      #   It could screw things up...
      log('Changing working directory: %s' % dir)
      os.chdir(dir)
    
    # Else, if we are execute Shell commands
    elif 'shell' in item:
      cmd = item['shell']
      
      log('Executing shell command: %s' % cmd)
      
      #TODO(g): SECURITY:CRITICAL: Totally shit security.  FIX FIX FIX!!!
      os.system(cmd)
    
    # Else, if we are invoking a script
    elif 'call' in item:
      log('ERROR: Not yet implemented.  This will call another script, but its name.  invoked=True', logging.CRITICAL)
      pass
    
    # Else, if we are invoking a script
    elif 'except' in item:
      #log('ERROR: Not yet implemented.  This will deal with any exceptions in any of the preceding items.', logging.CRITICAL)
      log('ERROR: Not yet implemented.  This will deal with any exceptions in any of the preceding items.', logging.ERROR)
      pass
    
    
    # Else, error
    else:
      raise Exception('Unknown type of script: %s' % item)
  
  
  # Get the duration
  duration = time.time() - start_time
  
  # If the chain_output doesnt already have a duration, add it
  if 'duration' not in chain_output:
    chain_output['__duration'] = duration
  
  
  # Save when this script started, so we know which RRD slot it's best for
  chain_output['__start_time'] = start_time

  
  #log('Script result: %s.%s.%s.%s: %s' % (script, deployment, service, instance_name, chain_output))
  
  
  return chain_output


if __name__ == '__main__':
  script_data = {}
  script_data['run'] = [{'set':{'key':'value 555'}}, {'script':'control/control.py'}, {'script':'control/control.py'}]
  
  script_input = {}
  script_path_prefix = 'scripts'
  
  state = {}
  
  output = RunScriptBlock(script_data, script_input, state, script_path_prefix)
  
  print output

