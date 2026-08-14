"""
cpu monitor

"""

def ProcessBlock(pipe_data, block, request_state, input_data, tag=None, cwd=None, env=None, block_parent=None):
  data = {'cpu':5}
  
  pipe_data.update(data)
  
  print 'CPU!!!!!!!!!!!!!  CPU!'
  
  return data

