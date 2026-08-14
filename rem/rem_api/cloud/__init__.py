#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Cloud Package

This allows us to wrap all the different cloud offerings, include an Auto-Cloud.

TODO(g): Do the multi/auto-cloud stuff later.  EC2 for now.
"""


#TODO(g): Use all of REM's routines as if they were the only Cloud functoins,
#   but later this can be wrapped.
from rem_ec2 import *


# These are the Cloud-Neutral commands.
#TODO(g): Switch ALL calls to use these functions, and totally wrap rem_ec2
#   so that we are cloud neatral and can start to implement multiple cloud
#   vendor possibilities inside a single system for real Disaster Recovery
#   scenarios.
#
#   In this case, REM will serve to bridge the gap between multiple providers,
#   ensuring there are enough machines in all providers to re-create the entire
#   system from those seeds.
from cloud import *
