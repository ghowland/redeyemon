#!/usr/bin/python


#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Web HTTPd
  Run from rem_web.py

Handles all HTTP requests, GET only.  It is intended to be READ only.

Use RPC for doing interaction with the backend, doing this inside a web
rendering request is a total pain in the ass and has all kinds of times
you'd like to have some feature you dont, and this isnt an end-user
oriented service, so is it assumed their JS will be working and can
submit any data we need them to.  Code accordingly for best results.

When querying Cloud data from the Site Control API, we will always get the
cached version, so that web requests are fast.  This is not the place we need
to wait on data.

NOTE(g): I left this a single threaded HTTP server because the requests should
be infrequent enough and fast enough that even "heavy" usage of this server
should not back up.  It's an admin tool.
"""

import time
import mimetools
import re
import BaseHTTPServer
import SocketServer
import SimpleXMLRPCServer
import urlparse
import cgi
import string
import Cookie
import socket
import sys
import os
import urllib
import traceback
import threading


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *



def CGIArgsToDict(args):
  """Convert our args string into a dictionary."""
  # Get our arg data
  data = {}
  
  for item in args.split('&'):
    #NOTE(g): I am specifically including empty vars, because they
    #    are sometimes exactly what we want.
    if '=' in item:
      (key, value) = item.split('=', 1)
      data[urllib.unquote(key)] = urllib.unquote(value.replace('+', ' '))
  
  return data


def UriParse(uri):
  """We want to parse the URI into a path and argument section.  Return tuple.
  
  Python's urlparse module fails on more complex data, such as sending Python
  code across the line.  It crops our data, breaking the submit, so we must do
  this ourselves.
  
  Args:
    uri: string, uri (url, minus the protocol and host name)
  
  Returns: tuple (path, args).  Both strings.
  """
  if '?' in uri:
    (path, args) = uri.split('?', 1)
  else:
    (path, args) = (uri, '')
  
  return (path, args)



class WebHttpdThread(threading.Thread):
  """XMLRPC Listener Thread"""

  def __init__(self, state=None):
    logging.SetLogFile('/usr/local/site_control/web_httpd.log')
    
    if not state:
      state = {'not_quitting':False}
    
    self.state = state
    
    # Get this machine.id.  This can be done, even if Site Control DB is
    #   unavailable, via a cached file, if SC has ever been run here
    self.machine_id = site_control.GetThisMachineId()
    
    # Initialize this as a Thread
    threading.Thread.__init__(self)


  def run(self):
    """Once start() is called, this function is executed, which is the thread's
    run function.
    """
    # If we come up and Site Control isnt available, wait so we can configure
    #   ourselves properly with the rest of the site.  Site Control will
    #   come back as long as a DB is available
    while not site_control.IsSiteControlAvailable():
      log('RpcListenerThread: Site control is not available')
      time.sleep(5)
    
    # Get our site configuration
    site_config = site_control.GetSiteConfig(site_control.GetSiteByMachine(self.machine_id))
    
    #TODO(g): Change this to site_config based, also dont use 80, use 8000
    #   and 8001 for RPC, and put them behind Nginx with password AUTH.
    WEB_HTTPD_PORT = 80
    port = WEB_HTTPD_PORT
    
    self.server = BaseHTTPServer.HTTPServer(('0.0.0.0', port), HTTPRequest)
    self.fd_server = self.server.fileno()
    
    # Loop forever, or until we quit, whichever comes first
    while self.state['not_quitting']:
      try:
        # Run the server's main loop
        #server.serve_forever() # Wont allow us to quit
        # Should just handle 1 request at a time, I think it blocks
        self.server.handle_request()
        
        # Give back to the system as we spin loop
        time.sleep(0.1)
      
      # Log and ignore, if we can
      except Exception, e:
        try:
          log('WebHttpdThread: Unhandled exception: %s' % e)
          #TODO(g): Critical to do?
          #site_control.LogMachineError(self.machine_id, 'RpcListenerThread: %s' % e)
        except:
          log('WebHttpdThread: Failed to log error.')
          pass # If this wont work, we just keep trudging on


class HTTPRequest(BaseHTTPServer.BaseHTTPRequestHandler):
  """HTTP Request handler."""
  
  def do_GET(self):
    path = self.path
    
    #NOTE(g): urlparse is not good enough.  It can kill data payload in our
    #   POST requests passed to GET.  I would guess the same problem could
    #   occur with a regular GET too.  Not sure why it does this, but when
    #   trying to pass Python Code from a textarea tag I lose data as urlparse
    #   crops it right here.
    #(_, _, path, _, args, _) = urlparse.urlparse(path)
    (path, args) = UriParse(path)
    
    # Strip the leading slash (/)
    path = path[1:]
    
    # Having 2 var names is confusing.  We never care about the string version
    #   again.  Ditch it.
    args = CGIArgsToDict(args)
    
    try:
      # This wraps the real work of the request.  This keeps GET and other
      #   HTTP methods wrapped.
      self.handle_everything(path, args)
    except:
      text = error_info.GetExceptionDetails()
      log(text)
  
  
  def handle_everything(self, path, args):
    # Get the cookies
    write_cookies = {}
    cookies = {}
    if self.headers.has_key("Cookie"):
      cookie = Cookie.SimpleCookie(self.headers["Cookie"])
      for name in cookie:
        cookies[name] = cookie[name].value
    
    # Get the host header, for our application
    if self.headers.has_key('X-Forwarded-Host'):
      host_header = self.headers['X-Forwarded-Host']
    elif self.headers.has_key('Host'):
      host_header = self.headers['Host']
      if ':' in host_header:
        host_header = host_header.split(':')[0]
    else:
      host_header = None
    
    # Init response data
    output = ''
    content_type = 'text/html'
    response_code = 400
    
    #log('Rendering request: %s %s %s %s' % (path, self.headers, cookies, args))
    
    # Start the duration clock
    start_time = time.time()
    
    # Render the request 
    try:
      (output, content_type, response_code, redirect_url, write_cookies,
          write_headers) = self.RenderRequest(path, self.headers, cookies, args)
    
    # On render failures, report the error as best we can
    except Exception, e:
      details = error_info.GetExceptionDetails()
      print 'ERROR: %s' % details
      output = details.replace('\n', '<br>\n')
      content_type = 'text/html'
      response_code = 500
    
    # Write headers
    self.send_response(response_code)
    self.send_header('Content-type', content_type)
    
    # Write cookies
    for name in write_cookies:
      self.send_header('Set-Cookie', '%s="%s"; Path=/' % (name,
                                                          write_cookies[name]))
    
    # Write headers
    for name in write_headers:
      self.send_header(name, write_headers[name])
    
    # End the headers
    self.end_headers()
    
    # Write output
    self.wfile.write(output)
    
    # Stop the duration clock
    duration = time.time() - start_time
    
    # Dont log static content, boring
    if not path.startswith('static/'):
      log('Path: %s  Duration: %0.2fs' % (path, duration))


  def RenderRequest(self, path, headers, cookies, args):
    # Initialize result data
    output = ''
    content_type = 'text/html'
    response_code = 200
    redirect_url = None
    write_cookies = {}
    write_headers = {}
    
    # If this is a static request
    if path.startswith('static/'):
      # Most of our static context are binary files
      file_flag = 'rb'
      
      # Set content type by extension
      if path.lower().endswith('.png'):
        content_type = 'image/png'
      elif path.lower().endswith('.jpg'):
        content_type = 'image/jpg'
      elif path.lower().endswith('.bmp'):
        content_type = 'image/bmp'
      elif path.lower().endswith('.gif'):
        content_type = 'image/gif'
      elif path.lower().endswith('.css'):
        content_type = 'text/css'
        file_flag = 'r'
      elif path.lower().endswith('.js') or path.split('.')[-1] in ('txt', 'html'):
        content_type = 'text/html'
        file_flag = 'r'
      
      # Split out the static/ prefix
      path = path.split('static/', 1)[1]
      
      # Build out full path
      #TODO(g): Remove this hard coding
      STATIC_CONTENT_PATH = '/usr/local/site_control/rem/web/static/%s'
      full_path = STATIC_CONTENT_PATH % path
      
      # Set the cache control
      STATIC_CACHE_TIMEOUT = 3600 # Seconds
      write_headers['Cache-Control'] = 'max-age=%s, must-revalidate' % STATIC_CACHE_TIMEOUT
      
      # Get the data from this full path
      output = open(full_path, file_flag).read()
    
    # Else, this is dynamic content.  Get the page, render the view.
    else:
      page = site_control.GetWebPageByPath(path)
      #log('Path: %s  Page: %s' % (path, page))
      
      # If we have a page from this path
      if page and page['view']:
        # Get this page's view's render output
        try:
          # Set up the initial data and state
          data = args
          #TODO(g): Add session information here.  We only need the
          #   admin_user.id and auth-cookie
          state = {'headers':headers, 'cookies':cookies, 'session':None}
          
          # Review the page's view (sub-views get rendered recursively)
          render_output = site_control.WebRenderView(page['view'], None, data, state)
          
          # Copy out the render data
          output = render_output.output
          
          # Replace the title with the page title, if it exists
          if page['title']:
            output = output.replace('%(page_title)s', page['title'])
          
          # Replace out unfilled in defaults
          output = output.replace('%(page_header)s', '')
          output = output.replace('%(page_body)s', '')
        
        except site_control.WebRenderViewError, e:
          log(e.log)
          
          # Render View wraps any exceptions, so we get an output and code
          output = e.output
          response_code = e.response_code
        
        except Exception, e:
          msg = 'WebRenderView (path=%s) did not return a WebRenderViewError: %s' % (path, e)
          log(msg, logging.CRITICAL)
          output = 'Internal Error: %s' % msg
          response_code = 500
      
      # Else, we couldnt find this page, so report it
      else:
        output = 'Page not found: %s' % path
        response_code = 404
    
    
    return (output, content_type, response_code, redirect_url, write_cookies,
            write_headers)
