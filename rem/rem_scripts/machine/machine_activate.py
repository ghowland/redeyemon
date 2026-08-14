#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Machine: Activate

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


def Activate():
  """Configure our local machine."""
  # Activate any machines in the Verified category
  machines = site_control.GetMachines(status=4)

  # Process our machines
  for (machine_id, machine) in machines.items():
    # Update our data
    data = dict(machine)
    data['status'] = 5 # Active!

    # Save our data
    site_control.UpdateData('machine', machine_id, data)



def main():
  Activate()



if __name__ == '__main__':
  main()
