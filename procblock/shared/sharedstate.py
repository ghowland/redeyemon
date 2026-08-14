"""
sharedstate

Shared State module.  Get access to shared state.

All state has a namespace, and then the state id.  sharecounter is used to
procure new state ids, so it can be incremented atomically and shared with
other procblock programs.

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


import threading
import time


import threadsafedict


# Global for state buckets.  Each bucket is dict and contains keys in a dict.
#   Temporary?
#TODO(g): Convert to threadsafe and use a better store than module, so it
#   survives reloads.
#TODO(g): Why not allow state to be passed in and store the locks there?
#   So state management and serialization can be dealt with someone else.
SHARED_STATE = threadsafedict.ThreadSafeDict()

# When setting or getting a value in a bucket, use locking to ensure this is
#   an atomic operation
SHARED_STATE_LOCKS = threadsafedict.ThreadSafeDict_IgnoreOverwrites()


class StateBucketDoesntExist(Exception):
  """This state bucket does not exist, so it cannot by returned."""


class StateBucketNotFound:
  """This state bucket was not found.  Different than it having a value of None."""
  
  
class StateKeyNotFound:
  """This state key was not found.  Different than it having a value of None."""


def _LockState(bucket):
  global SHARED_STATE_LOCKS
  
  if bucket not in SHARED_STATE_LOCKS:
    #NOTE(g): This is a race condition, which is why we use the
    #   ThreadSafeDict_IgnoreOverwrites class, which will ignore multiple
    #   attempts to create locks.  Only the first lock is created, and then
    #   will be safely used.  Any additional attempts to create locks will be
    #   ignored.
    SHARED_STATE_LOCKS[bucket] = threading.Lock()
  
  # Lock it
  SHARED_STATE_LOCKS[bucket].acquire()


def _UnlockState(bucket):
  global SHARED_STATE_LOCKS
  
  # Throw an exception if this counter doesnt exist, something is wrong
  if bucket not in SHARED_STATE_LOCKS:
    raise StateDoesntExist('Not found: %s' % bucket)
  
  # Release it
  SHARED_STATE_LOCKS[bucket].release()


def _EnsureBucketExists(bucket):
  global SHARED_STATE
  
  # Ensure no one else can operate on this bucket
  _LockState(bucket)
  
  # Test that the bucket does not exist
  if bucket not in SHARED_STATE:
    # Create the bucket
    SHARED_STATE[bucket] = threadsafedict.ThreadSafeDict()
  
  # Release the bucket, others may attempt this call now, or others
  _UnlockState(bucket)
  


def BucketExists(bucket):
  """A bucket exists."""
  global SHARED_STATE
  
  try:
    _LockState(bucket)
    
    exists = bucket in SHARED_STATE
    
    return exists

  finally:
    _UnlockState(bucket)
  

def KeyExists(bucket, key):
  """A key exists inside a bucket."""
  global SHARED_STATE
  
  if not BucketExists(bucket):
    raise StateBucketDoesntExist('Bucket doesnt exist: %s' % bucket)
  
  exists = key in SHARED_STATE[bucket]
  
  return exists


def GetBucketKeys(bucket):
  """Returns the keys in a bucket."""
  global SHARED_STATE
  
  if not BucketExists(bucket):
    raise StateBucketDoesntExist('Bucket doesnt exist: %s' % bucket)
  
  # ThreadSafeDict protects
  keys = SHARED_STATE[bucket].keys()
  
  return keys


def Set(bucket, key, value):
  """Lock the shared control access to locks.  This way we can safely acquire
  an individual lock or create a new lock without a race condition.
  """
  global SHARED_STATE
  
  # Ensure this bucket exists, we're going to create it
  _EnsureBucketExists(bucket)
  
  # Set the bucket key to the value.  Safe via ThreadSafeDict
  SHARED_STATE[bucket][key] = value
  
  # All functions should behave similarly, so this returns the value we set
  return value
  


def Get(bucket, key):
  """Lock the shared control access to locks.  This way we can safely acquire
  an individual lock or create a new lock without a race condition.
  """
  global SHARED_STATE
  
  if not BucketExists(bucket):
    raise StateBucketDoesntExist('Bucket doesnt exist: %s' % bucket)
  
  return SHARED_STATE[bucket][key]


def GetSet(bucket, key, value):
  """Returns boolean if this named lock is locked.  If doesnt exist, still False
  """
  global SHARED_STATE
  
  # Ensure this bucket exists, we're going to create it
  _EnsureBucketExists(bucket)
  
  # Set the bucket key to the value, and get original.  Safe via ThreadSafeDict
  previous_value = SHARED_STATE[bucket].GetSet(key, value)
  
  # Return the previous value, before we set this new value
  return previous_value

  
  
  
if __name__ == '__main__':
  print BucketExists('sofa')
  
  print Set('sofa', 'barn', 15)
  
  print BucketExists('sofa')
  
  print Get('sofa', 'barn')
  
  print Set('sofa', 'bush', 'Tundra!')
  
  print GetSet('sofa', 'bush', 'Tornado!')
  print GetSet('sofa', 'bush', 'Ohio!')
  
  print GetBucketKeys('sofa')
  
  print KeyExists('sofa', 'bush')
  print KeyExists('sofa', 'bush2')
  
  try:
    print KeyExists('sortaaaa', 'bush2')
  except StateBucketDoesntExist, e:
    print e


