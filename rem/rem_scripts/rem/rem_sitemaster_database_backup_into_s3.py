#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
REM: Site Control Master Database backup into S3

We want to keep a local copy of our Site Control master database in S3 in case
of the Master Failing.

This should happen regularly, and on configuration change.
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def BackupSiteControl():
  """Backup our Site Control database into S3."""
  # Backup our database into S3
  site_control.BackupSiteControlDatabaseToS3()


def main():
  BackupSiteControl()


if __name__ == '__main__':
  main()
