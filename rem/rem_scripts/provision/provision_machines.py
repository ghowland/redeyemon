#!/usr/bin/python


#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Provision: EC2 Machines
"""

# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def main():
  # Provision the Pool Machines
  site_control.ProvisionMachines()


if __name__ == '__main__':
  main()
