#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
REM Listener: XMLRPC listener

Provides: Local machine monitoring information

Does not provide: Control over machine, control over Site Control.

This provides an XMLRPC interface to the internal network (not enforced) to give
RRD information to the RRD collection monitor, and also to request an immediate
machine reconfiguration from the Site Control database (protected against
possible flood attacks).

Security: Local information about the system is not dangerous, but some commands
    take a few seconds to run.  A DoS on this service will hurt machines.
    There is currently no security in this software.  The listening port must
    be protected by the network.
    
    Additionally, the XMLRPC listener is not a threaded socket server, so
    a single connection could block collection attempts.

TODO(g): SECURITY: Make IP restrictions (from Site Control?), make secret key
    for the poller to get from Site Control, and this too, so we can work off
    Shared Secrets the Site Control machine knows.  PKI per machine?
    HTTPS is easy win, but no reason until secrets start flying.


TODO(g):SECURITY:ANSWER!: We know what machine should be connected to us,
    the Monitoring machine.  If it's not that machine, then reject the
    requester.  This gives us the basic security we need, when HTTPS is added.
"""


import sys
import time


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *

from rem_client import rpc_listener


# State for controlling thread exit
DAEMON_STATE = {'not_quitting':True, 'local_ip':None}



def ManageDaemonThreads():
  """Put here so it can be invoked directly or through the Daemon object."""
  # This is a shared state, so that all threads can coordinate quitting, for now
  #   Other things could be added here, but unlikely to be needed.  Using a dict
  #   ensures values can be updated cleanly and the container object remains.
  global DAEMON_STATE

  logging.SetLogFile('/usr/local/site_control/listener.log')

  log('Starting up')
  
  # XMLRPC Listener
  rpc = rpc_listener.RpcListenerThread(state=DAEMON_STATE)
  rpc.start()
  log('Started RPC listener')

  # We have to stick around until the threads have quit
  while DAEMON_STATE['not_quitting']:
    try:
      log('Running')
      # Prove this false, to end
      threads_have_quit = True

      if rpc.isAlive():
        threads_have_quit = False

      # If the threads have all quit, then quit out
      if threads_have_quit:
        DAEMON_STATE['not_quitting'] = False # Redundant change
        break
      
      # Update our modules (protects us from frequent calling internally)
      #TODO(g): Risk vs reward ratio needed...  Any chance of killing working
      #   clients is not worth worth any price.  Remove if no compelling reason
      #   for having this appears.
      if 0:
        reloader.Update()
      
      # Give back to the system, as we're spin looping
      time.sleep(0.25)

    # If we have been told to quit by the user or signal, then let the threads
    #   know through our state dict, and follow our own state rules out.
    except (KeyboardInterrupt, SystemExit), e:
      log('Keyboard initiated quit')
      DAEMON_STATE['not_quitting'] = False

    # All exceptions must be handled, so log it and keep going.  Monitoring
    #   will have to take care of failures here.  Too hard to know all the
    #   states and thats exactly what monitoring is for.
    except Exception, e:
      msg = 'ManageDaemonThreads: Unhandled exception: %s\n%s' % \
            (e, stack.Mini(5, 1))
      log('Unhandled Exception: %s' % msg) # First in case SC is gone
      site_control.LogMachineError(machine_id, msg)
  
  log('Quitting REM listener')


class RemListenerDaemon(daemon.Daemon):
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
    daemon = RemListenerDaemon('/usr/local/site_control/rem_listener.pid')

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
