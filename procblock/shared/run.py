import subprocess
import logging

from log import log


def Run(command):
  """Actually run the command on the local machine.  Blocks until complete.
  """
  #global ENVIRONMENT
  
  output_error = '' #Later, how to handle reading the timing stream between the two?  It's lost...

  #log('Run: %s' % command)

  #TODO(g): Remove when subprocess method works
  #(status, output, output_error) = os.popen3(command)

  # Subprocess is beautiful and finally makes this a pleasant experience!
  #   Imagine, OUTPUT, ERRORS and EXIT CODE!!!  Not exclusively choosing two!
  #   Newbs be rejoice in your ignorance.
  pipe = subprocess.Popen(command, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, shell=True)
  status = pipe.wait()
  output = pipe.stdout.read()
  output_error = pipe.stderr.read()
  
  # Close the pipes
  pipe.stderr.close()
  pipe.stdout.close()

  if status != 0:
    log('Non-Zero Exit Code: %s: %s' % (status, command), logging.INFO)

  return (status, output, output_error)
  
