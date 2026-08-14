#!/usr/bin/python


#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control Script Runner
  Run from rem_client.py

This checks in with Site Control DB as the brain, via site_control_client API,
and runs appropriate local scripts, and logs start/finish-output to the
Site Control DB.
"""


from threading import Thread
import time
import os


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


#TODO(g): Remove this after proving.  All DR is handled through our S3
#   master backup and election process.  This is not needed at all.
## This is the hard coded script that will be run if site control cant be found.
##   If run, this thread will block on this command completing, as there is
##   no reason to do anything else until Site Control is recovered.
#SITE_CONTROL_DISASTER_RECOVERY_SCRIPT = '/root/scripts/rem_disaster_recovery.sh'
#
#
## In case no state has ever been saved on this machine for Site Control,
##   we will use this name (instead of Site Config var) as the Write Master DB
##   for Site Control, and any Disaster Recovery efforts will focus here.
##   Internal DNS and DB are the key elements in bringing everything back up.
#SITE_CONTROL_MASTER_DNS_OF_LAST_RESORT = 'sitecontrol01' # Is this needed now that we have a script?


class SiteControlScriptRunner(Thread):
  """Runs scripts (like a seconds-based cron) specified by Site Control.

  All scripts are local, so no information is fed it beside what script to run
  and args that reference Site Control table rows by ids.

  This thread also runs scripts for triggers marked to be run on this machine.

  Pretty much all jobs are handled through this, since all process control
  and scripts are based on services.  These then have scripts that run, and
  are run by this process, unless they are supposed to always run, and then
  a monit configuration file is created for them, as monit is a better
  tested long-running process enforcer.
  """

  def __init__(self, state=None):
    if not state:
      state = {'not_quitting':False}

    self.state = state

    # Get this machine.id.  This can be done, even if Site Control DB is
    #   unavailable, via a cached file, if SC has ever been run here
    self.machine_id = site_control.GetThisMachineId()

    # Our machine info
    self.machine = site_control.GetMachine(self.machine_id)

    # We will keep our updated site configuration fields here
    self.site_config = None

    # Initialize this as a Thread
    Thread.__init__(self)


  def run(self):
    """Once start() is called, this function is executed, which is the thread's
    run function.
    """
    self.StartDirectly()


  def StartDirectly(self):
    """Calling by run() for threaded more, or directly to run without a thread."""
    
    #TODO(g): Do we cache our scripts, and then re-cache on Reconfigure?  Which
    #   happens every 5 minutes?  For now just naively cache scripts all the
    #   time.  I think the API should wrap caching, if at all, and people
    #   should use it naively and let it make the system decisions to not
    #   outsource these difficult problems of cache/poison/update/timing issues.
    
    
    #TODO(g): Trigger scripts.  Need to check for those too.
    
    while self.state['not_quitting']:
      #try:
      if 1:
        # Update our self-understanding, our status and stuff will change
        self.machine = site_control.GetMachine(self.machine_id)
        
        # Let us know who we are
        log('Running: %s    Master: %s' % \
            (site_control.GetMachineStatusName(self.machine['status']),
             self.state['is_site_control_master']))
        
        # Run our REM disaster recovery scripts:  First, disasters dont wait.
        self.RunRemDisasterRecoveryScripts()
        
        # Get the site config
        self.site_config = site_control.GetSiteConfig(site_control.GetSiteByMachine(self.machine_id))
        
        # Run our service scripts
        self.RunServiceScripts()
        
        # Run our trigger scripts
        self.RunTriggerScripts()
        
        # Give back to the system as we spin loop
        time.sleep(float(self.site_config['run_delay_script_runner']))
      
      ## Log and ignore, if we can
      #except Exception, e:
      #  try:
      #    print 'SiteControlScriptRunner: Unhandled exception: %s' % e
      #    site_control.LogMachineError(self.machine_id, 'SiteControlScriptRunner: %s\n%s' % (e, stack.Mini(5, 1)))
      #  except:
      #    print 'SiteControlScriptRunner: Failed to log error.'
      #    pass # If this wont work, we just keep trudging on


  def RunServiceScripts(self):
    # Get all the scripts to be run on this machine
    scripts = site_control.GetMachineServiceScripts(self.machine_id)

    # Loop through each script (two-levels, script->[service_scripts,...]
    for script_id in scripts:
      service_scripts = scripts[script_id]
      
      #NOTE(g): We only want to run any given script once.  They are all single
      #   purpose and running more than once just causes problems
      
      # Take the first service script to run as
      service_script_id = service_scripts[0]
      service_script = site_control.GetServiceScript(service_script_id)
      
      
      ## Process every service_script
      #for service_script_id in service_scripts:
      
      # Process one script for all services
      #TODO(g): Make this work for more than one service, while still not
      #   re-running scripts that are the same thing for each service.
      #   Maybe add a flag in script that says it is not service dependent?
      #   None of them are now, so easy default...
      if 1:
        # Get the service script
        service_script = site_control.GetServiceScript(service_script_id)

        # Ask Site Control if we should run this script now?
        run_now = site_control.ScriptRunRequired_MachineService(self.machine_id, script_id, service_script_id)
        #print 'RunServiceScripts: %s: %s' % (script_id, run_now)

        # If we are going to run this, let the API handle executing it so
        #   that all the logging is done properly.  We dont have about the
        #   result or anything but whether it will be run.
        if run_now:
          #NOTE(g): The Site Control API takes care of running these in threads,
          #   so that callers can truly not worry about what happens to this
          #   script.
          script = site_control.GetScript(script_id)
          
          # No triggers are ever run while the Site is frozen.  These are all part
          #   of REM functionality that may be changing or are being tested.
          if self.site_config and self.site_config['site_freeze'] == '1' and \
              not service_script['freeze_exempt']:
            log('Site Frozen: Skipping script: %s(%s)' % (script['name'], script_id))
            continue # Skip this script
          
          # Else, run the script
          else:
            #log('Run script on %s(%s): %s (%s:%s)' % \
            #    (self.machine['name'], self.machine_id, script['name'], script_id,
            #     service_script_id))
            site_control.RunLocalServiceScript(self.machine_id, script_id, service_script_id)


  def RunTriggerScripts(self):
    """Run scripts for any triggers that are set to run locally on this machine."""
    # No triggers are ever run while the Site is frozen.  These are all part
    #   of REM functionality that may be changing or are being tested.
    if self.site_config and self.site_config['site_freeze'] == '1':
      return
    
    # Get all the active trigger scripts that need running locally on this
    #   machine
    active_trigger_scripts = site_control.GetScripts_Trigger_Active(self.machine_id)

    # Cycle through all the triggers/scripts that need runnign
    for (trigger_instance_id, script_id) in active_trigger_scripts:
        
        # Run them locally, letting the API handle all the wrapping and logging
        #NOTE(g): The Site Control API takes care of running these in threads,
        #   so that callers can truly not worry about what happens to this
        #   script.
        site_control.RunLocalTriggerScript(self.machine_id, trigger_instance_id,
                                           script_id)


  def RunRemDisasterRecoveryScripts(self):
    """This method protects against the worst problem the site can face, the
    Site Control write-master database is not available, so a new one needs
    to be elected, and may also need to be provisioned and restored from backup.

    Whatever the causes, all machines are required to help in the case of a
    disaster, regardless of the type.  They will do so by following a series
    of timed steps.  The machines first in line, and still surviving, will
    be the ones that complete all their steps first, unless something stops them
    which means they werent the fittest for the job.

    DNS names are the final arbitrator of who the Site Control master is.
    The format for the Site Control DNS name is in:

        site_config->dns_site_control_format

    If no site config information has ever been found, this machine will default
    to the hardcoded variable in this module:

        SITE_CONTROL_MASTER_DNS_OF_LAST_RESORT

    This DNS name is ALWAYS created and pointed at the sitecontrol, just as
    a last resort.  Configurability is nice, but we have to be able to fall
    back to something when all our data is gone.

    TODO(g): Is all the above stuff needed, now that this is a local script?  I dont think so...  Wait, then remove...
    """
    # Only necessary to run if we dont have access to Site Control
    if not site_control.IsSiteControlAvailable():

      #TODO(g): Remove this after proving.  All DR is handled through our S3
      #   master backup and election process.  This is not needed at all.
      ## Run the REM Disaster Recovery script, blocking, so we dont try to do
      ##   anything until this script completes
      #os.system(SITE_CONTROL_DISASTER_RECOVERY_SCRIPT)
      
      # Start the election process
      site_control.MasterElectionStartup()
