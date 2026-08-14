"""
messagequeue

Message Queue management for procblocks

TODO(g): Add auto-deleting options by count or age.  Date tag their arrival
    in a dict so we can track stuff about it, and can maybe skip it.

TODO(g): Implement serialization, archiving, snapshotting, and replication to
sharestate.  This will allow us flexibility in many things.  This is not
necessarily going to be the best scaling solution, but it will work and provide
a way to keep state and distribute.  Name spaces should have this specified
individually.  If not specified, state will not be archived, serialized,
snapshotted or replicated.

  * Use the "archive" and "snapshot" modules for this, so archival and
      snapshotting is universal.  Ensure a process restart will do the right
      thing in attempting to restore from snapshot, then archive, if present.
      
      TODO(g): Merge achive and snapshot.  They are the same technology.  If we
          really want to keep state, then we must archive each transactions and
          snapshot to avoid having to replay too many archives.
"""

import threadsafedict
import threadsafelist


# Global for message queues
#TODO(g):  Temporary?  Better way to hold data for the duration of a process?
MESSAGE_QUEUES = threadsafedict.ThreadSafeDict()


def QueueExists(queue):
  """Does this queue exist?"""
  global MESSAGE_QUEUES
  
  if queue not in MESSAGE_QUEUES:
    return False
  else:
    return True


def AddMessage(queue, message):
  global MESSAGE_QUEUES
  
  #log('Add message: %s: %s' % (queue, message))
  
  if queue not in MESSAGE_QUEUES:
    #TODO(g): Use thread-safe lists
    MESSAGE_QUEUES[queue] = threadsafelist.ThreadSafeList()
  
  MESSAGE_QUEUES[queue].append(message)


def GetMessageCount(queue):
  global MESSAGE_QUEUES
  
  # If we dont have this queue, return None
  if queue not in MESSAGE_QUEUES:
    return None
  
  return len(MESSAGE_QUEUES[queue])


def GetMessage_Oldest(queue, remove=True):
  """Returns the oldest message in the queue(0)."""
  global MESSAGE_QUEUES
  
  # If we dont have this queue or it is empty, return None
  if queue not in MESSAGE_QUEUES or not MESSAGE_QUEUES[queue]:
    return None
  
  # Get the first element
  message = MESSAGE_QUEUES[queue][0]
  
  # Remove it
  if remove:
    MESSAGE_QUEUES[queue].remove(message)
  
  #log('Get oldest message: %s: %s' % (queue, message))
  
  return message


def GetMessage_Newest(queue, remove=True):
  """Returns the oldest message in the queue(-1)."""
  global MESSAGE_QUEUES
  
  # If we dont have this queue or it is empty, return None
  if queue not in MESSAGE_QUEUES or not MESSAGE_QUEUES[queue]:
    return None
  
  # Get the first element
  message = MESSAGE_QUEUES[queue][-1]
  
  # Remove it
  if remove:
    del MESSAGE_QUEUES[queue][-1]
  
  #log('Get newest message: %s: %s' % (queue, message))
  
  return message


if __name__ == '__main__':
  queue = 'testing'
  
  print QueueExists(queue)
  
  AddMessage(queue, 1)
  AddMessage(queue, 2)
  AddMessage(queue, 3)
  
  print GetMessage_Newest(queue)
  print GetMessage_Oldest(queue)
  print GetMessageCount(queue)
  