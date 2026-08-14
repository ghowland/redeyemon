"""
dropSTAR: Drop Scripts, Templates and RPC

Wraps HTTP handler to pass in state.
"""

import sys
sys.path.append('../../')
from shared import log as logging
from shared.log import log
import procyaml

import httpd


def DropStar(filename):
  """Returns a dropSTAR server object, which wraps everything you need.
  
  HTTP and XMLRPC servers run in their own threads on starting.  Many sites
  may be run off one set of thread listeners on a single port, or many thread
  listeners can be specified on their respective ports.
  
  This allows many dropSTAR installations on a single machine, and the ability
  to add totally new sites to an existing dropSTAR installation without
  running a second dropSTAR process or interfering with any of the existing
  dropSTAR sites.
  
  
  Args:
    filename: string, filename of YAML configuration file specifying all the
        websites to manage, their pages scripts, templates and functions.
  """
  ds = _DropStar(filename)
  
  return ds


class _DropStartListener:
  """This represents a port being listened to."""
  
  def __init__(self, conf):
    self.conf = conf


class _DropStar:
  
  def __init__(self, conf_filename, state=None):
    self.conf_filename = conf_filename
    
    log('DropStar: __init__: %s' % conf_filename)
    
    if not state:
      state = {'not_quitting':True}
    
    self.state = state

    #logging.SetLogFile('logs/dropstar.log')
    
    # Each site is stored in here as a listening thread pool, key=int(port)
    self.listeners = {}
    
    # Application data, key=string(application name).  This is the shared data
    #   between applications.  When a listening is started, the selected
    #   applications for its' sites are passed in.  Requests for a given site
    #   are then again only passed in the application data relevant to them.
    #   User specific data is stored in their session dict, which is shared
    #   between all sites loaded by dropSTAR, since that is information about
    #   the requester and considered in the security domain of the request.
    #SECURITY: First level of security, application data is not passed to
    #   threads that do not have sites using that application data.
    #NOTE(g): SECURITY: It is important to note that while it is good to
    #   separate application data, and provide this level of security, if these
    #   are things like normal user requests and finance transactions, do not
    #   put them on the same machine if you want them to be secure.  Any machine
    #   that runs general user requests is more likely to have security flaws
    #   and that will allow them to breach the entire machine and access the
    #   financial transacations.  Real security means separating things that
    #   matter the proper distance to ensure maximum difficulty for an intruder.
    self.applications = {}
    
    # Load this from the conf_filename
    self.conf = None
    
    # Load the dropSTAR configuration
    self.Load()
    
    # Start the dropSTAR site listening thread pools
    self._Start()
  
  
  def Load(self):
    """Load the YAML configuration file.  Sets self.conf"""
    conf = procyaml.LoadYaml(self.conf_filename)
    log('Load: %s' % self.conf_filename)
    
    if conf != self.conf:
      self.conf = conf
      
      for port in self.listeners:
        log('Updating listener: %s' % port)
        self.listeners[port].SetConf(self.conf)
  
  
  def _Start(self):
    """Start all the listening pools."""
    # Determine if we need to open the default port (80/http).
    default_port = False
    
    # Determine all the ports (and their protocols) we need to listen on.
    #   Keyed on port number, with protocol as value (http, https, rpc)
    #NOTE(g): http and https protocols as listen on RPC by default at /rpc/
    ports = {}
    for (site, site_data) in self.conf.items():
      # Skip non-sites, like our default information
      if site == '_default':
        continue
      
      # If this site has a port, save it
      if 'port' in site_data:
        port = site_data['port']
        protocol = site_data.get('protocol', 'http')
        ports[port] = protocol
        log('site: %s  Port: %s  Protocol: %s' % (site, port, protocol), logging.INFO)
      
      # Else, this site uses the default port
      else:
        default_port = True
        log('site: %s  (No port specified)' % site, logging.INFO)
    
    # If we want to use the default port
    if default_port:
      if '_default' in self.conf:
        port = self.conf['_default'].get('port', DEFAULT_PORT)
        protocol = self.conf['_default'].get('protocol', DEFAULT_PROTOCOL)
      else:
        port = DEFAULT_PORT
        protocol = DEFAULT_PROTOCOL
      
      # Warn if the port was already specified
      if port in ports:
        log('Default port used, but also specified in site ports: %s' % port, logging.DEBUG)
      # Else, add this port to the ports
      else:
        ports[port] = protocol
    
    # Start listening thread poor for each port
    for (port, protocol) in ports.items():
      log('%s:%s' % (port, protocol), logging.INFO)
      
      # Create the listening thread pool
      self.listeners[port] = httpd.HttpdThread(port, protocol, self.conf,
                                               self.applications,
                                               state=self.state)
      
      # Start it running now
      self.listeners[port].start()

