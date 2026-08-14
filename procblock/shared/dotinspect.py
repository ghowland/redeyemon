"""
dotinspect

by Geoff Howland  <geoff AT ge01f DOT com>

dotinspect is a method of working with containers (dicts and sequences).

Format:  "var1.-1.(var2a.var2b).var3"

Explanation: Each dot represents an inspection of the current data.  The
first inspection would inspect the keyword "var1" in a dict.  The second
inspection would inspect the last item of a sequence.  The third inspection
is a sub-inspection.  It will first look into the value of it's sub-inspection
by evaluating all the terms in the parenthesis as if they were a new request.
These would then return a value, which would be used as the term to look into
the current container.  The final inspection is yet another term specified
for a dictionary lookup after the sub-inspection created a dynamic lookup.

This is useful for allowing user-specified content, and expanding data-oriented
development methods by making the processing of data generic, and leaving
the specifics to a data-based specification that will be processed or
interpretted into the specific result desired.

The attempt is to push more towards "real code" being very general in nature.
It processes a formatted statement.  Then the statements contain the actual
goal the user is aiming for.  This allows the "real code" to be hardended
significantly from when it is implementing the goals directly, as human goals
change frequently, and often require numerous levels of special cases to meet
our demanding needs.  By creating generalized processors at higher and higher
levels we can use hardened and battle-tested "real code", which can validate
and specify to greater precision the problems with the "goal directions",
because the rules of processing are known and operating at a directed level,
instead of "real code"'s totally general level, which could create anything.

This also allows for pipelining in other important processes, like regressive
testing, monitoring and request authentication, which are all universal issues
and have to be solved in every "real code" goal solution.  With generalized
processors, these issues only have to be solved once, for the generalized
processor, and then all "goal directions" (chunks of information), will
be processed by the general processors and get all the common functionality
for "free".

TODO(g): Test with sets.
"""


class NoValue(Exception):
  """No value was found."""


class EmptyContainer(Exception):
  """The container was empty."""


class NoValueMissingParents(Exception):
  """No value was found, because parents of the desired inspection pount were missing."""


def GetInspectTerms(inspect):
  """Returns a list of inspection terms.
  
  A term is typically a string or a number, but could also be a sub-inspection
  term: "var.(subvar)".  In this case the sub-inspection term is returned
  between the parenthesis.
  """
  # Break into terms
  terms = []
  
  subterms_rough = str(inspect).split('(')
  
  # If we have any sub-terms, find their ends
  for item in subterms_rough:
    # If we have a sub-term (there should only be one, but Im not checking)
    if ')' in item:
      # Break off the sub-term and redefine the item to be processed as the rest
      (subterm, item) = item.split(')', 1)
      
      # Add the subterm, wrapped in parens so we know it's a subinspect
      subinspect = '(%s)' % subterm
      terms.append(subinspect)
    
    # Skip empties
    if not item:
      continue
    
    parts = item.split('.')
    for part in parts:
      if part != '':
        terms.append(part)
  
  return terms


def CreateInspect(terms):
  """Create a term sequence.  Returns string:  var1.-1.var2"""
  # Ensure all the values are strings, so we can join them
  #TODO(g): Anything more clever here?  Per-type?
  for count in range(0, len(terms)):
    terms[count] = str(terms[count])
  
  # Join them, naively
  inspect = '.'.join(terms)
  
  return inspect


def CreateSubInspect(terms):
  subinspect = '(%s)' % CreateInspect(terms)
  
  return subinspect


def IsSubInspect(term):
  """If this term is actually a sub-insection phrase."""
  if term.startswith('('):
    return True
  else:
    return False


def SubInspect(subinspect, data):
  """Perform a sub-inspection of the data."""
  # Strip off the parens
  inspect = subinspect[1:-1]
  
  #print 'SubInspect: %s -> %s' % (subinspect, inspect)
  
  # Inspect and return
  return Inspect(inspect, data)


def Inspect(inspect, data, subinspect_data=None, _current_data=None):
  """Process the dotinspect notation from inspect, using the data as the target.
  
  Args:
    inspect: string, the formatted dotted inspection string
    data: container, dict or sequence
    subinspect_data: container [optional], if there is a sub-inspection, use
        this other data for that.  Allows some flexibility for crossing
        data sources, but rigid in only allowing one.  That is enough for this
        solution set, more would complicate things too much to keep it easy.
    _current_data: [internal use, private], container of current place in
        processing the inspection.
  """
  print 'Inspect: %s' % inspect
  
  # Inspect is always a string
  inspect = str(inspect)
  
  # If this is is a fully quoted value, then do not look it up, just return
  #   the quoted data as a string.
  # This is the only way to specify a pure value, without inspecting the data
  #TODO(g): This is a naive approach, but really, we dont allow double quotes
  #   in our keys or numbers, do we?
  if inspect.startswith('"') and inspect.endswith('"'):
    # Return a string, without the quotes.  Do NO testing of values
    return inspect[1:-1]
  
  # If no current data was passed in, then use the original data
  #   We use the _current_data for inspection, and the data for sub-inspection.
  if _current_data == None:
    _current_data = data
  
  # Get the terms for this inspection
  terms = GetInspectTerms(inspect)
  
  # Process the first term only, then recurse, after rebuilding the terms
  term = terms[0]
  
  #print 'Inspect: Term: %s' % term
  
  # If this is a sub-inspection phrase, then process it first
  if IsSubInspect(term):
    # If we are using special sub-inspection data, use that for this term value
    if subinspect_data:
      term_value = SubInspect(term, subinspect_data)
    # Else, use the normal data set for our sub-inspection for this term value
    else:
      term_value = SubInspect(term, data)
    
    #print 'SubInspect term: %s: %s' % (term, term_value)
  
  # Else, the value for the term is just the term itself, no sub-inspection
  #   to change the value
  else:
    term_value = term
  
  # Try to convert to numberic value
  try:
    term_value = int(term_value)
  except ValueError, e:
    try:
      term_value = float(term_value)
    except ValueError, e:
      term_value = str(term_value)
  
  # Get the term, or find out it's failed
  try:
    value = _current_data[term_value]
  except Exception, e:
    print e
    print 'Inspect: ERROR: Term not found: %s (%s): %s (%s)' % (term_value, type(term_value), _current_data, type(_current_data))
    
    # Is this the final term we were looking for?
    if len(terms) == 1:
      return NoValue
    
    else:
      return NoValueMissingParents
  
  
  # Are there more terms?
  if len(terms) > 1:
    # Then process the rest of the terms, and get the result
    recursive_inspect = CreateInspect(terms[1:])
    
    # Inspect our remaining terms, and return the final result
    result = Inspect(recursive_inspect, data,
                     _current_data=_current_data[term_value])
    
    return result
  
  # Else, this is the last term, so result the result
  else:
    result = _current_data[term_value]
    
    #print 'Inspect: RESULT: %s' % result
    return result


def Get(inspect, data):
  """Calls Inspect().  This function is sugar."""
  return Inspect(inspect, data)
  

#TODO(g): Other ways to work with data and dotinspect...
def __Pop(inspect, data, subinspect_data=None):
  """TODO(g): Pop an entry off the list specified by the inspect phrase."""
def __Pull(inspect, data, subinspect_data=None):
  """TODO(g): Pop an entry off the list specified by the inspect phrase."""
def __Push(inspect, data, subinspect_data=None):
  """TODO(g): Pop an entry off the list specified by the inspect phrase."""
def __Dequeue(inspect, data, subinspect_data=None):
  """TODO(g): Pop an entry off the list specified by the inspect phrase."""
  __Pull(inspect, data, subinspect_data=subinspect_data)
def __Set(inspect, data, subinspect_data=None):
  """TODO(g): Pop an entry off the list specified by the inspect phrase."""
def __Exists(inspect, data, subinspect_data=None):
  """TODO(g): NoValue, not allowed, specifically."""
def __ExistsAll(inspect, data, subinspect_data=None):
  """TODO(g): NoValueMissingParents, not allowed, specifically."""


  

  
if __name__ == '__main__':
  # Main test
  if 1:
    terms1 = ['tennis', -1]
    subinspect = CreateSubInspect(terms1)
    print subinspect
    terms2 = ['bagau', subinspect, 0]
    inspect = CreateInspect(terms2)
    print inspect
    
    get_terms = GetInspectTerms(inspect)
    print get_terms
    
    if 1:
      data = {}
      data['bagau'] = [[888, 111], [999, '000']]
      data['tennis'] = [0, 3, 2, 1]
      
      result = Inspect(inspect, data)
      
      print result
  
  
  # Simple value test (numbers and strings)
  if 1:
    # First element
    print Inspect(0, [500,400,300])
    
    # First element
    print Inspect('0', [500,400,300])
    
    # The string: '0'
    print Inspect('"0"', [500,400,300])
