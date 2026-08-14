#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Scripts
"""


import time
import os
import imp


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def GetScripts():
  """Returns dict of all the scripts, keyed on the script.id."""
  scripts = {}

  sql = "SELECT * FROM script"
  result = Query(sql)

  for item in result:
    scripts[item['id']] = item

  return scripts


def GetScript(script_id):
  """Returns field dict for a script_id"""
  sql = "SELECT * FROM script WHERE id = %d" % script_id
  item = Query(sql)[0]

  #log('Script: %s (%s): %s' % (item['name'], script_id, stack.Mini(4)))

  return item


def RunLocalServiceScript(machine_id, script_id, service_script_id):
  """Runs the specified service script on this local machine.
  """
  #log('RunLocalServiceScript: machine %s: script %s: service_script: %s' % \
  #      (machine_id, script_id, service_script_id))

  # Run this command in a thread (thread_id is not tracked, just showing it)
  thread_id = run_script.RunScriptInThread(script_id=script_id,
                                           service_script_id=service_script_id,
                                           clean_on_finish=True)


def MachineScriptLogStart(machine_id, script_id, service_script_id=None):
  """Log that this script has been started, when the finishing is not being
  waited for.

  If the script was run and waited for, just use MachineScriptLog and do
  all the input at once.

  The reason for this is that some jobs may not complete, and we want to track
  that, so we start those and log them, and then we can check their progress
  later.

  Returns: int, log id to use to update with MachineScriptLog() result
  """
  if not service_script_id:
    sql = "INSERT INTO log_script_run (machine, script, run) VALUES (%d, %d, NOW())" % \
          (machine_id, script_id)
  else:
    sql = "INSERT INTO log_script_run (machine, script, service_script, run) VALUES (%d, %d, %d, NOW())" % \
          (machine_id, script_id, service_script_id)

  log_id = Query(sql)

  return log_id


def MachineScriptLog(machine_id, script_id, exit_code, output, run_duration,
                     service_script_id=None, output_error=None, log_id=None):
  """Log that this script has been run, and result.

  log_id was received when MachineScriptLogStart() was run to initation this.
      If not specified or None, then this command is considered to be completed
      already, and will both start and finish it with this command.

      TODO(g): What if a matching log event was already started and not finished?
          Seems like extra logic may be useful here.  LATER!  Not critical.
  """
  # If we know the Id
  if log_id:
    #TODO(g): Add output error, when we have it from our scripts (not in now)
    sql = "UPDATE log_script_run SET output = '%s', exit_code = %d, run_duration = %0.4f WHERE id = %d" % \
          (SanitizeSQL(output), exit_code, run_duration, log_id)
    Query(sql)

  # Else, we dont know the ID, so it's a now entry that is complete
  else:
    # Init the script, and get a log id
    log_id = site_control.MachineScriptLogStart(machine_id, script_id,
                                   service_script_id=service_script_id)

    # Finish it with ourselves (will not recurse)
    site_control.MachineScriptLog(machine_id, script_id, exit_code, output, run_duration,
                     service_script_id=service_script_id,
                     output_error=output_error, log_id=log_id)


def GetScriptLastRunLog(machine_id, script_id, service_script_id=None):
  """Returns the log field data for the last time this script ran."""
  if not service_script_id:
    sql = "SELECT * FROM log_script_run WHERE machine = %d AND script = %d AND ORDER BY run DESC LIMIT 1" % \
          (machine_id, script_id)
  else:
    sql = "SELECT * FROM log_script_run WHERE machine = %d AND script = %d AND service_script = %d ORDER BY run DESC LIMIT 1" % \
          (machine_id, script_id, service_script_id)

  result = Query(sql)

  if not result:
    return None
  else:
    return result[0]


def ScriptRunRequired_MachineService(machine_id, script_id, service_script_id,
                                     site=site_control.SITE_DEFAULT):
  """Does this script require running?  The Site Control API will decide.

  This way all script running is determined by a hardened algorithm using the
  run logs, and the data inside the service_script.id record to determine
  if this script needs to be run again, or has been run with the equivalent
  args recently.

  Returns: boolean, run this script?
  """
  # Deny by default
  should_run_script = False

  # Get the last for the last time this was run
  last_run_log = GetScriptLastRunLog(machine_id, script_id, service_script_id)

  # If its never been run before
  if not last_run_log or last_run_log['run'] == None:
    script_last_run = 0
    run_already_today = False
  # Else, it has, convert it to time.time() format
  else:
    script_last_run = ConvertTimeToEpoch(last_run_log['run'])

    # If the last run time is the same as our date, then we already ran this today
    if last_run_log['run'].timetuple()[:3] == last_run_log['run'].today().timetuple()[:3]:
      run_already_today = True
    else:
      run_already_today = False

  # Get when this script should run next
  script_next_run = None

  # Get the service_script item data
  service_script = site_control.GetServiceScript(service_script_id)

  # We dont manage scripts that are always running, a process monitor (like
  #   Monit) does.
  if service_script['is_always_running']:
    return False #NOTE(g): Dont log this, it's the design not to handle these

  machine = site_control.GetMachine(machine_id)
  site_config = site_control.GetSiteConfig(machine['site'])

  # If we care about the machine status, ensure it's the right one or fail
  if service_script['run_on_machine_status'] and \
      service_script['run_on_machine_status'] != machine['status']:
    #log('%d: Machine in wrong status (RunOnStatus:%s != MachineStatus:%s)' % \
    #    (script_id, service_script['run_on_machine_status'], machine['status']))
    return False

  #TODO(g): All the day stuff, but Im not using those right now (just run_delay)
  #   and that works as-is, so

  # --

  # -- Need to get the last time-of-day, day-of-week, day-of-month,
  #     and week-of-month, and determine if these are later than the one
  #     when this ran last.  Each of these things must pass

  # --

  # True, if later than the time of day listed
  correct_time_of_day = True

  # True, if the same day of week
  correct_day_of_week = True

  # True, if the correct day of the month
  correct_day_of_month = True

  # True, if the correct week of the month
  correct_week_of_month = True

  # If run delay is not specified, do not run this
  if not service_script['run_delay']:
    return False

  # True, if enough time has lapsed
  correct_run_delay = True
  if service_script['run_delay']:
    # Fail if it is not later than the last run plus the run delay
    if time.time() - script_last_run <= int(service_script['run_delay']):
      correct_run_delay = False

  # Else, we have no run_delay, so fail if it's trying to run faster than
  #   our site's run delay default
  elif script_last_run + int(site_config['script_run_delay_default']) > time.time():
    log('%d: Site Default delay not met' % script_id)
    return False

  # If all our checks work out, run it
  if correct_run_delay and correct_day_of_week and correct_time_of_day \
      and correct_day_of_month and correct_week_of_month:
    should_run_script = True

  # Else, log reason for not running it (Noisy!)
  else:
    pass
    #script = GetScript(script_id)
    #log('%s (%d): Failed due to not passing flags: Delay=%s DayOfWeek=%s TimeOfDay=%s DayOfMonth=%s WeekOfMonth=%s: Run Seconds Age: %0.1f, Run Delay: %s' % \
    #      (script['name'], script_id, correct_run_delay, correct_day_of_week,
    #       correct_time_of_day, correct_day_of_month, correct_week_of_month,
    #       time.time() - script_last_run, service_script['run_delay']))

  return should_run_script


def GetScriptCommand(script_id):
  """Returns the full path of the command that must be run for this script."""
  machine_id = site_control.GetThisMachineId()
  site = site_control.GetSiteByMachine(machine_id)
  site_config = site_control.GetSiteConfig(site)

  script = GetScript(script_id)

  # Build the command from the path to scripts and the relative path of the script
  command = '%s/%s' % (site_config['path_script'], script['path_relative_script'])

  return command




def GetScriptPythonModule(script_id):
  """Will return a Python module for this script_id, or None."""
  # Get the script file name for this item
  script_filename = site_control.GetScriptFullFileName(script_id)
  log('Script: %s (%s)' % (script_filename, script_id)) 
  
  # Get the name and path, we need them seperate
  name = os.path.basename(script_filename)
  path = os.path.dirname(script_filename)
  
  # Split the suffix off the name
  if name.endswith('.py'):
    name = name[:-3]
  else:
    # Skip this one, but report it as a critical failure
    log('Script (%d) is not a python text file or is improperly named: %s' % \
        (item['script_call'], script_filename), logging.CRITICAL)
    return None
  
  # Open a file handle to this file
  fp = open(script_filename, 'r')
  
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
      log('Failed to import script (%d): %s: %s' % \
          (script_id, script_filename, e), logging.CRITICAL)
    except Exception, e:
      log('Failed to import script for non-import reasons (%d): %s: %s' % \
          (script_id, script_filename, e), logging.CRITICAL)
  
  finally:
    # Close the file handle whether there was an exception or not
    fp.close()
    
  
  # Failed
  return None


def GetScriptFullFileName(script_id):
  """Returns the absolute path to this script, or None if not found."""
  script = GetScript(script_id)
  
  if not script:
    return None
  
  #TODO(g): Unhardcode this, its in site_config table
  SCRIPT_PATH = '/usr/local/site_control/rem/rem_scripts/%s'
  
  # Generate the full path to this script
  full_path = SCRIPT_PATH % script['path_relative_script']
  
  return full_path


class ExecuteScriptNotFound(Exception):
  """If we cant find a Python module for a specified script, throw this."""


class ExecuteFunctionNotFound(Exception):
  """If we cant find a Python module's Execute function, throw this."""


def ExecuteScript(script_id, data, state):
  """Execute this script.  Returns result.
  
  Throws: ExecuteScriptNotFound, ExecuteFunctionNotFound
  """
  script = GetScript(script_id)
  
  # Get the python module
  script_module = site_control.GetScriptPythonModule(script_id)
  if script_module == None:
    raise ExecuteScriptNotFound('Module for script not found: %s' % script_id)
  
  log('Executing: %s   Module: %s' % (script['name'], script_module))
  
  # Get the Execute function
  execute_function = getattr(script_module, 'Execute', None)
  if execute_function == None:
    raise ExecuteFunctionNotFound('Execute() for script not found: %s' % script_id)
  
  # Call the function
  log('Executing Script(%d): %s: %s' % (script_id, script['path_relative_script'], data))
  try:
    result = execute_function(data, state)
  except Exception, e:
    log('Script Failure: %s (%s): %s' % (script['path_relative_script'], script_id, e))
    log('\n' + error_info.GetExceptionDetails(webify=False))
    raise e
  
  return result
  
