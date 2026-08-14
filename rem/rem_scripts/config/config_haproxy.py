#!/usr/bin/python


#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Service Configure: HA Proxy
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
  #TODO(g): If this is an Edge machine, configure the Floating IP address
  if 0:
    #TODO(g): This is important needs to be done
    #TODO(g): This command DEFINITELY needs to check if it already is this,
    #   and not try to set it.  Wastefulness seen as a DoS would be bad.
    rem_ec2.AssignFloatingIp(FLOAT_IP_NAME_FROM_SC_MASTER, THIS_EC2_IMAGE_ID_FOR_FLOAT_IP)

  #TODO(g): Get this from the service config!
  HA_PROXY_CONFIG = '/etc/haproxy/haproxy.cfg'
  template_item = '  server %(name)s %(ip)s:80 weight 1 minconn 1 maxconn 6 check inter 20000\n'

  # Get HTTP machines
  http_machines = site_control.GetPoolMachineList(2)

  # Generate HTTP listening services
  http_output = ''
  for machine_id in http_machines:
    machine = site_control.GetMachine(machine_id)
    label = 'http_machine_%s' % machine_id
    http_output += template_item % {'name':label, 'ip':machine['ip_internal']}

  # Get App machines
  app_machines = site_control.GetPoolMachineList(4)

  # Generate App listening services
  app_output = ''
  for machine_id in app_machines:
    machine = site_control.GetMachine(machine_id)
    label = 'app_machine_%s' % machine_id
    app_output += template_item % {'name':label, 'ip':machine['ip_internal']}

  # Get the template
  if not test_template:
    template = config_util.LoadTemplate('haproxy.txt')
  else:
    template = open(test_template).read()
  
  # Create final output
  # Edge -> HTTP.  (HTTP -> Proxy.)  Proxy -> App.
  final_output = template % {'edge':http_output, 'proxy':app_output}

  # If we are working from a test template
  if test_template:
    config_util.PrintTestTemplate(HA_PROXY_CONFIG, final_output)
    return # We cant save

  # Save final output
  if save:
    changed = config_util.SaveFile(HA_PROXY_CONFIG, final_output)

    # Turn the service on
    config_util.RunCommand('/sbin/chkconfig --levels 2345 haproxy on')

    # Dont restart it if its already started
    config_util.RunCommand('/sbin/service haproxy start')

    # If the data changed, reload it
    if changed:
      # But do reload the config
      config_util.RunCommand('/sbin/service haproxy reload')


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