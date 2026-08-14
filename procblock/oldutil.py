"""
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


import time
import subprocess
import os

import sys
sys.path.append('../')
from shared import log as logging
from shared.log import log

from shared import sharedstate

from run import running


#####(pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):
####def RunScriptBlock(script_data, script_input, state, script_path_prefix=None):

#def RunScriptBlock(pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):  ### <----  New format for ProcessBlock().  This reorders and renames vars so that the most used is first: pipe_data, and its name better suits its function.  It is made to pipe data.  input_data is the original input, but not supposed to be used all the time, just as a reference.  The block data is used frequently.  States is renamed to request_state to separate it from shared.staredstate, request_state is the state just for the REQUEST, and has already been broken out as such, if applicable.  Authentication will update request_state to provide user information and stored data they may need for this request.
#TODO(g): Get rid of state in favor of using shared.sharedstate?  State is still passed, and could be sub-state, so I think it makes more sense.  Basically it's the session's state...  Change to request_state?

def RunScriptBlock(pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):
  # Get the script path prefix, if there is one, from the block
  #TODO(g): Document or improve this.
  if block_parent:
    script_path_prefix = block_parent.get('script_path_prefix', None)
  else:
    script_path_prefix = None
  
  
  # Time the script started
  start_time = time.time()
  
  #print 'Run Script Execute: %s   (Instance: %s   Count: %s)' % (script, instance_name, script_run_count)
  
  # Execute the chain of scripts
  for item in block:
    
    log('RunBlock: Item: %s' % item)
    
    # If this is a script
    if 'script' in item:
      
      # If this in an Interval Caching script...
      if 'cache' in item:
        #print 'Running Python Script: Interval Caching'
        ## Get the RunThreadIntervalThingy for this cache item
        #run_thread = running.GetRunThreadByName(item['cache'])
        
        # Try to get the run thread
        try:
          run_thread = sharedstate.Get('threads', item['cache'])
        except Exception, e:
          run_thread = None
        
        # If we dont already have a run thread by this name, create it
        if run_thread == None:
          #print 'Creating new run_thread: %s' % item['cache']
          
          # Create the run thread
          run_thread = running.RunThread_IntervalCache(item['cache'], pipe_data, block, request_state, input_data, tag=tag, cwd=cwd, env=env,
                                                       block_parent=block_parent, interval=item.get('interval', None),
                                                       duration=item.get('duration', None), history_maximum=item.get('history', None))
          
          sharedstate.Set('threads', item['cache'], run_thread)
          
          ## Add this to the handler
          #running.AddRunThread(run_thread)
          
          # Start the thread
          run_thread.start()
          
          # Wait until the first_run has been completed
          while run_thread.last_finished == None and run_thread.output != None:
            #print 'Waiting for first thread result for: %s' % item['cache']
            time.sleep(2.1) #TODO(g): Something better than this...
        
        else:
          #print 'Already have run_thread: %s' % item['cache']
          pass
        
        # Get the result, the last entry in it's history of output
        #result = run_thread.history[-1]
        result = run_thread.output
        
        # Update chain_output with result
        if type(result) == dict:
          pipe_data.update(result)
        else:
          # Get the python script
          python_script = item['script']
          log('Python Script Execute did not return dict: %s: %s' % (python_script, result), logging.ERROR)
      
      # Else, this is not an Interval Caching script, so just run it
      else:
        #print 'Running Python Script: Directly'
        
        # Get the python script
        python_script = item['script']
        
        # If we have a script prefix, and this isnt an absolute path, prefix it
        if script_path_prefix and not python_script.startswith('/'):
          python_script = '%s/%s' % (script_path_prefix, python_script)
        
        # Execute the script, get the result to update chain_output
        result = running.ExecuteScript(python_script, pipe_data, block,
                                       request_state, input_data, tag=tag,
                                       cwd=cwd, env=env,
                                       block_parent=block_parent)
        #result = running.ExecuteScript(python_script, tag, block, data, state, chain_output, env=env, block_parent=block_parent)
        #result = running.ExecuteScript(python_script, data, chain_output, state, env=None)
        
        # Update chain_output with result
        if type(result) == dict:
          pipe_data.update(result)
        else:
          log('Python Script Execute did not return dict: %s: %s' %
              (python_script, result), logging.ERROR)
    
    
    # Else, if we are 
    elif 'set' in item:
      # Set all the keypairs specified into our data
      for (key, value) in item['set'].items():
        # Update the data, we are using
        pipe_data[key] = value
    
    
    # Else, if we are Changing Directories
    elif 'cd' in item:
      dir = item['cd']
      
      # Check if any of our script_input keys are variables here
      found = False
      for key in pipe_data:
        if '%%(%s)' % key in dir:
          found = True
          break
      
      # If we found a script_input variable, then expand the variables
      if found:
        dir = dir % data
      
      #TODO(g): NOTTHREADSAFE: Is this safe to do outside of a child thread?
      #   It could screw things up...
      #TODO(g): ACTUAL FIX: DO THIS!: Just keep track of the CWD string, and
      #   append it, so it is ALWAYS an absolute path (security is better too),
      #   and that way it will be thread safe and not fucking up our relative
      #   pathed file loads!  (Dont do those relative EITHER!  Not thread safe!)
      log('Changing working directory: %s' % dir)
      os.chdir(dir)
    
    # Else, if we are execute Shell commands
    elif 'shell' in item:
      cmd = item['shell']
      
      log('Executing shell command: %s' % cmd)
      
      #TODO(g): Set up the ENV vars!
      #TODO(g): SECURITY:CRITICAL: Totally shit security.  FIX FIX FIX!!!
      #os.system(cmd)
      (status, output, output_error) = running.Run(cmd)
      
      if 'status' not in pipe_data:
        pipe_data['status'] = []
      if 'output' not in pipe_data:
        pipe_data['output'] = ''
      if 'output_error' not in pipe_data:
        pipe_data['output_error'] = ''
      
      pipe_data['status'].append(status)
      pipe_data['output'] += output
      pipe_data['output_error'] += output_error
    
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
  #TODO(g): How to make this not stomp on things?  So that this can be tracked
  #   in a useful way for things in a pipe...
  if 'duration' not in pipe_data:
    pipe_data['__duration'] = duration
  
  
  # Save when this script started, so we know which RRD slot it's best for
  pipe_data['__start_time'] = start_time

  
  #log('Script result: %s.%s.%s.%s: %s' % (script, deployment, service, instance_name, chain_output))
  
  
  return pipe_data


if __name__ == '__main__':
  script_data = {}
  script_data['run'] = [{'set':{'key':'value 555'}}, {'script':'control/control.py'}, {'script':'control/control.py'}]
  
  script_input = {}
  script_path_prefix = 'scripts'
  
  state = {}
  
  #output = RunScriptBlock(script_data, script_input, state, script_path_prefix)
  
  print output

