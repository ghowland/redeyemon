"""
threadsafedict

by Geoff Howland <geoff AT ge01f.com>

Dictionaries are extremely useful in sharing information in a threaded program,
as any thread can update the dictionary, and be used by all threads.

However when changing the dictionary, problems can occur as the operations
are not atomic, and threads may step on each other's execution.

This class extends UserDict to make it thread safe.  There are still a number
of other locking issues that need to be dealt with in a threaded environment,
but gets and sets to the dictionary, and retrieving it's keys will be done in
a thread safe manner.

Key iteration just returns all keys in a sequence to avoid an extended lock.
Expect large key stores to perform accordingly.

This will be slower and potentially cause delays in access, by design.
"""


import UserDict
import threading


class NoValue:
  """No value was present.  Will be used when GetSet is called, and there was
  no key there originally.
  """


class ThreadSafeDict(UserDict.UserDict, UserDict.DictMixin):
  """A thread-safe dictionary.  Subclassed from UserDict.
  
  NOTE(g): Does not implement __iter__, so keys() is used instead.  __iter__
      is inherently thread-unsafe, or requires blocking for a period of time
      which is not worth it.  Design accordingly.
  """
  
  def __init__(self, initialdata=None):
    self.lock = threading.Lock()
    
    if initialdata:
      self.data = dict(initialdata)
    else:
      self.data = dict()
  
  
  def __setitem__(self, key, value):
    """Set an item."""
    self.lock.acquire()
    
    try:
      self.data[key] = value
    
    finally:
      self.lock.release()
  
  
  def __getitem__(self, key):
    """Get an item."""
    self.lock.acquire()
    
    try:
      value = self.data[key]
      
      return value
    
    finally:
      self.lock.release()
  
  
  def __delitem__(self, key):
    """Delete an item."""
    self.lock.acquire()
    
    try:
      del self.data[key]
    
    finally:
      self.lock.release()
  
  
  def keys(self):
    """Return keys."""
    self.lock.acquire()
    
    try:
      keys = self.data.keys()
      
      return keys
    
    finally:
      self.lock.release()
  
  
  def __contains__(self, key):
    self.lock.acquire()
    
    try:
      has_key = key in self.data
      
      return has_key
    
    finally:
      self.lock.release()
  
  
  def iteritems(self):
    self.lock.acquire()
    
    try:
      keys = self.data.keys()
      
      return keys
    
    finally:
      self.lock.release()

 
  def GetSet(self, key, value):
    """Atomically sets a value, and returns the original value."""
    self.lock.acquire()
    
    try:
      if key not in self.data:
        previous_value = NoValue
      else:
        previous_value = self.data[key]
      
      self.data[key] = value
      
      return previous_value
    
    finally:
      self.lock.release()


class ThreadSafeDict_IgnoreOverwrites(ThreadSafeDict):
  
  def __setitem__(self, key, value):
    """Just ignore any attempt to overwrite an existing value."""
    self.lock.acquire()
    
    try:
      # Only write this value, if another value does not exist.
      #   Useful for locks and other values we only want to store ONCE and we
      #   want to get rid of race conditions.
      if key not in self.data:
        self.data[key] = value
      
      # Silently fail...
      #TODO(g): Log once uber-logging has been created.
      else:
        pass
    
    finally:
      self.lock.release()

  


if __name__ == '__main__':
  a = ThreadSafeDict()
  
  a['test'] = 5
  
  print a.keys()
  
  print a
  
  b = {'test2':10}
  
  c = ThreadSafeDict(b)
  
  print c.keys()
  
  print c
  
  if 'test2' in c:
    print True
  else:
    print False
  
  if 'test5' in c:
    print True
  else:
    print False
  
  for item in c:
    print 'C: %s: %s' % (item, c[item])
