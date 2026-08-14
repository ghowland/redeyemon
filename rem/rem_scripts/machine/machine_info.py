#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Machine Info.

Collect information about this machine, such as it's machine.id in Site Control.
"""


import rem_scripts.config.config_util as config_util


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


import pprint


def GetMachineInfo():
  """Returns text output of information about this machine."""

  template = config_util.LoadTemplate('machine_info.txt')

  machine_id = site_control.GetThisMachineId()
  machine = site_control.GetMachine(machine_id)
  pool_ids = site_control.GetMachinePools(machine_id)

  # Get list of pool names
  pool_names = []
  for pool_id in pool_ids:
    pool = site_control.GetPoolById(pool_id)
    pool_names.append(pool['name'])

  data = dict(machine)
  data['pools'] = pool_names
  site_data = site_control.GetSiteById(machine['site'])
  data['site_name'] = site_data['name']
  data['machine'] = pprint.pformat(machine, indent=2)
  data['site_data'] = pprint.pformat(site_data, indent=2)
  data['master_ip'] = rem_ec2.GetMasterIp()
  if data['master_ip'] == data['ip_internal']:
    data['is_master'] = True
  else:
    data['is_master'] = False

  # Format the template, non-destructively.  (Keep unused format strings and %s)
  output = site_control.WebTemplateFormat(template, data)

  return output


if __name__ == '__main__':
  logging.Disable()

  output = GetMachineInfo()
  print output
