#!/usr/bin/python


#Author: Geoff Howland
#Project: Drop Star                  http://redeyemon.sourceforge.net/dropstar/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
HTTPd

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

import process


import sys
sys.path.append('../../')
import shared.log as logging
from shared.log import log

from shared import error_info


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
import logging


def parse_multipart(fp, pdict):
    """Parse multipart input.
    
    Arguments:
    fp   : input file
    pdict: dictionary containing other parameters of content-type header
    
    Returns a dictionary just like parse_qs(): keys are the field names, each
    value is a list of values for that field.  This is easy to use but not
    much good if you are expecting megabytes to be uploaded -- in that case,
    use the FieldStorage class instead which is much more flexible.  Note
    that content-type is the raw, unparsed contents of the content-type
    header.
    
    XXX This does not parse nested multipart parts -- use FieldStorage for
    that.
    
    XXX This should really be subsumed by FieldStorage altogether -- no
    point in having two implementations of the same parsing algorithm.
    
    """
    boundary = ""
    if 'boundary' in pdict:
        boundary = pdict['boundary']
    if not cgi.valid_boundary(boundary):
        raise ValueError,  ('Invalid boundary in multipart form: %r'
                            % (boundary,))
    
    nextpart = "--" + boundary
    lastpart = "--" + boundary + "--"
    partdict = {}
    terminator = ""
    
    while terminator != lastpart:
        bytes = -1
        data = None
        if terminator:
            # At start of next part.  Read headers first.
            headers = mimetools.Message(fp)
            
            #NOTE(ghowland): This was the reason to copy this function,
            #   we want this file name!
            filename_result = re.findall('filename="(.*?)"', str(headers))
            if filename_result:
              filename_result = filename_result[0]
              if len(filename_result) > 2 and filename_result[1] == ':':
                filename_result = filename_result[2:]
              filename_result = filename_result.replace('\\', '/')
              filename_result = os.path.basename(filename_result)
              # Pack into list again, since the upload side expects that
              partdict['_filename'] = [filename_result]
            
            clength = headers.getheader('content-length')
            if clength:
                try:
                    bytes = int(clength)
                except ValueError:
                    pass
            if bytes > 0:
                if maxlen and bytes > maxlen:
                    raise ValueError, 'Maximum content length exceeded'
                data = fp.read(bytes)
            else:
                data = ""
        # Read lines until end of part.
        lines = []
        while 1:
            line = fp.readline()
            if not line:
                terminator = lastpart # End outer loop
                break
            if line[:2] == "--":
                terminator = line.strip()
                if terminator in (nextpart, lastpart):
                    break
            lines.append(line)
        # Done with part.
        if data is None:
            continue
        if bytes < 0:
            if lines:
                # Strip final line terminator
                line = lines[-1]
                if line[-2:] == "\r\n":
                    line = line[:-2]
                elif line[-1:] == "\n":
                    line = line[:-1]
                lines[-1] = line
                data = "".join(lines)
        line = headers['content-disposition']
        if not line:
            continue
        key, params = cgi.parse_header(line)
        if key != 'form-data':
            continue
        if 'name' in params:
            name = params['name']
        else:
            continue
        if name in partdict:
            partdict[name].append(data)
        else:
            partdict[name] = [data]
    
    return partdict



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



class HttpdThread(threading.Thread):
  """HTTP Listener Thread"""

  def __init__(self, port, protocol, conf, apps, state=None):
    #TODO(g): Each Listener thread needs it's own log files.  Do this later.
    #logging.SetLogFile('web_httpd.log')
    
    self.port = port
    self.protocol = protocol
    
    #TODO(g): Improve this and do the security separation stuff, so that the
    #   HTTP handles know about this.
    #TODO(g): Make there a way to update this when our conf files change.
    self.conf = conf
    self.apps = apps
    
    # Global state dict
    #TODO(g): This needs to be SO much better!  I am going to pack all
    #   shared data in here, temporarily.  Built for the ActionHandler.
    self.global_state = {'http_id':id(self)}
    
    # Server objects: To be populated later
    self.server = None
    self.fd_server = None
    
    log('Starting HTTP Listener: %s:%s' % (port, protocol), logging.INFO)
    
    if not state:
      state = {'not_quitting':True}
    
    self.state = state
    
    # Initialize this as a Thread
    threading.Thread.__init__(self)

  
  def SetConf(self, conf):
    self.conf = conf
    
    # If we have our server, populate that too
    if self.server:
      self.server.conf = self.conf


  def run(self):
    """Once start() is called, this function is executed, which is the thread's
    run function.
    """
    #TODO(g): Allow specifying the interface, for localhost only or flexibility
    self.server = BaseHTTPServer.HTTPServer(('0.0.0.0', self.port), HTTPRequest)
    self.fd_server = self.server.fileno()
    
    # Populate the server's conf and apps
    #TODO(g): Do this better.
    self.server.conf = self.conf
    self.server.apps = self.apps
    self.server.global_state = self.global_state
    
    # Loop forever, or until we quit, whichever comes first
    while self.state['not_quitting']:
      try:
        # Run the server's main loop
        #server.serve_forever() # Wont allow us to quit
        # Should just handle 1 request at a time, I think it blocks
        log('HTTP Listener (%s): Waiting for request...' % self.port, logging.DEBUG)
        self.server.handle_request()
        
        # Give back to the system as we spin loop
        time.sleep(0.1)
      
      # Log and ignore, if we can
      except Exception, e:
        try:
          log('HttpdThread: Unhandled exception: %s' % e, logging.ERROR)
          #TODO(g): Critical to do?
          #site_control.LogMachineError(self.machine_id, 'RpcListenerThread: %s' % e)
        except:
          log('HttpdThread: Failed to log error.', logging.ERROR)
          pass # If this wont work, we just keep trudging on
    
    log('HTTP Listener (%s): Finished' % self.port, logging.INFO)


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
      log(text, logging.ERROR)


  def do_POST(self):
    path = self.path
    
    (_, _, path, _, args, _) = urlparse.urlparse(path)
    
    # Strip the leading slash (/)
    path = path[1:]
    
    # Get our args
    (ctype, pdict) = cgi.parse_header(self.headers.getheader('content-type'))
    # Normal CGI arg passing, with POST
    if ctype == 'application/x-www-form-urlencoded':
      clen = self.headers.getheader('content-length')
      if clen:
          clen = string.atoi(clen)
      data = self.rfile.read(clen)
      self.path = '%s?%s' % (self.path, data)
      
      #print 'POST: GET Path: %s' % self.path
      
      # Now we have set all the args back to someething GET understands
      self.do_GET()
      return
    
    # POST Upload
    elif ctype == 'multipart/form-data':
      query = parse_multipart(self.rfile, pdict)
      
      # Build up the args
      args = {}
      for key in query:
        args[key] = query[key][0]
      
      # Business as usual
      try:
        self.handle_everything(path, args)
      except Exception, e:
        text = GetExceptionDetails()
        log.critical(text)
        print text
      
      return
    else:
      #TODO(ghowland): Add error handling here
      log('Uncaught POST error', logging.CRITICAL)
      pass
  
  
  def handle_everything(self, path, args):
    # Get the cookies
    write_cookies = {}
    write_headers = {}
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
    
    log('Rendering request: %s %s %s %s' % (path, self.headers, cookies, args), logging.DEBUG)
    
    # Start the duration clock
    start_time = time.time()
    
    # Render the request 
    try:
      (output, content_type, response_code, redirect_url, write_cookies,
          write_headers) = self.RenderRequest(path, self.headers, cookies, args)
    
    # On render failures, report the error as best we can
    except Exception, e:
      details = error_info.GetExceptionDetails()
      log('%s' % details, logging.ERROR)
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
      log('Path: %s  Duration: %0.2fs' % (path, duration), logging.INFO)


  def RenderRequest(self, path, headers, cookies, args):
    # Initialize result data
    output = ''
    content_type = 'text/html'
    response_code = 200
    redirect_url = None
    write_cookies = {}
    write_headers = {}
    
    # Get the host and port (if specified)
    host = None
    port = None
    if 'host' in headers:
      if ':' in headers['host']:
        (host, port) = headers['host'].split(':', 1)
        port = int(port)
      else:
        host = headers['host']
    
    #print 'Headers: %s' % headers
    
    # If this is a static request
    if path.startswith('static/'):
      # Most of our static context are binary files
      file_flag = 'rb'
      
      # Set content type by extension
      #TODO(g): Do a statis content-type lookup
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
      STATIC_CONTENT_PATH = 'www/%s'
      full_path = STATIC_CONTENT_PATH % path
      
      # Set the cache control
      STATIC_CACHE_TIMEOUT = 3600 # Seconds
      write_headers['Cache-Control'] = 'max-age=%s, must-revalidate' % STATIC_CACHE_TIMEOUT
      
      # Get the data from this full path
      output = open(full_path, file_flag).read()
    
    # Else, this is dynamic content.  Get the page, render the view.
    else:
      # Get the site from the host/port
      site = process.GetSite(self.server.conf, host)
      page = process.GetPage(host, path, site, self.server.conf)
      log('Path: %s  Page: %s' % (path, page), logging.INFO)
      
      # If we have a page from this path
      #if page and page['view']:
      if page:
        # Get this page's view's render output
        #try:
        if 1:
          # Set up the initial data and state
          data = args
          #TODO(g): Add session information here.  We only need the
          #   admin_user.id and auth-cookie
          state = {'headers':dict(headers), 'cookies':dict(cookies), 'session':None,
                   'global':self.server.global_state}
          
          # Review the page's view (sub-views get rendered recursively)
          #TODO(g): SECURITY: Apply application level security for this site
          render_output = process.RenderPage(site, page, self.server.conf,
                                             self.server.apps, data,
                                             state)
          
          # Copy out the render data
          output = render_output.output
          
          # Replace the title with the page title, if it exists
          if page['title']:
            output = output.replace('%(page_title)s', page['title'])
          
          # Add in custom content-type, if specified
          if 'content-type' in page:
            content_type = page['content-type']
          
          # Write any cookies that are new, or changed
          #TODO(g): Delete cookies that are no longer present?
          for key in state['cookies']:
            if key not in cookies or state['cookies'][key] != cookies[key]:
              write_cookies[key] = state['cookies'][key]
          
          # Replace out unfilled in defaults
          output = output.replace('%(page_header)s', '')
          output = output.replace('%(page_body)s', '')
        
        #except process.RenderError, e:
        #  log(logging.ERROR, e.log)
        #  
        #  # Render View wraps any exceptions, so we get an output and code
        #  output = e.output
        #  response_code = e.response_code
        #
        #except Exception, e:
        #  msg = 'Render (path=%s) did not return a RenderError: %s' % (path, e)
        #  log(logging.CRITICAL, msg)
        #  output = 'Internal Error: %s' % msg
        #  response_code = 500
      
      # Else, we couldnt find this page, so report it
      else:
        output = 'Page not found: %s' % path
        response_code = 404
        log(output, logging.DEBUG)
    
    
    return (output, content_type, response_code, redirect_url, write_cookies,
            write_headers)
