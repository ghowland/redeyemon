"""
processing

Processing procblock blocks.  This is where the magic happens!
"""

import Queue #NOTE(g): Python 2.6 required
import re

import procyaml
import builtins

from shared import log as logging
from shared.log import log


# Default Tag Functions
PROCESSING_DEFAULT_TAGS = None

CONDITIION_DEFAULT_TAGS = None


class DoNotSaveTag(Exception):
  """Do not save tags that have this exception thrown.  They are not meant
  to be returned as data, they operate in the shadows."""


class UpdateBlockData(Exception):
  """Update the block data of the parent block with the target data."""
  
  def __init__(self, data):
    self.data = data


def LoadDefaultTagFunctions():
  """Load the default Tag Functions."""
  #TODO(g): Un-hard code?
  functions = procyaml.ImportYaml('data/default_tag_functions.yaml')
  
  return functions


def LoadDefaultConditionFunctions():
  """Load the default Condition Functions."""
  #TODO(g): Un-hard code?
  functions = procyaml.ImportYaml('data/default_condition_functions.yaml')
  
  return functions


def Init_ReEntrant():
  """Initialize our Default Tag Functions."""
  global PROCESSING_DEFAULT_TAGS
  global CONDITIION_DEFAULT_TAGS
  
  if PROCESSING_DEFAULT_TAGS == None:
    PROCESSING_DEFAULT_TAGS = {} #TODO(g): Thread safe dict!
    PROCESSING_DEFAULT_TAGS.update(LoadDefaultTagFunctions())
  
  if CONDITIION_DEFAULT_TAGS == None:
    CONDITIION_DEFAULT_TAGS = {} #TODO(g): Thread safe dict!
    CONDITIION_DEFAULT_TAGS.update(LoadDefaultConditionFunctions())


def AddTagFunction(tag_name, tag_function_block):
  """Add a Tag Functions to our defaults."""
  PROCESSING_DEFAULT_TAGS[tag_name] = tag_function_block


def GetDefaultTagFunctionBlock(tag):
  global PROCESSING_DEFAULT_TAGS
  
  # If we straight up have the tag, return it
  if tag in PROCESSING_DEFAULT_TAGS:
    return PROCESSING_DEFAULT_TAGS[tag]
  
  # Look for globs in our tag functions
  for tag_function in PROCESSING_DEFAULT_TAGS:
    ## Replace any globbing character for regex
    #if '*' in tag_function:
    #  tag_search = tag_function.replace('*', '.*?')
    #else:
    #  tag_search = tag_function 
    tag_search = tag_function #TODO(g): Any processing needed?
    
    # Build regex string
    regex = '^(%s)$' % tag_search
    
    found_list = re.findall(regex, tag)
    
    #print 'Regex: %s --> %s --> %s' % (tag, regex, found_list)
    
    # If this matched, then return this tag function block
    if found_list:
      return PROCESSING_DEFAULT_TAGS[tag_function]
  
  # Failed to find the tag, return None
  return None



def Process(pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):
#def Process(block, data, state, chain_output, env=None, block_parent=None):
  """Process this block.  This is where the magic happens!
  
  Args:
    data: dict, used as input
    state: dict, used as long running shared state, another kind of input.
    chain_output: dict, like state, but for a pipeline or chain of
        Process() calls.  chain_output is a dictionary that is updated()d at
        with the result of this function.
    env: dict (optional), if executing shell commands, all keys are set
        to the str() of their values in the shell environment.
    block_parent: dict (optional), if we know and want to pass along the parent,
        do it this way to avoid another piece of data to keep track of, as
        a given piece of data could think of parents in different ways.
  """
  #log('Processing Block: %s' % tag)
  #log('Processing Block: %s  Data: %s' % (block, input_data))
  
  # Ensure block will not be changed from the source (only 1 level deep)
  if type(block) in (dict, ):
    block = dict(block)
  
  global PROCESSING_DEFAULT_TAGS
  Init_ReEntrant()
  
  # Collect the tags (keys) in this block
  tags = []
  for key in block:
    tags.append(key)
  # Sort so non-prioritized come out in alpha-deterministic order (minimizes
  #   side effects)
  tags.sort()
  
  #print 'Block tags: %s' % tags
  
  # Prioritize processing the keys based on procblock's list of Tag Functions
  prioritized_tags = Queue.PriorityQueue()
  for tag in tags:
    # Default
    priority = 500
    
    # Get our tag function, if it exists
    tag_function_block = GetDefaultTagFunctionBlock(tag)
    
    # If a priority was specified, use that
    if type(block[tag]) == type({}) and '__priority' in block[tag]:
      priority = int(block[tag]['__priority'])
    # Else, If we have this tag function, give it a priority
    elif tag_function_block and '__priority' in tag_function_block:
      priority = tag_function_block['__priority']
    
    # Put the tag into the queue
    prioritized_tags.put((priority, tag))
    #print 'Priority: %s: %s' % (priority, tag)

  # Create a prioritized list, so I can print it out
  prioritized_list = []
  done = False
  while not done:
    try:
      (priority, tag) = prioritized_tags.get_nowait()
      
      prioritized_list.append((priority, tag))
    
    except Queue.Empty, e:
      done = True
  
  #print prioritized_list
  
  
  # Never modify the block we are passed.  We always create a new dictionary
  #   and populate it
  #TODO(g): Create thread-safe dictionary replacement when done, and test with
  #   working code to see that it doesnt interfere with coding.  Normal
  #   coding practices should be able to be followed.  (type()=={} wont...,
  #   instanceof(UserDict) will)
  new_block = {}
  
  # Process prioritized tags into a new dictionary
  for (priority, tag) in prioritized_list:
      #print 'Processing: %s: %s' % (priority, tag)
      
      # If this tag is in a Default Tag Functions, then process it with that
      tag_function_block = GetDefaultTagFunctionBlock(tag)
      if tag_function_block:
        #print 'Tag Function Block: %s' % tag_function_block
        
        if '__builtin' in tag_function_block:
          function = builtins.GetFunctionByName(tag_function_block['__builtin'])
          
          if function == None:
            raise Exception('Found tag function, but returned None: %s' % tag_function_block['__builtin'])
        else:
          raise Exception('No __builtin specified for Tag Function: %s' % tag)
        
        # Call the function and populate the new_block
        try:
          out_block = function(pipe_data, block[tag], request_state, input_data, tag=tag, cwd=cwd, env=env, block_parent=block)
          #out_block = function(tag, block[tag], data, state, chain_output, env=env, block_parent=block)
          new_block[tag] = out_block
        except DoNotSaveTag, e:
          pass
        except UpdateBlockData, e:
          new_block.update(e.data)
        #TODO(g): CRITICAL: Un-comment
        #except Exception, e:
        #  print 'Exception on: %s: %s: %s: %s' % (tag_function_block['__builtin'], tag, block[tag], e)
        #  raise e
      
      #TODO(g): Add a check for user specified tag functions separate than
      #   the default tags?  Not sure how this should work yet, think about it.
      elif 0:
        pass
      
      # Else, process this tag's block like a standard block process, and assign
      #   it into the new_block that we save data into.  This gives us recursive
      #   processing through all the hierarchical data, so all conditions are
      #   tested against this data, state and chain_output.
      else:
        # If this block is a dictionary, so it's another block, process it
        #TODO(g): Add UserDict instanceof test
        if type(block[tag]) == type({}):
          log('Processing block: Tag: %s' % tag)
          # Process the tag block, and store the result
          try:
            out_block = Process(pipe_data, block[tag], request_state, input_data, tag=tag, cwd=cwd, env=env, block_parent=block)
            #out_block = Process(block[tag], data, state, chain_output, env=env, block_parent=block)
            new_block[tag] = out_block
            #print 'Tag Out Block: %s: %s' % (tag, out_block)
          except DoNotSaveTag, e:
            pass
          except UpdateBlockData, e:
            #print 'UpdateBlockData: %s: %s' % (tag, e.data)
            new_block.update(e.data)
        
        # Else, it's not a dictionary, so it's data.  Store it in new_block
        else:
          #print 'Assigning data: %s (%s)' % (tag, type(block[tag]))
          new_block[tag] = block[tag]
    
    ## Remove internal data we no longer need.  ONLY do this for non-output.
    #if '__skip' in result:
    #  del result['__skip']
  
  # If we have a command to return a tag's data, instead of the new block,
  #   then save that as the result
  if '__return_tag' in new_block:
    result = new_block.get(new_block['__return_tag'], None)
    
    #print 'Returning tag data:'
    #print '  Return tag: %s' % new_block['__return_tag']
    #print '  Result: %s' % result
    #print '  Block: %s' % block
    
  # Else, save the new_block data is the result
  else:
    result = new_block
  
  # Remove any internal variables (starting with __)
  for key in result.keys():
    if key.startswith('__'):
      del result[key]
  
  # Update the chain_output dictionary with our result dict
  pipe_data.update(result)
  
  # Return the result
  return result
  
