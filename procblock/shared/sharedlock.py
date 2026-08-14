"""
sharedlock

Shared Locking module.  Get access to shared locks for any program using
this procblock module's state.


NOTE(g): Locks are never stored for process restarts.  If a process goes down,
    assume all locks are lost and must be restored.  There is no way to
    determine the effect that the process restarting will have on a lock, so
    the assumption must be made that the locks have been lost.
    
    Only distributed locking can solve this, so that any given nodes loss of
    locks means nothing, because a quorum (N/2+1) must be reached before a
    new lock will be acquired, and so the restart of this lock databes node
    means nothing in itself, as a minimum of 3 nodes must be present for a
    quorum to decide on a lock.
    
    An individual node's code will restart as well, so the code will proceed
    as if no locks are already set, and start requesting locks.  This appears
    to be the right way to handle this.


TODO(g): Allow quorum-locking for multi-region locks.  This isn't about
    implementation in this module, it's about creating the method for how to
    link a number of locks together so that inside an entire system the first
    to get the (N/2)+1 locks is the victor, and all other locks are undone and
    given to the victor.  Other lock attempts must block until the quorum
    releases the lock and allows another (N/2)+1 locks to be made.
    
    Distributed lock systems allow flexibility on lock servers coming and going
    for large scale systems.  No system can be the master in this environment
    and a majority quorum must be met to enforce any lock.  Each lock server
    should attempt to gain the quorum lock before locking itself.
    
    There is a dual-layer of locking here.  The attempt-lock and the actual-lock.
    The attempt lock is this node only, the actual-lock is when a quorum has
    been reached.  Attempt locks are blocked by actual locks.
    
    All distributed locks must have a timeout specified so that the network does
    not come to a halt.
    
    To avoid dead-locks, locks must have a unique priority, so a lock name
    must register it's unique priority.  To get a lower lock, you must attain
    higher locks first, and only go from low to high.  This allows dead-locks
    to be avoided by design.  Locks must be designed as a priority so a high
    lock is never requested before a low-lock.
    
    This can be enforced by using credentials for locks, so a node request
    sessions has a crendential, and the credentials are tracked, and any
    requests from that credential must come in order, or will be rejected
    due to creating a possible dead-lock scenario.
"""


import threading
import time

import threadsafedict


SHARED_LOCK_CONTROL = threading.Lock()


# Global for message queues - Temporary
#TODO(g): Convert to threadsafe and use a better store than module, so it
#   survives reloads.
#TODO(g): Why not allow state to be passed in and store the locks there?
#   So state management and serialization can be dealt with someone else.
SHARED_LOCKS = threadsafedict.ThreadSafeDict()

# Seconds to sleep while looping on a lock.acquire() timeout
TIMEOUT_SLEEP_SECONDS = 0.1


class LockDoesntExist(Exception):
  """This lock does not exist, so it cant be released."""


def SharedControl_Lock():
  """Lock the shared control access to locks.  This way we can safely acquire
  an individual lock or create a new lock without a race condition.
  """
  global SHARED_LOCK_CONTROL
  
  SHARED_LOCK_CONTROL.acquire()


def SharedControl_Release():
  """Lock the shared control access to locks.  This way we can safely acquire
  an individual lock or create a new lock without a race condition.
  """
  global SHARED_LOCK_CONTROL
  
  SHARED_LOCK_CONTROL.release()


def IsLocked(name):
  """Returns boolean if this named lock is locked.  If doesnt exist, still False
  """
  global SHARED_LOCKS
  
  # If we dont have this lock, return False.  Will not raise an exception here
  #   because it is not really an error, and no lock may have been needed to
  #   be set yet, but checks are already happening.
  if name not in SHARED_LOCKS:
    #log('sharedlock.IsLocked: %s: Doesnt exist: False' % name)
    return False
  
  # Else return the locked status
  else:
    locked = SHARED_LOCKS[name].locked()
    
    #log('sharedlock.IsLocked: %s: %s' % (name, locked))
    
    return locked


def Acquire(name, timeout=None, save=False):
  """Acquire the lock.
  
  Args:
    name: string, name of the lock.  Use naming convertion like:
        "top.middle.bottom" or other layered naming convertion to be able to
        maintain specific resource locks.
    time: float or None (optional), if float, number of seconds until timeout
    save: boolean, if True this lock will be saved to disk on restart, so
        the resource is still locked or unlocked after sharedlock's module
        has been reloaded
        TODO(g): Use state and not module, or maybe in addition to module...
  
  Returns: boolean, success of lock (only False if timeout is set and exceeded)
  """
  global SHARED_LOCKS
  
  # Start the time of this function
  time_start = time.time()
  
  # If we dont have this name yet, create a new lock
  #TODO(g): Functionize?  Acquire and AcquireIfNotLocked use this same code...
  if name not in SHARED_LOCKS:
    # Enforce we are safe to add this new lock.  Should be fast, ignore timeout.
    SharedControl_Lock()
    
    # Check that this item has not been added since we acquired our lock
    if name not in SHARED_LOCKS:
      SHARED_LOCKS[name] = threading.Lock()
    
    # Release shared control
    SharedControl_Release()
  
  # Lock the shared lock
  if timeout == None:
    SHARED_LOCKS[name].acquire()
    #log('sharedlock.Aquire: %s (timeout=%s): True' % (name, timeout))
    return True
  
  # Else, handle possible timeout
  else:
    # Loop forever, until duration timeout or success...
    while True:
      # Check if we successfully acquired the named lock
      success = SHARED_LOCKS[name].acquire(0)
      
      duration = time.time() - time_start
      
      # If we have a lock, we're done
      if success:
        #log('sharedlock.Aquire: %s (timeout=%s): True' % (name, timeout))
        return success
      
      # If the duration is over our timeout, or timeout is zero, we're done
      elif duration > timeout or timeout == 0:
        #log('sharedlock.Aquire: %s (timeout=%s): False' % (name, timeout))
        return success
      
      else:
        pass


def Release(name):
  """Acquire the lock.
  
  TODO(g): Could have optional secret to enforce who can release this lock...
  
  Args:
    name: string, name of the lock.  Use naming convertion like:
        "top.middle.bottom" or other layered naming convertion to be able to
        maintain specific resource locks.
    time: float or None (optional), if float, number of seconds until timeout
  """
  global SHARED_LOCKS
  
  #log('sharedlock.Release: %s' % name)
  
  # If we dont have this name yet, raise an exception.
  #   Code thought it already had this locked, but didnt: error up.
  if name not in SHARED_LOCKS:
    raise LockDoesntExist(name)
  
  # Lock the shared lock
  #TODO(g): Deal with function timeout...
  SHARED_LOCKS[name].release()


def FindAllLocked():
  """Returns a list of strings, for the names of all the locks currentl locked."""
  all_locks = []
  
  global SHARED_LOCKS
  
  keys = SHARED_LOCKS.keys()
  
  for key in keys:
    if IsLocked(key):
      all_locks.append(key)
  
  all_locks.sort()
  
  return all_locks
  
  
  
if __name__ == '__main__':
  Acquire('one')
  Acquire('two')
  
  print 'Currently locked locks: %s' % FindAllLocked()
  
  # Aquire one again, timeout after 2
  success = Acquire('one', 2)
  
  IsLocked('two')
  
  Release('two')

  IsLocked('two')
  
  Release('one')
  
  Acquire('one')
  
  print 'Currently locked locks: %s' % FindAllLocked()


