"""
sharedcounter

Shared Counter module.  Get access to shared counters.  Numeric values, which
can be atomically get/set, or atomically incremented.

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

import threadsafedict


# Global for message queues - Temporary
#TODO(g): Why not allow state to be passed in and store the locks there?
#   So state management and serialization can be dealt with someone else.
SHARED_COUNTERS = threadsafedict.ThreadSafeDict()

# Each counter gets it's own lock, so that each counter can have atomic
#   transactions, but is not impacted by transactions of other counters.
SHARED_COUNTER_LOCKS = threadsafedict.ThreadSafeDict_IgnoreOverwrites()


class CounterDoesntExist(Exception):
  """This counter does not exist, so it cannot by returned."""


def _LockCounter(name):
  global SHARED_COUNTER_LOCKS
  
  if name not in SHARED_COUNTER_LOCKS:
    #NOTE(g): This is a race condition, which is why we use the
    #   ThreadSafeDict_IgnoreOverwrites class, which will ignore multiple
    #   attempts to create locks.  Only the first lock is created, and then
    #   will be safely used.  Any additional attempts to create locks will be
    #   ignored.
    SHARED_COUNTER_LOCKS[name] = threading.Lock()
  
  # Lock it
  SHARED_COUNTER_LOCKS[name].acquire()


def _UnlockCounter(name):
  global SHARED_COUNTER_LOCKS
  
  # Throw an exception if this counter doesnt exist, something is wrong
  if name not in SHARED_COUNTER_LOCKS:
    raise CounterDoesntExist('Not found: %s' % name)
  
  # Release it
  SHARED_COUNTER_LOCKS[name].release()


def Get(name):
  """Returns the value of this counter, or CounterDoesntExist class.
  
  If named counter does not exist, starts counter value at zero.
  """
  global SHARED_COUNTERS
  
  # If we dont have this counter yet, set it to 0.  All counters start at 0,
  #   by default.  If you dont want that, set it yourself.
  if name not in SHARED_COUNTERS:
    Set(name, 0)
    
    return 0
  
  # Else return the counter
  else:
    value = SHARED_COUNTERS[name]
    
    #log('sharedcounter.Get: %s: %s' % (name, value))
    
    return value


def Set(name, value):
  """Sets the named counter to this value.  Should be numeric, but is not tested.
  
  Returns value after setting (for consistency between other functions).
  """
  global SHARED_COUNTERS
  
  try:
    _LockCounter(name)
    
    SHARED_COUNTERS[name] = value
    #log('sharedcounter.Set: %s: %s' % (name, SHARED_COUNTERS[name]))
    
    return SHARED_COUNTERS[name]
  
  finally:
    _UnlockCounter(name)
  
  

def GetSet(name, value):
  """Sets the named counter to this value.  Returns the previous value.
  """
  global SHARED_COUNTERS
  
  try:
    _LockCounter(name)
    
    if name not in SHARED_COUNTERS:
      previous_value = 0
    else:
      previous_value = SHARED_COUNTERS[name]
    
    SHARED_COUNTERS[name] = value
    #log('sharedcounter.GetSet: %s: Previous=%s  New=%s' % (name, previous_value, SHARED_COUNTERS[name]))
    
    return previous_value
  
  finally:
    _UnlockCounter(name)
  

def GetIncrement(name, value=1):
  """Increments the named counter to this value.  Returns the previous value.
  
  If named counter does not exist, starts counter value at zero.
  """
  global SHARED_COUNTERS
  
  try:
    _LockCounter(name)
    
    if name not in SHARED_COUNTERS:
      previous_value = 0
    else:
      previous_value = SHARED_COUNTERS[name]
    
    SHARED_COUNTERS[name] = previous_value + value
    
    #log('sharedcounter.GetThenIncrement: %s: Previous=%s  New=%s' % (name, previous_value, SHARED_COUNTERS[name]))
    
    return previous_value
  
  finally:
    _UnlockCounter(name)
  

def Increment(name, value=1):
  """Increments the named counter by value (default is 1).  Returns the new
  value.
  
  If named counter does not exist, starts counter value at zero.
  """
  global SHARED_COUNTERS
  
  try:
    _LockCounter(name)
    
    if name not in SHARED_COUNTERS:
      previous_value = 0
    else:
      previous_value = SHARED_COUNTERS[name]
    
    SHARED_COUNTERS[name] = previous_value + value
    #log('sharedcounter.Increment: %s: Previous=%s  New=%s' % (name, previous_value, SHARED_COUNTERS[name]))
    
    return SHARED_COUNTERS[name]
  
  finally:
    _UnlockCounter(name)


def GetAllCounters():
  global SHARED_COUNTERS
  
  counters = dict(SHARED_COUNTERS)
  
  return counters
  
  
  
if __name__ == '__main__':
  print Get('bongo')
  print Set('bongo', 5)
  print GetSet('bongo', 10)
  print GetSet('bongo', 15)
  print GetIncrement('bongo')
  print GetIncrement('bongo')
  print Increment('bongo')
  print Increment('bongo')
  print Increment('bongo', 5)

