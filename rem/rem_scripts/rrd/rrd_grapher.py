#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
REM Grapher

Creates graphs for all our RRD files, so we can visualize our data.
"""

import time
import glob
import re
import os


import rem_scripts.config.config_util as config_util


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *

# Special Import for this Package
import rem_poller



def CreateHtml(hostname, image_data):
  """Create an HTML file for this host and image data."""
  #log('Host HTML: %s' % hostname)
  
  # If the WEB_PATH doesnt exist, create it
  if not os.path.isdir(rem_poller.WEB_PATH):
    os.mkdir(rem_poller.WEB_PATH)
  
  filename = '%s/%s.html' % (rem_poller.WEB_PATH, hostname)
  
  output = '<html><head><title>%s</title></head><meta http-equiv="refresh" content="20" /><body><a href="/"><h2>Home</h2></a>\n' % hostname
  
  # Get machine information
  machine = site_control.GetMachineByName(hostname)
  
  # Get a list of the machine Pool names
  pool_names = []
  pools = site_control.GetMachinePools(machine['id'])
  for pool_id in pools:
    pool = site_control.GetPool(pool_id)
    pool_names.append(pool['name'])
  pool_names.sort()
  
  # Get all the DNS names for this machine
  dns_names = site_control.GetMachineDNSNames(machine['id'])
  
  # Add the machine information
  output += '<br>'
  output += '<b>Machine:</b> %(name)s  <b>Private:</b> %(dns_private)s  <b>Public:</b> %(dns_public)s<br><b>Launched:</b> %(time_launch)s<br>' % machine
  output += '<br>'
  output += '<b>Hardware:</b> %(name)s  <b>Cores:</b> %(core)s   <b>RAM:</b> %(size_ram_gb)0.1fG<br>' % \
            site_control.GetHardwareKind(machine['hardware_kind'])
  output += '<b>Image:</b> %(name)s  <b>OS:</b> %(os)s %(os_bit)s  <b>Keypair:</b> %(keypair)s<br>' % \
             site_control.GetHardwareImage(machine['hardware_image'])
  output += '<br>'
  output += '<b>Pools:</b> %s<br>' % ', '.join(pool_names) #TODO(g): Link...
  output += '<b>DNS Names:</b> %s<br><br>' % ', '.join(dns_names) #TODO(g): Link...
  
  # Add the graphs
  output += '<table>'
  count = 0
  for data in image_data:
    if count % 2 == 0:
      output += '<tr><td>'
    else:
      output += '<td>'
    
    image_name = rem_poller.GetImageFilename(hostname, data['service'],
                                  service_item=data['service_item'], path='images/')
    output += '<a href="__%s.html#%s" name="%s"><img src="%s" border="0"></a><br>\n' % \
              (data['service'], hostname, data['service'], image_name)
    
    if count % 2 == 0:
      output += '</td><td>'
    else:
      output += '</td><tr>'
    
    # Increment the counter
    count += 1
  
  output += '</table></body></html>\n'
  
  
  # Write this output into a file
  open(filename, 'w').write(output)


def CreateCombinationHtml():
  """Create combination HTML files for all our images."""
  # If the WEB_PATH doesnt exist, create it
  if not os.path.isdir(rem_poller.WEB_PATH):
    os.mkdir(rem_poller.WEB_PATH)
  
  for (service, name) in rem_poller.SERVICES.items():
    path = '%s/images/*_%s*.png' % (rem_poller.WEB_PATH, service)
    log('Searching combinations %s: %s' % (service, path))
    files = glob.glob(path)
    files.sort()
    
    # Write the output for the file
    output = '<html><head><title>All: %s</title></head><meta http-equiv="refresh" content="60" /><body><a href="/"><h2>Home</h2></a><br>\n' % name
    
    # Save our graph data here, by machine label
    graphs = {}
    
    # Create all our labels
    for file in files:
      hostname = os.path.basename(file).split('_')[0]
      
      # Get the machine
      machine = site_control.GetMachineByName(hostname)
      dns_names = site_control.GetMachineDNSNames(machine['id'])
      if dns_names:
        key = dns_names[0]
      else:
        key = hostname
      
      label = '<a href="%s.html#%s" name="%s"><img src="images/%s" border="0"></a><br>\n' % \
              (hostname, service, hostname, os.path.basename(file))
      
      # Save the label
      graphs[key] = label
    
    # Sort the graph keys
    keys = graphs.keys()
    keys.sort()
    
    # Create our HTML
    output += '<table>\n'
    count = 0
    for key in keys:
      if count % 2 == 0:
        output += '<tr><td>'
      else:
        output += '<td>'
      
      output += graphs[key]
      
      if count % 2 == 0:
        output += '</td><td>'
      else:
        output += '</td><tr>'
      count += 1
    output += '</table></body></html>\n'
    
    # Write this output into a file
    open('%s/__%s.html' % (rem_poller.WEB_PATH, service), 'w').write(output)
    
    # Save the filenames to a text file, so they can be parsed by other systems
    #   without using the index page, so we can make something fancy there
    open('%s/_list_%s.txt' % (rem_poller.WEB_PATH, service), 'w').write('\n'.join(files))


def CreateIndexHtml(hosts):
  """Create the Index HTML.
  
  TODO(g): Create the service list dynamically too.  And any other RRD
      collections that are good to view at the same time.
  """
  # The output to insert into the template
  data = {'machines':'', 'pools':'', 'services':''}
  
  # Get the template for this
  template = config_util.LoadTemplate('monitoring_index.txt')
  
  # Show hosts in alphabetic order
  keys = hosts.keys()
  keys.sort()
  
  # Process all the hosts
  labels = []
  for host in keys:
    # Get the machine
    machine = site_control.GetMachineByName(host)
    
    # Get a list of the machine Pool names
    pool_names = []
    pools = site_control.GetMachinePools(machine['id'])
    for pool_id in pools:
      pool = site_control.GetPool(pool_id)
      pool_names.append(pool['name'])
    pool_names.sort()
    
    # Get all the DNS names for this machine
    dns_names = site_control.GetMachineDNSNames(machine['id'])
    
    # Create the machine label for the URL
    label = '%s</td><td><a href="%s.html">%s</a></td><td>%s' % \
            (', '.join(dns_names), machine['name'], machine['name'],
             ', '.join(pool_names))
    labels.append(label)
  
  # Sort the labels, so we have pools grouped
  labels.sort()
  
  # Add all the labels
  data['machines'] += '<table>\n'
  for label in labels:
    # Add the host data
    data['machines'] += '<tr><td>%s</td></tr>\n' % label
  data['machines'] += '</table>\n'
  
  #TODO(g): Add a section for Pools, so we can look at Pool info
  data['pools'] += ''
  
  #TODO(g): Add a section for Services, so we can look just at service perf
  data['services'] += ''
  
  # Format the template
  if 1:
    output = template % data
  #TODO(g): Switch to this method, after I fix the templates to remove double
  #   percent(%) signs.  The below way is better in all the ways we care about.
  #elif 0:
  #  # Format the template, non-destructively.  (Keep unused format strings and %s)
  #  output = site_control.WebTemplateFormat(template, data)
  
  # Save the index
  open('%s/index.html' % (rem_poller.WEB_PATH), 'w').write(output)


def Graph():
  """Graph all the RRD files that need graphing at this time."""
  logging.SetLogFile('/usr/local/site_control/rrd_grapher.log')
  
  rrd_search = '%s/*.rrd' % rem_poller.DATA_PATH
  files = glob.glob(rrd_search)
  files.sort()
  
  # Store data about the hosts
  hosts = {}
  
  total_graphs = 0
  start_time = time.time()
  
  log('Graphing...')
  
  # Go through all our RRD files
  for file in files:
    # Get data out of filename, chopping the .rrd
    filename = os.path.basename(file)
    chunks = filename[:-4].split('_', 2)
    if len(chunks) == 2:
      hostname = chunks[0]
      service = chunks[1]
      service_item = None
    elif len(chunks) == 3:
      hostname = chunks[0]
      service = chunks[1]
      service_item = chunks[2]
    else:
      raise Exception('Unsupported RRD file format: %s' % filename)
    
    log('Graphing: %s: %s (%s)' % (hostname, service, service_item))
    
    if hostname not in hosts:
      hosts[hostname] = []
    
    # If this is a CPU service, load the CPU count as a comment\
    comment = ''
    
    #TODO(g): Figure out interesting comments.  This shows one I'm not
    #   tracking anymore (as CPUs are known by machine_kind), but this is
    #   good stuff, and we have a lot of data we can add to these graphs
    #   in the future.
    #
    #   Really, figure out how to make these automatable.  A script would
    #   work, then they could code up anything they want for it.
    #   Too many scripts?  Easy, just make all their relative paths include
    #   a subdirectory to segment them, the DB doesnt care about their
    #   filenames, so it's an easy change.
    #
    #if 0:
    #  cpu_count_file = '%s/%s_cpu_count.txt' % (rem_poller.rem_poller.WEB_PATH, hostname)
    #  if service == 'cpu' and os.path.isfile(cpu_count_file):
    #    comment = 'CPUs: %s' % open(cpu_count_file, 'r').read()
    
    # Graph this
    image = rem_poller.Graph(hostname, service, service_item=service_item, comment=comment)
    hosts[hostname].append({'image':image, 'host':hostname, 'service':service,
                           'service_item':service_item})
    
    # Increment graph counter
    total_graphs += 1
  
  # Create all the HTML pages for the hosts
  log('Creating HTML pages: %s hosts' % len(hosts))
  for host in hosts:
    CreateHtml(host, hosts[host])

  # Create all the combination HTML pages
  CreateCombinationHtml()
  
  # Create the index page
  CreateIndexHtml(hosts)
  
  log('Total graphs created: %s' % total_graphs)
  log('Time to create graphs: %0.1f minutes' % ((time.time() - start_time) / 60.0))


def GraphForever():
  """Keep graphing forever."""
  logging.SetLogFile('/usr/local/site_control/rrd_grapher.log')
  
  while True:
    
    Graph()
    
    #TODO(g): Put someplace better
    SLEEP_TIME = 60
    log('Sleeping...  (%s seconds)' % SLEEP_TIME)
    
    # Wait to graph again, so we arent ALWAYS graphing.  Too slow.
    time.sleep(SLEEP_TIME)


def main():
  #GraphForever()
  Graph()


if __name__ == '__main__':
  main()


