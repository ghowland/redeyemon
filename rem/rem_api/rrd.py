#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: RRD
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *



def GetRrd(rrd_id):
  """Gets the info for an RRD and all it's fields, in order."""
  rrd = {'fields':[], 'data':None}

  # RRD data
  sql = "SELECT * FROM rrd WHERE id = %d" % rrd_id
  result = Query(sql)
  rrd['data'] = result[0]

  # RRD Fields
  sql = "SELECT * FROM rrd_field WHERE rrd = %d ORDER BY field_order" % rrd_id
  result = Query(sql)
  for item in result:
    # Textify the RRD field types
    type_name = Query("SELECT * FROM rrd_field_type WHERE id = %d" % item['field_type'])[0]

    # Create dict from item, and fix up fields that are more useful as text
    field = dict(item)
    field['field_type'] = type_name

    # Add this ordered field to our RRD fields
    rrd['fields'].append(field)

  return rrd




def RunLocalMachineRrdCollect():
  """Returns a dict of RRD collection output, keyed on the machine_rrd.id,
  value is the output of the rrd.script_collect script.
  """
  machine_rrd = {}

  machine_id = site_control.GetThisMachineId()

  log('RunLocalMachineRrdCollect: Invoked (machine: %s)' % machine_id)

  rrds = site_control.GetMachineRrds(machine_id)

  # Collect for each RRD
  for rrd_id in rrds:
    rrd = GetRrd(rrd_id)

    # Run the script, and log that we run it
    (exit_code, output) = run_script.RunScript(rrd['script_collect'])

    # Save the RRD output
    machine_rrd[rrd_id] = output

  return machine_rrd


