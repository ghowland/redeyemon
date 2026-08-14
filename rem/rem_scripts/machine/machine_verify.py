#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Machine: Verify

Second stage of brining a machine up.  Once a machine is Requested(1), we
have it's instance info, but not access info, because it hasnt been provisioned
by EC2 yet.  This runs to collect that connection information and then
set the machine's state to Allocated(2) to let to be Installed(3).

Configure: local files
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def Verify():
  """Configure our local machine."""
  # Verify any machines in the Installed category
  machines = site_control.GetMachines(status=3)

  # Process our machines
  for (machine_id, machine) in machines.items():
    # Update our data
    data = dict(machine)
    data['status'] = 4 # Verified!

    #TODO(g): Run Verification script

    # Save our data
    site_control.UpdateData('machine', machine_id, data)



def main():
  Verify()



if __name__ == '__main__':
  main()
