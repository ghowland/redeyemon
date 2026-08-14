#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
REM Web Control

This is an HTTP and XMLRPC server that intends to provide an easy way to use
the REM API (site_control.py) directly for web page creation.

This is an extremely simple system, whose structure resides in the Site Control
database, and whose logic and data reside in scripts and text files.

The process works like this:

The web_page table lists all our pages, and the main view to render them.  The
name of the page is the URI for the way to access the Master machine (could be
accessed directly, or proxied through a web server with access control,
URL re-writing could be done before it gets here, etc.).

The "view" of the web_page resides in the web_view table.  This consists of
the path to a template text file in ./rem/web/templates/, which will be the
content for this view, and then a script to run.

If no script is present, then the template is just rendered raw.

If a script is present, then the script is executed by calling:

  Execute(data_dict, state_dict)

This allows all scripts to start the same way, and take both a semi-stable set
of state data that gets passed to all views, and unique data that was passed
just for this script.

The Execute() function will return an Output object consisting of:

  output_head, output_body, output_data, new_cookies

output_head and output_body are HTML strings that will be inserted into the
body at the position of insert, and into the header section of the page (for
JS and CSS requirements, so includes can be thought of inside a view and still
make it into the page header).

output_data is the data dictionary that was created to be formated into the
template text.  This can be useful in a lot of ways, so it is being returned.

new_cookies will be any new cookies we will tell the browser to save.  This
allows any view to add cookies on render.  Adding cookies in JS is also useful
if doing dynamic activities.

So the script.Execute(data, state) gets called, returns our data, and we add it
to the total output
"""


import sys
import time
import threading


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *

from rem_client import web_httpd
from rem_client import web_rpc


# State for controlling thread exit
DAEMON_STATE = {'not_quitting':True, 'local_ip':None}


def ManageDaemonThreads():
  """Put here so it can be invoked directly or through the Daemon object."""
  # This is a shared state, so that all threads can coordinate quitting, for now
  #   Other things could be added here, but unlikely to be needed.  Using a dict
  #   ensures values can be updated cleanly and the container object remains.
  global DAEMON_STATE

  logging.SetLogFile('/usr/local/site_control/web.log')

  log('Starting up')
  
  # Web API XMLRPC Listener
  httpd = web_httpd.WebHttpdThread(state=DAEMON_STATE)
  httpd.start()
  log('Started Web HTTP listener')

  # Web API XMLRPC Listener
  web_rpcd = web_rpc.WebRpcThread(state=DAEMON_STATE)
  web_rpcd.start()
  log('Started Web RPC listener')


  # We have to stick around until the threads have quit
  loop_counter = 0
  while DAEMON_STATE['not_quitting']:
    try:
      loop_counter += 1
      if loop_counter % 2500 == 0:
        log('Running: Loops: %s' % loop_counter)
      
      # Prove this false, to end
      threads_have_quit = True
      
      # Any thread alive keeps this manager thread from closing
      if httpd.isAlive():
        threads_have_quit = False
      
      if web_rpcd.isAlive():
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
  
  log('Quitting REM Web')
  sys.exit(0)


class RemWebDaemon(daemon.Daemon):
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
    daemon = RemWebDaemon('/usr/local/site_control/rem_listener.pid')

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
