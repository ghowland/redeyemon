#TODO(g): Remove this file once Ive pillaged all the good things out of it.
#   I wrote this as a preliminary pass, and it didnt get used, but had some
#   good code in it.

##!/usr/bin/python
#
#
##Author: Geoff Howland
##Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
##Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License
#
#"""
#Config Storage
#
#Manages calling the scripts related to Storage Management.
#
#It's like a framework handler, as the logic is all wrapped inside the scripts
#and the structure of the call order of the scripts is the way that things get
#done.
#
#This executes that structure.
#"""
#
#
## REM libraries
#import site_control
#import run_script
#from rem_api import cloud as rem_ec2
#from rem_util import *
#
#
#def Manage():
#  """Manage all the storage on this machine."""
#  # This just runs the storage_handler scripts, config...blah...
#  #   Those scripts are the ones that set the storage.status, as only they
#  #   can truly know when the device goes from one status to another.
#  
#  # This function just looks at the status, and then calls the correct script
#  
#  # Get all our storages on this machine
#  machine_storages = site_control.GetMachineStorages()
#  
#  # Process all this machines storage, if they need Status related scripts run
#  for storage_id in machine_storages:
#    storage = site_control.GetStorage(storage_id)
#    
#    # Dont run any scripts if the status is currently being processed by scripts
#    if not storage['status_is_processing']:
#      
#      # status < Configured(4): Run the configure script
#      if status < 4:
#        script_list = GetStackConfigScriptList(storage_id)
#      
#      # Else, if its Configured(4), then verify it
#      elif status == 4:
#        script_list = GetStackVerifyScriptList(storage_id)
#      
#      # Else, if its Verified(5), then Activate it
#      elif status == 5:
#        #NOTE(g): This is the one Status change that we do, because it just
#        #   pushes it active.  It allows one more space to do something, maybe
#        #   run a command, but its not needed yet.  The status difference is
#        #   useful, even if we dont have a command here.
#        site_control.SetStorageStatus(storage_id, site_control.STORAGE_STATUS__VERIFIED)
#      
#      # Else, if its Repairing(7), then repair it
#      elif status == 7:
#        script_list = GetStackRepairScriptList(storage_id)
#      
#      # Else, if its Decommissioned(8), then decomm it
#      elif status == 8:
#        script_list = GetStackDecommissionScriptList(storage_id)
#  
#  
#  # Run all the scripts in order
#  for script_id in script_list:
#    run_script.RunScript(script_id)
#
#
#def GetHandlerStack(storage_id):
#  """Returns a list of ints, storage_handler.id, forming the Handler Stack.
#  
#  Returns in Top to Bottom format, so that the file system is most likely the
#  top stack item, and the bottom item might be something like the EBS SAN-like
#  provisioned storage.
#  """
#  stack = []
#  
#  # Get our storage
#  storage = site_control.GetStorage(storage_id)
#  
#  # Get the starting stack place
#  handler_stack_id = storage['handler_stack']
#  
#  # Add our Top (first) element in the stack
#  stack.append(handler_id)
#  
#  # Build our stack, stopping with a handler_stack that has no parent.
#  found_top_parent = False
#  while not found_top_parent:
#    # Get this current stack item
#    stack_item = site_control.GetStorageHandlerStack(handler_stack_id)
#    
#    # If this stack item has a parent
#    if stack_item['stack_parent']:
#      # Add the stack_parent to our stack
#      stack.append(stack_item['stack_parent'])
#      
#      # Set our new storage_handler_stack.id, for the next go round
#      handler_stack_id = stack_item['stack_parent']
#    
#    # Else, we found our top parent.  Done.
#    else:
#      found_top_parent = True
#  
#  return stack
#
#
#def GetHandlerListFromStack(handler_stack):
#  """Takes a handler stack list (provided by GetHandlerStack()), returns a
#  list of the storage_handler.id ints."""
#  handlers = []
#  
#  # Add all the storage handlers from the handler stack
#  for handler_stack_id in handler_stack:
#    stack_info = site_control.GetStorageHandlerStack(handler_stack_id)
#    handlers.append(stack_info['storage_handler'])
#  
#  return handelrs
#
#
#def GetStackConfigScriptList(storage_id, upwards=True):
#  """Get a stack script list, defaults to up stack.
#  
#  Config goes from bottom to top
#  """
#  # Scripts, meant to be executed in the ordered returned
#  scripts = []
#  
#  # Get the storage_function.id
#  function_id = site_control.GetStorageFunctionByName(function_name)['id']
#  
#  # Get the Handler Stack for this Storage (storage_handler_stack), linking data
#  # Get the list of handlers from the stack, this is what we need
#  handler_list = GetHandlerListFromStack(GetHandlerStack(storage_id))
#  
#  # If we want a Bottom to Top stack, then reverse the handlers and stack
#  if upwards:
#    handler_list.reverse()
#  
#  # Add all the functions of this name for each of the handlers
#  for handler_id in handler_list:
#    handler = site_control.GetStorageHandler(handler_id)
#    
#    # If we have functions for this handler, add them to our enter/exit scripts
#    if handler_function:
#      if handler_function['script_config']:
#        scripts.append(handler_function['script_config'])
#  
#  return scripts
#  
#
#def GetStackVerifyScriptList(storage_id, upwards=True):
#  """Get a stack script list, defaults to up stack.
#  
#  Verify goes from bottom to top.
#  """
#  # Scripts, meant to be executed in the ordered returned
#  scripts = []
#  
#  # Get the storage_function.id
#  function_id = site_control.GetStorageFunctionByName(function_name)['id']
#  
#  # Get the Handler Stack for this Storage (storage_handler_stack), linking data
#  # Get the list of handlers from the stack, this is what we need
#  handler_list = GetHandlerListFromStack(GetHandlerStack(storage_id))
#  
#  # If we want a Bottom to Top stack, then reverse the handlers and stack
#  if upwards:
#    handler_list.reverse()
#  
#  # Add all the functions of this name for each of the handlers
#  for handler_id in handler_list:
#    handler = site_control.GetStorageHandler(handler_id)
#    
#    # If we have functions for this handler, add them to our enter/exit scripts
#    if handler_function:
#      if handler_function['script_verify']:
#        scripts.append(handler_function['script_verify'])
#  
#  return scripts
#  
#
#def GetStackMonitorScriptList(storage_id, upwards=False):
#  """Get a stack script list, defaults to up stack.
#  
#  Monitor goes from top to bottom.
#  """
#  # Scripts, meant to be executed in the ordered returned
#  scripts = []
#  
#  # Get the storage_function.id
#  function_id = site_control.GetStorageFunctionByName(function_name)['id']
#  
#  # Get the Handler Stack for this Storage (storage_handler_stack), linking data
#  # Get the list of handlers from the stack, this is what we need
#  handler_list = GetHandlerListFromStack(GetHandlerStack(storage_id))
#  
#  # If we want a Bottom to Top stack, then reverse the handlers and stack
#  if upwards:
#    handler_list.reverse()
#  
#  # Add all the functions of this name for each of the handlers
#  for handler_id in handler_list:
#    handler = site_control.GetStorageHandler(handler_id)
#    
#    # If we have functions for this handler, add them to our enter/exit scripts
#    if handler_function:
#      if handler_function['script_monitor']:
#        scripts.append(handler_function['script_monitor'])
#  
#  return scripts
#  
#
#def GetStackRepairScriptList(storage_id, upwards=False):
#  """Get a stack script list, defaults to up stack.
#  
#  Repair goes from top to bottom.
#  """
#  # Scripts, meant to be executed in the ordered returned
#  scripts = []
#  
#  # Get the storage_function.id
#  function_id = site_control.GetStorageFunctionByName(function_name)['id']
#  
#  # Get the Handler Stack for this Storage (storage_handler_stack), linking data
#  # Get the list of handlers from the stack, this is what we need
#  handler_list = GetHandlerListFromStack(GetHandlerStack(storage_id))
#  
#  # If we want a Bottom to Top stack, then reverse the handlers and stack
#  if upwards:
#    handler_list.reverse()
#  
#  # Add all the functions of this name for each of the handlers
#  for handler_id in handler_list:
#    handler = site_control.GetStorageHandler(handler_id)
#    
#    # If we have functions for this handler, add them to our enter/exit scripts
#    if handler_function:
#      if handler_function['script_repair']:
#        scripts.append(handler_function['script_repair'])
#  
#  return scripts
#  
#
#def GetStackDecommissionScriptList(storage_id, upwards=False):
#  """Get a stack script list, defaults to up stack.
#  
#  Decomm goes from top to bottom.
#  """
#  # Scripts, meant to be executed in the ordered returned
#  scripts = []
#  
#  # Get the storage_function.id
#  function_id = site_control.GetStorageFunctionByName(function_name)['id']
#  
#  # Get the Handler Stack for this Storage (storage_handler_stack), linking data
#  # Get the list of handlers from the stack, this is what we need
#  handler_list = GetHandlerListFromStack(GetHandlerStack(storage_id))
#  
#  # If we want a Bottom to Top stack, then reverse the handlers and stack
#  if upwards:
#    handler_list.reverse()
#  
#  # Add all the functions of this name for each of the handlers
#  for handler_id in handler_list:
#    handler = site_control.GetStorageHandler(handler_id)
#    
#    # If we have functions for this handler, add them to our enter/exit scripts
#    if handler_function:
#      if handler_function['script_decommission']:
#        scripts.append(handler_function['script_decommission'])
#  
#  return scripts
#
#
#def GetStackFunctionScriptList(storage_id, function_name):
#  """Get a stack script list, defaults to up stack.
#  
#  Functions go from top to bottom.
#  
#  Args:
#    upwards: boolean, True==Return the stack as Bottom to Top.
#  
#  Returns: list of ints, script.id, meant to be executed in the ordered returned
#  """
#  # Scripts, meant to be executed in the ordered returned
#  enter_scripts = []
#  exit_scripts = []
#  
#  # Get the Handler Stack for this Storage (storage_handler_stack), linking data
#  handler_stack = GetHandlerStack(storage_id)
#  # Get the list of handlers from the stack, this is what we need
#  handler_list = GetHandlerListFromStack(handler_stack)
#  
#  # Add all the functions of this name for each of the handlers
#  for handler_id in handler_list:
#    #handler = site_control.GetStorageHandler(handler_id)
#    handler_function = site_control.GetStorageHandlerFunction(handler_id,
#                                                              function_name)
#    
#    # If we have functions for this handler, add them to our enter/exit scripts
#    if handler_function:
#      if handler_function['script_enter']:
#        enter_scripts.append(handler_function['script_enter'])
#      
#      if handler_function['script_exit']:
#        exit_scripts.append(handler_function['script_exit'])
#  
#  # Reverse the exit scripts, so we can run them Bottom-Up
#  exit_scripts.reverse()
#  
#  # Build our final script list, by going Top-Down on enter, and Bottom-Up on
#  #   exit
#  scripts = enter_scripts + exit_scripts
#  
#  return scripts
#  
