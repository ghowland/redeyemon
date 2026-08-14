#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
If the AMI changes for a pool of machines, then those machines must be
swapped out, one by one, so that the new AMI is brought up.  This automates
being able to upgrade the machines while they are still in production.

TODO(g): Do this, this is critical to making REM easy to admin.
"""

# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *

