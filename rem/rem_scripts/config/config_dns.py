#!/usr/bin/python


#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Service Configure: Internal DNS
"""


import os

import config_util

# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *



def Configure(save=True, test_template=None):
  """Configure is intelligent, and knows how to handle different machine's
  configuration, so that in the same pool, some machines are masters, others
  are slaves.  Or whatever the circumstances may call for.
  
  Args:
    save: boolean, if true, will save this file
    test_template: string, file name to test a different template.  If set this
        will not save the configuration.
  """
  #TODO(g): test_template needs an update for this, multiple files are generated
  
  log('Starting')
  any_changed = False

  # Get all our domains
  domains = {}
  sites = site_control.GetSites()
  for site_name in sites:
    site = sites[site_name]

    site_config = site_control.GetSiteConfig(site['id'])

    domains[site_config['domain_internal']] = {'site':site, 'site_config':site_config}

  # Create the /etc/named.conf
  output_filename = '/etc/named.conf'
  named_conf_template = config_util.LoadTemplate('bind_named_conf.txt')

  # Create zone data
  template_item = '''\

zone "%(domain)s" {
  type master;
  file "/var/named/data/internal/%(domain)s.db";
};

'''
  output = ''
  for domain in domains:
    output += template_item % {'domain': domain}

  # Get the output for this file template and data
  final_output = named_conf_template % {'zones':output}

  # Save the file
  if save:
    changed = config_util.SaveFile(output_filename, final_output)

    # We have a number of possible changes to track, any will do
    if changed:
      any_changed = True

  # Create all the zone files
  for domain in domains:
    # Make the path if it doestn exist
    if not os.path.isdir('/var/named/data/internal/'):
      os.mkdir('/var/named/data/internal/')
    output_filename = '/var/named/data/internal/%s.db' % domain
    zone_template = config_util.LoadTemplate('bind_zone.txt')
    template_item = '%(name)s       A       %(ip)s\n'
    output = ''

    pools = site_control.GetPools()

    # Process pools
    pool_names = pools.keys()
    pool_names.sort()
    for pool_name in pool_names:
      pool = pools[pool_name]

      # Get list of machine.ids that run this service, in order
      pool_machines = site_control.GetPoolMachineList(pool['id'])

      #log('Pool: %s   Count: %s' % (pool_name, len(pool_machines)))

      # Process service machines
      for count in range(0, len(pool_machines)):
        #log('Pool %s: Machine: %s' % (pool['id'], pool_machines[count]))
        pool_machine = site_control.GetMachine(pool_machines[count])

        # Create the record data
        dns_name = pool['machine_name_format'] % (count+1)
        # If this machine has an Interal IP
        if pool_machine['ip_internal']:
          output += template_item % {'name':dns_name,
                                     'ip':pool_machine['ip_internal']}
        
        # Update this machine with it's public DNS name
        sql = "SELECT * FROM pool_machine WHERE pool = %d AND machine = %d" % \
              (pool['id'], pool_machine['id'])
        has_pool_machine = query.Query(sql)
        if has_pool_machine:
          sql = "UPDATE pool_machine SET dns_public = '%s' WHERE pool = %d AND machine = %d" % \
                (query.SanitizeSQL(dns_name), pool['id'], pool_machine['id'])
          query.Query(sql)
        else:
          # Create the entry.  It will get cleaned up automatically, and cant
          #   hurt us.  It still defines the relationship, even though this
          #   pool isnt managing their own children.
          #NOTE(g): All important field "provisioned" here, we are setting it to
          #   0(False), because this is not a provisioned Pool Machine, this
          #   is a phantom pool machine which is here for information purposes
          #   only.  If a pool is not a parent pool, delete any phantom machine
          #   entries.
          sql = "INSERT INTO pool_machine (pool, machine, dns_public, provisioned) VALUES " + \
                "(%d, %d, '%s', 0)" % \
                (pool['id'], pool_machine['id'], query.SanitizeSQL(dns_name))
          query.Query(sql)
    
    # Get master machine info (dont need it now)
    if 0:
      pass
      #master_ip = site_control.GetMasterConfig()['ip']
      #master_machine_id = site_control.GetMasterConfig()['machine']
      #master_machine = site_control.GetMachine(master_machine_id)
    
    # Get the floating IP address
    floating_ip_info = site_control.GetFloatingIpByName('Prod DNS')
    
    # Name servers
    name_servers = ''
    if floating_ip_info:
      # Add the Name Server header
      name_servers = '                NS       ns1'
      # Add the Name Server record
      output += 'ns1             A        %s' % floating_ip_info['ip_address']
    
    
    # Add each machine by instance name, with an external address
    
    
    # Add the external monitoring machine for seeing graphs
    
    
    # Create the final output
    final_output = zone_template % {'domain':domain, 'records':output,
                                    'ns':name_servers,
                                    'date':config_util.GetTimeStamp(minutes=False, seconds=False)}
    log(final_output)

    # Save the file
    if save:
      changed = config_util.SaveFile(output_filename, final_output)

      # We have a number of possible changes to track, any will do
      if changed:
        any_changed = True

  # Turn on the capability module.  Bind requires capset
  #TODO(g): Remove this once its been added to the AMI
  config_util.RunCommand('modprobe capability')

  # Update the DNS Root Hints file
  config_util.RunCommand('/usr/local/site_control/rem/scripts/update_dns_root_hints')
  
  # Turn the service on
  config_util.RunCommand('/sbin/chkconfig --levels 2345 named on')

  # Dont restart it if its already started
  config_util.RunCommand('/sbin/service named start')

  # If anythnig chnaged, reload the information
  if any_changed:
    #TODO(g): Change to reload after we fix the file timestamp/whatever master
    #   update problem.  It's not picking up zone file changes.
    #config_util.RunCommand('/sbin/service named reload')
    config_util.RunCommand('/sbin/service named restart')


def main(args=None):
  if not args:
    args = []
  
  if not args:
    save = True
    template = None
  else:
    save = False
    template = args[0]
  
  Configure(save=save, test_template=template)



if __name__ == '__main__':
  main(sys.argv[1:])