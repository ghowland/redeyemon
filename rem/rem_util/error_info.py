#!/usr/bin/python


#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Error Information: Prints detailed stack information
"""


import traceback
import sys


def GetExceptionDetails(long=False, webify=True):
  """Print the usual traceback information, followed by a listing of all the
  local variables in each frame.
  """
  output = '\n-----START-----\n'
  
  tb = sys.exc_info()[2]
  
  while 1:
    if not tb.tb_next:
        break
    tb = tb.tb_next
  stack = []
  f = tb.tb_frame
  
  while f:
    stack.append(f)
    f = f.f_back
  stack.reverse()
  #traceback.print_exc()
  output += traceback.format_exc()
  
  if long:
    output += "Locals by frame, innermost last\n"
    
    for frame in stack:
      output += "\nFrame %s in %s at line %s\n" % (frame.f_code.co_name,
                                           frame.f_code.co_filename,
                                           frame.f_lineno)
      for key, value in frame.f_locals.items():
        output += "\t%20s = " % key
        #We have to be careful not to cause a new error in our error
        #printer! Calling str() on an unknown object could cause an
        #error we don't want.
        try:
          output += str(value) + '\n'
        except:
          output += "<ERROR WHILE PRINTING VALUE>\n"
  
  output += '-----END-----'
  
  # If we want to make this web readable
  if webify:
    output = output.replace('\n', '<br>\n')
    output = output.replace('-----START-----', '<b>-----START-----</b>')
    output = output.replace('-----END-----', '<b>-----END-----</b>')
    
    #TODO(g): Any more niceification?
    pass#...
  
  return output
