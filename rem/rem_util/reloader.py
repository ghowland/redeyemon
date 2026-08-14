#!/usr/bin/python


#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Python Module Reloader

If any of our Python modules get newer (with a delay, to avoid file shearing),
then reload them so we never have to quit the daemon and can run forever while
getting code updates underneath us.
"""


import time
import os
import stat
import sys


import log as logging
from log import log


# Seconds before we will reload after a file changes, to ensure other files
#   are also reloaded at the same time, so there arent errors
RELOAD_DELAY = 60


RELOADER = None


class Reloader:
  """Keeps track of all the modules we've loaded, and reloads any that are stale"""

  def __init__(self):
    # Keyed on filename, with epoch time as value.
    self.modules = {}


  def Update(self):
    """Reload any of our stale module files."""
    # Seed our list with new items, they get their current times saved now
    all_modules = self.GetAllModules()
    for mod in all_modules:
      # If we dont already have this, get it's current file time
      if mod not in self.modules:
        filename = self.GetModuleFile(mod)
        self.modules[mod] = self.GetFileChanged(filename)

    # Check all the modules
    for mod in self.modules:
      filename = self.GetModuleFile(mod)
      changed = self.GetFileChanged(filename)
      
      # If its not the same changed time we have stored
      if changed != self.modules[mod]:
        # Only reload this file if it's older than our reload delay
        #   This prevents loading a file while its being saved, and also
        #   from reloading a single file when a number of files where changed
        #   but not all of them have been completed yet.
        if self.GetFileAge(filename) > RELOAD_DELAY:
          # Reload the module
          self.Reload(mod)
          
          # Save our updated reload time
          self.modules[mod] = changed


  def GetFileChanged(self, filename):
    """Stats the file and returns diff from current time.

    Returns: int, seconds since file changed
    """
    change_time = os.stat(filename)[stat.ST_MTIME]

    return change_time


  def GetFileAge(self, filename):
    """Stats the file and returns diff from current time.

    Returns: int, seconds since file changed
    """
    change_time = self.GetFileChanged(filename)

    age = time.time() - change_time

    return age


  def Reload(self, mod):
    """Reload the filename."""
    log('Reloading Python Module: %s' % mod)
    
    reload(mod)


  def GetModuleFile(self, mod):
    """Returns the filename for this module."""
    filename = getattr(mod, '__file__')

    # Crop the .PYC to .PY
    if filename.lower().endswith('.pyc'):
      filename = filename[:-1]
    
    return filename


  def GetAllModules(self):
    """."""
    all_modules = []

    for key in sys.modules:
      mod = sys.modules[key]

      # If this is a module that comes from a file (not a builtin)
      if hasattr(mod, '__file__'):
        all_modules.append(mod)
    
    return all_modules


LAST_CALLED = 0
LAST_CALLED_TOO_SOON = 30 # seconds
def Update():
  """Checks all the loaded modules, looks at their source files, and reloads
  them if they have changed."""
  global RELOADER
  global LAST_CALLED
  global LAST_CALLED_TOO_SOON
  
  # If we have run recently dont run now
  if LAST_CALLED + LAST_CALLED_TOO_SOON > time.time():
    return

  if not RELOADER:
    RELOADER = Reloader()

  RELOADER.Update()
  
  # Update when we were last called
  LAST_CALLED = time.time()


if __name__ == '__main__':
  #TEST: manually update a module while were running
  Update()
  print RELOADER.GetFileChanged('C:\\Users\\Geoff\\Documents\\Projects\\Sonoma\\src\\site_control\\rem\\rem_ec2.py')
  print RELOADER.GetFileAge('C:\\Users\\Geoff\\Documents\\Projects\\Sonoma\\src\\site_control\\rem\\rem_ec2.py')
  print 'Sleeping'
  time.sleep(6)
  print RELOADER.GetFileChanged('C:\\Users\\Geoff\\Documents\\Projects\\Sonoma\\src\\site_control\\rem\\rem_ec2.py')
  print RELOADER.GetFileAge('C:\\Users\\Geoff\\Documents\\Projects\\Sonoma\\src\\site_control\\rem\\rem_ec2.py')
  Update()
