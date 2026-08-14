"""
running

Running threads and shell commands, for procblock.
"""


import subprocess
import threading
import builtins
import time
import os
import copy

import sys
sys.path.append('../')
from shared import error_info

from shared import log as logging
from shared.log import log

from shared import sharedlock

from run import code_python


# Default number of maximum history to keep for this interval cache
RUN_CACHE_DEFAULT_HISTORY_MAXIMUM = 100

# Default interval for run cache, in seconds, if not specified
RUN_CACHE_DEFAULT_INTERVAL = 5


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
  



def ExecuteScript(python_script, pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):
#def ExecuteScript(python_script, tag, block, data, state, chain_output, env=None, block_parent=None):
  """Execute the specified script.  This will ensure it is imported, and
  re-imported if the code changes on the disk.
  
  TODO(g): Implement in-memory cache of md5-sums from the Manager, specifying
      the md5-sum of each script, and do not import if it is not the same.
      Instead, alert on a locally changed script.
  """
  
  # Import the Python Script module
  script_module = code_python.GetPythonScriptModule(python_script)
  
  if script_module == None:
    log('Failed to find python script: %s' % os.path.abspath(python_script), logging.ERROR)
    return
  
  # Execute the script, and return the data (which will update chain_output)
  try:
  #if 1:
    ##DONE(g): SUPER AWESOME!: Change Execute() to ProcessBlock() so that EVERY
    #   program written for procblock is SEEN as a block processor.  So people
    #   think that they are writing another processor in a chain of processors
    #   which can spawn more chains of processors at whim.  It's an integrated
    #   way of thinking about how code fits into the bigger picture...
    #         ...AND ITS THE SAME!!!  The SAME as all the data procblocks.
    result = script_module.ProcessBlock(pipe_data, block, request_state,
                                        input_data, tag=tag, cwd=cwd, env=env,
                                        block_parent=block_parent)
    #result = script_module.ProcessBlock(tag, block, data, state, chain_output, env=env, block_parent=block_parent)
    #TODO(g): Remove this old method when it's not needed any more.
    #result = script_module.Execute(data, chain_output, state, env)
  except Exception, e:
    #TODO(g): Print the exception out here, so we keep all this data together,
    #   Im only doing it this less-optimal way (exception and python script
    #   are not in the same lines, and will be hard to see when threaded),
    #   because I havent baked Python 2.6 into the EC2 AMIs yet.
    log('Exception in script: %s: %s' % (python_script, e))
    #raise RunScriptFailedCondition(e)#TODO(g): Better...
    raise
  
  return result


class RunScriptFailedCondition(Exception):
  """Failed to pass all "if" conditions."""



class RunThreadHandler:

  def __init__(self):
    self.run_thread_id_next = 0
    self.run_thread_id_lock = threading.Lock()
    
    self.run_thread_objects = {}
  
  
  def GetNextRunThreadId(self):
    """Returns the next action_id, for a new RunThread."""
    self.run_thread_id_lock.acquire()
    
    # Save next ID
    next_id = self.run_thread_id_next
    
    # Increment next ID
    self.run_thread_id_next += 1
    
    self.run_thread_id_lock.release()
    
    return next_id
  
  
  def Add(self, run_thread_object):
    """Adds this run_thread_object.  Get() by run_thread_object.id"""
    self.run_thread_objects[run_thread_object.id] = run_thread_object
  
  
  def Get(self, run_thread_id):
    """Returns run_threadObject specified, or None if not found."""
    if int(run_thread_id) in self.run_thread_objects:
      return self.run_thread_objects[int(run_thread_id)]
    else:
      return None



class RunThread(threading.Thread):

  def __init__(self, run_thread_id, pipe_data, block, request_state,
               input_data, tag=None, cwd=None, env=None, block_parent=None):
  #def __init__(self, run_thread_id, run_block_data, data, state, chain_output,
  #             env=None, cwd=None):
    self.id = run_thread_id
    self.run_block_data = copy.deepcopy(block)
    
    self.pipe_data = pipe_data
    self.request_state = request_state
    # Ensure input_data is a separate dictionary, and will not update the
    #   original if a programmer does something sloppy.
    #NOTE(g): This is NOT a deepcopy, so a programmer could still update a
    #   sub-item, since they are still the same references.  If they want to
    #   do that, I'm letting them, even though it is sloppy design wise, it is
    #   not worth the effort to build the wall, and still provide easy access.
    #   This is a rapid development effort, all optimization is for short
    #   development times and desired functionality correctness, not stopping
    #   people from hanging themselves with the rope that gives them.
    if type(input_data) in (dict, ):
      self.input_data = dict(input_data)
    else:
      self.input_data = None
    self.tag = tag
    self.cwd = cwd
    self.env = env
    self.block_parent = block_parent
    
    # When we have finished running, the chain_output goes here
    self.output = None
    
    # Add ourselves to our pipe_data, our run script block needs this
    self.pipe_data['run_thread'] = self
    
    # Running flags
    self.create_time = time.time()
    self.has_started = False
    self.is_running = False
    self.status = None
    self.success = None
    self.run_start = None
    self.run_finish = None
    self.error = None
    
    # For now, just save each of these as text, can create objects later
    #TODO(g): Create ActionStage(name, message, status), for BEGIN/UPDATE/END
    #   so we can track all stages of running hyper-intelligently...
    self.stages = []
    
    # Initialize the super class for the thread
    threading.Thread.__init__(self)
  
  
  def StageBegin(self, name, message):
    """Logging Stages: Begin a new stage"""
    data = {'type':'begin', 'time':time.time(), 'name':name, 'message':message}
    self.stages.append(data)
  
  
  def StageUpdate(self, name, message):
    """Logging Stages: Begin a new stage"""
    data = {'type':'update', 'time':time.time(), 'name':name, 'message':message}
    self.stages.append(data)
  
  
  def StageEnd(self, name, message, status):
    """Logging Stages: Begin a new stage"""
    data = {'type':'end', 'time':time.time(), 'name':name, 'message':message,
            'status':status}
    self.stages.append(data)
  
  
  def StageError(self, name, message):
    """Logging Stages: Begin a new stage"""
    data = {'type':'error', 'time':time.time(), 'name':name, 'message':message}
    self.stages.append(data)
  
  
  def Log(self, name, message):
    """Logging:  Regular old logging."""
    data = {'type':'log', 'time':time.time(), 'name':name, 'message':message}
    self.stages.append(data)
  
  
  def run(self):
    # We're starting
    self.has_started = True
    self.run_start = time.time()
    
    self.is_running = True
    
    #TODO(g): Add the ActionObject to data, so we can do StageStart/StageUpdate/StageEnd function calls and shit
    #TODO(g): Get the scripts path out of the run_block_data['scripts']?
    try:
      self.output = builtins.RunBlock(self.pipe_data, self.run_block_data,
                                      self.request_state, self.input_data,
                                      tag='run', cwd=self.cwd, env=self.env,
                                      block_parent=self.block_parent)
      #self.output = builtins.RunBlock('run', self.run_block_data, self.data,
      #                                self.state, self.chain_output,
      #                                env=self.env)
      #self.output = RunScriptBlock(self.run_block_data, self.data,
      #                                      'scripts')
    except Exception, e:
      details = error_info.GetExceptionDetails()
      self.error = details
      log(details, logging.ERROR)
    
    self.is_running = False
    self.run_finish = time.time()
  
  
  def Render(self):
    """Render all the interesting information about the state and our Stages."""
    if self.error:
      output = '<h4 style="color: red">ERROR: %s</h4>\n' % self.error
    elif self.run_finish:
      output = '<h4>Completed: Duration %0.1f seconds</h4>\n' % (self.run_finish - self.run_start)
      if 'output' in self.output:
        output += '<br>%s<br><br>' % self.output['output']
    elif self.is_running:
      output = '<h4>Running... %0.1f seconds</h4>\n' % (time.time() - self.run_start)
    else:
      output = '<h4>Not yet running...</h4>\n'
    
    # Render our stages, in reverse order so newest is first
    stages = list(self.stages)
    stages.reverse()
    output += '<table border="1" cellspacing="0">\n'
    for stage in stages:
      output += '<tr>'
      output += '  <td valign="top"><b>%s</b></td>\n' % stage['name']
      output += '  <td valign="top" width="10%%">%0.1fs</td>\n' % (stage['time'] - self.run_start)
      output += '  <td valign="top">%s</td>\n' % stage['type'].upper()
      output += '  <td valign="top">%s</td>\n' % stage['message']
      if 'status' in stage:
        if stage['status']:
          output += '  <td valign="top" style="color: green">Success</td>\n'
        else:
          output += '  <td valign="top" style="color: red">Failure</td>\n'
      else:
        output += '  <td valign="top">&nbsp;</td>\n'
      
      output += '</tr>\n'
    output += '</table>\n'
    
    #output += '<br><br>Run Thread: %s' % self.id
    
    return output


class RunThread_IntervalCache(RunThread):
  """This run thread will run a block at a specified interval until a timer
  has expired or a lock is released.
  """
  
  def __init__(self, run_thread_id, pipe_data, block, request_state,
               input_data, tag=None, cwd=None, env=None, block_parent=None,
               interval=None, run_lock='__running', duration=None,
               history_maximum=None):
    """Creates a RunThread with extra parameters to cache the content, and
    repeat the run every interval-seconds, until either a run_lock is released
    or the duration (if specified) is over.
    """
    # Initialize the run thread.
    RunThread.__init__(self, run_thread_id, pipe_data, block, request_state, input_data,
              tag=tag, cwd=cwd, env=env, block_parent=block_parent)
    
    # Save extra information
    if interval != None:
      self.interval = interval
    else:
      self.interval = RUN_CACHE_DEFAULT_INTERVAL
    self.run_lock = run_lock
    #NOTE(g): Duration allows impromtu timeseries collection!  Just run a
    #   5 second interval (or 1 second!) script for 30 seconds, and return the
    #   result, and process the time series, to discover data you dont want to
    #   monitor all the time!
    self.duration = duration
    if history_maximum != None:
      self.history_maximum = history_maximum
    else:
      self.history_maximum = RUN_CACHE_DEFAULT_HISTORY_MAXIMUM
    
    # History of outputs
    self.history = []
    
    # The last time this interval RunThread was run
    self.last_run = None
    
    # The last time this interval RunTHread was finished running
    self.last_finished = None


  def run(self):
    print 'Running Thread: Starting: %s' % self.id
    
    # We're starting
    self.has_started = True
    self.run_start = time.time()
    
    self.is_running = True
    
    # Loop forever, until either the run_lock is released, or the duration has expired
    while (self.run_lock and sharedlock.IsLocked(self.run_lock)) or (self.duration and self.create_time + self.duration < time.time()):
      try:
        # The last time we were run...
        self.last_run = time.time()
        
        # Track whether this run attempt is the only run attempt with this mutex
        #TODO(g): Does this make any sense as it is?  I thought it was useful
        #   when I thought of this, and so I coded it, but now it seems pointless.
        #   The thread is the only one with this ID and of course it's single-threaded
        #   in itself...  We'd need a truly unique name, so that run-simul couldnt
        #   run multiple of something, since theyd have different IDs.
        #mutex_held = False
        
        # This thread will 
        #if sharedlock.Acquire('mutex.run_thread.%s' % self.id):
        #  mutex_held = True
        if 1:
          
          # Remove the cache from the run block, so it is run normally.
          #run_block = dict(self.run_block_data)
          
          # Ensure we will run this block once, were alread in the thread
          if 'cache' in self.run_block_data[0]:
            #print '++ Removing cache directive from self.run_block_data'
            del self.run_block_data[0]['cache']
          
          #print 'Running block: %s' % self.run_block_data
          self.output = builtins.RunBlock(self.pipe_data, self.run_block_data,
                                          self.request_state, self.input_data,
                                          tag='run', cwd=self.cwd, env=self.env,
                                          block_parent=self.block_parent)
          
          #print 'Output: %s' % self.output
          
          # Add the latest output to our history
          self.history.append(self.output)
          
          # If our history is over the max, then crop it to the max
          if len(self.history) > self.history_maximum:
            self.history = self.history[-self.history_maximum:]
          
          # Mark the last time we finished running
          self.last_finished = time.time()
          
          # Sleep our interval
          #TODO(g): CRITICAL: Reduce out time it took to run, intervals should be
          #   even, not gapped
          time.sleep(self.interval)
      
      except Exception, e:
        details = error_info.GetExceptionDetails()
        self.error = details
        log(details, logging.ERROR)
      
      ## If we hold the mutex, always release it
      #finally:
      #  if mutex_held:
      #    sharedlock.Release('mutex.run_thread.%s' % self.id)
    
    self.is_running = False
    self.run_finish = time.time()
    
    print 'Running Thread: Quitting: %s' % self.id

