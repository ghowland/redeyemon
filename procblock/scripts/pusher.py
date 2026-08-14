"""
pusher

TEST: Push things onto a queue to be processed.  Simultaneously!
"""

import time

#TODO(g): What if I moved the insertion of these modules at Import time,
#   so they could just be assumed to work, and be used?  This makes
#   the most sense...  Saved as procblock.messagequeue, as if imported properly...
import sys
sys.path.append('..')
from shared import messagequeue
from shared import sharedlock

from shared.log import log


def ProcessBlock(pipe_data, block, request_state, input_data, tag=None,
                 cwd=None, env=None, block_parent=None):
  """Execute!"""
  while sharedlock.IsLocked('__running'):
    value = time.time()
    
    log('Pushing: %s' % value)
    
    # Add a message
    messagequeue.AddMessage('push', value)
    
    # Sleep
    time.sleep(1)
  
  
  return pipe_data
