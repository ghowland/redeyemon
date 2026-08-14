#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


import xmlrpclib

proxy = xmlrpclib.ServerProxy("http://localhost:3737/")

import pprint

a = proxy.CollectRrdData()

pprint.pprint(a)
