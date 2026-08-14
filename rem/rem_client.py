#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
REM Client.  Single long-running script needed to manage REM machines, pools,
and services.  One correctly configured instance of a REM client should be able
to bring an entire site back online, by creating a new DB master, installing
from backup, and rebuilding the rest of the site.

The REM Client is made to be very thin.  It is a simple wrapper over the
REM site_control_client API, which is itself a very thin wrapper around the
REM SQL database structured data.

This client has two purposes:

1) Run scripts for: scheduled service job queue (second-based cron) and
    trigger scripts that are meant to run on the local machine

2) Provides XMLRPC interface to the internal network (not enforced) to give
RRD information to the RRD collection monitor, and also to request an immediate
machine reconfiguration from the Site Control database (protected against
possible flood attacks).

It does the RPC service in the same process as the script running process
to give better insight, through tighter coupling, into both of them.

I believe this will pan out well, and if it doesn't it is not at all difficult
to split them and give up the added functionality, as it isn't worth it if
it doesn't become useful as well as very secure.


TODO(g): RPC and Script Running can be split, and an advantage would be it
    removes any threading issues with MySQL connections.  I am not maintaining
    a connection/cursor manager for MySQL, because it is doing basic
    single-query stuff, but threading problems can come up with poorly-timed
    concurrent calls.  Splitting RPC from Script Running will fix this, so
    if I see any problems in Production usage, thats what I'm going to do.

    The system will recover from the problems currently, even a segfault (worst
    possible scenario, MySQL C code bombs) and the REM Client will be relaunched
    by the local process monitor (ie. monit).
"""


import sys
import time

# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *

from rem_client import *


# State for controlling thread exit
DAEMON_STATE = {'not_quitting':True, 'is_site_control_master':False,
                'site_control_master_ip':None, 'local_ip':None}



def REMClientStartup():
  """Client startup process."""
  global DAEMON_STATE

  log('Starting...')

  # Get the site control master's IP
  master_ip = site_control.GetSiteControlMasterIP(state=DAEMON_STATE)

  log('Master IP: %s' % master_ip)

  # Site Control Master
  if DAEMON_STATE['is_site_control_master']:
    log('This machine is the Site Control Master.')
    site_control.SiteControlMasterStartup(DAEMON_STATE)

  # Site Control Client
  else:
    # Test if our master can be contacted, no point going further if not
    master_listens = query._PortListeningTest(master_ip)
    
    # If the master DB isnt listening
    if not master_listens:
      site_control.MasterElectionStartup(state=DAEMON_STATE)
    
    # Else, the master is listen, try to collect our configuration
    else:
      # Get our reconfiguration data.  If the master is unavailable an election
      #   process is started automatically, and a new master is found, then
      #   we get our config_data still.  It is supposed to be "fail proof".
      log('Configuring this machine from the Site Control master')
      config_data = site_control.GetConfigurationDataFromMaster()
  
      # If we couldnt bring this machine up, start a Master Election
      if config_data == None:
        site_control.MasterElectionStartup(state=DAEMON_STATE)
      
      # Else, we got our data, so let's run a machine config and continue
      else:
        # Run this every time we start up, just to ensure things are on track
        run_script.Run('/usr/local/site_control/rem/scripts/machine_config.py')


  log('Startup Complete: Master: %s (This Machine=%s)' % (master_ip, DAEMON_STATE['is_site_control_master']))


def ManageDaemonThreads():
  """Put here so it can be invoked directly or through the Daemon object."""
  # This is a shared state, so that all threads can coordinate quitting, for now
  #   Other things could be added here, but unlikely to be needed.  Using a dict
  #   ensures values can be updated cleanly and the container object remains.
  global DAEMON_STATE

  # REM needs to have access to a Site Control master, this will ensure that
  #   this is accomplished.  This machine may already be the master, or may not
  #   currently but might be after this command.
  REMClientStartup()

  # First thing we need to do: Reconfigure our Machine from Site Control
  site_control.ConfigureLocalMachine()

  # Get this machine.id
  machine_id = site_control.GetThisMachineId()


  ## XMLRPC Listener
  #rpc = rpc_listener.RpcListenerThread(state=DAEMON_STATE)
  #rpc.start()
  #log('Started RPC listener')

  # Script Runner
  script_runner = site_control_script_runner.SiteControlScriptRunner(state=DAEMON_STATE)
  
  # Start the script runner in single threaded mode
  if 1:
    script_runner.StartDirectly()
  
  # Threaded mode, Im disabling this because it's not useful now
  else:
    pass
    #script_runner.start()
    #log('Started Script Runner')
    #
    ## We have to stick around until the threads have quit
    #while DAEMON_STATE['not_quitting']:
    #  try:
    #    # Prove this false, to end
    #    threads_have_quit = True
    #
    #    #if rpc.isAlive():
    #    #  threads_have_quit = False
    #
    #    if script_runner.isAlive():
    #      threads_have_quit = False
    #
    #    # If the threads have all quit, then quit out
    #    if threads_have_quit:
    #      DAEMON_STATE['not_quitting'] = False # Redundant change
    #      break
    #    
    #    # Update our modules (protects us from frequent calling internally)
    #    reloader.Update()
    #    
    #    # Give back to the system, as we're spin looping
    #    time.sleep(0.25)
    #
    #  # If we have been told to quit by the user or signal, then let the threads
    #  #   know through our state dict, and follow our own state rules out.
    #  except (KeyboardInterrupt, SystemExit), e:
    #    log('Keyboard initiated quit')
    #    DAEMON_STATE['not_quitting'] = False
    #
    #  # All exceptions must be handled, so log it and keep going.  Monitoring
    #  #   will have to take care of failures here.  Too hard to know all the
    #  #   states and thats exactly what monitoring is for.
    #  except Exception, e:
    #    msg = 'ManageDaemonThreads: Unhandled exception: %s\n%s' % \
    #          (e, stack.Mini(5, 1))
    #    log('Unhandled Exception: %s' % msg) # First, in case SC is gone
    #    site_control.LogMachineError(machine_id, msg)


class RemClientDaemon(daemon.Daemon):
  """Daemonized version of this command.  Use in production.  Default."""

  def run(self):
    ManageDaemonThreads()


def main(args=None):
  if not args:
    args = []

  # If we dont want to Daemonize (for testing), just create the threads
  if args == ['debug']:
    ManageDaemonThreads()
    sys.exit(0)

  # Else, handle it as a daemonized process
  elif len(args) == 1:
    daemon = RemClientDaemon('/usr/local/site_control/rem_client.pid')

    if 'start' == args[0]:
      daemon.start()
    elif 'stop' == args[0]:
      daemon.stop()
    elif 'restart' == args[0]:
      daemon.restart()
    else:
      print "Error: Unknown command: %s" % args[0]
      print "usage: %s start|stop|restart|debug" % sys.argv[0]
      sys.exit(1)

    sys.exit(0)

  # Else, usage
  else:
    print "usage: %s start|stop|restart|debug" % sys.argv[0]
    sys.exit(1)


if __name__ == '__main__':
  main(sys.argv[1:])
