#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Utilities
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def UpdateData(table, table_id, data):
  """Updates a Site Controls tables data, by dict.  Handles logging and
  checking if any fields changed for easy use.  Also will handle un-flattening
  field data that is was flatten from relational data for tables that need it.
  """
  # If we are trying to update the Site Control Master with a Decomm Status
  if table == 'machine' and site_control.GetMasterMachineId() == table_id and 'status' in data and data['status'] == 7:
    log('Will not set the Site Control Master machine to Decomissioned: %s' % stack.Mini(5))
    return
  
  schema = query.GetSchema()

  #TODO(g): Make this work better, for now, just update all the fields
  #   without any tests or logging
  for key in data:
    value = data[key]
    
    # If this key is not in the original schema, skip it
    if key not in schema[table]:
      continue
    # Else, If value is None/NULL
    elif value == None:
      value = 'NULL'
    # Wrap text/varchars with single quotes
    elif schema[table][key]['type'].startswith('varchar') or schema[table][key]['type'] == 'text':
      value = "'%s'" % data[key]
    # Wrap dates and times with single quotes
    elif schema[table][key]['type'] in ('datetime', 'time', 'date'):
      value = "'%s'" % data[key]
    # Else, Numbers dont need wrapping
    #TODO(g): There are more types to deal with later
    else:
      value = data[key]

    sql = "UPDATE %s SET `%s` = %s WHERE id = %d" % (table, key, value, table_id)
    Query(sql)


