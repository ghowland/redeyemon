#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: API Package manager

Add any additional API modules to this list, and import all their members in
site_control.py
"""


class IncorrectExecuteArgs(Exception):
  """The args that were passed to the script Execute function were incorrect."""


# ** Import all our API modules, including all their functions to have a grand
#   API all collection in a single module. **

from database import *
from floating_ip import *
from hardware import *
from load_balancing import *
from machine import *
from master import *
from pool import *
from provisioning import *
from rrd import *
from script import *
from service import *
from site import *
from storage import *
from trigger import *
from update import *
from web import *
from rpc_site_control import *

# Web rendering for our data
from web_render import *
from web_render_machine import *
from web_render_database import *
from web_render_storage import *
from web_render_site import *
from web_render_pool import *
from web_render_service import *


# Import the cloud as rem_ec2, for backwards compatibility
#TODO(g): Remove this once all the cloud commands have been wrapped
import cloud

# Mach as rem_ec2 as well
rem_ec2 = cloud

# This module is special, in that it will wrap a number of different cloud
#   providers (including Auto-Cloud), evenentually.  For now it's just EC2.
#TODO(g): Move all rem_ec2 instances to this
from cloud import *
