"""
httpd

HTTP Daemon, as a procblock.  Uses other procblock to process the HTTP
requests (and breaks out XMLRPC, to integrate the two).
"""


import time


import dropstar

import sys
sys.path.append('../../')
from shared import log as logging
from shared.log import log
from shared import sharedlock


#TODO(g): Move globals into procblock data.

DEFAULT_IP = '0.0.0.0'
DEFAULT_PORT = 8080

# If, for some reason, there is no _default section in the YAML conf, then
#   use these values as default defaults
DEFAULT_PROTOCOL = 'http'

#TODO(g): Move into defaults
DEFAULT_LOGFILE = 'dropstar.log'


def ProcessBlock(pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):
  """Run Threaded HTTP and XMLRPC combined server.
  
  This block will run until sharedlock.Get('running') is not held, then will
      exit.
  """
  
  conf = {}
  applications = {}
  
  log('Creating dropSTAR')
  ds = dropstar.DropStar('/users/ghowland/Documents/projects/dropstar/conf/dropstar.yaml')
  
  pipe_data['dropstar'] = ds
  
  #if 0:
  #  # Track all listeners by the port they listen on.  One process block can
  #  #   host many threaded HTTP listeners
  #  listeners = {}
  #  
  #  # Create the IP:Port combination we can uniquely identify our listeners with
  #  port = DEFAULT_PORT
  #  ip_port = '%s:%s' % (DEFAULT_IP, port)
  #  protocol = DEFAULT_PROTOCOL
  #  
  #  # Create the listening thread pool
  #  #NOTE(g): 
  #  listeners[ip_port] = httpd.HttpdThread(port, protocol, conf, applications, state=state)
  #  
  #  # Start it running now
  #  listeners[ip_port].start()
  
  done = False
  # While a procblock is still holding the __running lock, we run
  #TODO(g): Implement this...  Ditch "done"
  #while sharedlock.IsLocked('__running'):
  while not done:
    # Wait...
    time.sleep(0.1)
  
  return pipe_data


  
