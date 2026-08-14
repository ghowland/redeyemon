#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Print out a one-line version of the stack.
"""


import traceback
import os


def Mini(depth=0, start_back_offset=0):
  """Returns a miniaturized string of the stack, useful for debugging."""
  depth += 2

  start_back = -1
  start_back -= start_back_offset

  stack = traceback.extract_stack()

  items = []

  for item in stack[len(stack)-depth:start_back]:
    msg = '%s:%s:%s' % (os.path.basename(item[0]), item[1], item[2])
    items.append(msg)

  return ' -> '.join(items)



if __name__ == '__main__':
  #Test it
  def a(arg):
    b(arg)

  def b(arg):
    print Get(arg, 1)

  a(3)
