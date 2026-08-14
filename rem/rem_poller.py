#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
REM Poller

Connects to the REM Listener and calls CollectRrdData(), which returns a dict
collection of machine statistics.  Those stats are written into RRD files for
the current time.

This uses a worker thread model (number of worker threades specified by
COLLECTOR_POOL_SIZE), which make RPC calls to the target machines, and collect
their local data, then store it in RRD files.
"""

import xmlrpclib
import socket
import os
import commands
import time
import threading
import sys
import subprocess
import glob


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


# Are we quitting the application?
QUITTING = False


# CollectThread pool size
COLLECTOR_POOL_SIZE = 20


# A time we last collected each server in our list
LAST_COLLECTED = {}


# Services and names
SERVICES = {'cpu':'CPU Usage', 'diskspace':'Disk Usage',
            'network':'Network Usage', 'diskio':'Disk I/O',
            'diskinode':'Disk Inodes'}


# Cache dict for all our connections to servers (poll_listeners)
SERVERS={}


# Seconds to delay polling of data
POLL_DELAY = 60


# Path information for graphing server
DATA_PATH = '/usr/local/site_control/rrd'
WEB_PATH = '/usr/local/site_control/www'
RRD_TOOL = '/usr/bin/rrdtool'


def Run(cmd):
  """Run a command on the system."""
  
  SHOW_ERRORS=0
  
  if SHOW_ERRORS:
    log('Run: %s' % cmd)
    os.system(cmd)
  else:
    fnull = open(os.devnull, 'w')
    result = subprocess.call(cmd, shell=True, stdout=fnull, stderr=fnull)
    fnull.close()
  
  return ''


def TestConnection(hostname):
  if hostname in SERVERS:
    #log('Testing connection for: %s' % hostname)
    
    try:
      SERVERS[hostname].Loopback()
      pass
    except Exception, e:
      log('Connection failed...  Removing from connection pool: %s' % e)
      
      # Remove the connection
      del SERVERS[hostname]
  else:
    #log('No connection for: %s' % hostname)
    pass


def Connect(hostname):
  # Test that we either dont have this connection, or it is still valid
  TestConnection(hostname)
  
  # If we dont already have this server
  if hostname not in SERVERS:
    log('Connecting to: %s' % hostname)
    
    # Create our connection
    #TODO(g): Get from site_control
    try:
      server = xmlrpclib.ServerProxy('http://%s:3737' % hostname)
    except Exception, e:
      return False
    
    SERVERS[hostname] = server
    
    TestConnection(hostname)
  
  #TODO(g): What is the deal here?  Just disconnecting sometimes...
  if hostname in SERVERS:
    return True
  else:
    return False
  

def IsConnected(hostname):
  return hostname in SERVERS


def Collect(hostname, instance_name):
  """Get information about this machine.
  
  Args:
    hostname: DNS Private name to connect to
    instance_name: Instance Name to write data as
  """
  # Connect
  try:
    success = Connect(hostname)
  except Exception, e:
    log('ERROR: Cannot connect: %s' % e, logging.ERROR)
    return False
  
  # Test connection
  if not success or not IsConnected(hostname):
    log('ERROR: Cannot collect for %s, no connection.' % hostname, logging.ERROR)
    return False
  
  # Get the server from our dict
  server = SERVERS[hostname]
  
  # Get the storage time, even intervals of 60 seconds
  cur_time = int(time.time())
  #NOTE(g): This simple algorithm took a ridiculously long time to test out.
  #   RRD is very picky about what time you insert into it, and I had very bad
  #   results using the NOW options, as I had skipped minutes, times where it
  #   just didnt insert any data at all, times where it wrote over other data
  #   I had written previously.  Using this method, the data goes in reliably,
  #   without missing any entries, or skipping any, as long as polling keeps up.
  store_time = cur_time - (cur_time % 60) + 60 + 60
  
  # Collect
  try:
    data = server.CollectRrdData()
    cpu_usage = data['cpu_usage']
    disk_space = data['disk_space']
    disk_inodes = data['disk_inodes']
    disk_io = data['disk_io']
    network_usage = data['network_usage']
    vm_usage = data['vm_usage']
    
  except socket.gaierror, e:
    log('ERROR: Collection failed (%s): %s' % (hostname, e), logging.ERROR)
    return False
  except Exception, e:
    log('ERROR: Unknown exception (%s): %s' % (hostname, e), logging.ERROR)
    return False
  
  
  # Store and graph each service
  Store(instance_name, 'cpu', cpu_usage, store_time)
  
  # Store network usage by interface name
  for interface in network_usage:
    Store(instance_name, 'network', network_usage[interface], store_time, service_item=interface)
  
  # Store disk space by mount point
  for mount_point in disk_space:
    # Skip non-/dev/ devices.  Dont want /net/ things.
    if not disk_space[mount_point]['device'].startswith('/dev/'):
      continue
    
    Store(instance_name, 'diskspace', disk_space[mount_point], store_time, service_item=mount_point)
  
  # Store disk inodes by mount point
  for mount_point in disk_inodes:
    # Skip non-/dev/ devices.  Dont want /net/ things.
    if not disk_inodes[mount_point]['device'].startswith('/dev/'):
      continue
    
    Store(instance_name, 'diskinode', disk_inodes[mount_point], store_time, service_item=mount_point)
  
  # Store disk IO by device
  for device in disk_io:
    Store(instance_name, 'diskio', disk_io[device], store_time, service_item=device)
  
  # Success!
  return True


def GetRrdFilename(hostname, service, service_item=None):
  # Find the RRD file for this machine and service information
  if service_item == None:
    rrd_filename = '%s/%s_%s.rrd' % (DATA_PATH, hostname, service)
  else:
    # Make useable filenames
    service_item = service_item.replace('/', 'slash')
    
    rrd_filename = '%s/%s_%s_%s.rrd' % (DATA_PATH, hostname, service,
                                        service_item)
  
  return rrd_filename


def GetImageFilename(hostname, service, service_item=None,
                     path=WEB_PATH+'/images/'):
  # If this image path doesnt exist, create it
  if not os.path.isdir(path):
    os.mkdir(path)
  
  # Get the filename
  if service_item == None:
    image_filename = '%s%s_%s.png' % (path, hostname, service)
  else:
    # Make useable filenames
    service_item = service_item.replace('/', 'slash')
    
    image_filename = '%s%s_%s_%s.png' % (path, hostname, service, service_item)
  
  return image_filename


def Graph(hostname, service, service_item=None, comment=None):
  """Graph the latest changes.
  
  NOTE(g): This is in rem_poller instead of rem_grapher because it keeps all
      the RRD definitions together.  It really belongs there, but this is a
      better way to keep all this data in sync, in one file.
  """
  rrd_filename = GetRrdFilename(hostname, service, service_item=service_item)
  image_filename = GetImageFilename(hostname, service, service_item=service_item)
  
  # Get the first DNS name associated with this machine to improve the label
  machine = site_control.GetMachineByName(hostname)
  dns_names = site_control.GetMachineDNSNames(machine['id'])
  if dns_names:
    label = '%s %s' % (dns_names[0], hostname)
  else:
    label = hostname
  
  # General formatting data
  data = {
    'host': label,
    'rrd': rrd_filename,
    'image': image_filename,
    'date':time.asctime().replace(':', '\\:'),
  }
  
  # Add comments, where needed
  if comment:
    data['comment'] = "'COMMENT:\\n'  'COMMENT:" + comment.replace(':', '\\:') + "\\n'"
  else:
    data['comment'] = ''
  
  # Handle each graphing uniquely, to get the correct look and feel
  if service == 'cpu':
    data['service'] = SERVICES[service]
    data['vertical_label'] = '% Used'
    
    cmd = '''/usr/bin/rrdtool graph %(image)s \
    --title="%(host)s %(service)s" \
    --vertical-label "%(vertical_label)s" \
    --start -4h \
    -w 400 -h 100 \
    --lower-limit=0 --upper-limit=100 \
    'DEF:system=%(rrd)s:system:AVERAGE' \
    'DEF:user=%(rrd)s:user:AVERAGE' \
    'DEF:wait=%(rrd)s:wait:AVERAGE' \
    'DEF:idle=%(rrd)s:idle:AVERAGE' \
    'CDEF:Ln1=system' \
    'CDEF:Ln2=system,user,+' \
    'CDEF:Ln3=system,user,wait,+,+' \
    'CDEF:Ln4=system,user,wait,idle,+,+,+' \
    'AREA:system#EA644A:System' \
    'AREA:user#EC9D48:User:STACK' \
    'AREA:wait#ECD748:Wait:STACK' \
    'AREA:idle#BBBBBB:idle:STACK' \
    'LINE1:Ln1#CA442A' \
    'LINE1:Ln2#CC7D28' \
    'LINE1:Ln3#CCB728' \
    'COMMENT:\\\\n' \
    'COMMENT:%(date)s\\\\n' \
    %(comment)s \
    'GPRINT:user:LAST:User\\: %%2.1lf' \
    'GPRINT:system:LAST:System\\: %%2.1lf' \
    'GPRINT:wait:LAST:Wait\\: %%2.1lf' \
    'GPRINT:idle:LAST:Idle\\: %%2.1lf' \
    'COMMENT:\\\\n' \
    'GPRINT:Ln3:MAX:MAX Total\\: %%2.1lf%%%%'
    ''' % data
    Run(cmd)
  elif service == 'diskspace':
    data['service'] = '%s %s' % (service_item.replace('slash', '/'), SERVICES[service])
    data['vertical_label'] = 'KBytes'
    
    cmd = '''/usr/bin/rrdtool graph %(image)s \
    --title="%(host)s %(service)s" \
    --vertical-label "%(vertical_label)s" \
    --start -4h \
    -w 400 -h 100 \
    --lower-limit=0 \
    'DEF:used=%(rrd)s:used:AVERAGE' \
    'DEF:available=%(rrd)s:available:AVERAGE' \
    'DEF:total=%(rrd)s:total:AVERAGE' \
    'DEF:percent_used=%(rrd)s:percent_used:AVERAGE' \
    'CDEF:Ln1=used' \
    'CDEF:Ln2=used,available,+' \
    'AREA:used#EA644A:Used' \
    'AREA:available#EC9D48:Available:STACK' \
    'LINE1:Ln1#CA442A' \
    'LINE1:Ln2#CC7D28' \
    'COMMENT:\\\\n' \
    'COMMENT:%(date)s\\\\n' \
    'GPRINT:used:LAST:Used\\: %%0.0lf' \
    'GPRINT:available:LAST:Available\\: %%0.0lf' \
    'GPRINT:total:LAST:Total\\: %%0.0lf' \
    'GPRINT:percent_used:LAST:Total Used\\: %%0.0lf%%%%' \
    'COMMENT:\\\\n' \
    'GPRINT:available:MIN:MIN Available\\: %%0.0lf' \
    'GPRINT:available:MAX:MAX Available\\: %%0.0lf'
    ''' % data
    Run(cmd)
  elif service == 'diskinode':
    data['service'] = '%s %s' % (service_item.replace('slash', '/'), SERVICES[service])
    data['vertical_label'] = 'Inodes'
    
    cmd = '''/usr/bin/rrdtool graph %(image)s \
    --title="%(host)s %(service)s" \
    --vertical-label "%(vertical_label)s" \
    --start -4h \
    -w 400 -h 100 \
    --lower-limit=0 \
    'DEF:used=%(rrd)s:used:AVERAGE' \
    'DEF:available=%(rrd)s:available:AVERAGE' \
    'DEF:total=%(rrd)s:total:AVERAGE' \
    'DEF:percent_used=%(rrd)s:percent_used:AVERAGE' \
    'CDEF:Ln1=used' \
    'CDEF:Ln2=used,available,+' \
    'AREA:used#EA644A:Used' \
    'AREA:available#EC9D48:Available:STACK' \
    'LINE1:Ln1#CA442A' \
    'LINE1:Ln2#CC7D28' \
    'COMMENT:\\\\n' \
    'COMMENT:%(date)s\\\\n' \
    'GPRINT:used:LAST:Used\\: %%0.0lf' \
    'GPRINT:available:LAST:Available\\: %%0.0lf' \
    'GPRINT:total:LAST:Total\\: %%0.0lf' \
    'GPRINT:percent_used:LAST:Total Used\\: %%0.0lf%%%%' \
    'COMMENT:\\\\n' \
    'GPRINT:available:MIN:MIN Available\\: %%0.0lf' \
    'GPRINT:available:MAX:MAX Available\\: %%0.0lf'
    ''' % data
    Run(cmd)
  elif service == 'diskio':
    data['service'] = '%s %s' % (service_item, SERVICES[service])
    data['vertical_label'] = 'KBytes'
    
    cmd = '''/usr/bin/rrdtool graph %(image)s \
    --title="%(host)s %(service)s" \
    --vertical-label "%(vertical_label)s" \
    --start -4h \
    -w 400 -h 100 \
    --lower-limit=0 \
    'DEF:kb_read=%(rrd)s:kb_read:AVERAGE' \
    'DEF:kb_write=%(rrd)s:kb_write:AVERAGE' \
    'DEF:kb_read_per_s=%(rrd)s:kb_read_per_s:AVERAGE' \
    'DEF:kb_write_per_s=%(rrd)s:kb_write_per_s:AVERAGE' \
    'DEF:tps=%(rrd)s:tps:AVERAGE' \
    'CDEF:Ln1=kb_read' \
    'CDEF:Ln2=kb_read,kb_write,+' \
    'AREA:kb_read#EA644A:KByte Read' \
    'AREA:kb_write#EC9D48:KByte Written:STACK' \
    'LINE1:Ln1#CA442A' \
    'LINE1:Ln2#CC7D28' \
    'COMMENT:\\\\n' \
    'COMMENT:%(date)s\\\\n' \
    'GPRINT:kb_read_per_s:AVERAGE:AVG Kb Read Per S\\: %%0.0lf' \
    'GPRINT:kb_read_per_s:MAX:MAX Kb Read Per S\\: %%0.0lf' \
    'COMMENT:\\\\n' \
    'GPRINT:kb_write_per_s:AVERAGE:AVG Kb Written Per Sec\\: %%0.0lf' \
    'GPRINT:kb_write_per_s:MAX:MAX Kb Read Written Sec\\: %%0.0lf'
    ''' % data
    Run(cmd)
  elif service == 'network':
    data['service'] = '%s %s' % (service_item, SERVICES[service])
    data['vertical_label'] = 'Bytes'
    
    cmd = '''/usr/bin/rrdtool graph %(image)s \
    --title="%(host)s %(service)s" \
    --vertical-label "%(vertical_label)s" \
    --start -4h \
    -w 400 -h 100 \
    --lower-limit=0 \
    'DEF:rx_byte=%(rrd)s:rx_byte:AVERAGE' \
    'DEF:tx_byte=%(rrd)s:tx_byte:AVERAGE' \
    'CDEF:Ln1=rx_byte' \
    'CDEF:Ln2=rx_byte,tx_byte,+' \
    'AREA:rx_byte#EA644A:RX Bytes' \
    'AREA:tx_byte#EC9D48:TX Bytes:STACK' \
    'LINE1:Ln1#CA442A' \
    'LINE1:Ln2#CC7D28' \
    'COMMENT:\\\\n' \
    'COMMENT:%(date)s\\\\n' \
    'GPRINT:rx_byte:LAST:RX Bytes\\: %%0.0lf' \
    'GPRINT:tx_byte:LAST:TX Bytes\\: %%0.0lf' \
    'COMMENT:\\\\n' \
    'GPRINT:rx_byte:MIN:MAX RX\\: %%0.0lf' \
    'GPRINT:tx_byte:MAX:MAX TX\\: %%0.0lf'
    ''' % data
    Run(cmd)
  else:
    raise Exception('Not yet implemented.')
  
  return image_filename


def Store(hostname, service, data, store_time, service_item=None):
  """Store information about this machine."""
  rrd_filename = GetRrdFilename(hostname, service, service_item=service_item)
  
  # If we dont have this directory, create it.  Preceding path will exist.
  if not os.path.isdir(DATA_PATH):
    os.mkdir(DATA_PATH)
  
  # Create this RRD file if it doesn't exist already
  if not os.path.isfile(rrd_filename):
    CreateRrd(service, rrd_filename)
  
  try:
    StoreDataInRrd(hostname, rrd_filename, service, data, store_time)
  except KeyError, e:
    log('ERROR: Missing data for host "%s", service "%s(%s)": %s' % \
        (hostname, service, service_item, e))



def CreateRrd(service, filename):
  """Create an RRD file for this service and filename."""
  log('Creating RRD %s file: %s' % (service, filename))
  
  if service == 'cpu':
    cmd = '''/usr/bin/rrdtool create %s \
  --start N \
  --step 60 \
  DS:user:GAUGE:120:0:100 \
  DS:system:GAUGE:120:0:100 \
  DS:idle:GAUGE:120:0:100 \
  DS:wait:GAUGE:120:0:100 \
  DS:irq:GAUGE:120:0:100 \
  DS:soft:GAUGE:120:0:100 \
  DS:interrupt:GAUGE:120:0:U \
  RRA:AVERAGE:0.5:1:86400 \
  RRA:AVERAGE:0.5:10:1008 \
  RRA:MAX:0.5:10:1008 \
  RRA:MIN:0.5:10:1008 \
  RRA:AVERAGE:0.5:60:8544
    ''' % (filename)
  elif service == 'network':
    cmd = '''/usr/bin/rrdtool create %s \
  --start N \
  --step 60 \
  DS:rx_packet:COUNTER:120:0:U \
  DS:tx_packet:COUNTER:120:0:U \
  DS:rx_byte:COUNTER:120:0:U \
  DS:tx_byte:COUNTER:120:0:U \
  RRA:AVERAGE:0.5:1:86400 \
  RRA:AVERAGE:0.5:10:1008 \
  RRA:MAX:0.5:10:1008 \
  RRA:MIN:0.5:10:1008 \
  RRA:AVERAGE:0.5:60:8544
    ''' % (filename)
  elif service == 'diskspace':
    cmd = '''/usr/bin/rrdtool create %s \
  --start N \
  --step 60 \
  DS:total:GAUGE:120:0:U \
  DS:used:GAUGE:120:0:U \
  DS:available:GAUGE:120:0:U \
  DS:percent_used:GAUGE:120:0:U \
  RRA:AVERAGE:0.5:1:86400 \
  RRA:AVERAGE:0.5:10:1008 \
  RRA:MAX:0.5:10:1008 \
  RRA:MIN:0.5:10:1008 \
  RRA:AVERAGE:0.5:60:8544
    ''' % (filename)
  elif service == 'diskinode':
    cmd = '''/usr/bin/rrdtool create %s \
  --start N \
  --step 60 \
  DS:total:GAUGE:120:0:U \
  DS:used:GAUGE:120:0:U \
  DS:available:GAUGE:120:0:U \
  DS:percent_used:GAUGE:120:0:U \
  RRA:AVERAGE:0.5:1:86400 \
  RRA:AVERAGE:0.5:10:1008 \
  RRA:MAX:0.5:10:1008 \
  RRA:MIN:0.5:10:1008 \
  RRA:AVERAGE:0.5:60:8544
    ''' % (filename)
  elif service == 'diskio':
    cmd = '''/usr/bin/rrdtool create %s \
  --start N \
  --step 60 \
  DS:tps:GAUGE:120:0:U \
  DS:kb_read_per_s:GAUGE:120:0:U \
  DS:kb_write_per_s:GAUGE:120:0:U \
  DS:kb_read:GAUGE:120:0:U \
  DS:kb_write:GAUGE:120:0:U \
  RRA:AVERAGE:0.5:1:86400 \
  RRA:AVERAGE:0.5:10:1008 \
  RRA:MAX:0.5:10:1008 \
  RRA:MIN:0.5:10:1008 \
  RRA:AVERAGE:0.5:60:8544
    ''' % (filename)
  else:
    raise Exception('Unknown service for %s: %s' % (hostname, service))
    
  # Create the RRD file
  Run(cmd)


def StoreDataInRrd(hostname, rrd_filename, service, data, store_time):
  #TODO(g): Shouldnt these use the RRD Tool path in our config/globals?
  
  # Storage switch, building an RRD command
  if service == 'cpu':
    log('Updating CPU for: %s' % hostname)
    cmd = '/usr/bin/rrdtool update %s %s:%s:%s:%s:%s:%s:%s:%s' % \
          (rrd_filename, store_time, data['user'], data['system'], data['idle'],
           data['wait'], data['irq'], data['soft'],
           data['interrupts_per_second'])
  elif service == 'network':
    log('Updating Network for: %s: %s' % (hostname, rrd_filename))
    cmd = '/usr/bin/rrdtool update %s %s:%s:%s:%s:%s' % \
          (rrd_filename, store_time, data['rx_packets'], data['tx_packets'],
           data['rx_bytes'], data['tx_bytes'])
  elif service == 'diskspace':
    log('Updating Disk Space for: %s: %s' % (hostname, rrd_filename))
    cmd = '/usr/bin/rrdtool update %s %s:%s:%s:%s:%s' % \
          (rrd_filename, store_time, data['total'], data['used'],
           data['available'], data['percent_used'])
  elif service == 'diskinode':
    log('Updating Disk Inodes for: %s: %s' % (hostname, rrd_filename))
    cmd = '/usr/bin/rrdtool update %s %s:%s:%s:%s:%s' % \
          (rrd_filename, store_time, data['total'], data['used'],
           data['available'], data['percent_used'])
  elif service == 'diskio':
    log('Updating Disk Space for: %s: %s' % (hostname, rrd_filename))
    cmd = '/usr/bin/rrdtool update %s %s:%s:%s:%s:%s:%s' % \
          (rrd_filename, store_time, data['tps'], data['kb_read_per_s'],
           data['kb_write_per_s'], data['kb_read'], data['kb_write'])
  else:
    raise Exception('Not implemented yet: %s' % service)
  
  # Execute the command
  Run(cmd)



class CollectorThread(threading.Thread):
  
  def __init__(self, count):
    self.count = count
    
    # A non-blocking lock.  Let it fall through to another CollectorThread
    self.lock = threading.Lock()
    
    # The hostname is stored here.  Both the acquired lock and the hostname
    #   must be present to start collecting.
    self.hostname = None
    
    # The file should be saved as the instance_name, we make our connected
    #   to the listener on the hostname (dns_private)
    self.instance_name = None
    
    # Init the Thread
    threading.Thread.__init__(self)
  
  
  def run(self):
    global QUITTING
    global LAST_COLLECTED
    
    # Loop until quit
    while not QUITTING:
      # If we are locked and our hostname is set
      if self.lock.locked() and self.hostname:
        log('Collector %s: Starting %s' % (self.count, self.hostname))
        try:
          success = Collect(self.hostname, self.instance_name)
        except Exception, e:
          log('ERROR: Collection failed: %s' % e)
        
        # Dont try them again, even if they fail.
        LAST_COLLECTED[self.hostname] = time.time()
        
        # Clear the hostname and release our lock
        self.hostname = None
        self.lock.release()
        #log('RELEASING %s: %s' % (self.count, self.lock.locked()))
      
      # Give back to the system
      time.sleep(0.1)
    
    log('QUITTING: Collector: %s' % self.count)



def IsThisTheMonitoringMachine():
  """Returns Boolean: is this the monitoring machine.  There can be only one!"""
  # Ensure we are the Monitoring machine
  machine_id = site_control.GetThisMachineId()
  fip = site_control.GetFloatingIpByName('Monitoring Graphs')
  if machine_id != fip['machine']:
    log('This is not the Monitoring machine.  Monitor=%s.  This=%s.' % (fip['machine'], machine_id))
    return False
  else:
    return True


def StartPolling():
  log('Starting up...')
  
  # If this is not the monitoring machine, quit
  if not IsThisTheMonitoringMachine():
    sys.exit(1)
  
  # Record when we last checked if we were the monitor
  MONITOR_RECHECK_DELAY = 60
  last_monitor_check = time.time()
  
  # Create a collector pool
  log('Creating CollectorThread pool: %s' % COLLECTOR_POOL_SIZE)
  collector_pool = []
  for count in range(0, COLLECTOR_POOL_SIZE):
    ct = CollectorThread(count)
    ct.start()
    collector_pool.append(ct)
  
  # Loop until quit is received
  try:
    while True:
      # If we need to check that this is still the monitor machine
      if time.time() > last_monitor_check + MONITOR_RECHECK_DELAY:
        # Check, if it isn't fail out
        if not IsThisTheMonitoringMachine():
          sys.exit(1)
        else:
          last_monitor_check = time.time()
      
      # Get our machine name (instance name) list from Site Control
      machine_ids = site_control.GetMachines(status=5, site=None)
      machines = {}
      for machine_id in machine_ids:
        machine = site_control.GetMachine(machine_id)
        machines[machine['dns_private']] = machine['name']
      
      # Look through all our servers and make sure we have collected them with
      #   the collection time limit
      for hostname in machines:
        instance_name = machines[hostname]
        
        #log('Processing: %s' % hostname)
        if hostname not in LAST_COLLECTED or \
            time.time() > LAST_COLLECTED[hostname] + POLL_DELAY:
          
          # Find an open collector thread
          done = False
          while not done:
            for count in range(0, COLLECTOR_POOL_SIZE):
              
              # Try to aquire the lock, fail if not immediately available
              success = collector_pool[count].lock.acquire(0)
              
              # If we got this CollectorThread set the hostname and, we are
              #   done with our loop
              if success:
                log('Scheduling %s on %s' % (hostname, count))
                collector_pool[count].hostname = hostname
                collector_pool[count].instance_name = instance_name
                done = True
                break
            
            # If all our collectors are busy, log it so it is not lost
            if not done:
              #log('STALL: No collectors available: %s' % hostname)
              pass
      
      # Give back to the system, so we dont use up all the resources
      time.sleep(0.5)
  
  except KeyboardInterrupt, e:
    global QUITTING
    QUITTING = True
    sys.exit(0)



class RemPollerDaemon(daemon.Daemon):
  """Daemonized version of this command.  Use in production.  Default."""

  def run(self):
    StartPolling()


def main(args=None):
  if not args:
    args = []

  logging.SetLogFile('/usr/local/site_control/poller.log')

  # If we dont want to Daemonize (for testing), just create the threads
  if args == ['debug']:
    StartPolling()
    sys.exit(0)

  # Else, handle it as a daemonized process
  elif len(args) == 1:
    daemon = RemPollerDaemon('/usr/local/site_control/rem_poller.pid')

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
