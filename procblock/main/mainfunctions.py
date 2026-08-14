"""
mainfunctions

main() related functions for procblock
"""


import sys
import os
import getopt
import time

sys.path.append('../')
from shared.log import log
import logging

import processing
import daemon as daemonize


from shared import sharedlock


class OptionsAndArgsFailure(Exception):
  """A problem in the options and args."""


def Usage_GetArgNames(usage):
  args = []
  
  if 'args' in usage:
    for arg in usage['args']:
      name = arg['name']
      required = arg.get('required', False)
      remaining = arg.get('remaining', False)
      
      # If this will absorb the remaining items, it is by definition optional
      #NOTE(g): This optional-always for this is a design decision to simplify
      #   this code.  Use a forced first argument if you require a first arg.
      if remaining:
        name = '[%s1 %s2 ...]' % (name, name)
      
      elif 'default' in arg and not required:
        name = '[%s]' % name
      
      args.append(name)
  
  return args


def GetProgramName():
  return os.path.basename(sys.argv[0])


def PrintUsage(block, error=None):
  """Print out any __usage information in this block.
  
  Returns: string or None, string if __usage information found
  """
  if '__usage' not in block:
    return None
  
  # Get the usage
  usage = block['__usage']
  
  # Our output string
  output = ''
  
  if 'name' in usage:
    output += 'Name: %s\n' % usage['name']
  
  if 'author' in usage:
    output += 'Author: %s\n' % usage['author']
  
  if 'website' in usage:
    output += 'Website: %s\n' % usage['website']
  
  # Vertical buffer, if needed
  if output:
    output += '\n'
  
  # Get program name
  program_name = GetProgramName()
  
  # Create list of args
  args = Usage_GetArgNames(usage)
  
  if error:
    output += '  error: %s\n\n' % error
  
  output += 'usage: %s <options> %s\n\n' % (GetProgramName(), ' '.join(args))
  
  # Args
  if args:
    output += 'Args:\n'
    
    for arg in usage['args']:
      name = arg['name']
      
      # Data
      info = arg.get('info', '*NO INFO*')
      required = arg.get('required', False)
      default = arg.get('default', None)
      remaining = arg.get('remaining', False)
      
      # Build descriptive text
      text = ''
      if default:
        text += 'Default=%s ' % default
      
      if required:
        text += 'Required '
      
      if remaining:
        text += '<Takes 0 or more args> '
      
      
      if text:
        text = '   (%s)' % text.strip()
        
      output += '  %-30s %-40s%s\n' % (name, info, text)
    
    output += '\n'
  
  # Options
  if 'options' in usage:
    output += 'Options:\n'
    
    for name in usage['options']:
      arg = usage['options'][name]
      
      # Data
      info = arg.get('info', '*NO INFO*')
      type = arg.get('type', 'flag')
      default = arg.get('default', None)
      letter = arg.get('letter', None)
      
      # Build descriptive text
      text = ''
      if default:
        text += 'Default=%s ' % default
      
      # Create our name and argument, for value options
      if type != 'flag':
        name_arg = '--%s <value>' % name
      else:
        name_arg = '--%s' % name
        text += '<Flag> '
      
      # If we have a letter
      if letter:
        name_arg = '-%s, %s' % (letter, name_arg)
      
      if text:
        text = '   (%s)' % text.strip()
        
      output += '  %-30s %-40s%s\n' % (name_arg, info, text)
  
  return output


def PrintStartup(usage):
  output = ''
  
  if not usage:
    return 'No usage.'

  if 'name' in usage:
    output += 'Name: %s\n' % usage['name']
  
  if 'author' in usage:
    output += 'Author: %s\n' % usage['author']
  
  if 'info' in usage:
    output += 'Info: %s\n' % usage['info']
  
  if 'website' in usage:
    output += 'Website: %s\n' % usage['website']
  
  return output


def ProcessOptionsAndArgs_NoUsageBlock(block, starting_arg=2):
  """Returns a dictionary with all options and args processed.
  
  All options are put into their own keywords.  All args are put into _args.
  """
  data = {'args':[]}
  
  # Get our args
  args = sys.argv[starting_arg:]
  
  # Start processing the options
  initial_options = True
  option_name = None
  
  # Process all the args
  for arg in args:
    # If we are processing options (no raw args yet)
    if initial_options:
      # If we dont have an option name selected yet...
      if option_name == None:
        # Long option name
        if arg.startswith('--'):
          option_name = arg[2:]
        # Short option name (letter)
        elif arg.startswith('-'):
          option_name = arg[1:]
        # Else, not an option at all, so start saving args
        else:
          initial_options = False
      
      # Else, we already have an option name, and are going to save a value
      else:
        # Save this arg into the option name that was specified
        data[option_name] = arg
        
        # Clear the option name, we already saved the value
        option_name = None
    
    # Dont use elif, because we just set it as the failed case in the last test
    if not initial_options:
      data['args'].append(arg)
  
  # If we still have an option name, we didnt give it an option value
  if option_name != None:
    raise Exception('Option missing value: %s' % option_name)
  
  return data


def ProcessOptionsAndArgs(block, starting_arg=2):
  """Returns a dictionary with all options and args processed.
  
  NOTE(g): starting_arg=2, and not 1, because procblock will typically
      be given a procblock YAML file to process first, then options and args
      will be extracted.  Change if required.
  """
  data = {}
  
  if '__usage' not in block:
    log('No __usage block')
    return ProcessOptionsAndArgs_NoUsageBlock(block, starting_arg=starting_arg)
  
  # Get the usage
  usage = block['__usage']
  
  # Get list of args
  args = []
  if 'args' in usage:
    for count in range(0, len(usage['args'])):
      args.append(usage['args'][count])
  
  # Get dict of options
  options = {}
  if 'options' in usage:
    for key in usage['options']:
      options[key] = usage['options'][key]
  
  # Format getopt argument input structure: [(--option, default), ...]
  getopt_options = ['help',]
  getopt_short = 'h'
  for (name, option) in options.items():
    default = option.get('default', None)
    
    # Tell getopt to expect a value if this isnt a flag
    if option.get('type', 'flag') != 'flag':
      name = '%s=' % name
    
    getopt_options.append(name)
    
    # If this option has a letter, add it too
    if 'letter' in option:
      # If this letter requires a value
      if option.get('type', 'flag') != 'flag':
        getopt_short += '%s:' % option['letter']
      else:
        getopt_short += '%s' % option['letter']

  # Get our args
  args = sys.argv[starting_arg:]
  
  #print 'Getopt args: %s' % args
  #print 'Getopt short: %s' % getopt_short
  #print 'Getopt options: %s' % getopt_options
  
  # Use getopts
  (post_options, post_args) = getopt.getopt(args, getopt_short, getopt_options)
  
  #print 'Options: %s' % post_options
  #print 'Args: %s' % post_args
  

  # Process the options
  if 'options' in usage:
    for (key, option) in usage['options'].items():
      letter = option.get('letter', None)
      
      # Process each post_option entry against this option's details
      for (opt_name, opt_value) in post_options:
        # Hard code the usage request, and exit
        if opt_name in ('-h', '--help'):
          output = PrintUsage(block)
          print output
          sys.exit(0)
        
        
        # If the long name was used
        if '--%s' % key == opt_name:
          if option.get('type', 'flag') != 'flag':
            data[key] = opt_value
          else:
            data[key] = True
        
        # Else, if the short name was used
        elif letter and '-%s' % letter == opt_name:
          if option.get('type', 'flag') != 'flag':
            data[key] = opt_value
          else:
            data[key] = True
      
      # If this option was not set, and it has a default, set it
      if key not in data and 'default' in option:
        data[key] = option['default']
      elif key not in data and option.get('type', 'flag') == 'flag':
        data[key] = False

  
  # Process the args
  if 'args' in usage:
    for count in range(0, len(usage['args'])):
      arg = usage['args'][count]
      name = arg['name']
      
      #TODO(g): Remaining will absorb the REST!!!!!
      
      #print '%s: %s: %s' % (count, len(post_args), arg)
      
      # If we have this argument
      if count < len(post_args):
        # If this is not a "remaining" arg, that takes the rest
        if not arg.get('remaining', False):
          data[name] = post_args[count]
        
        # Else, this is a "remaining" arg, it takes all the rest of the args
        else:
          # Take all the rest of the args
          data[name] = post_args[count:]
          
          # Break out of our arg counter, we're done
          break
      
      # Else, we dont have this argument
      else:
        # If this argument is required, quit
        if arg.get('required', False):
          #TODO(g): Better failure method...  USAGE!
          error = 'Required argument missing: Arg count %s: Name: %s' % (count, arg.get('name', '*UNKNOWN NAME*'))
          raise OptionsAndArgsFailure(error)
        
        # Else, if this arg has a default
        elif 'default' in arg:
          data[name] = arg.get('default', None)
        
        # Else, if this arg is for remaining vars, but doesnt exist, set it to
        #   an empty set
        elif arg.get('remaining', False):
          data[name] = []
  
  return data


class ProcessAndLoopDaemon(daemonize.Daemon):
  """Daemonized version of this command.  Use in production.  Default."""

  def __init__(self, usage, block, data, state, chain_output):
    self.usage = usage
    self.block = block
    self.data = data
    self.state = state
    self.chain_output = chain_output
    
    # Initialize superclass
    daemonize.Daemon(self, pidfile)

  def run(self):
    log('ProcessAndLoopDaemon')
    
    sharedlock.Acquire('__running')
    
    try:
      output = processing.Process(self.block, self.data, self.state, self.chain_output)
      
      print 'Output:'
      import pprint
      pprint.pprint(output)
    except Exception, e:
      log(e, logging.ERROR)
      raise e


def ProcessAndLoop(usage, block, input_data, request_state, pipe_data):
  """Process the block, and loop while it is executing RunThreads.
  
  Handles daemonization as well.
  """
  log('ProcessAndLoop')
  #log('ProcessAndLoop: %s' % block)
  #log(' input_data: %s' % input_data)
  
  # We are now running.  When this lock is released all procblock threads
  #   that check this lock will exit.  This is key to having lots of threads
  #   that will actually exit when we globally want to quit.
  sharedlock.Acquire('__running')
  
  # Daemonize ourselves
  if usage and usage.get('daemon', False):
    #TODO(g): More unique default name.  sys.argv[0] based...
    pidfile = usage.get('pidfile', 'procblock.pid')
    stdout = 'procblock.out'
    
    try:
      #TODO(g): Have to sub-class daemon.   This wont work!
      raise Exception('Have to sub-class Daemon class, so we can pass in the proper arguments to have it run processing.Process()')
      log('Daemonizing: pidfile: %s' % pidfile)
      #daemon = daemonize.Daemon(pidfile, stdout=stdout)
      daemon = daemonize.Daemon(pidfile)
      log('Daemonizing: Starting')
      daemon.start()
    except Exception, e:
      log(e, logging.ERROR)
      raise e
  
  # Else, if this is not a daemonized process, but is long running.
  #   We need to stick around and wait until the user aborts.
  elif usage and usage.get('longrunning', False):
    log('Long Running Process: Starting...')
    
    # Process the data, but the output should be a dict of RunThread objects
    output = processing.Process(pipe_data, block, request_state, input_data,
                                tag=None, cwd=None, env=None,
                                block_parent=None)
    #output = processing.Process(block, input_data, request_state, pipe_data)
    
    print 'Output:'
    import pprint
    pprint.pprint(output)
    
    # While we are still running, loop
    try:
      while sharedlock.IsLocked('__running'):
          log('Running...')
          time.sleep(2)
    
    except KeyboardInterrupt, e:
      log('ProcessAndLoop: Keyboard Interrupt: Releasing lock: __running')
      sharedlock.Release('__running')
  
  # Else, run without daemonization
  else:
    log('ProcessAndLoop: Running once...')
    try:
      output = processing.Process(pipe_data, block, request_state, input_data,
                                  tag=None, cwd=None, env=None,
                                  block_parent=None)
      #output = processing.Process(block, input_data, request_state, pipe_data)
      
      print 'Output:'
      import pprint
      pprint.pprint(output)
    
    # Always release the lock
    finally:
      sharedlock.Release('__running')

  
  log('Quitting...')


