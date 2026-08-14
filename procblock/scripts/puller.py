"""
pusher

TEST: Push things onto a queue to be processed.  Simultaneously!
"""

import time

#TODO(g): What if I moved the insertion of these modules at Import time,
#   so they could just be assumed to work, and be used?  This makes
#   the most sense...  Saved as procblock.messagequeue, as if imported properly...
#
#   No....  This is best as shared being a Python Site library, and then any
#     script using this Python executable's Site library will have all the
#     access they need, inside this process.
import sys
sys.path.append('..')
from shared import messagequeue
from shared import sharedlock
from shared.log import log


def ProcessBlock(pipe_data, block, request_state, input_data, tag=None,
                 cwd=None, env=None, block_parent=None):
  """Execute!"""
  while sharedlock.IsLocked('__running'):
    
    found_messages = False
    
    # Process all the messages in the queue, if any
    while messagequeue.GetMessageCount('push'):
      # Add a message
      message = messagequeue.GetMessage_Oldest('push')
      
      if message != None:
        found_messages = True
        log('Pulled message: %s' % message)
    
    if not found_messages:
      log('No messages to process.')
    
    # Sleep
    time.sleep(3)
  
  return pipe_data
  
