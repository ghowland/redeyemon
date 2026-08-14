#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Hardware (Instance Types, Images, Data Centers)
"""


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def GetHardwareKind(kind_id):
  """Returns the hardware_kind associated with the id.  None if not found."""
  sql = "SELECT * FROM hardware_kind WHERE id = %d" % kind_id
  result = Query(sql)

  # If we didnt find anything, failed
  if not result:
    log('Couldnt find Hardware Kind: %s' % kind_id, logging.ERROR)
    return None
  # Else, return the hardware image data
  else:
    return result[0]


def GetHardwareImage(image_id):
  """Returns the hardware_image associated with the id.  None if not found."""
  sql = "SELECT * FROM hardware_image WHERE id = %d" % image_id
  result = Query(sql)

  # If we didnt find anything, failed
  if not result:
    log('Couldnt find Hardware Image: %s' % image_id, logging.ERROR)
    return None
  # Else, return the hardware image data
  else:
    return result[0]


def GetHardwareImageByName(name):
  """Returns the hardware_image associated with the name.  Adds if not found."""
  sql = "SELECT * FROM hardware_image WHERE name = '%s'" % SanitizeSQL(name)
  result = Query(sql)

  # If we didnt find anything, failed
  if not result:
    # If we didnt find it add it.  It's obviously new.
    sql = "INSERT INTO hardware_image (name, info) VALUES ('%s', 'Unknown.  Added by GetHardwareImageByName()')" % \
          SanitizeSQL(name)
    image_id = Query(sql)

    log('Calling self.  Recursing to pick up newly inserted hardware_image.')
    return GetHardwareImageByName(name)
  # Else, return the hardware image data
  else:
    return result[0]


def UpdateHardwareImage(hardware_image_id, name):
  """Updates a hardware_image.id with the latest named identifier (ex: AMI).

  Wheneven an AMI is rebuilt, it will get a new name, so update it with this.
  """
  log('This always causes a problem, but is required.  Why is this happening?', logging.CRITICAL)
  sql = "UPDATE hardware_image SET name = '%s' WHERE id = %d" % \
        (SanitizeSQL(name), hardware_image_id)
  Query(sql)


