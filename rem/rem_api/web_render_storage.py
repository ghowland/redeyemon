#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Web: Render the Site Control data: Storage

rem_api.web_render.py is the main module.  Because there are so many methods
per data group they are being seperated into seperate modules.
"""


import os


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *

# Special web_render_* imports from web_render
from web_render import GetWebRenderTemplate
from web_render import _RenderHeader


def WebRender_Storage(storage_id):
  """Render this storage from it's RpcGetStorage() data."""
  # Get our base rendering data
  storage = site_control.RpcGetStorage(storage_id)
  if not storage:
    msg = 'Storage not found: %s' % storage_id
    log(msg)
    return msg
  
  # Make our own data, to match to the template
  data = dict(storage)
  
  # Add Parent Set info (Database Instance or Storage Set)
  data['parent_set'] = None
  sql = "SELECT * FROM db_instance WHERE mount_storage = %d" % storage_id
  db_instances = Query(sql)
  if db_instances:
    #NOTE(g): Only the first one should matter, if this becomes false, change it
    instance = site_control.RpcGetDatabaseInstance(db_instances[0]['id'])
    data['parent_set'] = 'This Storage is owned by the Database Instance: <a href="database_instance?id=%(id)s">%(db_name)s</a> %(status_image)s' % instance

  
  #TODO(g): Handle storage_set stuff here...
  pass#todo...

  
  # If parent_set hasnt been set yet, tell em whats up
  if data['parent_set'] == None:
    data['parent_set'] = 'This Storage does not have a Database Instance owner, or a Storage Set owner.'
  
  
  # Add the Volumes
  data['volume_info'] = ''
  # Get our volumes, already sorted in our storage_order
  data['volumes'] = site_control.GetStorageVolumeList(storage_id)
  for volume_id in data['volumes']:
    if volume_id == data['volumes']:
      data['volume_info'] += site_control.WebRender_StorageVolume_Line(volume_id, print_header=True)
    else:
      data['volume_info'] += site_control.WebRender_StorageVolume_Line(volume_id)
  
  # Get the template
  template = GetWebRenderTemplate('render/storage.txt')
  
  # Format the template, non-destructively.  (Keep unused format strings and %s)
  output = site_control.WebTemplateFormat(template, data)
  
  return output


def WebRender_Storage_Line(storage_id, table_row=True, print_header=False):
  """Render this storage from it's RpcGetStorage() data, on a single line."""
  # Get our base rendering data
  storage = site_control.RpcGetStorage(storage_id)
  
  if not storage:
    msg = 'Storage not found: %s' % storage_id
    log(msg)
    return msg
  
  # Make our own data, to match to the template
  data = dict(storage)
  
  # Get the template
  template = GetWebRenderTemplate('render/storage_line.txt')
  
  # Format the template, non-destructively.  (Keep unused format strings and %s)
  output = site_control.WebTemplateFormat(template, data)
  
  # If we want to print the header too
  if print_header:
    # Create custom header data for this template
    header_data = {'name':'Storage', 'id':'', 'handler_stack':'',
                   'handler_stack_name':'Handler Stack',
                   'size_gb':'Size ', 'mount_machine_name':'Machine', 
                   'mount_machine':'', 'status_image':''
                   }
    
    # Render the header
    header = _RenderHeader(template, header_data)
    
    # Append the header
    output = header + output
  
  return output


def WebRender_Storage_Status(storage_id):
  """Render just a status item (16x16 image, can have popup) for this item."""
  output = ''
  
  # Get the RPC synthesized data, without status (cause thats us, loop)
  storage = site_control.RpcGetStorage(storage_id, render_status=False)
  
  if not storage:
    log('Storage not found: %s' % storage_id)
    return '<img src="/static/images/candle.png" title="Not Found">'
  
  # If this Instance is Assigned: Green
  if storage['status'] == 3:
    output += '<a href="storage?id=%(id)s"><img src="/static/images/led_green.png" border=0 title="%(status_name)s"></a>' % storage
  
  # Else, if this Instance is in configuration (Requested): Yellow
  elif storage['status'] == 2:
    output += '<a href="storage?id=%(id)s"><img src="/static/images/led_yellow.png" border=0 title="%(status_name)s"></a>' % storage
  
  # Else, if this Instance is Initialized: White
  elif storage['status'] == 1:
    output += '<a href="storage?id=%(id)s"><img src="/static/images/led_white.png" border=0 title="%(status_name)s"></a>' % storage
  
  # Else, if this Instance is in repairs: Red
  elif storage['status'] == 4:
    output += '<a href="storage?id=%(id)s"><img src="/static/images/led_red.png" border=0 title="%(status_name)s"></a>' % storage
  
  # Else, WTF is this?  Blue
  else:
    log('Unhandled status: %s' % storage['status'])
    output += '<a href="storage?id=%(id)s"><img src="/static/images/led_blue.png" border=0 title="%(status_name)s"></a>' % storage
  
  return output


def WebRender_StorageVolume(volume_id):
  """Render this storage volume from it's RpcGetStorageVolume() data."""
  # Get our base rendering data
  volume = site_control.RpcGetStorageVolume(volume_id)
  if not volume:
    msg = 'Storage Volume not found: %s' % volume_id
    log(msg)
    return msg
  
  # Make our own data, to match to the template
  data = dict(volume)
  
  # Get the template
  template = GetWebRenderTemplate('render/storage_volume.txt')
  
  # Format the template, non-destructively.  (Keep unused format strings and %s)
  output = site_control.WebTemplateFormat(template, data)
  
  return output


def WebRender_StorageHandlerStack(handler_stack_id):
  """Render this storage handler_stack from it's RpcGetStorageHandlerStack() data."""
  # Get our base rendering data
  handler_stack = site_control.RpcGetStorageHandlerStack(handler_stack_id)
  if not handler_stack:
    msg = 'Storage Handler Stack not found: %s' % handler_stack_id
    log(msg)
    return msg
  
  # Make our own data, to match to the template
  data = dict(handler_stack)
  
  # Add the Storages
  data['storage_info'] = ''
  storages = data['storages'].keys()
  storages.sort() # Ensure they are always in the same order
  for storage_id in storages:
    if storage_id == storages[0]:
      data['storage_info'] += site_control.WebRender_Storage_Line(storage_id, print_header=True)
    else:
      data['storage_info'] += site_control.WebRender_Storage_Line(storage_id)
  
  # Get the template
  template = GetWebRenderTemplate('render/storage_handler_stack.txt')
  
  # Format the template, non-destructively.  (Keep unused format strings and %s)
  output = site_control.WebTemplateFormat(template, data)
  
  return output


def WebRender_StorageHandler(handler_id):
  """Render this storage handler from it's RpcGetStorageHandler() data."""
  # Get our base rendering data
  handler = site_control.RpcGetStorageHandler(handler_id)
  if not handler:
    msg = 'Storage Handler not found: %s' % handler_id
    log(msg)
    return msg
  
  # Make our own data, to match to the template
  data = dict(handler)
  
  # Get the template
  template = GetWebRenderTemplate('render/storage_handler.txt')
  
  # Format the template, non-destructively.  (Keep unused format strings and %s)
  output = site_control.WebTemplateFormat(template, data)
  
  return output


def WebRender_StorageVolume_Status(volume_id):
  """Render just a status item (16x16 image, can have popup) for this item."""
  output = ''
  
  # Get the RPC synthesized data, without status (cause thats us, loop)
  volume = site_control.RpcGetStorageVolume(volume_id, render_status=False)
  
  if not volume:
    log('Storage Volume not found: %s' % volume_id)
    return '<img src="/static/images/candle.png" title="Not Found">'
  
  # If this Instance is Active: Green
  if volume['status'] == 6:
    output += '<a href="volume?id=%(id)s"><img src="/static/images/led_green.png" border=0 title="%(status_name)s"></a>' % volume
  
  # Else, if this Instance is in configuration/verifying: Yellow
  elif volume['status'] in (3, 4, 5):
    output += '<a href="volume?id=%(id)s"><img src="/static/images/led_yellow.png" border=0 title="%(status_name)s"></a>' % volume
  
  # Else, if this Instance is in request/allocation: White
  elif volume['status'] in (1, 2):
    output += '<a href="volume?id=%(id)s"><img src="/static/images/led_white.png" border=0 title="%(status_name)s"></a>' % volume
  
  # Else, if this Instance is in repairs: Red
  elif volume['status'] == 8:
    output += '<a href="volume?id=%(id)s"><img src="/static/images/led_red.png" border=0 title="%(status_name)s"></a>' % volume
  
  # Else, WTF is this?  Blue
  else:
    log('Unhandled status: %s' % volume['status'])
    output += '<a href="volume?id=%(id)s"><img src="/static/images/led_blue.png" border=0 title="%(status_name)s"></a>' % volume
  
  return output


def WebRender_StorageVolume_Line(volume_id, table_row=True, print_header=False):
  """Render this storage volume from it's RpcGetStorageVolume() data, on a single line."""
  # Get our base rendering data
  volume = site_control.RpcGetStorageVolume(volume_id)
  
  if not volume:
    msg = 'Storage Volume not found: %s' % volume_id
    log(msg)
    return msg
  
  # Make our own data, to match to the template
  data = dict(volume)
  
  # Get the template
  template = GetWebRenderTemplate('render/storage_volume_line.txt')
  
  # Format the template, non-destructively.  (Keep unused format strings and %s)
  output = site_control.WebTemplateFormat(template, data)
  
  # If we want to print the header too
  if print_header:
    # Create custom header data for this template
    header_data = {'storage':'Storage', 'id':'', 'storage_order':'Order',
                   'zone':'Zone', 'size_gb':'Size ', 'volume_id':'Volume ID',
                   'machine':'Machine', 'machine_device':'Device'
                   }
    
    # Render the header
    header = _RenderHeader(template, header_data)
    
    # Append the header
    output = header + output
  
  return output


