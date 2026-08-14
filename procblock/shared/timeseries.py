import os

from log import log
from run import Run


#
#
#def RunScript_Execute_Thread(site, site_data, deployment, service, service_data, script,
#                             script_data, instance=None):
#  
#
#  # Save chain_output data into our Local RRD Buffer
#  if 'rrd' in script_data:
#    for (rrd, rrd_data) in script_data['rrd'].items():
#      
#      # If this data is for a group
#      if 'group' in rrd_data and rrd_data['group'] != None:
#        log('Group RRD Data: %s (%s): %s' % (rrd_data['columns'].keys(), rrd_data['group'], chain_output.keys()))
#        
#        # Process the difference data sets in this group
#        for key in chain_output:
#          # Skip remlite private keys (no public key should start with __)
#          if key.startswith('__'):
#            continue
#          
#          # group_output
#          group_output = chain_output[key]
#          
#          if 'columns' in rrd_data:
#            for (column, column_data) in rrd_data['columns'].items():
#              # If this column is specified by key, and group_output has the key
#              if 'key' in column_data:
#                #TODO(g): Handle nested dict searches with multiple keys.  Today
#                #   just the [0] is enough to get us by.
#                if column_data['key'][0] in group_output:
#                  # Get the store_delay, so we know how to give to Collectors
#                  #NOTE(g): This makes Collecting very easy, no information needs
#                  #   to be passed.  As long as updating the conf files is
#                  #   done in syncronous and the conf data keeps integrity, this
#                  #   is a fast-ideal way to do it, because it's remlite.
#                  if 'store_delay' in rrd_data:
#                    store_delay = rrd_data['store_delay']
#                  else:
#                    store_delay = config_loader.GetRrdDefaults()['store_delay']
#                  
#                  # Save the value
#                  #TODO(g): column_data['key'][0] will need more depth searching,
#                  #   later.  For now, single depth is fine.
#                  SaveLocalRrdColumnValue(site, deployment, service, instance_name,
#                                          rrd, key, column,
#                                          group_output[column_data['key'][0]],
#                                          start_time, group_output, store_delay)
#                else:
#                  #log('Not in Chain Data: %s: %s: %s: %s' % (script, column, column_data['key'][0], chain_output), logging.ERROR)
#                  pass
#              else:
#                log('Key missing: %s: %s' % (script, column_data), logging.ERROR)
#          
#          
#        
#        continue
#      
#      if 'columns' in rrd_data:
#        for (column, column_data) in rrd_data['columns'].items():
#          # If this column is specified by key, and chain_output has the key
#          if 'key' in column_data:
#            #TODO(g): Handle nested dict searches with multiple keys.  Today
#            #   just the [0] is enough to get us by.
#            if column_data['key'][0] in chain_output:
#              # Get the store_delay, so we know how to give to Collectors
#              #NOTE(g): This makes Collecting very easy, no information needs
#              #   to be passed.  As long as updating the conf files is
#              #   done in syncronous and the conf data keeps integrity, this
#              #   is a fast-ideal way to do it, because it's remlite.
#              if 'store_delay' in rrd_data:
#                store_delay = rrd_data['store_delay']
#              else:
#                store_delay = config_loader.GetRrdDefaults()['store_delay']
#              
#              # Save the value
#              #TODO(g): column_data['key'][0] will need more depth searching,
#              #   later.  For now, single depth is fine.
#              SaveLocalRrdColumnValue(site, deployment, service, instance_name,
#                                      rrd, None, column,
#                                      chain_output[column_data['key'][0]],
#                                      start_time, chain_output, store_delay)
#            else:
#              log('Not in Chain Data: %s: %s: %s: %s' % (script, column, column_data['key'][0], chain_output), logging.ERROR)
#          else:
#            log('Key missing: %s: %s' % (script, column_data), logging.ERROR)
#  else:
#    #log('No RRD in script_data: %s' % script, logging.ERROR)
#    pass
#  
#  #log('Script result: %s.%s.%s.%s: %s' % (script, deployment, service, instance_name, chain_output))


#class RrdBufferItem:
#  
#  def __init__(self, value, occurred, full_output):
#    self.value = value
#    self.occurred = occurred
#    self.full_output = full_output
#  
#  
#  def __repr__(self):
#    output = '(%0.2f, %0.2f)' % (self.occurred, self.value)
#    return output
#
#
#class RrdBuffer:
#  
#  def __init__(self, key, store_delay):
#    # Key for the RRD
#    self.key = key
#    self.store_delay = store_delay
#    
#    # List of RrdBufferItem objects
#    self.buffer = []
#  
#  
#  def AddItem(self, item):
#    """Add an item."""
#    self.buffer.append(item)
#    
#    # Crop the buffer list, so it doesnt consume all our memory
#    #TODO(g): If these havent been collected yet, save them to disk, and
#    #   check when collecting to send items on disk as well, so we have
#    #   continuous graphing, even during extended network partitions.
#    BUFFER_MAX_SIZE = 100
#    if len(self.buffer) > BUFFER_MAX_SIZE:
#      self.buffer = self.buffer[-BUFFER_MAX_SIZE:]
#    
#    
#    #print self.buffer#DEBUG
#    
#  
#  
#  def CollectRrdValues(self, last_collect_time):
#    """Returns a list of tuples (time, value) for this RRD column's data.
#    
#    Every store_delay seconds, starting up last_collect_time, will be returned
#    as a list of tuples, so that the closest collected data to that time
#    (comparing the item prior to the time, and after the time, whichever is
#    closest to the time), will be returned at the store_delay rounded collection
#    time.  RRD requires times sync up exactly to the frequency that the data
#    is expected to be inserted.
#    """
#    rrd_values = []
#    
#    log('Collect RRD Values: %s' % last_collect_time)
#    
#    # Set our starting collection time
#    collect_time = last_collect_time
#    
#    # Always keep track of the last item, as we compare it and the current
#    #   item to determine which was closer to the collect_time.
#    item_previous = None
#    
#    # Collect up until the current moment
#    for item in self.buffer:
#      #print 'collect_time: %s   item.occurred: %s' % (collect_time, item.occurred)
#      
#      # Ensure collect_time is never more than 1*collect_time behind the
#      #   current item.  If it is, then skip it forward until it is just
#      #   behind the current item, so we catch up.
#      
#      
#      
#      # If we found an item that is post-collect time
#      if item.occurred > collect_time:
#        #print '  Found collectable item: %s' % item
#        # Get time difference
#        item_diff = item.occurred - collect_time
#        item_previous = item
#        collect_item = item
#        
#        # See if our previous item was closer to this collect_time.
#        if item_previous != None:
#          # If the previous item is closer to collect_item, use it instead
#          #print '%s - %s: %s' % (collect_time, item_previous.occurred, collect_time - item_previous.occurred)
#          if collect_time - item_previous.occurred < item_diff:
#            collect_item = item_previous
#            #print '  Taking previous item: %s' % item_previous
#        
#        # Save the collect item in rrd_values
#        rrd_values.append((collect_time, collect_item.value))
#        
#        # Increment the collect_time by store_delay
#        collect_time += self.store_delay
#      
#      
#      # Final task, always push this item into the "previous" spot
#      item_previous = item
#    
#    # Return the RRD Values
#    return rrd_values
#
#
## Global buffer storage
#RRD_BUFFER = {}
#
#
#def SaveLocalRrdColumnValue(site, deployment, service, instance_id, rrd, group, column, value, start_time, chain_output, store_delay):
#  """TODO(g): Move this to it's own module.
#  
#  Save the chain output, with each one, and start_time
#  """
#  # Convert Group so it isnt poisoned
#  if group != None:
#    group_name = group.replace('/', 'SLASH')
#  else:
#    group_name = None
#  
#  key = '%s.%s.%s.%s.%s.%s' % (site, service, instance_id, rrd, group_name, column)
#  
#  log('Save RRD Column: %s = %s (%s)' % (key, value, start_time))
#
#  global RRD_BUFFER
#  
#  # If we dont already have a buffer for this key, make one
#  if key not in RRD_BUFFER:
#    RRD_BUFFER[key] = RrdBuffer(key, store_delay)
#  
#  # Create an RrdBufferItem to store our information in
#  buffer_item = RrdBufferItem(value, start_time, chain_output)
#  
#  
#  # Store the data in the buffer.  It takes care of everything else.
#  RRD_BUFFER[key].AddItem(buffer_item)
#
#
#def CollectLocalRrdColumns(last_collect_time):
#  """Collect all the local RRD column values since we last collected."""
#  columns = {}
#  
#  global RRD_BUFFER
#  
#  # Save each of the key buffers, to be stored in RRDs
#  #NOTE(g): dict value is a tuple:  (time, value)
#  for key in RRD_BUFFER:
#    columns[key] = RRD_BUFFER[key].CollectRrdValues(last_collect_time)
#  
#  return columns
#


#
def StoreRrdColumns(collection):
  """Store the collected column data in the appropriate RRD files.
  
  Create the RRD files if they dont already exist.
  
  Returns: int, (epoch time) the last collected items time
  """
  
  # Create all the RRD data, by merging all the individual columns together
  rrds = {}
  
  # Process all the keys in the collect into their rrds
  for key in collection:
    #TODO(g): Enforce that these vars cannot have a period (.) in the conf names
    #print key
    (site, service, instance_id, rrd, group, column) = key.split('.')
    
    # Create a key without the column, so we can group those
    new_key = '%s.%s.%s.%s.%s' % (site, service, instance_id, rrd, group)
    
    # If this is a new RRD, create it's dict
    if new_key not in rrds:
      rrds[new_key] = {}
    
    # Save this column, so we have all the column data together
    rrds[new_key][column] = collection[key]
  
  #print rrds
  
  # Update this with the latest time from StoreInRrd()
  latest_collection_time = 0
  
  # Process all our RRDs
  for (rrd_key, columns) in rrds.items():
    (site, service, instance_id, rrd, group) = rrd_key.split('.')
    
    # Get the RRD data, so we know what we're dealing with
    rrd_data = config_loader.GetRrdData(site, service, int(instance_id), rrd, group)
    
    # Store the column_data in the RRD
    last_collection_time = StoreInRrd(rrd_data, group, columns)
    
    # Update the latest collection time
    if last_collection_time != None and last_collection_time > latest_collection_time:
      latest_collection_time = last_collection_time
  
  return latest_collection_time


def StoreInRrd(rrd_data, group, columns):
  """Store all the columns at the same time, for each occured time.
  
  Returns: int, (epoch time) highest time collected
  """
  # Get the lowest_occurred_time
  lowest_occurred_time = None
  for (column, column_data) in columns.items():
    # If we havent set a lowest time yet, this is it
    if lowest_occurred_time == None and column_data and column_data[0]:
      lowest_occurred_time = column_data[0][0]
    
    # Else, if this time is lower than the other current time, use it
    elif column_data[0][0] < lowest_occurred_time and column_data and column_data[0]:
      lowest_occurred_time = column_data[0][0]
  
  # Get the highest_occurred_time
  highest_occurred_time = None
  for (column, column_data) in columns.items():
    # If we havent set a lowest time yet, this is it
    if highest_occurred_time == None and column_data and column_data[-1]:
      highest_occurred_time = column_data[-1][0]
    
    # Else, if this time is lower than the other current time, use it
    elif column_data[-1][0] > highest_occurred_time and column_data and column_data[-1]:
      highest_occurred_time = column_data[-1][0]
  
  # We dont have any entries in our column data, so return
  if lowest_occurred_time == None or highest_occurred_time == None:
    return None
  
  log('StoreInRRD: Low: %s  High: %s  Delay: %s  Group: %s' % (lowest_occurred_time, highest_occurred_time, rrd_data['store_delay'], group))
  
  # Starting at the lowest occurred time, get all of the times for the columns,
  #   in a double list
  occurrances = {}
  
  ## Start at the lowest time, and work up store_delay increments
  #cur_time = lowest_occurred_time
  
  #while cur_time <= highest_occurred_time:
  #  occurrance = {}
  #  
  #  for (column, column_data) in columns.items():
  #    
  #    # Find the value that matches cur_time for this column
  #    for (occurred, value) in column_data:
  #      if occurred == cur_time:
  #        occurrance[column] = value
  #        # Done with this column
  #        break
  #    
  #    # If this column wasnt found, fill it in with a None
  #    if column not in occurrance:
  #      occurrance[column] = None
  #  
  #  occurrances[cur_time] = occurrance
  #  
  #  # Increment cur_time
  #  cur_time += rrd_data['store_delay']
  
  #import pprint
  #pprint.pprint(columns)
  
  # Build out occurrance dictionary, from the occurred times and columns
  for (column, column_data) in columns.items():
    for (occurred, value) in column_data:
      if occurred not in occurrances:
        occurrances[occurred] = {}
      
      # Update all the keys for these columns
      occurrances[occurred][column] = value
  
  
  times = occurrances.keys()
  times.sort()
  print times
  
  # Return the higher time we have
  highest_cur_time = 0
  
  # Get the last time this RRD was updated
  #rrd_last_updated = GetRrdLastUpdateTime(rrd_data, lowest_occurred_time)
  
  
  # Store all our occurrances
  for cur_time in times:
    log('RRD Update: %s' % cur_time)
    
    # Update any higher times
    if cur_time > highest_cur_time:
      highest_cur_time = cur_time
    
    ## Skip any entries older than the next update expected
    #if cur_time < rrd_last_updated + rrd_data['store_delay']:
    #  log('Skipping RRD: %s: %s  Older than: %s' % (rrd_data['path'], cur_time, rrd_last_updated))
    #  continue
    
    StoreInRrd_Occurrance(rrd_data, group, cur_time, occurrances[cur_time])
  
  # If our last RRD update is more than our entries, bump up the next time
  #   we want to store things.
  #NOTE(g): rrdtool is too particular about sending in times, and it gets
  #   stuck and you have to move ahead of it when this happens.  To do so,
  #   just move the next time we want to pick up results (because we have
  #   already updated all the times before this, in theory).
  #if rrd_last_updated >= highest_cur_time:
  #  log('RRD FIX: NEEDED: %s >= %s' % (rrd_last_updated, highest_cur_time))
  #  highest_cur_time = rrd_last_updated + rrd_data['store_delay']
  
  return highest_cur_time
  

def GetRrdLastUpdateTime(rrd_data):
  """Returns: int, epooch time, last time RRD was updated"""
  updated = 0
  
  if not os.path.isfile(rrd_data['path']):
    Exception('RRD Does not exist: %s' % rrd_data['path'])
  
  cmd = 'rrdtool last %(path)s' % rrd_data
  (status, output, output_error) = Run(cmd)
  
  if status == 0:
    updated = int(output.strip())
  else:
    log('RRD File failed to find last update: %s: %s' % (rrd_data['path'], output_error), logging.ERROR)
  
  return updated


def StoreInRrd_Occurrance(rrd_data, group, occurred, occurrance):
  if not os.path.isfile(rrd_data['path']):
    CreateRrd(rrd_data, group, occurred)
  
  log('Storing RRD Occurrance: %s - %s (%s)' % (occurred, occurrance, group))

  # Start off the command
  cmd = 'rrdtool update %s %s:' % (rrd_data['path'], occurred)
  
  # Sort the columns
  columns = rrd_data['columns'].keys()
  columns.sort()


  # Add each of the columns, in order (always)
  for column in columns:
    #
    if column in occurrance:
      value = occurrance[column]
      
      if value == None:
        cmd += 'U:'
      else:
        cmd += '%s:' % value
    
    else:
      cmd += 'U:'
  
  # Trim the trailing colon (:)
  cmd = cmd[:-1]
  
  #print cmd
  (status, output, output_error) = Run(cmd)
  print 'cmd: %s: %s: %s' % (cmd, status, output)
  
  if output_error:
    #log('Cmd: %s  Error: %s' % (cmd, output_error))
    
    site = rrd_data['site']
    deployment = rrd_data['deployment']
    service = rrd_data['service']
    instance_id = rrd_data['instance_id']
    
    # Strip the last time RRD says we have updated, out of output_error
    try:
      rrd_last_update_time = int(output_error.split(' ')[-5])
    
    # If this is not telling us we have the wrong time...  We're done
    except ValueError, e:
      raise e
    
    # Update the instance with this data
    data = {'last_collect_time':rrd_last_update_time + rrd_data['store_delay']}
    
    log('RRD FIX: Bumping up the last updated time to: %s (%s.%s.%s.%s)' % (data['last_collect_time'], site, deployment, service, instance_id))
    
    # Update the instance
    #config_loader.UpdateInstanceData(site, deployment, service, instance_id, data)



def CreateRrd(rrd_data, group, start=0):
  """Create the RRD file."""
  log('Creating RRD file: %s (%s)' % (rrd_data['path'], group))

  #cmd = '/usr/bin/rrdtool create %(path)s --start N --step %(store_delay)s ' % rrd_data
  #NOTE(g): If you try to insert any entries in the past in a new RRD, it
  #   freaks out and basically denies all other entries insertion.  To avoid
  #   this, start our time at the beginning.
  cmd = 'rrdtool create %s --start %s --step %s ' % (rrd_data['path'], int(start - rrd_data['store_delay']), rrd_data['store_delay'])
  
  #import pprint
  #pprint.pprint(rrd_data)
  
  # Create them in sorted order, so we can insert them properly
  columns = rrd_data['columns'].keys()
  columns.sort()
  
  
  # Add DSs for each column (sorted so order is repeatable)
  for column in columns:
    column_data = rrd_data['columns'][column]
    
    #DS:user:GAUGE:120:0:100 \
    # Update the default column data with the specified column data
    info = dict(rrd_data['column_default'])
    info.update(column_data)
    
    cmd += 'DS:%s:%s:%s:%s:%s ' % (column, info['type'], info['heartbeat'], info['range_bottom'], info['range_top'])
  
  
  # Add RRAs
  for rra in rrd_data['rra']:
    #RRA:MIN:0.5:10:1008 \
    #print rra
    #print len(rra)
    cmd += 'RRA:%s:%s:%s:%s ' % (rra[0], rra[1], rra[2], rra[3])
  
  #print cmd

  # Run the command
  (status, output, output_error) = Run(cmd)
  
  if output_error:
    log('Failed to created RRD: %s: %s' % (cmd, output_error))


def GraphRrds():
  """Graph all our RRD files.
  
  Dont discriminate, just do them all.  We will come back and make this
  more intelligent later (graphing by scheduled delay.)
  """
  for path in GlobDirectoryWalker('rrd', '*.rrd'):
    # Pull all the data we need out of the path
    path = path.replace('\\', '/') # Convert windows to Unix
    print path
    (_, site, deployment, service, rem_path) = path.split('/')
    pieces = rem_path[:-4].split('_')
    
    log('%s: %s: %s' % (path, rem_path, pieces))
    
    #NOTE(g): Format: %s_%s_%s: (rrd, instance_id, group)
    if len(pieces) == 2:
      group = None
      instance_id = pieces[-1]
      rrd = '_'.join(pieces[:-1])
    else:
      group = pieces[-1]
      instance_id = pieces[-2]
      rrd = '_'.join(pieces[:-2])
    
    #print (site, deployment, service, instance_id, rrd)
    
    #
    rrd_data = config_loader.GetRrdData(site, service, int(instance_id), rrd, group)
    
    log('Graphing RRD: %s' % rrd_data['path'])
    
    # Get the deployment name
    #deployment = rrd_data['deployment']
    
    #import pprint
    #pprint.pprint(rrd_data)
    
    #for (schedule_period, schedule_info) in rrd_data['graph_schedule'].items():
    if 1:
      
      for (rrd_graph, rrd_graph_info) in rrd_data['graph'].items():
        
        #print 'Graphing: %s %s' % (path, schedule_period)
        #print 'Graphing: %s %s' % (path, 'hourly')
        
        if group in ('None', None):
          image_path = 'www/static/rrd/%s_%s_%s_%s_%s.png' % (site, deployment, service, instance_id, rrd)
        else:
          image_path = 'www/static/rrd/%s_%s_%s_%s_%s_%s.png' % (site, deployment, service, instance_id, rrd, group)
        
        cmd = 'rrdtool graph %s ' % image_path
        cmd += '--title "%s   Instance %s   %s" ' % (service, instance_id, rrd)
        #print rrd_graph_info
        cmd += '--vertical-label "%s" ' % rrd_graph_info['label_vertical']
        cmd += '--start -1h ' #TODO
        cmd += '-w 400 -h 100 '
        
        # DEF
        for column in rrd_graph_info['columns']:
          column_data = dict(rrd_data['column_default'])
          column_data.update(rrd_data['columns'][column])
          
          cmd += 'DEF:%s=%s:%s:AVERAGE ' % (column, path, column)
        
        # CDEF
        line = 1
        line_stack = []
        for column in rrd_graph_info['columns']:
          column_data = dict(rrd_data['column_default'])
          column_data.update(rrd_data['columns'][column])
          #{'key': ['duration'], 'heartbeat': 120, 'range_top': 100, 'range_bottom': 0, 'type': 'GAUGE'}
          #print column_data
          
          # Add the column to the line stack
          line_stack.append(column)
          
          # Create the line items
          line_items = ','.join(line_stack)
          
          # Add the pluses so they stack
          line_items += ',+' * (len(line_stack)-1)
          
          cmd += 'CDEF:Ln%d=%s ' % (line, line_items)
          
          # Include the line
          line += 1
        
        # AREA
        line = 1
        line_stack = []
        for column in rrd_graph_info['columns']:
          column_data = dict(rrd_data['column_default'])
          column_data.update(rrd_data['columns'][column])
          #{'key': ['duration'], 'heartbeat': 120, 'range_top': 100, 'range_bottom': 0, 'type': 'GAUGE'}
          #print column_data
          
          # Add the column to the line stack
          line_stack.append(column)
          
          # Create the line items
          line_items = ','.join(line_stack)
          
          # Add the pluses so they stack
          line_items += ',+' * (len(line_stack)-1)
          
          # Label the lines
          if line == 1:
            line_label = column
          else:
            line_label = '%s:STACK' % column
          
          cmd += 'AREA:%s%s:%s ' % (column, rrd_data['colors']['area'][line-1], line_label)
          
          # Include the line
          line += 1
        
        # LINE
        line = 1
        line_stack = []
        for column in rrd_graph_info['columns']:
          cmd += 'LINE1:Ln%d%s ' % (line, rrd_data['colors']['line'][line-1])
          
          # Include the line
          line += 1
        
        # Date COMMENT
        cmd += '"COMMENT:\\n" '
        cmd += '"COMMENT:%s\\n" ' % time.asctime(time.localtime()).replace(':', '\\:')
        
        # GRPINTs
        for column in rrd_graph_info['columns']:
          cmd += '"GPRINT:%s:LAST:Last %s\\: %%2.1lf" ' % (column, column)
        
        
        #print cmd
        Run(cmd)
    
    
    #cmd = '''/usr/bin/rrdtool graph %(image)s \
    #--title="%(host)s %(service)s" \
    #--vertical-label "%(vertical_label)s" \
    #--start -4h \
    #-w 400 -h 100 \
    #--lower-limit=0 --upper-limit=100 \
    #'DEF:system=%(rrd)s:system:AVERAGE' \
    #'DEF:user=%(rrd)s:user:AVERAGE' \
    #'DEF:wait=%(rrd)s:wait:AVERAGE' \
    #'DEF:idle=%(rrd)s:idle:AVERAGE' \
    #'CDEF:Ln1=system' \
    #'CDEF:Ln2=system,user,+' \
    #'CDEF:Ln3=system,user,wait,+,+' \
    #'CDEF:Ln4=system,user,wait,idle,+,+,+' \
    #'AREA:system#EA644A:System' \
    #'AREA:user#EC9D48:User:STACK' \
    #'AREA:wait#ECD748:Wait:STACK' \
    #'AREA:idle#BBBBBB:idle:STACK' \
    #'LINE1:Ln1#CA442A' \
    #'LINE1:Ln2#CC7D28' \
    #'LINE1:Ln3#CCB728' \
    #'COMMENT:\\\\n' \
    #'COMMENT:%(date)s\\\\n' \
    #%(comment)s \
    #'GPRINT:user:LAST:User\\: %%2.1lf' \
    #'GPRINT:system:LAST:System\\: %%2.1lf' \
    #'GPRINT:wait:LAST:Wait\\: %%2.1lf' \
    #'GPRINT:idle:LAST:Idle\\: %%2.1lf' \
    #'COMMENT:\\\\n' \
    #'GPRINT:Ln3:MAX:MAX Total\\: %%2.1lf%%%%'


'''
    rrd:
      traffic:
        store_delay: 60
        
        columns:
          requests:
            key: ["requests"]
            type: COUNTER
            range_top: U
          
          requests_kb_ingress:
            key: ["requests_kb_ingress"]
            type: COUNTER
            range_top: U
          
          requests_kb_egress:
            key: ["requests_kb_egress"]
            type: COUNTER
            range_top: U
          
          failures:
            key: ["failures"]
            type: COUNTER
            range_top: U
          
          wait_seconds:
            key: ["wait_seconds"]
            type: GAUGE
            range_top: U
          
          queue:
            key: ["queue"]
            type: GAUGE
            range_top: U
        
        graph:
          traffic:
            columns: [request, queue, failures]
            label_vertical: Requests, Queue & Failures
          
          traffic_kb:
            columns: [requests_kb_ingress, requests_kb_egress]
            label_vertical: Traffic in KB
          
          wait_seconds:
            columns: [wait_seconds]
            label_vertical: Wait in Seconds
'''


def Test():
  import yaml
  defaults = yaml.load(open('timeseries_rrd_default.yaml'))

  # Create the RRD
  create_fields = {}
  create_fields['user'] = {'type':'GAUGE', 'range_top':'U', 'range_bottom':0, 'heartbeat':120}
  create_fields['system'] = {'type':'GAUGE', 'range_top':'U', 'range_bottom':0, 'heartbeat':120}
  create_fields['idle'] = {'type':'GAUGE', 'range_top':'U', 'range_bottom':0, 'heartbeat':120}
  CreateRrd(filename, interval, create_fields, defaults)
  
  #Old_CreateRrd(rrd_data, group)

  # Get last updated
  print GetRrdLastUpdateTime(rrd_data)

  # Insert data
  import time
  fields = {'user':42, 'system':11, 'idle':46}
  StoreInRrd(filename, time.time(), fields)
  
  fields = {'user':56, 'system':6, 'idle':38}
  StoreInRrd(filename, time.time()+5, fields)
  
  fields = {'user':36, 'system':16, 'idle':48}
  StoreInRrd(filename, time.time()+10, fields)
  
  #Old_StoreInRrd(rrd_data, group, {'items':columns})

  # Get last updated
  print GetRrdLastUpdateTime(rrd_data)
  
  # Fetch the data back
  fields = ['system', 'user', 'idle']
  start_time = -60 # 60 seconds from now
  fetched = FetchFromRrd(filename, fields, start_time)
  import pprint
  pprint.pprint(fetched)
  
  # Graph the RRD
  fields = ['system', 'user', 'idle']
  method = 'STACK'
  GraphRrd(filename, fields, method, defaults)
  #GraphRrds()
  
  


if __name__ == '__main__':
  Test()
