#!/usr/bin/python


#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Web RPC
  Run from rem_web.py

Handles all RPC requests for the HTTP pages rem_web renders (by design,
not enforced), and also any external scripts that want to interface with
the REM Site Control API (site_control.py).

The RPC library is not initially meant to wrap the entire API, if you
need that level of access you should write a wrapper (and please submit
a patch :) ).

The RPC library is meant to be high level operations to alter the site's
system in functional ways.  It will also retrieve all the data from
the Site Control DB, but does so at a much higher level than the
Site Control API, which does everything at a table level.

The RPC library returns Site Control data in structured dictionaries,
with the required labels and child data already included, so scripts can
interact with REM on a very high level and not need to understand it's
site_control.py direct API.

RPC Functions are defined in the web_rpc_function table, and contain a name,
which they are called by, and a script_call field that points to their execution
script.  The execution script is invoked like this:

  script_name.Execute(...args...)

Args are whatever the caller wanted to pass in, so this can be totally left up
to the script that handles it, but having some standards for state/session
would be useful.

More functions can be added to the script_name module that Execute invokes once
it starts, so that classes and other things can be used, and of source access
to site control is available.

Because the scripts are all imported into this managing thread, they will not
have to be reloaded or re-interpretted each request, so this is not slow.
"""

from threading import Thread
from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
import time
import imp # Almost recursive...
import os


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *



def Loopback():
  """Just tests if this is working.  Returns 1(int)."""
  return 1


# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
  rpc_paths = ('/RPC2',)



class WebRpcThread(Thread):
  """XMLRPC Listener Thread"""

  def __init__(self, state=None):
    logging.SetLogFile('/usr/local/site_control/web_rpc.log')
    
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
      log('WebRpcThread: Site control is not available, sleeping...')
      time.sleep(5)
    
    # If this machine is not the Site Control Master, then quit
    if not site_control.IsThisMachineMaster():
      log('This machine is not the Site Control Master, quitting.')
      return
    
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
    
    # Get all the Web RPC Functions, and add their script.Execute function,
    #   JavaScript or scripts calling us know to pass the data and state args.
    sql = "SELECT * FROM web_rpc_function"
    result = Query(sql)
    
    # Add all our functions
    for item in result:
      # Get the python module for our script_call
      script_module = site_control.GetScriptPythonModule(item['script_call'])
      
      # Log failure and skip to next
      if script_module == None:
        log('Failed to get the Python Module: Script %s' % item['script_call'], logging.CRITICAL)
        continue
      
      
      # Test if the module has the function we expect (Execute)
      if hasattr(script_module, 'Execute'):
        execute_function = getattr(script_module, 'Execute')
        
        # Add this function to our RPC functions under it's function name
        log('Adding RPC function: %s' % item['name'])
        try:
          server.register_function(execute_function, item['name'])
        
        except Exception, e:
          log('Failed to register RPC function for script (%d): %s: %s' \
              (item['script_call'], script_filename, e), logging.CRITICAL)
      else:
        log('No function Execute in script (%d): %s: %s' \
            (item['script_call'], script_filename, e), logging.CRITICAL)
    
    
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
          log('WebRpcThread: Unhandled exception: %s' % e)
          #TODO(g): Critical to do?
          #site_control.LogMachineError(self.machine_id, 'RpcListenerThread: %s' % e)
        except:
          log('WebRpcThread: Failed to log error.')
          pass # If this wont work, we just keep trudging on
