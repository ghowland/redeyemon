#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
REM: Site Control configuration has changed

Backup the Site Control database, and alert all our machines to update their
configuration files be setting config_reload triggers on the machines.
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *



def SiteControlConfigChanged():
  """Deal with the config having been changed (by a user).
  
  Automated changes are backed up normally, except when a trauma-level event
  happens and we need to be safer than that.  This is for when a person makes
  a change.  We want to save those, because we dont want anyone to have to
  re-do work, and try to figure out what state the site has reverted back to
  because some work was not saved.
  """
  # Backup our database into S3
  site_control.BackupSiteControlDatabaseToS3()
  
  # Trigger our machines to reload their configurations
  site_control.TriggerMachinesToReloadConfigurations()


def main():
  SiteControlConfigChanged()


if __name__ == '__main__':
  main()
