"""
builtins

procblock built-in functions.

These are the foundational functions required to process our conditions,
state setting, message passing, thread management and code and script execution.
"""


from shared.log import log
import logging

from run import running
import processing
from shared import messagequeue
from shared import sharedlock
from shared import dotinspect


def GetFunctionByName(name):
  """Return the built-in function, by it's name."""
  FUNCTIONS = {
    'Set':Set,
    'RunBlock':RunBlock,
    'RunSimultaneousBlock':RunSimultaneousBlock,
    'ConditionIf':ConditionIf,
    #'ConditionElseIf':ConditionElseIf,
    #'ConditionElse':ConditionElse,
    'Conditions':Conditions,
    'Template':Template,
    'Control_PutTagResultInQueue':Control_PutTagResultInQueue,
    'Control_PreProcessLockAcquire':Control_PreProcessLockAcquire,
    'Control_FinalProcessLockRelease':Control_FinalProcessLockRelease,
    
    'List_Add':List_Add,
    'List_Remove':List_Remove,
    
    # Conditions
    'EqualTo':EqualTo,
    'GreaterThan':GreaterThan,
    'LessThan':LessThan,
    'GreaterThanOrEqualTo':GreaterThanOrEqualTo,
    'LessThanOrEqualTo':LessThanOrEqualTo,
    'NotEqualTo':NotEqualTo,
    'InSet':InSet,
    'NotInSet':NotInSet,
    'SetIsEmpty':SetIsEmpty,
    'SetIsNotEmpty':SetIsNotEmpty,
    'SetHas':SetHas,
    'SetHasNo':SetHasNo,
  }
  
  function = FUNCTIONS.get(name, None)
  
  if function == None:
    print 'Function not found: %s' % name
  
  return function


def Set(pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):
  """"Set a pipe_data variable.  Format:  set <variable name>: <data>"""
  print 'SET: %s (%s)' % (block, tag)
  
  add_to = tag.split(' ')[-1]
  
  if add_to in pipe_data:
    pipe_data[add_to] = block
  
  return block


def RunBlock(pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):
  """Run this block of functions serially."""
  import oldutil
  
  # Run it!
  output = oldutil.RunScriptBlock(pipe_data, block, request_state, input_data,
                                  tag=tag, cwd=cwd, env=env,
                                  block_parent=block_parent)
  #output = oldutil.RunScriptBlock(tag, block, input_data, request_state, pipe_data,
  #                                env=env, block_parent=block_parent, cwd=cwd)
  
  return output


def RunSimultaneousBlock(pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):
  """Run this block of functions in their own control threads.
  
  Returns: dict of RunThread objects, keyed on name
  """
  # Get our thread handler
  thread_handler = running.RunThreadHandler()
  pipe_data['_thread_handler'] = thread_handler
  
  # Our collection of running threads
  threads = {}
  
  # Create threads for all our actions, with their own run blocks
  for key in block:
    run_block = block[key]
    
    log('Run Block: %s' % run_block)
    
    # Create the run thread: block_parent = block
    run_thread = running.RunThread(thread_handler.GetNextRunThreadId(),
                                   pipe_data, run_block, request_state, input_data,
                                   tag=tag, cwd=cwd, env=env,
                                   block_parent=block)
    #run_thread = running.RunThread(thread_handler.GetNextRunThreadId(),
    #                               run_block, input_data, request_state, pipe_data,
    #                               env=env, cwd=cwd)
    
    # Save this RunThread object to our dict of threads
    threads[key] = run_thread
    
    # Start the Run Thread
    run_thread.start()
  
  return threads



def _ParseConditionTag(tag, inspect_data):
  data = {}
  
  
  #TODO(g): Convert to regex
  chunks = tag.split(' ')
  data['condition'] = chunks[0]
  data['operator'] = chunks[2]
  
  #TODO(g): This wont allow quoted strings with spaces on this side.
  #   Do a better job of parsing the chunks, splitting on space doesnt cut it.
  data['left'] = dotinspect.Inspect(chunks[1], inspect_data)
  
  
  # The remainder goes the text or variable on the Right Side
  text = ' '.join(chunks[3:])
  
  data['right'] = dotinspect.Inspect(text, inspect_data)

  print '_ParseConditionTag: %s: %s' % (tag, inspect_data)
  print '\n\n%s --> %s   %s   %s <-- %s\n' % (chunks[1], data['left'], data['operator'], data['right'], text)
  
  ## If text is quoted, save string
  #if text.startswith('"') and text.endswith('"'):
  #  text = text[1:-1]
  #  data['right_string'] = text
  #  data['right_variable'] = None
  ## ... If text is quoted, save string
  #elif text.startswith("'") and text.endswith("'"):
  #  text = text[1:-1]
  #  data['right_string'] = text
  #  data['right_variable'] = None
  ## Else, save variable
  #else:
  #  data['right_string'] = None
  #  data['right_variable'] = text
  
  return data


def _ConditionTest(left, operator, right):
  #print 'ConditionTest: %s %s %s' % (left, operator, right)
  
  # Get the operator function
  processing.Init_ReEntrant()
  operator_function = processing.CONDITIION_DEFAULT_TAGS[operator]['compare']
  
  function = GetFunctionByName(operator_function)
  
  # Execute the function to compare...
  success = function(left, right)
  
  if success:
    print 'ConditionTest: %s %s %s: True' % (left, operator, right)
    return True
  else:
    print 'ConditionTest: %s %s %s: False' % (left, operator, right)
    return False


def ConditionIf(pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):
  """If conditional statement."""
  log('If: %s' % tag)
  log('If: pipe_data: %s' % pipe_data)
  
  #TODO(g): Dont use right_string any more, in the condition, dotinspect will
  condition = _ParseConditionTag(tag, pipe_data)
  #print condition
  
  #print 'Conditions: %s' % condition
  #print 'Data: %s' % data
  
  left = condition['left']
  right = condition['right']
  
  ## If our left variable is in data
  #if condition['left'] in pipe_data:
  #  #left = pipe_data[condition['left']]
  #  
  #  left = dotinspect.Inspect(condition['left'], pipe_data)
  #else:
  #  #TODO(g): Create a VariableNotSet class, which is better than None
  #  log('Condition: Left not in data: %s' % condition['left'])
  #  left = None
  #
  #if condition['right_variable'] and condition['right_variable'] in pipe_data:
  #  #right = pipe_data[condition['right_variable']]
  #  right = dotinspect.Inspect(condition['right_variable'], pipe_data)
  #  
  #elif condition['right_string']:
  #  right = condition['right_string']
  #else:
  #  log('Condition: Right not matched: String: %s  Variable: %s' % (condition['right_string'], condition['right_variable']))
  #  right = None
  
  print 'If: Left: %s   Right: %s' % (left, right)
  
  # Remove "else" tag from update, if true
  remove_else = False
  
  # If the left variable is set and the Conditional test passes
  if left != None and _ConditionTest(left, condition['operator'], right):
    # Remove the "else" clause from this block, if it exists
    if 'else' in block:
      #TODO(g): I tried abstracting this until later, but then it gets
      #   processed, and it shouldnt...
      block = dict(block)
      del block['else']
    
    print 'If: -------- True: %s' % block
  
  # Else, if we have an else block, process that
  elif 'else' in block:
    # Turn the block into the "else" block
    block = block['else']
    
    print 'If: ******** Else: %s' % block
  
  else:
    # Do not store this tag in data, we operate on the black_parent
    raise processing.DoNotSaveTag('If')
  
  
  # Process this block
  result = processing.Process(pipe_data, block, request_state, input_data,
                              tag=tag, cwd=cwd, env=env,
                              block_parent=block_parent)
  
  # Update the block parent with this
  raise processing.UpdateBlockData(result)


#def ConditionElseIf(pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):
#  """Else, if, condititional statement."""
#  log('Condition Elif... %s' % tag)
#  
#  if block_parent and '__skip' in block_parent and 'elif' in block_parent['__skip']:
#  #if '__skip' in block and 'elif' in block['__skip']:
#    log('  Skipping...')
#    # Do not store this tag in data, we operate on the black_parent
#    raise processing.DoNotSaveTag('Elif')
#  
#  # Process this If...
#  try:
#    ConditionIf(pipe_data, block, request_state, input_data, tag=tag, cwd=cwd, env=env, block_parent=block_parent)
#    #ConditionIf(tag, block, data, state, chain_output, env=env, block_parent=block_parent)
#  except processing.DoNotSaveTag, e:
#    raise processing.DoNotSaveTag('Elif')
#
#
#def ConditionElse(pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):
#  """Else, condititional statement."""
#  log('Condition Else... %s' % tag)
#  
#  # If tagged for skipping, skip
#  if block_parent and '__skip' in block_parent and 'else' in block_parent['__skip']:
#  #if '__skip' in block and 'else' in block['__skip']:
#    log('  Skipping...')
#    # Do not store this tag in data, we operate on the black_parent
#    raise processing.DoNotSaveTag('Else')
#  
#  # Else, process
#  else:
#    # Process this block
#    result = processing.Process(pipe_data, block, request_state, input_data, tag=tag, cwd=cwd, env=env, block_parent=block_parent)
#    #result = processing.Process(block, data, state, chain_output, env=env, block_parent=block_parent)
#    
#    log('  Updating: %s' % result)
#    
#    # Update the block parent with this
#    raise processing.UpdateBlockData(result)
#  
#  return pipe_data


def Conditions(pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):
  """Ordered list of if/elif/else.
  
  ##NOTE(g): Not currently in use!  :P   Broken.
  
  Otherwise elif will not be ordered.  (TODO(g): Add priority to elif to fix.)
  """
  new_if = True
  if_scan = False
  elif_scan = False
  
  for item in block:
    # Determine if this is an if, elif or else
    style = item.keys()[0].split(' ', 1)[0]
    
    # If this is an if, then reset the new_if
    if style == 'if':
      new_if = True
      if_scan = False
      elif_scan = False
    
    # Process the item
    result = processing.Process(item)
  
  return chain_output
  
  
def Template(pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):
  """Use __output (if set) or block data and fill out template and store in
      __output Copy __output to __output_raw first.
  """
  
  return pipe_data
  
  
def Control_PutTagResultInQueue(pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):
  """Puts the appropriate message in the message queue."""
  # Process all the items in the queue list
  for item in block:
    # Get the tag data for this tag, or None
    tag_data = block_parent.get(item['tag'], None)
    
    # Add this tag's data to the message queue
    messagequeue.AddMessage(item['queue'], tag_data)
  
  
  # If we have this control statement, remove it as it already served it's
  #   purpose and is now cruft
  if '__control_PutTagResultInQueue' in block_parent:
    del block_parent['__control_PutTagResultInQueue']


def Control_PreProcessLockAcquire(pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):
  #TODO(g): Must know to unlock after processing, even on failure...
  sharedlock.Acquire(block['name'], block.get('timeout', None))
  
  #TODO(g): Figure out how to signal that lock must be unlocked...


def Control_FinalProcessLockRelease(pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):
  #TODO(g): Does this have to be explicitly defined?  Can
  #   Control_PreProcessLockAcquire() put the tag in the block so that this
  #   is tested afterwards?  It would be good to know...
  sharedlock.Release(block['name'])


def List_Add(pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):
  """Add this to a list."""
  print 'LIST ADD: %s' % block
  
  add_to = tag.split(' ')[-1]
  
  if add_to in pipe_data:
    pipe_data[add_to].append(block)
  
  raise processing.DoNotSaveTag('List_Add')
  

def List_Remove(pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):
  """Remove this from a list."""
  print 'LIST REMOVE: %s' % block
  
  block_parent['list_remove'] = tag
  
  raise processing.DoNotSaveTag('List_Add')


# Helper functions, not procblock builtins
def GetBlockOutput(block):
  if '__output' in block:
    return block['__output']
  else:
    return block


# Condition...

def EqualTo(left, right):
  log('%s == %s' % (left, right))
  return left == right


def GreaterThan(left, right):
  return left > right


def LessThan(left, right):
  return left < right


def GreaterThanOrEqualTo(left, right):
  return left >= right


def LessThanOrEqualTo(left, right):
  return left <= right


def NotEqualTo(left, right):
  return left != right


def InSet(left, right):
  return right in left


def NotInSet(left, right):
  return right not in left


def SetIsEmpty(left, right):
  return len(left) == 0


def SetIsNotEmpty(left, right):
  return len(left) > 0


def SetHas(left, right):
  return right in left


def SetHasNo(left, right):
  return right not in left






