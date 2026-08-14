"""
threadsafelist

by Geoff Howland <geoff AT ge01f.com>

Lists are extremely useful in sharing information in a threaded program,
as any thread can update the list, and be used by all threads.

However when changing the list, problems can occur as the operations
are not atomic, and threads may step on each other's execution.

This class extends UserList to make it thread safe.  There are still a number
of other locking issues that need to be dealt with in a threaded environment,
but gets and sets to the list will be done in a thread safe manner.

This will be slower and potentially cause delays in access, by design.
"""


import UserList
import threading


class ThreadSafeList(UserList.UserList):
  """A thread-safe list.  Subclassed from UserList."""
  
  def __init__(self, initialdata=None):
    self.lock = threading.Lock()
    
    if initialdata:
      self.data = list(initialdata)
    else:
      self.data = list()
  
  
  def append(self, value):
    """Set an item."""
    self.lock.acquire()
    
    try:
      self.data.append(value)
    
    finally:
      self.lock.release()
  
  
  def insert(self, index, value):
    """Set an item."""
    self.lock.acquire()
    
    try:
      self.data.insert(index, value)
    
    finally:
      self.lock.release()
  
  
  def remove(self, value):
    """Set an item."""
    self.lock.acquire()
    
    try:
      self.data.remove(value)
    
    finally:
      self.lock.release()
  
  
  def pop(self):
    """Pop off an item."""
    self.lock.acquire()
    
    try:
      item = self.data.pop()
      
      return item
    
    finally:
      self.lock.release()
  
  
  def reverse(self):
    """Reverse list."""
    self.lock.acquire()
    
    try:
      item = self.data.reverse()
      
      return item
    
    finally:
      self.lock.release()
  
  
  def sort(self):
    """Sort list."""
    self.lock.acquire()
    
    try:
      self.data.sort()
    
    finally:
      self.lock.release()
  
  
  def count(self, value):
    """Returns count of value in list."""
    self.lock.acquire()
    
    try:
      count = self.data.count(value)
      
      return count
    
    finally:
      self.lock.release()
  
  
  def __setitem__(self, key, value):
    """Set an item."""
    self.lock.acquire()
    
    try:
      self.data[key] = value
      
      return value
    
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
  
  
  def __add__(self, value):
    """In-place addition."""
    self.lock.acquire()
    
    try:
      self.data.__add__(value)
    
    finally:
      self.lock.release()
  
  
  def __iadd__(self, value):
    """In-place addition."""
    self.lock.acquire()
    
    try:
      self.data.__iadd__(value)
    
    finally:
      self.lock.release()
  
  
  def __delitem__(self, position):
    """Delete an item."""
    self.lock.acquire()
    
    try:
      del self.data[position]
    
    finally:
      self.lock.release()
  
  
  def __delslice__(self, start, stop):
    """Delete a slice of items."""
    self.lock.acquire()
    
    try:
      self.data.__delslice__(start, stop)
    
    finally:
      self.lock.release()
  
  
  def __contains__(self, value):
    self.lock.acquire()
    
    try:
      has_value = value in self.data
      
      return has_value
    
    finally:
      self.lock.release()
  
  
  def iteritems(self):
    self.lock.acquire()
    
    try:
      values = list(self.data)
      
      return values
    
    finally:
      self.lock.release()
  
  
  def __sizeof__(self):
    self.lock.acquire()
    
    try:
      size = len(self.data)
      
      return size
    
    finally:
      self.lock.release()


if __name__ == '__main__':
  a = ThreadSafeList()
  
  a.append(5)
  a.append(15)
  a.append(25)
  
  print a
  
  a.remove(5)
  
  print a
  
  a[0] = 3
  
  print a
  
  b = [10, 20, 30]
  
  c = ThreadSafeList(b)
  
  print c
  
  if 20 in c:
    print True
  else:
    print False
  
  if 21 in c:
    print True
  else:
    print False
  
  for item in c:
    print 'C: %s' % item
