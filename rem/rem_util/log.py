#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Logging
"""


import sys
import logging
import logging.handlers
import time


import stack


# Wrap logging labels
DEBUG = logging.DEBUG
INFO = logging.INFO
WARN = logging.WARN
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL
ALERT = 100

# Lookup log functions, to wrap them
LOG_FUNCTION = {
  DEBUG:'debug',
  INFO:'info',
  WARN:'warn',
  ERROR:'error',
  CRITICAL:'critical',
  ALERT:'critical',
}

# Default
DEFAULT_LOG_LEVEL = DEBUG


#TODO(g): Better...
DEFAULT_LOG_FILE = '/usr/local/site_control/rem.log'
#DEFAULT_LOG_FILE = 'rem.log'


# Logger object, singleton
LOGGER = None

# Globla for disabling logging, for scripts that we dont want having
#   interference
DISABLE_LOGGING = False


def SetLogFile(path):
  global DEFAULT_LOG_FILE
  DEFAULT_LOG_FILE = path


def Disable():
  """Logging will be disabled for this program.  Do not run for REM Client."""
  global DISABLE_LOGGING
  DISABLE_LOGGING = True


def _GetLogger():
  """Gets a singleton logger."""
  global LOGGER

  #TODO(g): ...
  log_file = DEFAULT_LOG_FILE

  # Set max file size
  #TODO(g): better...
  MAX_FILESIZE = 1024 * 1024 * 10 # 10 megs

  # Maximum backups to keep
  #TODO(g): better...
  MAX_BACKUPS = 5

  if not LOGGER:
    # Set up a specific logger with our desired output level
    LOGGER = logging.getLogger('REM')
    LOGGER.setLevel(DEFAULT_LOG_LEVEL) #TODO(g): Configure default level

    # Add the log message handler to the logger
    handler = logging.handlers.RotatingFileHandler(log_file,
                                                   maxBytes=MAX_FILESIZE,
                                                   backupCount=MAX_BACKUPS)

    LOGGER.addHandler(handler)

  return LOGGER


def log(text, level=DEFAULT_LOG_LEVEL):
  """Log data."""
  # If logging is disabled, return
  global DISABLE_LOGGING
  if DISABLE_LOGGING:
    return

  # Get the logger
  logger = _GetLogger()

  # Add the stack information for the calling function to our text, so we know
  #   who is logging this.
  text = '%s:%s: %s' % (GetTimeStamp(), stack.Mini(1, 1), text)

  # Get function for logging
  func_name = LOG_FUNCTION[level]
  func = getattr(logger, func_name)

  #Debug
  if 1:
    console_out = '%s:%s' % (LOG_FUNCTION[level].upper(), text)
    #DEBUG: Writing to STDERR to avoid mixing with data
    sys.stderr.write(console_out + '\n')
    sys.stderr.flush() # Force flush, to stay up to date

    #print text

  # If this is a critical entry, page
  #NOTE(g): CRITICAL is used for REM failures, ALERT is used for site failures
  if level in (CRITICAL, ALERT):
    Alert(text)

  # Log the text
  func(text)


# Cache on text as key, with dict: {'last_alerted':time.time(), 'count':0+each}
#TODO(g): Make generic Cache class for using instead of re-doing it.  Libs?
ALERT_CACHE = {}
ALERT_DELAY = 60 * 30 # 30 Minute #TODO(g): Use service/site config
def Alert(text):
  """Alert that something critical happened inside REM."""
  global ALERT_CACHE
  global ALERT_DELAY
  
  # If this text is new, or this the last time this alerted was past delay
  if text not in ALERT_CACHE or \
      ALERT_CACHE[text]['last_alerted'] + ALERT_DELAY < time.time():
    # Ensure cache dict entry exists
    if text not in ALERT_CACHE:
      ALERT_CACHE[text] = {'last_alerted':None, 'count':0}
    
    # Update cache settings
    ALERT_CACHE[text]['last_alerted'] = time.time()
    ALERT_CACHE[text]['count'] += 1
    
    # Alert!
    #TODO(g):...
    log('Todo(g): ALERT: %s' % text)
    pass#TODO...


def GetTimeStamp(minutes=True, seconds=True):
  """Gets time stamps, for use in dating backup files and other things."""
  import time
  (year, month, day, hour, minute, second, _, _, _) = time.localtime()

  if seconds:
    output = '%02d%02d%02d%02d%02d%02d' % (year, month, day, hour, minute, second)
  elif minutes:
    output = '%02d%02d%02d%02d%02d' % (year, month, day, hour, minute)
  else:
    output = '%02d%02d%02d%02d' % (year, month, day, hour)

  return output


if __name__ == '__main__':
  #Test
  def TestMe():
    for count in range(0, 5):
      log('Bingo: %d!' % count)

  TestMe()
