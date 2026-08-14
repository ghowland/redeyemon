#!/usr/bin/python


#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Service Configure: Nginx for Monitoring Graphs
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
  #TODO(g): Get this from the service config!
  NGINX_CONFIG = '/etc/nginx/nginx.conf'
  
  # Template item to roll over our data
  template_item = '\t\tserver %(ip)s:8200;\n'

  # Get Proxy machines
  MONITOR_POOL = 10
  machines = site_control.GetPoolMachineList(MONITOR_POOL)

  # Generate HTTP listening services
  proxy_output = ''
  for machine_id in machines:
    machine = site_control.GetMachine(machine_id)
    proxy_output += template_item % {'ip':machine['ip_internal']}

  # Create final output
  if not test_template:
    template = config_util.LoadTemplate('nginx.txt')
  else:
    template = open(test_template).read()
  
  final_output = template % {'proxy':proxy_output}

  # If we are working from a test template
  if test_template:
    config_util.PrintTestTemplate(NGINX_CONFIG, final_output)
    return # We cant save

  # Save final output
  if save:
    changed = config_util.SaveFile(NGINX_CONFIG, final_output)

    # Turn the service on
    config_util.RunCommand('/sbin/chkconfig --levels 2345 nginx on')

    # Dont restart it if its already started
    config_util.RunCommand('/sbin/service nginx start')

    # If the data changed, reload it
    if changed:
      # But do reload the config
      config_util.RunCommand('/sbin/service nginx reload')



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