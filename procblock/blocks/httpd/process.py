#!/usr/bin/python


#Author: Geoff Howland
#Project: dropSTAR                   http://redeyemon.sourceforge.net/dropstar/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Process page rendering.
"""

import sys
sys.path.append('../../')
import shared.log as logging
from shared.log import log

import runblock


DEFAULT_PAGE_ARGS = ('redirect', )


def GetSite(conf, host):
  """Get the site specified by the host in the conf."""
  for name in conf:
    # Ignore informational sites, like _default
    if name.startswith('_'):
      continue
    
    # Test this site
    site = conf[name]
    
    for hostname in site['hosts']:
      if hostname == host:
        return site
      elif hostname == '*':
        return site
      #TODO(g): Do globbing for non-total-glob(*) matching: ex. "something*"
      pass
  
  return None


def GetPage(host, path, site, conf):
  """"""
  #log('Get Path: "%s"  Host: %s' % (path, host), logging.DEBUG)
  
  # Get the page from the site
  for (name, page) in site['page'].items():
    if path in page['aliases']:
      log('Page: %s' % page['title'], logging.DEBUG)
      return page
  
  # No page found
  #TODO(g): Return site['page_not_found'] page
  #TODO(g): Return site['page_error'] page, on error
  return None


def RenderPage(site, page, conf, apps, data, state):
  """Render the page."""
  output = RenderOutput()
  
  # Prepare run input
  #TODO(g): This is ghetto.  Maybe some of this should stay, but the state
  #   has it's own var in RunScriptBlock now, so we can keep application data
  run_input = {}
  run_input.update(state['headers'])
  run_input.update(state['cookies'])
  if state['session']:
    run_input.update(state['session'])
  run_input.update(data)
  
  # Run the page run script block (page already has the 'run' block in it)
  log('Running script: %s  Path: %s' % (page, site['script_path_prefix']))
  run_output = runblock.RunScriptBlock(page, run_input, state, site['script_path_prefix'])
  #print 'Run output: %s' % run_output
  
  # Get the template
  template = GetTemplate(site, page, run_output)
  
  # Format the template
  template_output = FormatTemplate(template, run_output)
  
  # Add template to the output
  output += str(template_output)
  
  #TODO(g): Deal with cookies and other crap we want to set from the run_output
  
  return output


def GetTemplate(site, page, run_output):
  """Return the template needed for this page, based on the run_output data.
  
  Uses "default" template for this page if no other templates match the
  run_output data.
  """
  #TODO(g): Test conditions, dont just use default every time
  
  # Process each possible template, if they match, run them
  template = None
  for item in page['template']:
    #TODO(g): Implement conditional test in runblock module, test these, if
    #   positive, select
    if 'if' not in item:
      template = item
      break
  
  # If no template was found, use the last template.  Template of last resort.
  if template == None:
    log('Using template of last resort', logging.INFO)
    template = page['template'][-1]
  
  # Get the path
  template_path = template['path']
  
  # If we have a template path prefix, and this isnt an absolute path, prefix
  if 'template_path_prefix' in site and not template_path.startswith('/'):
    template_path = '%s/%s' % (site['template_path_prefix'], template_path)
  
  template_text = open(template_path).read()
  
  return template_text


def FormatTemplate(template, data):
  """Format the template with the run_output"""
  #TODO(g): Do it cleanly so we can use python format commands, but errors are
  #   ignored (fill in with the same value, so the variables are plainly visible)
  #print 'Formatting template: %s' % template
  #print 'With data: %s' % data
  
  # Ensure we do not change this data
  data = dict(data)
  
  done = False
  
  while not done:
    try:
      output = template % data
      done = True
    except KeyError, e:
      if e not in ['redirect']:
        log('Missing key: %s' % e)
        #print dir(e)
      
      if e.args[0] in DEFAULT_PAGE_ARGS:
        data[e.args[0]] = ''
      else:
        data[e.args[0]] = '--(%s)s--' % e.args[0]
  
  return output


class RenderError(Exception):
  """"""
  
  def __init__(self, log, output):
    self.log = log
    self.output = output
    self.response_code = 500 #TODO(g): Better?


class RenderOutput:
  
  def __init__(self):
    self.output = ''
    self.output_header = ''
    
    self.data = {}
    
    self.write_cookies = {}
    
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
  
  
  def AddCookie(self, name, data, duration=None, domain=None):
    """Add a cookie to be saved."""
    #TODO(g): Save duration too.
    #TODO(g): Specify domain (subdomains only).
    self.write_cookies[str(name)] = str(data)

