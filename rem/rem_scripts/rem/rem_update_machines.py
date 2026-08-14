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


def RemUpdateMachines():
  """Uses rsync to keep all our machines up to date with the Master."""
  return 'FAILURE: Need to get SSH working between the machines before this can work.'

  # If this machine is not the master, dont do this, ever
  is_master = IsThisMachineMaster()
  if not is_master:
    return 'This machine is not the master.  Quitting.'

  output = ''

  machines = site_control.GetMachines(status=None)

  # Copy all our REM data and script files to all the other non-Requested/Decomm
  #   machines.  All that can take the files.
  for (machine_id, machine) in machines.items():
    # Skip Requested and Decommissioned machines, they dont need them
    if machine['status'] in (1, 7):
      continue
    
    #TODO(g): Create a sync directory, sync there, move the directories, so the
    #   files are never tampered with one at a time...

    #TODO(g):ERROR: The machines cant SSH to each other by default...  Will have
    #   to fix this before this can work...
    cmd = '/usr/bin/rsync -r /usr/local/site_control/rem/* %s:/usr/local/site_control/rem/' % machine['dns_private']
    (status, output, output_error) = run_script.Run(cmd)

  return output


if __name__ == '__main__':
  logging.Disable()

  output = RemUpdateMachines()
  print output
