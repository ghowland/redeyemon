#!/usr/bin/python


#Author: Matt Kirk
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
Service Configure: Apache
"""


import os
import config_util
import config_tweetedia


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
  #TODO(g): Get this from the service config!
  APACHE_CONFIG = '/etc/httpd/conf/httpd.conf'

  # Create final output
  if not test_template:
    template = config_util.LoadTemplate('apache_conf.txt')
  else:
    template = open(test_template).read()
  
  # Create final output
  final_output = template

  # If we are working from a test template
  if test_template:
    config_util.PrintTestTemplate(APACHE_CONFIG, final_output)
    return # We cant save

  # Save final output
  if save:
    changed = config_util.SaveFile(APACHE_CONFIG, final_output)
    
    # Turn the service on
    config_util.RunCommand('/sbin/chkconfig --levels 2345 httpd on')
    
    
    # If the data changed, reload it
    if changed:
      # Dont restart it if its already started
      config_util.RunCommand('/sbin/service httpd start')
      
      # But do reload the config
      config_util.RunCommand('/sbin/service httpd reload')
    
    else:
      # Dont restart it if its already started
      config_util.RunCommand('/sbin/service httpd start')
  
  
  # Install the Tweetedia code base
  performed_install = config_tweetedia.Install()

  # If we installed it, restart
  if performed_install:
    config_util.RunCommand('/sbin/service httpd restart')



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
