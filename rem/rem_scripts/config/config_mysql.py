#!/usr/bin/python


#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Service Configure: MySQL
"""

import os

import config_util

# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def Configure(save=True, test_template=None):
  """Configure is intelligent, and knows how to handle different machine's
  configuration, so that in the same pool, some machines are masters, others
  are slaves.  Or whatever the circumstances may call for.
  
  Args:
    save: boolean, if true, will save this file
    test_template: string, file name to test a different template.  If set this
        will not save the configuration.
  """
  #TODO(g): Put in service config
  MYSQL_CONFIG = '/etc/my.cnf'
  
  if not test_template:
    template = config_util.LoadTemplate('mysql.txt')
  else:
    template = open(test_template).read()
  
  #TODO(g): Fill out the template more, then dynamically set the InnoDB pool
  #   sizes and other machine related stuff.
  #TODO(g): Fill out pathing to work with our storage solutions
  final_output = template

  # If we are working from a test template
  if test_template:
    config_util.PrintTestTemplate(APACHE_CONFIG, final_output)
    return # We cant save

  # Save the file
  if save:
    config_util.SaveFile(MYSQL_CONFIG, final_output)

    # Turn the service on
    config_util.RunCommand('/sbin/chkconfig --levels 2345 mysqld on')

    # Dont restart it if its already started
    config_util.RunCommand('/sbin/service mysqld start')



def main(args=None):
  if not args:
    args = []
  
  if not args:
    save = True
    template = None
  else:
    save = False
    template = args[0]
  
  Configure(save=save, test_template=template)



if __name__ == '__main__':
  main(sys.argv[1:])