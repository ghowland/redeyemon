#!/usr/bin/python


#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Run Script

Wraps running a script in a standardized way.  Handles all failure and corner
cases.

Handles running scripts that block, or in threads which dont block, and
handles queue threads after a maximum is reached, and logs all results to
Site Script, as long as a script_id is passed in.

Thread calls allow callbacks to handle updating things on finish.

TODO(g): Test run thread time.  Kill over N seconds?  Yes, but has to be set
    in DB, cant have a default because we dont know how long things might take,
    and some things have to be allowed to run for a long time sometimes, up
    to the user.
    
    Definitely need to warn when we run out of threads, and enlarge the pool,
    I think we stopped running things.
"""


import os
import threading
import time
import subprocess


# REM libraries
import site_control

# Import logging
from rem_util import *


# Singleton Instance of the _RunManager class
RUN_MANAGER_INSTANCE = None


# Maximum number of threads to created, then start queueing the requests
MAX_RUNNING_THREADS = 50


# Time until a thread who has already completed has until it will be cleared.
#   Badly written scripts, or ones that crash, will not release their threads,
#   but we dont want to track them forever.
#TODO(g): 1 hour may be too long, tune.
FINISHED_THREAD_EXPIRATION = 60 * 60 * 1 # 1 hour


# next_thread_id can get this high, then it goes back to 0.  ids are checked
#   before handed out, in case a low number is still around.
THREAD_ID_MAX_RESET_TO_ZERO = 10000


# Dont clean up the expired threads all the time, wastes cycles searching
#   through our thread list every time a script ends
EXPIRED_THREAD_CLEANUP_DELAY = 60 * 5 # 5 minutes


def Run(command):
  """Actually run the command on the local machine.  Blocks until complete.
  """
  output_error = '' #Later, how to handle reading the timing stream between the two?  It's lost...

  log('Run: %s' % command)

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

  if status != 0:
    log('Exit code is non-0: %s: %s' % (status, command))

  return (status, output, output_error)


def RunScript(script_id):
  """Runs a script, logs it Site Control.  Command is worked out automatically.
  
  TODO(g): Any timeout options in the future?
  """
  if script_id == None:
    msg = 'RunScript: script_id must be integer: "%s"' % script_id
    log(msg, logging.ERROR)
    raise Exception(msg)

  command = site_control.GetScriptCommand(script_id)

  #log('RunScript: %s: %s' % (script_id, command))

  start_time = time.time()

  # Run the command
  (exit_code, output, output_error) = Run(command)

  # Calculation duration
  duration = time.time() - start_time

  # Log this script's result
  site_control.MachineScriptLog(site_control.GetThisMachineId(), script_id,
                                exit_code, output, duration)

  return (exit_code, output)


def RunScriptInThread(script_id, service_script_id=None,
                      trigger_instance_id=None, clean_on_finish=True,
                      callback=None):
  """Runs a script, logs it Site Control.  Command is worked out automatically."""
  # Get the command
  command = site_control.GetScriptCommand(script_id)

  #log('RunScriptInThread: %s: %s' % (script_id, command))

  # Run in a thread
  return RunInThread(command, script_id, service_script_id=service_script_id,
                     trigger_instance_id=trigger_instance_id,
                     clean_on_finish=clean_on_finish, callback=callback)


def RunInThread(command, script_id=None, service_script_id=None,
                trigger_instance_id=None,
                clean_on_finish=True, callback=None):
  """Run the command on the local machine, in a thread.  Does not block.

  A thread_id is returned for this command, and calling IsThreadRunning()
  will return bool.

  Returns: int, thread_id.  The number of this thread in our manager.
  """
  # Create the run_thread and get it's thread_id, so it can be tracked
  thread_id = RunManager().AddRunThread(command, script_id=script_id,
                                        service_script_id=service_script_id,
                                        trigger_instance_id=trigger_instance_id,
                                        clean_on_finish=clean_on_finish,
                                        callback=callback)

  return thread_id


def HasThreadFinished(self, thread_id):
  """Has this thread finished?

  Im not wrapping the testing functions for this yet.  I think DoesThreadExist
  and HasThreadFinished is all users will care about.  We can change this later.
  """
  return RunManager().HasThreadFinished(thread_id)


def DoesThreadExist(thread_id):
  """Does this thread exist?  Returns: boolean"""
  return RunManager().DoesThreadExist(thread_id)


class _RunManager:
  """Manages the RunThreads needed to run lots of scripts on our local systems.

  Once run the scripts will block, so they are not worker threads.  Just single
  run, one time threads that call the Run() function in this module.
  """

  def __init__(self):
    # Store our threads in a dict, key=thread_id, value=_RunThread object
    self.threads = {}

    # RunThreads we created, but havent run yet, because we were at max threads
    #NOTE(g): RunThreads still go into self.threads, they are just here as
    #   well.
    self.queued_threads = []

    # Keep track of the next thread_id we are handing out.  We go in order
    #   to
    self.next_thread_id = 0

    # We need to make sure AddRunThread() is thread safe
    self.lock = threading.Lock()

    # The last time we ran the cleanup function
    self.last_cleanup_time = 0


  def GetRunThread(self, thread_id):
    return self.threads[thread_id]


  def AddRunThread(self, command, script_id=None, service_script_id=None,
                   trigger_instance_id=None, clean_on_finish=True,
                   callback=None):
    """Adds a run thread to our dict of them, returns it's thread_id.

    Returns: int, thread_id
    """
    # Acquire our Lock, so we are thread safe.  next_thread_id must be accurate.
    self.lock.acquire()

    # Create a _RunThread object, using our next_thread_id to keep an ordered
    #   list of all our threads.
    run_thread = _RunThread(self.next_thread_id, command, script_id,
                            service_script_id, trigger_instance_id,
                            clean_on_finish, callback, self)

    # Store the run_thread in our threads
    self.threads[self.next_thread_id] = run_thread

    # Increment the next_thread_id, so we are making uniquely identified threads
    self.next_thread_id += 1

    # If we have too many threads running already
    if len(self.threads) >= MAX_RUNNING_THREADS:
      log('Maximum threads in use(%s): Queueing this command (q len=%s): %s' % \
          (MAX_RUNNING_THREADS, len(self.queued_threads), command))
      # Add this to are pending thread queue
      self.queued_threads.append(run_thread)

    # Else, run the thread immediately
    else:
      # Start the run_thread, so our command is running
      run_thread.start()

    # Release our Lock
    self.lock.release()


  def DoesThreadExist(self, thread_id):
    """Does this thread exist?
    We dont delete threads until requested, so the process that starts it
    should be able to find it until they release it.
    """
    # If it's in the threads dict, it exists
    return thread_id in self.threads


  def IsThreadRunning(self, thread_id):
    """Is this thread running?"""
    # If there is no exit_code yet, it's still running
    is_finished = self.threads[thread_id].exit_code != None
    has_started = not self.threads[thread_id].start_time == None

    # Has it started, but not finished yet?
    is_running = has_started and not is_finished

    return is_running


  def IsThreadQueued(self, thread_id):
    """Is this thread queued?  Max running threads reached, pending others."""
    # If the thread hasnt started yet, it is queued
    return self.threads[thread_id].start_time == None


  def HasThreadFinished(self, thread_id):
    """Has this thread finished running?  Most useful test, others are tests."""
    # If this thread has a non-None exit_code, it is finished
    return self.threads[thread_id].exit_code != None


  def _CleanupOldThreads(self):
    """Clean up threads that have been completed longer than the max time.

    Badly written scripts did not release them, or crashed.
    """
    # If we have done a cleanup more recently than our delay time, skip this
    if self.last_cleanup_time + EXPIRED_THREAD_CLEANUP_DELAY > time.time():
      return

    for thread_id in self.threads:
      run_thread = self.threads[thread_id]

      # If this script has been run, and marked finished
      if run_thread.exit_code != None and run_thread.finish_time:

        # If it finished long enough ago to be cleaned up.  Grammar police!
        if run_thread.finish_time + FINISHED_THREAD_EXPIRATION < time.time():

          # Delete this thread, and it's gone.  Poof!
          del self.fields[thread_id]

    # Save that we did a cleanup, so we can delay runs and dont burn resources
    #   as this function will be called much more frequently than needed
    self.last_cleanup_time = time.time()


  def ThreadFinished(self, thread_id):
    """A thread is announcing itself as finished.  Now we can check in any
    threads are in our pending queue and start them.
    """
    # Remove this thread
    if thread_id in self.threads:
      del self.threads[thread_id]
    else:
      log('Thread ID %s not found in thread pool' % thread_id, logging.CRITICAL)
    
    #DEBUG: Show all our commands of running threads
    if 1 and self.queued_threads:
      # Print all the commands we have still running sucking up all our threads
      msg = 'Queued threads exist, here are the commands and threads they are taking up: \n'
      # Key = command, value = thread count
      commands = {}
      for cur_thread_id in self.threads:
        thread = self.threads[cur_thread_id]
        if thread.command not in commands:
          commands[thread.command] = 0
        commands[thread.command] += 1
      # Sort dict by values, commands = tupples (command, count)
      commands = [(k, v) for (v, k) in commands]
      for (command, count) in commands:
        msg += '  %s=%s\n' % (command, count)
      log(msg)
    
    # While we have queued threads and arent at our running thread maximum
    while self.queued_threads and len(self.threads) < MAX_RUNNING_THREADS:
      # Start the first thread
      self.queued_threads[0].start()

      # Remove the first thread, it has been started
      self.queued_threads.remove(self.queued_threads[0])

    # Now is also a great time to clean up old threads.
    self._CleanupOldThreads()



class _RunThread(threading.Thread):
  """Internal use only.  This is the thread for running a script.
  """

  def __init__(self, thread_id, command, script_id, service_script_id,
               trigger_instance_id, clean_on_finish, callback, run_manager):
    """Init the Run Thread

    Args:
      thread_id: int, identified for the thread
      command: str, command to run
      script_id: int or None, script.id
    """
    self.thread_id = thread_id
    self.command = command
    self.script_id = script_id
    self.service_script_id = service_script_id
    self.trigger_instance_id = trigger_instance_id
    self.clean_on_finish = clean_on_finish
    self.callback = callback
    self.run_manager = run_manager

    # log_id tracks the log_script_run.id for saving our input.  This way
    #   we know when a service_script was involved.
    self.log_id = None

    # Output vars
    self.exit_code = None
    self.output = None
    self.output_error = None

    # Time we were created.  Important for queued items, waiting around
    self.init_time = time.time()

    # Time we starting running the script
    self.start_time = None

    # Save when it completes, so we can clean up old ones
    self.finish_time = None


    # Initialize the thread
    threading.Thread.__init__(self)


  def GetRunDuration(self):
    """Returns seconds this has been running."""
    return self.start


  def run(self):
    """Runs the command in a thread.  The thread ends once the command finishes.

    If this is a command run with a script_id, this thread will be logged into
    the Site Control database in log_script_run.  If it has a service_script_id
    it will also have that saved, which is used by the Script Runner to
    determine when scripts need to be run (cron type functionality).

    The log is initiated before the command is run, so that it is visible
    the command is in progress, and when it is completed the log is updated
    to save the exit code and output, and how long it took to complete.
    """
    #TODO(g): self.output_error.  Two streams problem.

    # Start the clock!
    self.start_time = time.time()

    # If we know the script_id, then log this in SiteControl
    if self.script_id:
      machine_id = site_control.GetThisMachineId()

      # Get the log_id, so we can track that it is running in Site Control
      self.log_id = site_control.MachineScriptLogStart(machine_id, self.script_id,
                        service_script_id=self.service_script_id)

    # Run our script, then the thread ends
    try:
      (self.exit_code, self.output, self.output_error) = Run(self.command)
    except Exception, e:
      #NOTE(g): This is an impossibility for a process, so we know it's an exception
      self.exit_code = -1
      self.output = ''
      #TODO(g): Dump whole stack in output
      self.output_error = 'RunThread Run() exception: %s' % e

    # Save temp version of finish time, so we can log the duration
    temp_finish_time = time.time()

    # Get our run duration
    run_duration = temp_finish_time - self.start_time

    # If we know the script_id, then close the log for this in SiteControl
    if self.script_id:
      # Get the log_id, so we can track that it is running in Site Control
      site_control.MachineScriptLog(machine_id, self.script_id,
                                    self.exit_code, self.output, run_duration,
                                    service_script_id=self.service_script_id,
                                    log_id=self.log_id)


    # Save time it finished, so we can clean abandoned ones later
    self.finish_time = temp_finish_time

    # If we have a callback, call it
    if self.callback:
      # Call it, and pass in ourself, so it has access to our state (only
      #   reason they would want it)
      self.callback(self)

    # Tell the RunManager that we are finished
    self.run_manager.ThreadFinished(self.thread_id)
    
    # We are finished, the thread just ends
    pass


def RunManager():
  """Wraps the _RunManager class, returning a singleton object.  We only want 1.

  Returns: _RunManager object
  """
  global RUN_MANAGER_INSTANCE

  # If the singleton hasnt been instanced yet, create it
  if not RUN_MANAGER_INSTANCE:
    RUN_MANAGER_INSTANCE = _RunManager()

  return RUN_MANAGER_INSTANCE
