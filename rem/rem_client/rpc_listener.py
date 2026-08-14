#!/usr/bin/python


#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
RPC Listener
  Run from rem_listener.py

Handles RPC calls (XMLRPC)
"""

from threading import Thread
from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
import time


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *

import rem_scripts
rrd_collect = rem_scripts.rrd.rrd_collect_everything


def Loopback():
  """Just tests if this is working.  Returns 1(int)."""
  return 1


def CollectRrdData():
  """Gets all the RRD collection data"""
  log('Collect RRD Data')
  
  #TODO(g): Later all RRD collection scripts can be turned into more normal
  #   REM script processes, and be selected with script_collect from RRD.
  #   For now I'll just have everything hard-coded in a collection script,
  #   and when I get time I'll switch it to this data driven model which will
  #   allow easy customization of RRD collection per services, to get more
  #   service-specific RRD, and not just general machine info.
  #return site_control.RunLocalMachineRrdCollect()
  
  return rrd_collect.CollectEverything()


# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
  rpc_paths = ('/RPC2',)



class RpcListenerThread(Thread):
  """XMLRPC Listener Thread"""

  def __init__(self, state=None):
    logging.SetLogFile('/usr/local/site_control/listener.log')
    
    if not state:
      state = {'not_quitting':False}

    self.state = state

    # Get this machine.id.  This can be done, even if Site Control DB is
    #   unavailable, via a cached file, if SC has ever been run here
    self.machine_id = site_control.GetThisMachineId()

    # Initialize this as a Thread
    Thread.__init__(self)


  def run(self):
    """Once start() is called, this function is executed, which is the thread's
    run function.
    """
    # If we come up and Site Control isnt available, wait so we can configure
    #   ourselves properly with the rest of the site.  Site Control will
    #   come back as long as a DB is available
    while not site_control.IsSiteControlAvailable():
      log('RpcListenerThread: Site control is not available')
      time.sleep(5)
    
    # Get our site configuration
    site_config = site_control.GetSiteConfig(site_control.GetSiteByMachine(self.machine_id))

    # Create server
    #NOTE(g): This is not a threaded server for a reason.  It is meant to
    #   block as only 1 monitor server should be requesting things from it,
    #   or possible a server telling it to reconfigure.
    server = SimpleXMLRPCServer(("0.0.0.0", int(site_config['port_rpc'])),
                                requestHandler=RequestHandler)
    server.register_introspection_functions()

    # Add our our RPC functions
    server.register_function(Loopback, 'Loopback')
    server.register_function(CollectRrdData, 'CollectRrdData')

    #TODO(g): Add a full list of ALL(?) site_control API functions so that
    #   all of them are available through RPC.

    #TODO(g):SECURITY: Before we can add API functions to RPC, we must use
    #   SSL and do a real authentication test.  But this is a good idea and
    #   will make it easier for coders to add on their own REM services.  So
    #   plan on implementing later.


    while self.state['not_quitting']:
      try:
        # Run the server's main loop
        #server.serve_forever() # Wont allow us to quit
        # Should just handle 1 request at a time, I think it blocks
        server.handle_request()

        # Give back to the system as we spin loop
        time.sleep(0.1)

      # Log and ignore, if we can
      except Exception, e:
        try:
          log('RpcListenerThread: Unhandled exception: %s' % e)
          #TODO(g): Critical to do?
          #site_control.LogMachineError(self.machine_id, 'RpcListenerThread: %s' % e)
        except:
          log('RpcListenerThread: Failed to log error.')
          pass # If this wont work, we just keep trudging on
