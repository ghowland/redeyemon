#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License

"""
Site Control API: Site Control Master (Elections, Startup, Etc)
"""


import time
import os


# REM libraries
import site_control
import run_script
from rem_api import cloud as rem_ec2
from rem_util import *


def MasterElectionStartup(state=None):
  """This machine is now in the election process.  Looking for a working master,
  or if it's election delay time is up, attempting to become a master itself.
  """
  # Default time to delay for election self-promotion
  ELECTION_DELAY_DEFAULT = 60

  # Default time to sleep while rechecking on an election result
  ELECTION_LOOP_SLEEP_DEFAULT = 15

  log('Init with state: %s' % state)

  found_master = False

  # Try to get our local config
  local_config = site_control.LoadMachineConfigurationLocalCache()

  # If we dont have a cache image yet
  if not local_config:
    election_delay = ELECTION_DELAY_DEFAULT

  # Else, we have local config information, use those times
  else:
    election_delay = site_control.GetElectionDelayFromConfig(local_config)

  # Start the election
  election_start = time.time()

  # Loop until we find a master
  while not found_master:
    # Get the latest master_ip
    master_ip = GetSiteControlMasterIP(state=state)
    local_ip = rem_ec2.GetMachineInternalIp()

    # If we are now the master, initialize and break out
    if master_ip == local_ip:
      #NOTE(g): This takes care of configuring this machine, since it's special
      success = SiteControlMasterInitialize()
      if success:
        found_master = True
        break
      else:
        log('Failed to initialized ourselves, try everything again')
        
        # Time to wait to check again
        time.sleep(ELECTION_LOOP_SLEEP_DEFAULT)
        
        # Re-loop again
        continue
    
    # Test that we have a connection to the database.
    master_listens = query._PortListeningTest(master_ip)
    if master_listens:
      log('Found master database listening, trying to get site config...')
      # Get our reconfiguration data.
      #NOTE(g):This function is special in that it expects the master may
      #   not be there, because this is the most likely time to find that.
      config_data = GetConfigurationDataFromMaster()
    else:
      log('No master database listening...')
      config_data = None
    
    # If we couldnt get a good response from our listed SC Master
    if not config_data:
      # Duration since the election started
      duration = time.time() - election_start
      
      # If the duration is longer than our election delay
      if duration > election_delay:
        # We are now required to try to promote ourselves to be a master
        AttemptPromotionOfThisMachineToSiteControlMaster()
      else:
        log('Time until this machine makes a bid as the Master: %0.1f' % (election_delay - duration))
    
    # Else, we got back config data, we have a master!
    else:
      found_master = True
      
      # Configure this machine, it is now just a client
      site_control.ConfigureLocalMachine()
    
    # Time to wait to check again
    time.sleep(ELECTION_LOOP_SLEEP_DEFAULT)


def BuildSiteControlMasterDatabase(sql_file):
  # Ensure MySQL service has configured to start automatically
  run_script.Run('/sbin/chkconfig --levels 2345 mysqld on')

  # Start the MySQL service
  run_script.Run('/sbin/service mysqld start')
  #TODO(g): On our build, the first time I ran this it failed, the second
  #   time it worked.  Duplicating here, but this is not right so fix later.
  run_script.Run('/sbin/service mysqld start')

  # Create our MySQL database, after removing anything already there
  os.system('/bin/echo "DROP DATABASE site_control;" | /usr/bin/mysql')
  os.system('/bin/echo "CREATE DATABASE site_control;" | /usr/bin/mysql')

  # Import the SQL dump file into the site_control database
  os.system('/usr/bin/mysql site_control < %s' % sql_file)

  # Create permissions on our system: site_control user for site_control DB
  query.RunMysqlCommand("CREATE USER '%s'@'%%' IDENTIFIED BY '%s';" % (query.DATABASE_USER, query.DATABASE_PASSWORD))
  query.RunMysqlCommand("GRANT ALL PRIVILEGES ON site_control.* TO '%s'@'%%' WITH GRANT OPTION;" % (query.DATABASE_USER))
  query.RunMysqlCommand("CREATE USER '%s'@'localhost' IDENTIFIED BY '%s';" % (query.DATABASE_USER, query.DATABASE_PASSWORD))
  query.RunMysqlCommand("GRANT ALL PRIVILEGES ON site_control.* TO '%s'@'localhost' WITH GRANT OPTION;" % (query.DATABASE_USER))
  run_script.Run('/usr/bin/mysqladmin flush-privileges')

  # Check that it works
  try:
    log('Testing the database')
    result = Query('SELECT 1')
    if result:
      return True
    else:
      raise Exception('BuildSiteControlMasterDatabase failed: No result for SELECT 1.  Should always have a result.')
  except Exception, e:
    raise Exception('BuildSiteControlMasterDatabase failed: %s' % e)


def SiteControlMasterInitialize():
  """This machine is now the Site Control, and was not before.  Initialize."""
  log('Starting')
  config_data = site_control.LoadMachineConfigurationLocalCache()

  S3_SITE_CONTROL_DATABASE = 's3://%s/site_control.sql' % rem_ec2.S3_BUCKET

  # Get the control database from our config data, if we have it
  if config_data:
    s3_site_control_database = config_data['site_config']['s3_file_site_control_master']
  # Else, use the default
  #TODO(g): Is making this configurable worth it?  A good idea?  It's here for now...
  else:
    s3_site_control_database = S3_SITE_CONTROL_DATABASE

  log('Retrieving Site Control DB from S3: %s' % s3_site_control_database)

  # Get the control database SQL from S3
  site_control_database_sql = rem_ec2.S3Get(s3_site_control_database)

  log('Retrieved.  Saving.')

  # Write the control database SQL into a file, so it can be imported
  CONTROL_DATABASE_SQL_FILE = '/tmp/site_control.sql'
  open(CONTROL_DATABASE_SQL_FILE, 'w').write(site_control_database_sql)

  log('Building Site Control Master database.')

  # Build the Site Control Master Database
  BuildSiteControlMasterDatabase(CONTROL_DATABASE_SQL_FILE)

  log('Setting us to be the Master') #TODO(g): Redundant?  Check.

  # Set our IP as the master
  local_ip = rem_ec2.GetMachineInternalIp()
  SetMasterConfigField('ip', local_ip)

  log ('Initialization complete')

  # Start up the Master
  try:
    SiteControlMasterStartup()
  except Exception, e:
    #NOTE(g): Because we say we failed, we will try again.
    #TODO(g): Send alerts on critical errors
    log('Failed to Start the Site Control Master: %s' % e, logging.CRITICAL)
    return False
  
  # Site Control Master has been Initialized and Started
  return True


def SiteControlMasterStartup(state=None):
  """The Site Control master has extra responsibilities, and may need to bring
  up the entire REM realm."""
  #TODO(g): What site be set to?  site_control.SITE_DEFAULT seems too simplistic to be
  #   the best answer, can we know what site should run this beyond this?
  site = site_control.SITE_DEFAULT

  log('Starting as Master...  Site: %s' % site)

  # Ensure this machine is in the Site Control database, and listed as the
  #   Site Control Master and is in the Site Control Master pool (currently
  #   'Database')
  machine_id = site_control.GetThisMachineId()
  if machine_id == None:
    log('This machine does not exist, creating a new machine...')
    
    # Loop until we properly add our machine, so we start off properly
    #NOTE(g): EC2 sometimes fails to answer our ec2-describes-instances request,
    #   and if it happens here, the master fails and doesnt start, unless we
    #   handle it, so we are taking extra precautions to do so.
    machine_id = None
    while machine_id == None:
      machine_id = site_control.AddNewMachine_ThisOne(site=site)
      
      if not machine_id:
        EC2_GET_INSTANCE_FAILURE_DELAY = 5 # 5s delay to try EC2 again.
        log('EC2 failed to give us our instance info, sleeping %s seconds and trying again.' % EC2_GET_INSTANCE_FAILURE_DELAY)
        time.sleep(EC2_GET_INSTANCE_FAILURE_DELAY)
    
    # Add this machine to the Database pool, it is the master database
    sql = "INSERT INTO pool_machine (pool, machine) VALUES (5, %d)" % machine_id
    Query(sql)

  log('Machine ID: %s' % machine_id)
  # Save the machine.id, so we can access it later
  SetMasterConfigField('machine', machine_id)

  # Sets the site config: set the Site Control Master
  site_control.SetSiteConfigField(site, 'site_control_master', machine_id)

  # Configure this machine
  site_control.ConfigureLocalMachine()
  
  # Turning this machine to active
  site_control.SetMachineStatus(machine_id, 5)
  
  # Run provisioning here, just to do it?
  log('Provision machines...')
  site_control.ProvisionMachines()


  # Run enforcing EC2 floating IPs here, just to do it?  (After provisioning,
  #   well, we still may not have IPs, so only if we do)
  log('Provisioning Floating IPs...')
  site_control.ProvisionFloatingIps()

  # Allocates Requseted(1) machines (in the ProvisionMachines(), messed up wording)...
  log('Allocate provisioned machines...')
  site_control.AllocateMachines()

  log('Master Startup complete')



def SetMasterConfigField(name, value):
  """Sets a master config value.  Creates it if doesnt exist."""
  sql = "SELECT * FROM master_config WHERE name = '%s'" % name
  result = Query(sql)

  # If it already exists, update it
  if result:
    master_config = result[0]

    sql = "UPDATE master_config SET value = '%s', updated = NOW() WHERE id = %d" %\
          (SanitizeSQL(value), master_config['id'])
    Query(sql)

  # Else, its new, create it
  else:
    sql = "INSERT INTO master_config (name, value, updated) VALUES ('%s', '%s', NOW())" % \
          (SanitizeSQL(name), SanitizeSQL(value))
    Query(sql)


def GetMasterMachineId():
  """Returns the master's machine.id, or None if not found."""
  master_id = GetMasterConfig()['machine']
  
  if master_id != None:
    return int(master_id)
  else:
    return None


def GetMasterConfig():
  """Returns dict of all the master config fields."""
  data = {}

  sql = "SELECT * FROM master_config"
  result = Query(sql)

  # Save all our items by name
  for item in result:
    data[item['name']] = item['value']

  return data


def BackupSiteControlDatabaseToS3(site=site_control.SITE_DEFAULT):
  """Make a backup of the Site Control database into S3.  Returns boolean, success."""
  if not IsThisMachineSiteMaster():
    log('Cannot backup, this is not the Site Control Master machine.')
    return False
  
  site_config = site_control.GetSiteConfig(site=site)
  
  # Create our backup path for the Site Control DB
  backup_path = '%s/site_control.sql' % site_config['path_site_control']
  
  # Dump the MySQL database
  #TODO(g): Use MySQL security
  cmd = ('/usr/bin/mysqldump site_control > %s' % backup_path)
  run_script.Run(cmd)
  
  # Put our new backup in S3, straight from it's file
  rem_ec2.S3Put(site_config['s3_file_site_control_master'], None, backup_path)
  
  return True

def GetConfigurationDataFromMaster():
  """Returns the data necessary to configure this machine.

  This function assumes that the query may fail, because this is a startup
  related function, so the Site Master DB may not be available, and then
  None will be returns.

  Returns: dict with config elments if successful, None if failed
  """
  # Get our Master IP, important enough to get our data
  master_ip = rem_ec2.GetMasterIp(cache=False)
  
  #log('Get Config')
  #if 1:#DEBUG:REMOVE THIS AND PUT BACK THE EXCEPTION HANDLED!!! !!! !!! !!! !!! !!! !!! !!! !!! !!!
  try:
    #log('Get Machine')
    # Get machine info
    #log('Get machine ID')
    machine_id = site_control.GetThisMachineId()
    #log('Get machine data: %s' % machine_id)
    machine = site_control.GetMachine(machine_id)
    site = machine['site']

    #log('Got Machine: %s' % machine_id)
    
    # Create template to populate for config_data
    config_data = {
        'machine':{},
        'site':{},
        'pool':{},
        'service':{},
        'script':{},
        'site_config':{},
      }

    #log('Get Site')
    # Get the site data
    site_data = site_control.GetSiteById(machine['site'])
    config_data['site'] = site_data
    #log('Site data: %s' % site_data)

    #log('Get Pools')
    # Get all the pools
    pools = site_control.GetMachinePools(machine_id)
    #log('Machine pools: %s' % pools)
    for pool_id in pools:
      pool = site_control.GetPoolById(pool_id)

      config_data['pool'][pool['name']] = pool

    #log('Get Services')
    # Get all the services
    services = site_control.GetMachineServices(machine_id)
    #log('Services: %s' % services)
    for service_id in services:
      service = site_control.GetService(service_id)

      config_data['service'][service['name']] = service

    #log('Get Scripts')
    # Get all the script that could run on this machine
    scripts = site_control.GetMachineServiceScripts(machine_id)
    #log('Scripts: %s' % scripts)
    for script_id in scripts:
      script = site_control.GetScript(script_id)

      config_data['script'][script['name']] = script

    # Get this machine
    config_data['machine'] = machine

    # Get the site configuration fields
    config_data['site_config'] = site_control.GetSiteConfig(site=site)

    #log('Save local config')
    # Save config data to local machine cache YAML file
    site_control.SaveMachineConfigurationLocalCache(config_data)

  except Exception, e:
    log('Failed: %s' % e)

    # We failed, return None
    return None

  return config_data


#TODO(g): Do this better...
CACHE_SITE_AVAILABLE = False
CACHE_SITE_AVAILABLE_LAST_CHECKED = 0
def IsSiteControlAvailable():
  """Determine if we have access to Site Control now.

  We have to cache, or this will destroy the DB, its just calling GetConifg
  constantly.
  """
  global CACHE_SITE_AVAILABLE
  global CACHE_SITE_AVAILABLE_LAST_CHECKED

  # Time to cache this
  #TODO(g): This needs to be in Site Control config. later
  CACHE_TIME = 10

  # Cache timeout, pass last result
  if CACHE_SITE_AVAILABLE_LAST_CHECKED + CACHE_TIME > time.time():
    return CACHE_SITE_AVAILABLE

  #TODO(g): CRITICAL: Any caching here?  This will be called ALL the time,
  #   because its checked in with site_control.GetThisMachineId() calls, just to be sure.

  #TODO(g):OPTIMIZE:CRITICAL: This is very wasteful, its does a number of
  #   queries against the Site Control master.  Ignore for now.
  config_data = GetConfigurationDataFromMaster()

  # Cache this state, and the time we cached it, to protect from over calling
  CACHE_SITE_AVAILABLE = config_data
  CACHE_SITE_AVAILABLE_LAST_CHECKED = time.time()

  if config_data:
    log('Invoked: Available')
    site_control_available = True
  else:
    log('Invoked: Not Available')
    site_control_available = False

  return site_control_available


def GetSiteControlMasterIP(state=None):
  """Get the current Site Master IP from EC2.

  If state is present, it is updated.  This is the REM Client state.
  """
  # Get the master.ip, only called when Master Election/Startup is occuring
  master_ip = rem_ec2.GetMasterIp(cache=False)
  if state:
    state['site_control_master_ip'] = master_ip

  # Force on our query module this for all our SQL queries
  #NOTE(g): We have this because of "from util import *"
  query.DATABASE_HOST = master_ip

  # Get our own local IP to compare
  local_ip = rem_ec2.GetMachineInternalIp()
  if state:
    state['local_ip'] = local_ip

  # If this is the master
  if master_ip == local_ip:
    if state:
      state['is_site_control_master'] = True

  return master_ip


def AttemptPromotionOfThisMachineToSiteControlMaster():
  """Attempts to promote this machine to be the Site Control Master.

  The process works where once a machine is past it's election delay, it
  writes it's own IP into the s3://S3_BUCKET/master.ip file.  Then it
  continues as normal, if it finds it is the master, it then performs
  a SiteControlMasterStartup().
  """
  log('Self-promotion attempt')
  #TODO(g): Put this someplaces better.  Note not URL, path.
  S3_MASTER_IP = 's3://%s/master.ip' % rem_ec2.S3_BUCKET

  # Get the local IP
  local_ip = rem_ec2.GetMachineInternalIp()

  # Store it in
  rem_ec2.S3Put(S3_MASTER_IP, local_ip)


def IsThisMachineSiteMaster():
  """Returns boolean, if this machine is the Site Control master."""
  machine = site_control.GetMachine(site_control.GetThisMachineId())
  master_ip = rem_ec2.GetMasterIp()
  
  if machine['ip_internal'] == master_ip:
    return True
  else:
    return False



def GetElectionDelayFromConfig(config_data):
  """Returns int, number seconds until this machine starts self-promoting.

  Needs to check with all the pools associated with this machine, takes the
  lowest election_delay_item
  """
  lowest_election_delay = None

  for pool_key in config_data['pool']:
    pool = config_data['pool'][pool_key]

    # If we dont have an election delay value yet, set it
    if lowest_election_delay == None:
      lowest_election_delay = pool['election_delay_time']

    # Else, if this delay is lower, set it
    elif lowest_election_delay > pool['election_delay_time']:
      lowest_election_delay = pool['election_delay_time']

  return lowest_election_delay


