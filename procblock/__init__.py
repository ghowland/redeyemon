#!/usr/local/bin/python
"""
procblock

by Geoff Howland


procblock is a Data Based Logic Structure.

procblock intentionally blurs the line between data and code.  Use procblock
lightly for flow control, or heavily as the framework for your applications
and systems.  procblock includes many tools to decrease the amount of code
you need to write, by using powerful distributed system mechanisms to allow
a tiny bit of custom code to interact in a way normally reserved for
enterprise level applications.  Enterprise level applications, which already
handle distributed problems themselves, can use procblock as a way to create
lightweight interfaces with operating system oriented tasks, which change too
frequently to warrant re-designing the enterprise level application code base.

It is a not a programming language, though it could be useful to treat it that
way at times, as it is a software development tool.  procblock uses hierarchical
data structures (Python dictionaries and lists) to sturcture data which can be
processed through a series of rules and scripts.  A basic set of functions is
provided to conditionally return data, or run scripts, but from this much
richer functionality can be created by programmers using this structure to
create simpler custom logic to perform their specific intensions.

procblock is a Hardened Execution Environment.

It runs code with a common interface, and can run shell commands.  It can
run code in serial, simultaneously in threads, or caching while periodically
running in threads.  Many controls can be applied to running code and commands
due to procblock being dedicated to servicing logic, but only providing
minimal logic.

procblock intends to facilitate simpler programming and design,
and tries to provide structure which lends to simpler pieces of code being
connected together through procblock.

procblock was built to facilitate Pipe Oriented Design programming.

Unix shells have provided Pipe based programming for decades, and it's power
is undeniable in being able to stream output from one program as input to
another program.  Through a common interface, procblock executes scripts
and shell commands in a manner similar to pipes, but works with Python
dictionaries instead of character streams.

procblock provides Aspect Oriented Design.

Due to procblock's Pipe Oriented Design, Aspects are possible by inspecting
pipe data and modifying it, at any point in the pipeline.  By providing Flow
Blocks overrides, a programmer can add Aspect logic at any or every stage
of the execution pipeline.  This differentiates it from many frameworks which
require new code to fit into an existing object model.  Create your own object
model, procblock does not need to know or care.

procblock is Object Oriented Design agnostic.

It neither promotes or prevents working with Object Orientation, and so can
be used by heavy OO advocates, even though it is was not itself created with
a heavy OO orientation.

procblock provides long running and shared state.

Share state between sessions or over many executions of scripts, procblock
stays running and keeps a global state, which can be passed to different
scripts for sharing state, or providing input.  Use this for storing HTTP
session information, caching requests, resource locking or any other purpose.
State is a modified Python dictionary which provides thread safety on setting
keys for the top level of your state dictionary.  Optionally, all Python
dictionaries that procblock creates or converts are turned into thread safe
dictionaries.  (TODO(g): Add option to specify this.)

procblock is designed as a message and queueing system.

Any block tagged to be delivered to a previously registered listening block
will be delivered to a queue, which can be processed at the programmer's
leisure.  Many listeners can receive the same message, and code can be added
to remotely pass those messages to networked nodes which can procress the
block or result.  Shared state is useful for some activities, and message
passing is useful for a different set of activities, providing more coverage
between your simpler scripts and logic.

procblock can be used an a main() or library, or both.

Because procblock can run long running code or simultaneous threads, it can
be used as run control and glue for long running programs or daemons.  Because
procblock can be imported as a library and pass in any Python dictionary
format data, it can be used as a lightweight logic processer.

procblock is extendable.

Add your own Tag Functions, and any data you give that tag will be processed by
your Tag Function (just another block itself).

procblock can be a cross-language logic processor.

I'm not going to do it, but port the procblock engine to your favorite language.
Since procblock works on data primitives (Python dictionaries, lists and
strings), it is transferable to any other language which either has these
natively or uses libraries to acquire them.  Besides natively running Python
scripts, instead of your desired language, nothing about procblock is specific
to Python.  Your "scripts" may be Java classes you create instead of Python
modules with Execute() functions, but that is just the final implementation
step of procblock, not the core of what makes procblock useful.

procblock is a conditional data storage system.

When trying to retrieve data, where some data should be conditionally based
on a check against input or state information, procblock formatted data can be
used to reduce custom code and retrieve the conditional data.  Useful for
request configuration, where different configuration information will be
provided based on input state (like a HTTP Host Header returning a different
HTTP server configuration block).

procblock processes things recursively.

With the exception of some built-in (but overridable) functions, procblock
processes data blocks using other procblock formatted data blocks.  Even the
standard procblock Tag Functions are really just default Custom Tag Functions
that use the underlaying built-in functions, but process their tagged blocked
the same way you might create your own Tag Function.

You don't have to understand procblock to use procblock.

Grokking all the mechanisms of what makes procblock work, or how to overload it
and add your own Tag Functions is not necessary to use procblock effectively.
procblock is designed to be used by either careful construction of logic and
data flow, or casually placing data in a hierarchy and processing it to see
the result.  Both ways are effective, and while I don't encourage random
attempts to create solid logic, it can be useful to prototype and play with
an idea, and procblock tries to facilitate this easy and compact way to
hierarchically layer and play with the structure of both data and logic.


#TODO(g): Load ".procblock.yaml" for default procblock options.  Can easily
#   create development and production environments this way.  Cool.

#TODO(g): ALlow procblock to execute a procblock python file from the command
#   line the same way it would launch a YAML procblock.  This way there is
#   truly no difference between them.  Code or YAML is the same to procblock.
#     Benefits?
"""


import sys
import os


# NEW processing for blocks.
import processing

import procyaml

from main import mainfunctions

# Shared modules, we will access through procblock.NAME
from shared import messagequeue
from shared import sharedlock


def Main():
  # We may want to load this in the options...  But easy enough to do later
  #   and then just state.update() and done!
  request_state = {}
  pipe_data = {}

  if len(sys.argv) >= 2 and sys.argv[1] not in ('-h', '--help'):
    yaml_import = sys.argv[1]
  else:
    print 'error: no procblock YAML file was specified'
    print 'usage: %s <procblock.yaml> <options> <args>' % os.path.basename(sys.argv[0])
    sys.exit(1)
  
  # Load the block
  block = dict(procyaml.ImportYaml(yaml_import))
  
  # Process the options and arguments for this block
  try:
    # Collect our input data from options and arguments
    input_data = mainfunctions.ProcessOptionsAndArgs(block)
    
    # If the block had usage information, remove it as we have already used it
    if '__usage' in block:
      usage = block['__usage']
      del block['__usage']
    else:
      usage = None
    
    if input_data:
      pipe_data.update(input_data)
    
    #print 'Input Data: %s' % input_data
    #print 'Usage: %s' % usage
    
    # Print start up information
    output = mainfunctions.PrintStartup(block)
    print output
  
  # Failed, print usage for this block
  except mainfunctions.OptionsAndArgsFailure, e:
    output = mainfunctions.PrintUsage(block, error=e)
    print output
    sys.exit(1)
  
  
  # Process the block, and loop until all the threads close
  #TODO(g): Daemanize instead?  Usage specifies whether it's a daemon?
  mainfunctions.ProcessAndLoop(usage, block, input_data, request_state, pipe_data)


if __name__ == '__main__':
  Main()
