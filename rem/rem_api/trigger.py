#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Trigger
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def GetScripts_Trigger_Active(machine_id):
  """Returns any active trigger scripts to run locally on this machine.

  Returns: list of tuples (machine_trigger_instance.id, script,id)
  """
  data = []

  # Get all the active triggers on this machine (dont know about running
  #   locally yet), just that theyre not processing and are active
  sql = "SELECT * FROM machine_trigger_instance WHERE machine = %d AND active = 1 AND run_machine IS NULL" % machine_id
  result = Query(sql)

  # Loop over these active trigger instances, and find our details in the
  #   machine_trigger table
  for trigger in result:
    sql = "SELECT * FROM machine_trigger WHERE id = %d" % trigger['machine_trigger']
    item = Query(sql)[0]

    # If we want to run this on the local machine, otherwise ignore
    if item['on_local_machine']:
      # Add the trigger/script combo to be run on the local machine
      trigger_script = (trigger['id'], item['script'])
      data.append(trigger_script)

  return data


def TriggerScriptLogPreStart(trigger_instance_id):
  """Marks the machine_trigger_instance that the script has started."""
  sql = "UPDATE machine_trigger_instance SET run_machine = %d WHERE id = %d" % \
        (site_control.GetThisMachineId(), trigger_instance_id)
  Query(sql)


def TriggerScriptLogStart(trigger_instance_id, thread_id):
  """Marks the machine_trigger_instance that the script has started."""
  sql = "UPDATE machine_trigger_instance SET run_thread_id, = %d, run_start = NOW() WHERE id = %d" % \
        (thread_id, trigger_instance_id)
  Query(sql)


def TriggerScriptLogFinish(run_thread):
  """Invoked from run_script._RunThread, once this trigger script was run,
  by a function callback.
  """
  sql = "UPDATE machine_trigger_instance SET active = 0, exit_code = %d, output = '%s', run_end = NOW() WHERE id = %d" % \
        (run_thread.exit_code, SanitizeSQL(run_thread.output),
         run_thread.trigger_instance_id)
  Query(sql)


def RunLocalTriggerScript(machine_id, trigger_instance_id, script_id):
  """Runs a local script for an active trigger instance."""

  log('RunLocalTriggerScript: machine %s: trigger instance %s: script: %s' % \
        (machine_id, trigger_instance_id, script_id))

  # Log that this script has started, this avoicds a race condition with the
  #   script finishing before we know it's thread_id, which we update after it
  #   has actually started
  TriggerScriptLogPreStart(trigger_instance_id)

  # Run this command in a thread (thread_id is not tracked, just showing it)
  #NOTE(g):
  thread_id = run_script.RunScriptInThread(script_id=script_id,
                                           trigger_instance_id=trigger_instance_id,
                                           clean_on_finish=True,
                                           callback=TriggerScriptLogFinish)

  # Log that it started now, this second step avoids a race condition of the
  #   script finishing before we logged that it started.  All this does is
  #   update the thread_id, so it's ok if this is called after the callback
  #   logs that the script is finished
  TriggerScriptLogStart(trigger_instance_id, thread_id)



def SetTrigger_ReloadConfig_AllMachines(site=site_control.SITE_DEFAULT):
  """Insert a "Reload Configuration" trigger to all machines"""
  machines = GetMachines(site=site)

  for machine_id in machines:
    SetTrigger_ReloadConfig(machine_id, site=site)


def SetTrigger_ReloadConfig(machine_id, site=site_control.SITE_DEFAULT):
  """Insert a "Reload Configuration" trigger to this machine"""
  sql = "INSERT INTO machine_trigger_instance (machine, machine_trigger, active) VALUES " + \
        "(%d, 1, 1)" % machine_id
  Query(sql)



def TriggerMachinesToReloadConfigurations():
  """Trigger all our machines to reload their configuration, an event occurred."""
  #TODO(g):...
  pass#...


