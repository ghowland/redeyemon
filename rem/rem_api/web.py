#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Web and RPC
"""


import os


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


# Maximum number of times views can embed before it's too deep
MAX_RENDER_RECURSION_DEPTH = 20


def GetWebPageByPath(path):
  """Returns web page field data, or None of not found."""
  sql = "SELECT * FROM web_page WHERE name = '%s'" % SanitizeSQL(path)
  result = Query(sql)
  
  if result:
    return result[0]
  else:
    return None


def GetWebView(view_id):
  """Returns web page field data, or None of not found."""
  sql = "SELECT * FROM web_view WHERE id = %d" % view_id
  result = Query(sql)
  
  if result:
    return result[0]
  else:
    return None


class WebRenderViewError(Exception):
  """The only Exeption RenderView() will have."""
  def __init__(self, log_reason, output=None, response_code=400):
    self.log = log_reason
    
    log(log_reason)
    
    if output == None:
      self.output = log_reason
    else:
      self.output = output
    
    self.response_code = response_code


class WebRenderOutput:
  
  def __init__(self):
    self.output = ''
    self.output_header = ''
    
    self.data = {}
    
    #TODO(g): Are these useful here?  Im not using them at the moment.  Remove
    #   if they are not used soon.
    self.response_code = 200
    self.content_type = 'text/html'
  
  
  def __iadd__(self, data):
    """Allow in-place text additions to output.
    
    Example:
      output = RenderOutput()
      output += 'Add text'
    """
    # If this is a string, append it to output
    if type(data) == str:
      self.output += data
    
    # Else, if this is one of our own, we update based on it
    elif isinstance(data, RenderOutput):
      self.output += data.output
      self.output_header += data.output_header
      
      # We keep our data dict, but add theirs underneath
      data = dict(data)
      data.update(self.data)
      self.data = data
    
    return self
  
  
  def __repr__(self):
    output = 'Output:\n'
    output += self.output
    
    output = '\n\nOutput Header\n'
    output += self.output_header
    
    return output
  
  
  def AppendHeaderOutput(self, text):
    self.output_header += text


def WebRenderView(view_id, parent_view_id, data, state, depth=0):
  """All the complexity of view rendering is done with this.  Returns string.
  
  This function only throws one exception, WebRenderViewError
  """
  output = WebRenderOutput()
  
  # If we are in too deep, we are probably looping.  Log parent/child and return
  if depth >= MAX_RENDER_RECURSION_DEPTH:
    log('Maximum recurison depth reached: %s: Parent %d' %
        (view_id, parent_view_id), logging.CRITICAL)
    return output
  
  # Protect all rendering so we can report on exceptions easily
  try:
    # Get the view
    view = GetWebView(view_id)
    
    # Load the template
    template = GetWebViewTemplate(view_id)
    
    # If there is no script, then the template is the output
    if view['script_render'] == None:
      # Set the template to be the output, and we're done
      output.output = template
    
    # Else we have a script, so execute it and get our output
    else:
      #TODO(g): This seems to happen on import failures, if there is Python
      #   syntax errors.  Fix this in a more permanent way later.
      if os.path.isfile('/usr/local/site_control/rem/rem_scripts/webc'):
        os.unlink('/usr/local/site_control/rem/rem_scripts/webc')
      
      script_module = site_control.GetScriptPythonModule(view['script_render'])
      #script = site_control.GetScript(view['script_render'])
      #log('Running Script: %s: %s' % (script['name'], script_module))
      
      if script_module == None:
        raise WebRenderViewError('Render script module was not found: Script %s' % view['script_render'])
      
      if not hasattr(script_module, 'Execute'):
        raise WebRenderViewError('Execute function not found in module: Script %s' % view['script_render'])
      
      # Get the Execute function
      execute_function = getattr(script_module, 'Execute')
      
      # Pack data with the template, in a way that it's unlikely to collide with
      #   argument data
      data['_template'] = template
      
      # Pack data with any auto-executing view_fields
      #TODO(g): This will be handy in the future, as we can set things up to
      #   automatically chain, as long as they have usable data available.
      #   This will make very complex pages much easier to develop, as once
      #   a pattern has been established, then a lot of the includes dont need
      #   any work to set up for new pages or in-child-usage.
      pass#todo...
      
      # Execute the function, with our data and state args
      try:
        script_output = execute_function(data, state)
      except Exception, e:
        # Get information we can render about this exception
        text = error_info.GetExceptionDetails()
        
        # Get the script file name
        script = site_control.GetScript(view['script_render'])
        
        # Add our script information
        text = '<b>Script File:</b> %s\n<br>\n%s' % (script['path_relative_script'],
                                                 text)
        
        # Raise our WebRenderViewError
        raise WebRenderViewError('RenderView ERROR: %s' % e, text, 400)
      
      # Append the output to our RenderOutput (should be string or RenderOutput)
      output += script_output
  
  
  # If we had any problems in recursive calls, just bubble them up
  except WebRenderViewError, rve:
    raise rve
  
  # Any new problems, wrap in WebRenderViewError
  except Exception, e:
    # Get information we can render about this exception
    text = error_info.GetExceptionDetails()
    
    # Raise our WebRenderViewError
    raise WebRenderViewError('RenderView ERROR: %s' % e, text, 400)
  
  return output


def GetWebViewTemplate(view_id):
  """Returns the template text, or None if the file isnt found."""
  view = GetWebView(view_id)
  
  #TODO(g): Unhardcode this path
  WEB_TEMPLATE_PATH = '/usr/local/site_control/rem/web/templates/%s'
  
  # Get the full path name
  full_path = WEB_TEMPLATE_PATH % view['template_file']
  
  # If the path exists, load and return the text
  if os.path.isfile(full_path):
    try:
      output = open(full_path).read()
    except Exception, e:
      log('Couldnt load the file "%s": %s' % (full_path, e), logging.CRITICAL)
      return None
    
    return output
  
  # Else, the file wasnt found
  else:
    return None


def WebTemplateFormat(template, format_data):
  """Formats the template file, only covering keys in the format_data."""
  output = str(template)
  
  for key in format_data:
    # Create our format key, for replacing template data
    format_key = '%%(%s)s' % key
    
    # Replace template data.  Convert value to string, replace expects it.
    output = output.replace(format_key, str(format_data[key]))
  
  return output

