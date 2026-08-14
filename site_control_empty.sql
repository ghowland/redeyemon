/*
MySQL Data Transfer
Source Host: localhost
Source Database: sc
Target Host: localhost
Target Database: sc
Date: 1/13/2010 12:28:27 AM
*/

SET FOREIGN_KEY_CHECKS=0;
-- ----------------------------
-- Table structure for admin_user
-- ----------------------------
CREATE TABLE `admin_user` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `password_md5` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `name_full` varchar(255) NOT NULL,
  `email_alert` varchar(255) default NULL,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=4 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for cloud
-- ----------------------------
CREATE TABLE `cloud` (
  `id` int(11) NOT NULL auto_increment,
  `login` varchar(255) NOT NULL,
  `owner` varchar(255) NOT NULL COMMENT 'This is the EC2 owner # for this account.',
  `kind` int(11) NOT NULL default '1' COMMENT 'Default=EC2.  Make it easy for now.',
  PRIMARY KEY  (`id`),
  KEY `kind` (`kind`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for cloud_kind
-- ----------------------------
CREATE TABLE `cloud_kind` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `python_module` varchar(255) NOT NULL COMMENT 'This module wraps all the cloud functions together.  This makes adding a new cloud as easy as copying an existing python_module and changing all the function internals to use the other cloud''s API.',
  `info` text,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for db
-- ----------------------------
CREATE TABLE `db` (
  `id` int(11) NOT NULL auto_increment,
  `set` int(11) default NULL COMMENT 'This points to the db_set this is a part of.  All databases must be hosted in a set, so we know what data to track together.  This doesnt allow for unlimited flexibility, but its a good trade off in simplicity.',
  `name` varchar(255) NOT NULL,
  `kind` int(11) NOT NULL,
  `info` text,
  `replica_goal` int(11) NOT NULL default '1' COMMENT 'Number of replicas this database should have.  We assume 1, because we are enlightened about failover event delays.  Set manually, or can be scripted by config/monitor/trigger scripts that need a need for more or less replicas.  Hurray for dynamic sizing!',
  `storage_size_gb` int(11) default NULL COMMENT 'How many GB of space should be allocated for the backend storage.  Actual volume space requested by storage is up to the storage creation scripts which know about it''s redundancy requirements, but this much space should be usable by the database.',
  PRIMARY KEY  (`id`),
  KEY `set` (`set`),
  KEY `kind` (`kind`)
) ENGINE=MyISAM AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for db_backup
-- ----------------------------
CREATE TABLE `db_backup` (
  `id` int(11) NOT NULL auto_increment,
  `instance` int(11) NOT NULL,
  `machine` int(11) default NULL COMMENT 'Only the database write-master should do backups, but this lists which machine this was.  Cannot have a foreign key, we want to track this after a machine may have been terminated.',
  `created` datetime NOT NULL default '0000-00-00 00:00:00',
  `finished` datetime default NULL,
  `path` text NOT NULL,
  `relay_log` varchar(255) default NULL COMMENT 'Log currently being written on master.',
  `relay_position` int(11) default NULL COMMENT 'Position of relay log on master',
  PRIMARY KEY  (`id`),
  KEY `db` (`instance`),
  KEY `machine` (`machine`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for db_config
-- ----------------------------
CREATE TABLE `db_config` (
  `id` int(11) NOT NULL auto_increment,
  `db` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `value` text,
  `value_order` int(11) default NULL,
  `info` text,
  `updated` datetime default NULL,
  PRIMARY KEY  (`id`),
  KEY `db` (`db`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for db_function
-- ----------------------------
CREATE TABLE `db_function` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `info` text,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=9 DEFAULT CHARSET=latin1;

-- ----------------------------
-- Table structure for db_instance
-- ----------------------------
CREATE TABLE `db_instance` (
  `id` int(11) NOT NULL auto_increment,
  `db` int(11) NOT NULL,
  `machine` int(11) default NULL COMMENT 'NULL on insert, we get this provisioned and set later.',
  `kind` int(11) NOT NULL COMMENT 'References db_kind_instance_kind (not db_kind).  This holds all the scripts for THIS kind of the KIND of database.  2 layers deep.  We may be a RW MySql DB or a RO MySql DB, thats db_kind_instance_kind.',
  `status` int(11) NOT NULL default '1' COMMENT 'db_instance_status.id',
  `mount_storage` int(11) default NULL COMMENT 'Required, but not immediately.  This is the storage this DB resides on.',
  `mount_path` varchar(255) default NULL COMMENT 'Optional, but useful. If set, this is an additional path to use for data files on top of the local storage path.  Allows multiple databases to be stored on the same storage by putting their files in different paths.  If not set, 1 DB per storage.',
  `is_writable` int(1) NOT NULL default '0' COMMENT 'If 1, this is a write master database.  If shard_set=NULL, then this is the primary database.  If shard_set!=NULL this is the write-master for this shard_count, and will have replicas for this shard_count to slave to.  0 by default to be a little safer.',
  `shard_set` int(11) default NULL COMMENT 'If not NULL, then this db_instance is part of a shard set.  shard_count gives the bucket sequence number to use for sharding queries.',
  `shard_count` int(11) default NULL COMMENT 'Sequence order in the shard set.  This corresponds to it''s bucket system.',
  PRIMARY KEY  (`id`),
  KEY `db` (`db`),
  KEY `machine` (`machine`),
  KEY `kind` (`kind`),
  KEY `mount_storage` (`mount_storage`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for db_instance_status
-- ----------------------------
CREATE TABLE `db_instance_status` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `info` text,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=9 DEFAULT CHARSET=latin1;

-- ----------------------------
-- Table structure for db_kind
-- ----------------------------
CREATE TABLE `db_kind` (
  `id` int(11) NOT NULL auto_increment COMMENT 'For sites that use multiple databases in a single REM installer, instead of duplicating the Database service to customize each one, just use database_kind.script_* to automate specific databases.  Good for different  versions too.',
  `name` varchar(255) NOT NULL,
  `script_config` int(11) default NULL,
  `script_verify` int(11) default NULL,
  `script_monitor` int(11) default NULL,
  `script_repair` int(11) default NULL,
  `info` text,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for db_kind_function
-- ----------------------------
CREATE TABLE `db_kind_function` (
  `id` int(11) NOT NULL auto_increment,
  `kind` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `script` int(11) NOT NULL,
  `info` text,
  PRIMARY KEY  (`id`),
  KEY `script` (`script`),
  KEY `kind` (`kind`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for db_kind_instance_kind
-- ----------------------------
CREATE TABLE `db_kind_instance_kind` (
  `id` int(11) NOT NULL auto_increment COMMENT 'We are the KIND of database, not the database kind.  So this is differentating between a RW MySql DB and a RO MySql DB, not between a MySql and Oracle DB.',
  `kind` int(11) NOT NULL COMMENT 'db_kind, parent.',
  `name` varchar(255) NOT NULL,
  `storage_handler_stack` int(11) NOT NULL COMMENT 'References the storage_handler_stack that will manage this kind of database.  A RW database has different backup requirements than a RO, which may have no backup requirements.  Same with monitoring, RO are simply killed and rebuild, RW need to do DR.',
  `is_writable` int(1) NOT NULL COMMENT 'Is this DB Kind Instance Kind writable?  We know at a glance, this is a large differentiating factor between dealing with different database instance types.',
  `script_config` int(11) default NULL,
  `script_verify` int(11) default NULL,
  `script_monitor` int(11) default NULL,
  `script_repair` int(11) default NULL,
  `importance_count` int(11) default NULL COMMENT 'The order of importance for database kinds.  This allows us to list all databases in sequential orders of importance, so we know the most important and the least important db_instances.',
  `dns_format` varchar(255) default NULL COMMENT 'Databases need DNS reprensentation so they can be found consistently, this is the python string formatted value to create a database DNS name for the machine this database resides on.',
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

-- ----------------------------
-- Table structure for db_set
-- ----------------------------
CREATE TABLE `db_set` (
  `id` int(11) NOT NULL auto_increment COMMENT 'This is a group of databases that are controlled on the same service.',
  `name` varchar(255) NOT NULL,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for db_shard_instance
-- ----------------------------
CREATE TABLE `db_shard_instance` (
  `id` int(11) NOT NULL auto_increment,
  `shard` int(11) NOT NULL,
  `instance` int(11) NOT NULL,
  `count` int(11) NOT NULL COMMENT 'What shard # is this in the shard set?  Start counting at 0.',
  PRIMARY KEY  (`id`),
  KEY `shard` (`shard`),
  KEY `instance` (`instance`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

-- ----------------------------
-- Table structure for db_shard_set
-- ----------------------------
CREATE TABLE `db_shard_set` (
  `id` int(11) NOT NULL auto_increment,
  `duration_start_id` int(11) default NULL COMMENT 'Only one of these is filled out for each start/end, either the IDs or the Times, then the others are filled in once we know what the starting/ending time/id were, so we have an easy lookup for which shard duration to use.',
  `duration_start_time` datetime default NULL,
  `duration_end_id` int(11) default NULL COMMENT 'If end ID and end Time are NULL, then this duration will continue forever, or until manually capped.',
  `duration_end_time` datetime default NULL COMMENT 'If end ID and end Time are NULL, then this duration will continue forever, or until manually capped.',
  `shard_count` int(11) default NULL COMMENT 'Number of shards in this duration.',
  `shards_per_machine` int(11) default '1' COMMENT 'Number of shards per machine, by default each shard gets a machine (to spread out the load, as shards were designed).  However to grow actual machine usage slowly, higher numbers can be used.  0 means all shards are on 1 machine, the ultimate slow starter',
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

-- ----------------------------
-- Table structure for db_state
-- ----------------------------
CREATE TABLE `db_state` (
  `id` int(11) NOT NULL auto_increment,
  `db` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `value` text,
  `updated` datetime default NULL,
  `info` text,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for db_table_storage
-- ----------------------------
CREATE TABLE `db_table_storage` (
  `id` int(11) NOT NULL auto_increment,
  `db` int(11) NOT NULL COMMENT 'Parent database.',
  `size` int(11) NOT NULL,
  `script_config` int(11) NOT NULL COMMENT 'Script that configures the tables to sit on the storage.  This script will run often, the first time configuring, and later enforcing that it stays configured as specified.',
  `storage` int(11) NOT NULL COMMENT 'Storage that this attachs to.  All specifications of size are done through the database configuration, this is the reference pointer.',
  PRIMARY KEY  (`id`),
  KEY `script_config` (`script_config`),
  KEY `storage` (`storage`),
  KEY `db` (`db`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

-- ----------------------------
-- Table structure for floating_ip
-- ----------------------------
CREATE TABLE `floating_ip` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `kind` int(11) NOT NULL,
  `pool` int(11) NOT NULL,
  `dns_external` varchar(255) default NULL COMMENT 'Can be used to store the external DNS name associated with this Floating IP, for generation of external DNS.',
  `machine` int(11) default NULL COMMENT 'This will be set by the config or repair scripts, from the pool.',
  `ip_address` varchar(32) default NULL COMMENT 'The IP of the floating IP.  This can be used for external DNS.',
  `script_config` int(11) default NULL,
  `info` text,
  PRIMARY KEY  (`id`),
  KEY `pool` (`pool`),
  KEY `machine` (`machine`),
  KEY `script_config` (`script_config`),
  KEY `kind` (`kind`)
) ENGINE=MyISAM AUTO_INCREMENT=4 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for floating_ip_kind
-- ----------------------------
CREATE TABLE `floating_ip_kind` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `script_config` int(11) default NULL COMMENT 'This script sets up the floating IP to the correct internal machine.  This calls floating_ip.script_config to do fIP-specific assignment, this is for the service itself.  As does script_repair.',
  `script_verify` int(11) default NULL COMMENT 'This script verify the floating IP is working.  This could be conten checks from external network sources, or any number of things to verify this floating IP is working.  This is in effect an Edge test.',
  `script_monitor` int(11) default NULL COMMENT 'Monitor is like verify, but it runs all the time.  So verify can be super heavy handed, but monitoring should be lighter to be frequently repeated.',
  `script_repair` int(11) default NULL COMMENT 'If monitor fails, then repair is called.  Repair may just be the same as config, or it could be something unique.  If NULL, it calls config, but setting it gives alternatives, which may include doing some network tests to see why it may have happened.',
  `info` text,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for hardware_image
-- ----------------------------
CREATE TABLE `hardware_image` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `os` varchar(255) default NULL,
  `os_bit` int(11) default NULL,
  `keypair` varchar(255) default NULL,
  `info` text,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=7 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for hardware_image_package
-- ----------------------------
CREATE TABLE `hardware_image_package` (
  `id` int(11) NOT NULL auto_increment,
  `image` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `version` text,
  PRIMARY KEY  (`id`),
  KEY `image` (`image`)
) ENGINE=MyISAM AUTO_INCREMENT=15 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for hardware_kind
-- ----------------------------
CREATE TABLE `hardware_kind` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `info` text,
  `size_ram_gb` decimal(11,2) default NULL,
  `core` int(11) default NULL COMMENT 'Number of CPU cores (virtual)',
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=8 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for log_machine_error
-- ----------------------------
CREATE TABLE `log_machine_error` (
  `id` int(11) NOT NULL auto_increment COMMENT 'Unhandled errors need someone to pay attention to them, so they are logged here as a central source.  This also allows us to mark whether they have been processed (automatically or manually).',
  `machine` int(11) NOT NULL,
  `value` text NOT NULL,
  `occurred` datetime NOT NULL,
  `processed` int(1) NOT NULL default '0' COMMENT 'Stays 0 until it has been processed, lets us know we may need to alert or display it somewhere.',
  `processed_script_run_log` int(11) default NULL COMMENT 'If this item was processed by a script, the run log has an id that gose here, to link the script run to this error.',
  PRIMARY KEY  (`id`),
  KEY `machine` (`machine`),
  KEY `processed_script_run_log` (`processed_script_run_log`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for log_script_run
-- ----------------------------
CREATE TABLE `log_script_run` (
  `id` int(11) NOT NULL auto_increment COMMENT 'Number of seconds (4 places of precision) the script took to run.  Useful for timing things, and tracking processes that are taking longer or have eratic run times.',
  `script` int(11) NOT NULL,
  `machine` int(11) NOT NULL COMMENT 'This cannot have a foreign key, because this machine will go away, in which case the log should be deleted.',
  `run` datetime NOT NULL,
  `run_duration` decimal(11,4) default NULL,
  `service_script` int(11) default NULL COMMENT 'Optional.  Used for tracking when a service script has run on a given machine, or at all.',
  `output` text,
  `output_stderr` text,
  `exit_code` int(11) default NULL,
  `input` text COMMENT 'Args sent to command',
  PRIMARY KEY  (`id`),
  KEY `script` (`script`),
  KEY `machine` (`machine`),
  KEY `service_script` (`service_script`)
) ENGINE=MyISAM AUTO_INCREMENT=436086 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for log_site_control_admin
-- ----------------------------
CREATE TABLE `log_site_control_admin` (
  `id` int(11) NOT NULL auto_increment,
  `admin_user` int(11) NOT NULL,
  `updated` datetime NOT NULL,
  `target_table` varchar(255) NOT NULL,
  `target_field` varchar(255) NOT NULL,
  `target_id` int(11) NOT NULL,
  `data` text NOT NULL COMMENT 'JSON dict of changes',
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for machine
-- ----------------------------
CREATE TABLE `machine` (
  `id` int(11) NOT NULL auto_increment,
  `name` text NOT NULL,
  `site` int(11) NOT NULL,
  `site_data_center` int(11) NOT NULL COMMENT 'site_data_center, is used to refer to the actual machine_data_center, as the site may change it''s primary/secondary/etc, and this number refers to that order of primary/secondary DCs.',
  `hardware_kind` int(11) NOT NULL,
  `hardware_image` int(11) NOT NULL,
  `status` int(11) default NULL,
  `dns_internal` varchar(255) default NULL,
  `dns_public` varchar(255) NOT NULL,
  `dns_private` varchar(255) NOT NULL,
  `dns_external` varchar(255) default NULL,
  `time_launch` datetime default NULL,
  `time_reboot_last` int(11) default NULL,
  `ip_internal` varchar(50) default NULL,
  `ip_external` varchar(50) default NULL,
  PRIMARY KEY  (`id`),
  KEY `site` (`site`),
  KEY `site_data_center` (`site_data_center`),
  KEY `hardware_kind` (`hardware_kind`),
  KEY `hardware_image` (`hardware_image`),
  KEY `status` (`status`)
) ENGINE=MyISAM AUTO_INCREMENT=119 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for machine_data_center
-- ----------------------------
CREATE TABLE `machine_data_center` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=5 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for machine_rrd
-- ----------------------------
CREATE TABLE `machine_rrd` (
  `id` int(11) NOT NULL auto_increment,
  `machine` int(11) NOT NULL,
  `service` int(11) default NULL COMMENT 'If this is for a service, mark it.  Otherwise it''s a normal machine RRD.',
  `rrd` int(11) NOT NULL,
  `path` text COMMENT 'Relative Path on mounted EBS volume for writing RRD data',
  PRIMARY KEY  (`id`),
  KEY `machine` (`machine`),
  KEY `service` (`service`),
  KEY `rrd` (`rrd`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for machine_state
-- ----------------------------
CREATE TABLE `machine_state` (
  `id` int(11) NOT NULL auto_increment COMMENT 'Every machine can have it''s own state, though they will likely all have the same state vars, as the same scripts will run for Site Control to monitor them, but it''s not enforced.',
  `machine` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `value` text,
  `info` text,
  `updated` datetime default NULL COMMENT 'Last time this state was updated.',
  PRIMARY KEY  (`id`),
  KEY `machine` (`machine`)
) ENGINE=MyISAM AUTO_INCREMENT=27 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for machine_status
-- ----------------------------
CREATE TABLE `machine_status` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `info` text,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=8 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for machine_trigger
-- ----------------------------
CREATE TABLE `machine_trigger` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `script` int(11) NOT NULL,
  `info` text,
  `run_on_local_machine` int(1) NOT NULL default '1' COMMENT 'If 1, this trigger is run on the actual machine in question, not the monitoring machine.',
  PRIMARY KEY  (`id`),
  KEY `script` (`script`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for machine_trigger_instance
-- ----------------------------
CREATE TABLE `machine_trigger_instance` (
  `id` int(11) NOT NULL auto_increment,
  `machine` int(11) NOT NULL COMMENT 'Cannot have foreign key.  Needs to persist for troubleshooting if a machine is deleted.',
  `machine_trigger` int(11) NOT NULL,
  `active` int(1) NOT NULL default '0',
  `run_machine` int(11) default NULL,
  `run_thread_id` int(11) default NULL COMMENT 'This is the thread_id of the thread running on the run_machine',
  `run_start` datetime default NULL,
  `run_end` datetime default NULL,
  `input_data` text,
  `exit_code` int(11) default NULL,
  `output` text,
  `output_error` text,
  PRIMARY KEY  (`id`),
  KEY `machine` (`machine`),
  KEY `machine_trigger` (`machine_trigger`),
  KEY `run_machine` (`run_machine`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for master_config
-- ----------------------------
CREATE TABLE `master_config` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `value` text NOT NULL,
  `updated` datetime default NULL,
  `info` text,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for monitor_log
-- ----------------------------
CREATE TABLE `monitor_log` (
  `id` int(11) NOT NULL auto_increment,
  `machine` int(11) NOT NULL COMMENT 'Machine the monitoring command was run on.  Cannot have foreign key.  Needs to persist for troubleshooting if a machine is deleted.',
  `machine_target` int(11) default NULL COMMENT 'If not NULL, this is the machine the current machine was targetting in it''s monitoring.',
  `script` int(11) NOT NULL,
  `created` timestamp NOT NULL default '0000-00-00 00:00:00' on update CURRENT_TIMESTAMP,
  `data_json` text COMMENT 'JSON encoded data, which can be extracted and dealt with.',
  `processed` int(1) NOT NULL default '0',
  PRIMARY KEY  (`id`),
  KEY `machine` (`machine`),
  KEY `machine_target` (`machine_target`),
  KEY `script` (`script`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for pool
-- ----------------------------
CREATE TABLE `pool` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `site` int(11) NOT NULL COMMENT 'Site this pool belongs to.',
  `site_data_center` int(11) default NULL COMMENT 'Matche''s to the site''s data center order, so we can have primary(1) and secondary(2) data centers mapped out.',
  `parent_pool` int(11) default NULL COMMENT 'If not NULL, this pool uses another pool to provision machines, and just selects outo of those machines.  If NULL this pool provisions it''s own machines.',
  `hardware_kind` int(11) default NULL COMMENT 'Kind of hardware to use, uses: hardware_kind',
  `hardware_image` int(11) default NULL,
  `machine_goal` int(11) default NULL COMMENT 'Number of machines that should be in this pool.',
  `machine_total` int(11) default NULL COMMENT 'Number of machines that are in this pool.',
  `machine_active` int(11) default NULL,
  `machine_provisioned` int(11) default NULL COMMENT 'Only above 0 if this does not have a parent pool, so it provisions it''s own machines.',
  `db_set` int(11) default NULL COMMENT 'If this service deals with a set of databases, this points to them.',
  `storage_set` int(11) default NULL COMMENT 'Reference to storage_set, if not NULL then that storage_set''s configuration scripts control the pool.machine_goal.  Same with db_set.',
  `machine_name_format` varchar(255) default NULL,
  `election_delay_time` int(11) NOT NULL default '180' COMMENT 'Seconds to delay when lost connection with Site Control master until a machine in this pool decides to become the Site Control master by updating the S3 Master file with it''s own EC2 Internal DNS name',
  PRIMARY KEY  (`id`),
  KEY `site` (`site`),
  KEY `site_data_center` (`site_data_center`),
  KEY `parent_pool` (`parent_pool`),
  KEY `hardware_kind` (`hardware_kind`),
  KEY `db_set` (`db_set`)
) ENGINE=MyISAM AUTO_INCREMENT=13 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for pool_machine
-- ----------------------------
CREATE TABLE `pool_machine` (
  `id` int(11) NOT NULL auto_increment,
  `pool` int(11) NOT NULL,
  `machine` int(11) NOT NULL,
  `provisioned` int(1) default '1' COMMENT 'If this machine was provisioned, it is 1.  If 0, this machine is just a place holder for data about DNS or other Pool/Machine related issues, and should be deleted if a pool is not using parent_pool, as these tie other pool''s machines to this pool.',
  `dns_public` varchar(255) default NULL COMMENT 'For a given pool''s machine, it has a public DNS name.  Store it here, so a machine can be shown with all it''s DNS names.',
  PRIMARY KEY  (`id`),
  KEY `pool` (`pool`),
  KEY `machine` (`machine`)
) ENGINE=MyISAM AUTO_INCREMENT=151 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for pool_service
-- ----------------------------
CREATE TABLE `pool_service` (
  `id` int(11) NOT NULL auto_increment,
  `pool` int(11) NOT NULL,
  `service` int(11) NOT NULL,
  `info` text,
  `config_order` int(11) default NULL COMMENT 'If not NULL, this is the order of installation.  All NULL items are done last, and in random order.  Services with the same config_order will be done in random order.',
  PRIMARY KEY  (`id`),
  KEY `pool` (`pool`),
  KEY `service` (`service`)
) ENGINE=MyISAM AUTO_INCREMENT=33 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for pool_service_trigger_instance
-- ----------------------------
CREATE TABLE `pool_service_trigger_instance` (
  `id` int(11) NOT NULL auto_increment,
  `pool_service` int(11) NOT NULL,
  `service_trigger` int(11) NOT NULL,
  `active` int(1) NOT NULL,
  `run_machine` int(11) default NULL,
  `run_start` datetime default NULL,
  `input_data` text,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for rrd
-- ----------------------------
CREATE TABLE `rrd` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `script_collect` int(11) default NULL COMMENT 'Script to collect data on a local machine for this RRD.',
  `run_delay` int(11) NOT NULL default '60' COMMENT 'Run frequency.  How often does this RRD expect input?',
  `heart_beat` int(11) NOT NULL default '120' COMMENT 'Seconds for RRD heartbeat (starts inserting unknown data values)',
  `info` text,
  `format_path` varchar(255) default NULL,
  PRIMARY KEY  (`id`),
  KEY `script_collect` (`script_collect`)
) ENGINE=MyISAM AUTO_INCREMENT=7 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for rrd_field
-- ----------------------------
CREATE TABLE `rrd_field` (
  `id` int(11) NOT NULL auto_increment,
  `rrd` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `field_type` int(11) NOT NULL,
  `field_order` int(11) NOT NULL COMMENT 'All fields must be ordered, so that they are always saved and loaded in the proper order in the RRD file.  It is a column based database.',
  `label` varchar(255) default NULL COMMENT 'Label to use in graphing.',
  `value_min` int(11) default NULL COMMENT 'Minimum value.  If NULL then minimum is not specified.',
  `value_max` int(11) default NULL COMMENT 'Maximum value ammount.  If NULL, then "U" is used in RRD create.',
  `graph_order` int(11) default NULL COMMENT 'Order to graph this value in.',
  `graph_line_color` varchar(255) default NULL COMMENT '#00aa22 format color for graphing.',
  `graph_area_color` varchar(255) default NULL COMMENT '#00aa22 format color for graphing.',
  `format_value` varchar(255) default NULL COMMENT 'Python string formatting text for the value.',
  `format_comment` text,
  `info` text,
  PRIMARY KEY  (`id`),
  KEY `field_type` (`field_type`)
) ENGINE=MyISAM AUTO_INCREMENT=47 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for rrd_field_type
-- ----------------------------
CREATE TABLE `rrd_field_type` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `info` text,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for script
-- ----------------------------
CREATE TABLE `script` (
  `id` int(11) NOT NULL auto_increment COMMENT 'If true, this script is kept running on this machine, by monit, through monit config.',
  `name` varchar(255) NOT NULL,
  `info` text,
  `path_relative_script` text COMMENT 'Relative path to scripts, from site_config->path_script as the absolute path to start from.',
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=47 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for service
-- ----------------------------
CREATE TABLE `service` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `info` text,
  `init_service` varchar(255) default NULL COMMENT 'Using chkconfig, if you arent using an OS that uses chkconfig packages, do something else.',
  `script_monitor` int(11) default NULL,
  `script_config` int(11) default NULL,
  `script_config_verify` int(11) default NULL COMMENT 'Like monitor, but meant to only work on the config files.  Used to move a machine state from Verifying to Active.',
  PRIMARY KEY  (`id`),
  KEY `script_monitor` (`script_monitor`),
  KEY `script_config` (`script_config`),
  KEY `script_config_verify` (`script_config_verify`)
) ENGINE=MyISAM AUTO_INCREMENT=18 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for service_config
-- ----------------------------
CREATE TABLE `service_config` (
  `id` int(11) NOT NULL auto_increment,
  `service` int(11) NOT NULL,
  `name` varchar(255) NOT NULL COMMENT 'Field name for config value',
  `value` text COMMENT 'Int, float or text, they all go here and will have to be converted later, by those interested in this data.',
  `value_order` int(11) default NULL COMMENT 'Optional.  If set, this is the order this value comes in for this field.  This allows us to create lists for our config data.  All items with the same name, for the same service are returned in a list.  If order is not set, order is random.',
  `info` text,
  `updated` datetime default NULL COMMENT 'Time last updated.',
  PRIMARY KEY  (`id`),
  KEY `service` (`service`)
) ENGINE=MyISAM AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for service_required_service
-- ----------------------------
CREATE TABLE `service_required_service` (
  `id` int(11) NOT NULL auto_increment,
  `parent` int(11) NOT NULL,
  `service` int(11) NOT NULL,
  `info` text,
  PRIMARY KEY  (`id`),
  KEY `parent` (`parent`),
  KEY `service` (`service`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for service_rrd
-- ----------------------------
CREATE TABLE `service_rrd` (
  `id` int(11) NOT NULL auto_increment,
  `service` int(11) NOT NULL COMMENT 'Service that needs this RRD tracked, by machine running this service.',
  `rrd` int(11) NOT NULL COMMENT 'RRD to track on the machine running this service.',
  PRIMARY KEY  (`id`),
  KEY `rrd` (`rrd`),
  KEY `service` (`service`)
) ENGINE=MyISAM AUTO_INCREMENT=7 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for service_script
-- ----------------------------
CREATE TABLE `service_script` (
  `id` int(11) NOT NULL auto_increment COMMENT 'These are the scripts that run on a services machine.  Can run automatically every N seconds (run_delay), or on an event.',
  `service` int(11) NOT NULL,
  `script` int(11) NOT NULL,
  `run_on_all_machines` int(1) NOT NULL default '1' COMMENT 'If true, this script is run on all machines.  If not, it is only run on one machine in this time.  This allows a single script to run, or all machines to get this script to run.',
  `run_on_machine_status` int(11) default '5' COMMENT 'Default=Active.  Limits which machine.status a machine can be in to run this script.  Make it easy for the Script Runner to do it''s thing.',
  `info` text,
  `is_always_running` int(1) NOT NULL default '0' COMMENT 'If 1, then this script is enforced with monit to run all the time.',
  `run_delay` int(11) default NULL COMMENT 'Delay to run, in seconds.  If not NULL, this script is run every N seconds, respects other run limiters (day/week/month)',
  `run_time_of_day` time default NULL COMMENT 'If not NULL, this script is run only at this time of day.',
  `run_day_of_week` int(11) default NULL COMMENT 'If not NULL, this script is only run on this day of the week.  0=Sunday.',
  `run_day_of_month` int(11) default NULL COMMENT 'If not NULL, this script is only run on this day of the month.  Negative numbers count back from last day in the month.',
  `run_week_of_month` int(11) default NULL COMMENT 'If not NULL, this script is only run this week of the month.  Negative numbers counts back from last week in the month.',
  `freeze_exempt` int(1) NOT NULL default '0' COMMENT 'If 1, this service script will run even when the REM system is frozen.  This is needed for monitoring and other essential site actions the site must peform while REM maintenance is going on.',
  PRIMARY KEY  (`id`),
  KEY `service` (`service`),
  KEY `script` (`script`)
) ENGINE=MyISAM AUTO_INCREMENT=30 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for service_state
-- ----------------------------
CREATE TABLE `service_state` (
  `id` int(11) NOT NULL auto_increment,
  `service` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `value` text,
  `service_script_update` int(11) default NULL COMMENT 'If not NELL, when this item is updated, then this service script is invoked.',
  `info` text,
  `updated` datetime default NULL,
  PRIMARY KEY  (`id`),
  KEY `service` (`service`),
  KEY `service_script_update` (`service_script_update`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for service_trigger
-- ----------------------------
CREATE TABLE `service_trigger` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `script` int(11) NOT NULL COMMENT 'Pointer to script to be run if this trigger is enabled.',
  `info` text,
  PRIMARY KEY  (`id`),
  KEY `script` (`script`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for site
-- ----------------------------
CREATE TABLE `site` (
  `id` int(11) NOT NULL auto_increment,
  `zone` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `url` text,
  `url_admin` text,
  `url_login` text,
  PRIMARY KEY  (`id`),
  KEY `zone` (`zone`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for site_config
-- ----------------------------
CREATE TABLE `site_config` (
  `id` int(11) NOT NULL auto_increment,
  `site` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `value` text,
  `value_order` int(11) default NULL COMMENT 'Optional.  If set, this is the order this value comes in for this field.  This allows us to create lists for our config data.  All items with the same name, for the same site are returned in a list.  If order is not set, order is random.',
  `info` text,
  `updated` datetime default NULL COMMENT 'Time last updated.',
  PRIMARY KEY  (`id`),
  KEY `site` (`site`)
) ENGINE=MyISAM AUTO_INCREMENT=17 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for site_data_center
-- ----------------------------
CREATE TABLE `site_data_center` (
  `id` int(11) NOT NULL auto_increment,
  `site` int(11) NOT NULL,
  `cloud` int(11) NOT NULL default '1' COMMENT 'This allows us to have different site_data_centers in different clouds, which allows a load balancing between multiple ISPs.',
  `rank` int(11) NOT NULL,
  `machine_data_center` int(11) NOT NULL COMMENT 'machine_data_center to use, actual list of data centers, this is for site ranking for primary/secondary/etc',
  `info` text,
  PRIMARY KEY  (`id`),
  KEY `site` (`site`),
  KEY `machine_data_center` (`machine_data_center`),
  KEY `cloud` (`cloud`)
) ENGINE=MyISAM AUTO_INCREMENT=5 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for site_state
-- ----------------------------
CREATE TABLE `site_state` (
  `id` int(11) NOT NULL auto_increment,
  `site` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `value` text,
  `info` text,
  `updated` datetime default NULL,
  PRIMARY KEY  (`id`),
  KEY `site` (`site`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for site_trigger
-- ----------------------------
CREATE TABLE `site_trigger` (
  `id` int(11) NOT NULL auto_increment,
  `site` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `active` int(1) NOT NULL default '0',
  `script` int(11) default NULL COMMENT 'This should be set for something to automatically happen.  If it''s not set, this can be used as a boolean state.',
  `run_machine` int(11) default NULL,
  `run_start` datetime default NULL,
  PRIMARY KEY  (`id`),
  KEY `script` (`script`),
  KEY `run_machine` (`run_machine`),
  KEY `site` (`site`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for storage
-- ----------------------------
CREATE TABLE `storage` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `handler_stack` int(11) NOT NULL COMMENT 'This is the handler stack that takse care of each layer of volume management necessary to read and write to devices.  RAID, volume management, functions (snapshotting, freezing), all get thrown into the stack and the handlers automate creation, monitoring',
  `size_gb` decimal(10,2) NOT NULL COMMENT 'Total mount size of the system.  What happens in creating this in underlaying volumes depends on the storage_handler scripts that represent the storage_handler_stack.',
  `set` int(11) default NULL COMMENT 'If not NULL, this points to storage_set, which allows storage requirements to control pool provisioning sizes.  Set pool.storage_set to storage_set.id and the storage set''s machine requirements will control this pool.  Just like db (databases).',
  `mount_path` text COMMENT 'Local machine path to symlink to.  The actual device path is specified in storage_volume.machine_device',
  `mount_machine` int(11) default NULL,
  `status` int(11) NOT NULL default '1' COMMENT 'Status is managed by manage_storage.py script, which runs all the storage config, verification, monitor and repair scrpits, and these scripts actually set the status.  There is no way to know if a storage is Allocated unless the EBS handler tells us.',
  `status_is_processing` int(1) NOT NULL default '0' COMMENT 'If 1, this status is currently being processed and status related scripts should not be run.  When Active this is 0.  In between config/repair/whatever scripts status=0.  Status does not change on Functions, they do not relate to storage status by nature.',
  `storage_master` int(11) default NULL COMMENT 'If set, this is the master storage for this storage.  This allows storage to be set up in a master-slave system (like with DRBD), where each piece has a full set of volumes to make up a storage (with RAID or not), but the whole storage is linked.',
  `snapshot_delay` int(11) default NULL COMMENT 'Seconds between running snapshots',
  `backup_keep_count` int(11) NOT NULL default '8' COMMENT 'Number of backups to keep.  Culling of backups is left to the scripts that manage backups, and they may use a non-sequential culling technique to keep several recent backups and several older backups.',
  PRIMARY KEY  (`id`),
  KEY `handler_stack` (`handler_stack`),
  KEY `status` (`status`),
  KEY `storage_master` (`storage_master`),
  KEY `mount_machine` (`mount_machine`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for storage_backup
-- ----------------------------
CREATE TABLE `storage_backup` (
  `id` int(11) NOT NULL auto_increment,
  `storage` int(11) NOT NULL,
  `schedule` int(11) NOT NULL,
  PRIMARY KEY  (`id`),
  KEY `storage` (`storage`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

-- ----------------------------
-- Table structure for storage_backup_instance
-- ----------------------------
CREATE TABLE `storage_backup_instance` (
  `id` int(11) NOT NULL auto_increment,
  `backup` int(11) NOT NULL COMMENT 'Storage backup, parent.',
  `volume_snapshot` int(11) default NULL COMMENT 'One type of backup solution, the snapshot.  This points to storage_volume_snapshot for the actual data.  Repeat other types of backup in this fashion.',
  `volume_s3_file` text COMMENT 'If stored in S3, this is the full URL to the file that was stored.',
  `saved` datetime default NULL COMMENT 'When the backup was finally saved.  Everything is complete at this point.',
  `started` datetime default NULL COMMENT 'The time the backup was created.  NOW() on insert.',
  `started_save` datetime default NULL COMMENT 'Once we started the save process.  This lets us know how long it has been saving.  If there are other things to track, do them with this.',
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

-- ----------------------------
-- Table structure for storage_backup_schedule
-- ----------------------------
CREATE TABLE `storage_backup_schedule` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `info` text,
  `delay_minute` int(11) default NULL COMMENT 'Minutes to delay between backups.  Need second?  Add delay_second.  Need other stuff?  Add it.',
  `delay_script` int(11) default NULL COMMENT 'Run this script to determine when to run again.  The script returns 1 to run, and 0 to not run.  All logic and data aquisition and processing is wrapped by the script.',
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=latin1;

-- ----------------------------
-- Table structure for storage_config
-- ----------------------------
CREATE TABLE `storage_config` (
  `id` int(11) NOT NULL auto_increment,
  `storage` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `value` text,
  `value_order` int(11) default NULL,
  `info` text,
  `updated` datetime default NULL,
  PRIMARY KEY  (`id`),
  KEY `storage` (`storage`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for storage_function
-- ----------------------------
CREATE TABLE `storage_function` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `info` text,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=8 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for storage_handler
-- ----------------------------
CREATE TABLE `storage_handler` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `script_config` int(11) default NULL COMMENT 'Creates the storage, at this handler''s level.',
  `script_verify` int(11) default NULL,
  `script_monitor` int(11) default NULL,
  `script_repair` int(11) default NULL,
  `script_decommission` int(11) default NULL,
  `info` text,
  PRIMARY KEY  (`id`),
  KEY `script_config` (`script_config`),
  KEY `script_verify` (`script_verify`),
  KEY `script_monitor` (`script_monitor`),
  KEY `script_repair` (`script_repair`),
  KEY `script_decommission` (`script_decommission`)
) ENGINE=MyISAM AUTO_INCREMENT=6 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for storage_handler_function
-- ----------------------------
CREATE TABLE `storage_handler_function` (
  `id` int(11) NOT NULL auto_increment,
  `handler` int(11) NOT NULL,
  `function` int(11) NOT NULL,
  `script_enter` int(11) default NULL COMMENT 'Called when entering this function in this handler''s layer.  This sets things up, or does things.  After lower stacks have been called, then exit is called.  Example: Enter-> Freeze.  Exit -> Unfreez.',
  `script_exit` int(11) default NULL COMMENT 'Only needed if we need to un-do something we did in the script_enter.  Example:  Enter->Freeze.  Exit->Unfreeze.',
  `info` text,
  PRIMARY KEY  (`id`),
  KEY `handler` (`handler`),
  KEY `function` (`function`),
  KEY `script_enter` (`script_enter`),
  KEY `script_exit` (`script_exit`)
) ENGINE=MyISAM AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for storage_handler_stack
-- ----------------------------
CREATE TABLE `storage_handler_stack` (
  `id` int(11) NOT NULL auto_increment COMMENT 'The purpose of a storage_handler_stack is to be able to layer storage technology, as they start with device controllers, may have things that bind and replicate them, and finally have a file system which the OS interacts with.  The stack does each level.',
  `storage_handler` int(11) NOT NULL COMMENT 'The storage handler controlling this part of the stack.',
  `stack_parent` int(11) default NULL COMMENT 'If not NULL, this is the parent of this current stack position.  This is self-reflexive, pointing to storage_handler_stack, so that we can chain these items, with the order done by parent/child and the value being the storage_handler at this position.',
  `script_config_info` int(11) default NULL COMMENT 'This script gives configuration information for this Stack handler.  A Storage pointing to a stack ONLY uses the storage.handler_stack script_config_info, not up the chain.  It needs to know all for it''s parents.  Parents dont have to have their own scrpt',
  PRIMARY KEY  (`id`),
  KEY `storage_handler` (`storage_handler`),
  KEY `stack_parent` (`stack_parent`),
  KEY `script_config_info` (`script_config_info`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for storage_set
-- ----------------------------
CREATE TABLE `storage_set` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `info` text,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

-- ----------------------------
-- Table structure for storage_state
-- ----------------------------
CREATE TABLE `storage_state` (
  `id` int(11) NOT NULL auto_increment,
  `storage` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `value` text,
  `updated` datetime default NULL,
  `info` text,
  PRIMARY KEY  (`id`),
  KEY `storage` (`storage`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for storage_status
-- ----------------------------
CREATE TABLE `storage_status` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `info` text,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=10 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for storage_volume
-- ----------------------------
CREATE TABLE `storage_volume` (
  `id` int(11) NOT NULL auto_increment,
  `storage` int(11) NOT NULL,
  `storage_order` int(11) NOT NULL COMMENT '0 is the lowest order position.  Start counting there.',
  `zone` int(11) NOT NULL,
  `volume_id` varchar(255) NOT NULL,
  `size_gb` int(11) NOT NULL,
  `status` varchar(255) NOT NULL default '1' COMMENT 'Status is set by Amazon.  This just reflects latest status.',
  `machine` int(11) default NULL COMMENT 'When NULL, this volume is not assigned to a machine.  It will be picked up and assigned by the Storage Manager.',
  `machine_device` varchar(255) default NULL,
  PRIMARY KEY  (`id`),
  KEY `storage` (`storage`),
  KEY `zone` (`zone`),
  KEY `machine` (`machine`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for storage_volume_snapshot
-- ----------------------------
CREATE TABLE `storage_volume_snapshot` (
  `id` int(11) NOT NULL,
  `storage_volume` int(11) NOT NULL COMMENT 'Must delete the snapshots when removing a volume, we lose all history to it.  Otherwise create another status for volumes to be in where they arent mounted by snapshots remain...',
  `taken` datetime NOT NULL,
  `snapshot_id` varchar(255) NOT NULL,
  `status` varchar(255) default NULL,
  `progress` int(11) default NULL COMMENT 'Percent, 0 to 100.',
  `description` text,
  `started` text,
  PRIMARY KEY  (`id`),
  KEY `storage_volume` (`storage_volume`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for storage_volume_status
-- ----------------------------
CREATE TABLE `storage_volume_status` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `info` text,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=10 DEFAULT CHARSET=latin1;

-- ----------------------------
-- Table structure for terminated_machine
-- ----------------------------
CREATE TABLE `terminated_machine` (
  `id` int(11) NOT NULL auto_increment COMMENT 'This is used for old machines, so we can keep their logs and review after they were removed.  Logs dont use foreign keys to machine because of this.  Useful for debugging problems after machines have been removed from the system.',
  `machine` int(11) NOT NULL COMMENT 'No foreign key.  This is for dead and gone machines.  I dont want the machine table cluttered with them, and most of the issues surrounding live machines are irrelevant.  This isnt about tracking EC2 performance history, that can be done by monitoring.',
  `hardware_kind` int(11) NOT NULL COMMENT 'From this and the duration between launch and terminate, the total cost of this machine can be calculated.',
  `time_launch` datetime NOT NULL,
  `time_terminate` datetime NOT NULL,
  `reason` text,
  PRIMARY KEY  (`id`),
  KEY `hardware_kind` (`hardware_kind`)
) ENGINE=MyISAM AUTO_INCREMENT=106 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for zone
-- ----------------------------
CREATE TABLE `zone` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(255) NOT NULL,
  `info` text,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records 
-- ----------------------------
INSERT INTO `admin_user` VALUES ('1', 'geoff', '05f60ba25a20f67f442f4127e4d6c4dd', 'geoff@gmail.com', 'Geoff Howland', 'geoff@gmail.com');
INSERT INTO `admin_user` VALUES ('2', 'chris', '653a19d62c9c0be257d7eee56b225a00', 'chriss', 'Chris', 'chris');
INSERT INTO `admin_user` VALUES ('3', 'mkirk', '006e06c39f476eb21d9bf3c29800f224', 'mkirk@sonomait.com', 'Matt Kirk', 'mkirk@sonomait.com');
INSERT INTO `cloud` VALUES ('1', 'adgent007.ec2@sonomait.com', '', '1');
INSERT INTO `cloud_kind` VALUES ('1', 'Amazon EC2', 'rem_ec2', null);
INSERT INTO `db` VALUES ('1', '1', 'site_control', '2', 'Site Control (REM)', '1', null);
INSERT INTO `db` VALUES ('2', '1', 'rem_test', '1', 'REM Test Database', '1', null);
INSERT INTO `db_function` VALUES ('1', 'Create', 'For all.');
INSERT INTO `db_function` VALUES ('2', 'Backup', 'For masters.');
INSERT INTO `db_function` VALUES ('3', 'GetSecondsBehindMaster', 'For slaves.');
INSERT INTO `db_function` VALUES ('4', 'TestQuery', 'Gets success and time to complete.  (Need to specify tests)');
INSERT INTO `db_function` VALUES ('5', 'Start', 'Start the database.');
INSERT INTO `db_function` VALUES ('6', 'Shutdown', 'Stop the database.');
INSERT INTO `db_function` VALUES ('7', 'ReloadConfig', 'Reload configuration files.  (If available on this database)');
INSERT INTO `db_function` VALUES ('8', 'Restart', 'Stop and start the database.');
INSERT INTO `db_instance_status` VALUES ('1', 'Initialized', 'The database instance has been initialized, but without a machine allocation nothing further can happen.');
INSERT INTO `db_instance_status` VALUES ('2', 'Allocated', 'A machine exists for this database.  Now the storage and then database needs to be configured.');
INSERT INTO `db_instance_status` VALUES ('3', 'Configured Storage', 'Storage has been configured.  If it is a new instance, the device created is an empty file system for a DB to be created on it from a SQL dump in S3.  If it was an existing storage, the device was created from a backup(snapshot) and it populated with data.');
INSERT INTO `db_instance_status` VALUES ('4', 'Configuring', 'The database is currently being configured.  Leave it alone.');
INSERT INTO `db_instance_status` VALUES ('5', 'Configured', 'The database has been configured, so it\'s storage has been configured, and if new a new SQL database has been pulled from S3.');
INSERT INTO `db_instance_status` VALUES ('6', 'Verified', 'The database has been verified by basic queries, and custom scripts if available, and passes as a working database.');
INSERT INTO `db_instance_status` VALUES ('7', 'Active', 'The database is active.');
INSERT INTO `db_instance_status` VALUES ('8', 'Repairing', 'The database is being repaired.');
INSERT INTO `db_kind` VALUES ('1', 'MySQL 5: Replicated', null, null, null, null, 'Stores Master database on persistent storage, and slave databases on local storage.  New masters always recover from persistent storage spot.');
INSERT INTO `db_kind` VALUES ('2', 'MySQL 5: REM Site Control', null, null, null, null, 'REM does something special with it\'s database, storing it in S3 and restoring from that instead of storing on a peristent storage and trying to recover from that.');
INSERT INTO `db_kind_function` VALUES ('1', '1', 'Backup', '3', 'Backup the write-master database');
INSERT INTO `db_set` VALUES ('1', 'Site Control & Test Database');
INSERT INTO `floating_ip` VALUES ('2', 'Prod DNS', '1', '5', 'dns.redeyemon.org', '107', '75.101.134.192', '34', 'This is the internal DNS, prod.tweetedia.com.  Because of EC2 machines using DHCP I\'m choosing to just list prod.tweetedia.com in tweetedia.com\'s DNS server, pointing to this floating IP.  This short cuts figuring out the current systems DHCP override and the proper way to do it and still handle DC failures without having no access to any DNS at all (and thus not being able to reach S3 for election updates).');
INSERT INTO `floating_ip` VALUES ('3', 'Monitoring Graphs', '1', '10', 'monitor.redeyemon.com', null, '75.101.162.182', '44', 'This is the monitoring server, which serves HTTP for graph data.');
INSERT INTO `floating_ip_kind` VALUES ('1', 'Amazon Elastic IP', null, null, null, null, null);
INSERT INTO `hardware_image` VALUES ('1', 'ami-bea84ad7', 'CentOS', '32', 'webserver', null);
INSERT INTO `hardware_image` VALUES ('2', 'ami-0c5fbc65', 'CentOS', '64', 'webserver', '');
INSERT INTO `hardware_image` VALUES ('6', '1', null, null, null, 'Unknown.  Added by GetHardwareImageByName()');
INSERT INTO `hardware_image_package` VALUES ('1', '1', 'Nginx', null);
INSERT INTO `hardware_image_package` VALUES ('2', '1', 'HA Proxy', null);
INSERT INTO `hardware_image_package` VALUES ('3', '1', 'Postfix', null);
INSERT INTO `hardware_image_package` VALUES ('4', '1', 'DRDB', null);
INSERT INTO `hardware_image_package` VALUES ('5', '1', 'MySQL', null);
INSERT INTO `hardware_image_package` VALUES ('6', '1', 'Subversion', null);
INSERT INTO `hardware_image_package` VALUES ('7', '1', 'rrdtools', null);
INSERT INTO `hardware_image_package` VALUES ('8', '1', 'Python', null);
INSERT INTO `hardware_image_package` VALUES ('9', '1', 'PHP', null);
INSERT INTO `hardware_image_package` VALUES ('10', '1', 'Zend Foundation Library', null);
INSERT INTO `hardware_image_package` VALUES ('11', '1', 'bind', null);
INSERT INTO `hardware_image_package` VALUES ('12', '1', 'Java', null);
INSERT INTO `hardware_image_package` VALUES ('13', '1', 'Ruby', null);
INSERT INTO `hardware_image_package` VALUES ('14', '1', 'EC2 CLI Toolset', null);
INSERT INTO `hardware_kind` VALUES ('1', 'm1.small', '', '1.70', '1');
INSERT INTO `hardware_kind` VALUES ('2', 'm1.xlarge', '', '15.00', '4');
INSERT INTO `hardware_kind` VALUES ('3', 'm1.large', null, '7.50', '8');
INSERT INTO `hardware_kind` VALUES ('4', 'c1.medium', null, '1.70', '5');
INSERT INTO `hardware_kind` VALUES ('5', 'c1.xlarge', null, '7.00', '20');
INSERT INTO `hardware_kind` VALUES ('6', 'm2.2xlarge', null, '34.20', '13');
INSERT INTO `hardware_kind` VALUES ('7', 'm2.4xlarge', null, '68.40', '26');
INSERT INTO `machine_data_center` VALUES ('1', 'us-east-1d');
INSERT INTO `machine_data_center` VALUES ('2', 'us-east-1b');
INSERT INTO `machine_data_center` VALUES ('3', 'us-east-1a');
INSERT INTO `machine_data_center` VALUES ('4', 'us-east-1c');
INSERT INTO `machine_status` VALUES ('1', 'Requested', 'A Requested server does not have instance information, but has been saved as being requested. This way we know we already have made a request for a server, but it has not been delivered to us yet, and we dont have to make another request for it.');
INSERT INTO `machine_status` VALUES ('2', 'Allocated', 'An Allocated instance has been requested from the Amazon machine pool, and has been delivered, but has not been turned on to do its job yet. Final preparation (SVN up, copying recent files and configuration) has not been completed yet, so this machine is not yet serving requests.');
INSERT INTO `machine_status` VALUES ('3', 'Installed', 'An Installing instance has it\'s installation started, so is no longer just allocated, but not ready for active duty yet.');
INSERT INTO `machine_status` VALUES ('4', 'Verified', 'After Installing or Paused, a machine must go through Verifying before it can be active.  Failure to verify leads to decommissioning.');
INSERT INTO `machine_status` VALUES ('5', 'Active', 'An Active instance has been configured and is ready to server requests. This will be the normal operational state for our machines. As long as the instance is needed and is operating properly it will stay in the Active state.');
INSERT INTO `machine_status` VALUES ('6', 'Paused', 'A Paused instance has been Active, but is temporarily not serving requests. This state is used when determining if this machine is fit to be Active (if errors have been detected) or in transition to Decommissioned while we get any data we want off the machine.');
INSERT INTO `machine_status` VALUES ('7', 'Decommissioning', 'A Decommissioned instance is set to be removed from our pool. At this point we no longer care about any data on this instance and we are just waiting for it to be removed by AmazonÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢s instance system. This happens very quickly, so they wont stick around long.');
INSERT INTO `machine_trigger` VALUES ('1', 'config_reload', '4', 'Reloads all the configuration and service startup information for this machine.', '1');
INSERT INTO `pool` VALUES ('2', 'Http', '1', '1', null, '4', '1', '2', '2', '0', '2', null, null, 'http%02d', '120');
INSERT INTO `pool` VALUES ('4', 'App', '1', '1', '2', '4', '1', '2', '0', '0', '0', null, null, 'app%02d', '120');
INSERT INTO `pool` VALUES ('5', 'Database', '1', '1', null, '4', '1', '2', '2', '1', '1', '1', null, 'database%02d', '60');
INSERT INTO `pool` VALUES ('6', 'Database: DR', '1', '2', null, '4', '1', '1', '1', '0', '1', '1', null, 'databasedr%02d', '180');
INSERT INTO `pool` VALUES ('10', 'Monitoring', '1', '1', '7', '4', '1', '1', '0', '0', '0', null, null, 'monitor%02d', '120');
INSERT INTO `pool` VALUES ('11', 'Unmanaged', '1', '1', null, '4', '1', '1', '1', '0', '1', null, null, 'unmanaged%02d', '9999999');
INSERT INTO `pool_service` VALUES ('1', '1', '1', 'Edge: HA Proxy load balances the traffic to HTTP', null);
INSERT INTO `pool_service` VALUES ('2', '5', '10', 'Database: Bind handles Internal DNS.  The write-master is always the Internal DNS master as well, so it has all the information it needs for other machines, and just by knowing their internal DNS master they also have the Site Control master DB.  Can get this in S3.', null);
INSERT INTO `pool_service` VALUES ('3', '2', '2', 'Http: Apache handles static content requests and requests Proxy for dynamic requests', null);
INSERT INTO `pool_service` VALUES ('4', '3', '1', 'Proxy: HA Proxy load balances the traffic to the App Listeners', null);
INSERT INTO `pool_service` VALUES ('5', '4', '3', 'App: Application handles dynamic requests', null);
INSERT INTO `pool_service` VALUES ('6', '5', '4', 'Database: MySQL handles SQL queries', null);
INSERT INTO `pool_service` VALUES ('7', '5', '11', 'Database: DRDB keeps data in sync', null);
INSERT INTO `pool_service` VALUES ('8', '5', '7', 'Database: Monitor of last resort', null);
INSERT INTO `pool_service` VALUES ('9', '7', '11', 'Storage: DRDB keeps data in sync', null);
INSERT INTO `pool_service` VALUES ('12', '10', '5', 'Monitor: Data Collector, stores into RRD and DB state.  Runs scripts to process/act on RRD/state', null);
INSERT INTO `pool_service` VALUES ('13', '10', '16', 'Monitor: Nginx serves graph images', null);
INSERT INTO `pool_service` VALUES ('18', '1', '13', 'Edge: Site Control client', null);
INSERT INTO `pool_service` VALUES ('19', '2', '13', 'Http: Site Control client', null);
INSERT INTO `pool_service` VALUES ('20', '3', '13', 'Proxy: Site Control client', null);
INSERT INTO `pool_service` VALUES ('21', '4', '13', 'App: Site Control client', null);
INSERT INTO `pool_service` VALUES ('22', '5', '13', 'Database: Site Control client', null);
INSERT INTO `pool_service` VALUES ('23', '6', '13', 'Database-DR: Site Control client', null);
INSERT INTO `pool_service` VALUES ('24', '6', '4', 'Database-DR: MySQL keeps in sync with non-DR write-master', null);
INSERT INTO `pool_service` VALUES ('25', '6', '7', 'Database-DR: Monitor of last resort', null);
INSERT INTO `pool_service` VALUES ('29', '10', '13', 'Monitor: REM Site Control client', null);
INSERT INTO `pool_service` VALUES ('30', '5', '15', 'Database: REM Site Control Master.  Authoritative source for all site information.  Should be the same pool that runs Internal DNS.', null);
INSERT INTO `pool_service` VALUES ('32', '10', '17', 'Monitor: Syslog Daemon', null);
INSERT INTO `rrd` VALUES ('1', 'CPU', '16', '60', '120', 'CPU usage stats', '%(host)s_cpu');
INSERT INTO `rrd` VALUES ('2', 'Network', '17', '60', '120', 'Network interface stats', '%(host)s_network');
INSERT INTO `rrd` VALUES ('3', 'Disk Space', '18', '60', '120', 'Disk space available/used/total', '%(host)s_diskspace');
INSERT INTO `rrd` VALUES ('4', 'Disk Inodes', '19', '60', '120', 'Disk inodes available/used/total', '%(host)s_diskinode');
INSERT INTO `rrd` VALUES ('5', 'Disk IO', '20', '60', '120', 'Disk IO activity stats', '%(host)s_diskio');
INSERT INTO `rrd` VALUES ('6', 'VM', '21', '60', '120', 'VM usage stats (pages in/out, system cpu ticks, etc)', '%(host)s_vm');
INSERT INTO `rrd_field` VALUES ('1', '1', 'user', '1', '1', 'User', '0', '100', '1', null, null, '%0.1f', null, null);
INSERT INTO `rrd_field` VALUES ('2', '1', 'system', '1', '2', 'System', '0', '100', '2', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('3', '1', 'idle', '1', '3', 'Idle', '0', '100', '3', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('4', '1', 'wait', '1', '4', 'Wait', '0', '100', '4', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('5', '1', 'irq', '1', '5', 'Hard IRQ', '0', '100', null, null, null, null, null, 'Dont graph');
INSERT INTO `rrd_field` VALUES ('6', '1', 'soft', '1', '6', 'Soft IRQ', '0', '100', null, null, null, null, null, 'Dont graph');
INSERT INTO `rrd_field` VALUES ('7', '1', 'interrupt', '1', '6', 'Interrupt', '0', '100', null, null, null, null, null, 'Dont graph');
INSERT INTO `rrd_field` VALUES ('8', '2', 'rx_packet', '2', '1', 'RX Packets', '0', null, '1', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('9', '2', 'tx_packet', '2', '2', 'TX Packets', '0', null, '2', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('10', '2', 'rx_byte', '2', '3', 'RX Bytes', '0', null, '3', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('11', '2', 'tx_byte', '2', '4', 'TX Bytes', '0', null, '4', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('12', '3', 'total', '1', '1', 'Total', '0', null, '1', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('13', '3', 'used', '1', '2', 'Used', '0', null, '2', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('14', '3', 'available', '1', '3', 'Available', '0', null, '3', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('15', '3', 'percent_used', '1', '4', 'Percent Used', '0', '100', '4', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('16', '4', 'total', '1', '1', 'Total', '0', null, '1', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('17', '4', 'used', '1', '2', 'Used', '0', null, '2', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('18', '4', 'available', '1', '3', 'Available', '0', null, '3', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('19', '4', 'percent_used', '1', '4', 'Percent Used', '0', null, '4', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('20', '5', 'tps', '1', '1', 'Transfers/sec', '0', null, '1', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('21', '5', 'kb_read_per_sec', '1', '2', 'Read KB/sec', '0', null, '2', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('22', '5', 'kb_write_per_sec', '1', '3', 'Write KB/sec', '0', null, '3', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('23', '5', 'kb_read', '1', '4', 'Read KB', '0', null, '4', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('24', '5', 'kb_write', '1', '5', 'Write KB', '0', null, '5', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('25', '6', 'memory_total', '1', '1', 'Total Memory', '0', null, '1', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('26', '6', 'memory_used', '1', '2', 'Used Memory', '0', null, '2', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('27', '6', 'memory_active', '1', '3', 'Active Memory', '0', null, '3', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('28', '6', 'memory_inactive', '1', '4', 'Inactive Memory', '0', null, '4', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('29', '6', 'memory_free', '1', '5', 'Free Memory', '0', null, '5', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('30', '6', 'memory_buffer', '1', '6', 'Buffer Memory', '0', null, '6', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('31', '6', 'swap_cache', '1', '7', 'Swap Cache', '0', null, '7', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('32', '6', 'swap_total', '1', '8', 'Total Swap', '0', null, '8', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('33', '6', 'swap_used', '1', '9', 'Swap Used', '0', null, '9', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('34', '6', 'swap_free', '1', '10', 'Swap Free', '0', null, '10', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('35', '6', 'cpu_ticks_non_nice', '2', '11', 'CPU ticks: non-nice', '0', null, '11', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('36', '6', 'cpu_ticks_nice', '2', '12', 'CPU ticks: nice', '0', null, '12', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('37', '6', 'cpu_ticks_system', '2', '13', 'CPU ticks: system', '0', null, '13', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('38', '6', 'cpu_ticks_idle', '2', '14', 'CPU ticks: idle', '0', null, '14', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('39', '6', 'cpu_ticks_io_wait', '2', '15', 'CPU ticks: IO wait', '0', null, '15', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('40', '6', 'cpu_ticks_irq', '2', '16', 'CPU ticks: IRQ', '0', null, '16', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('41', '6', 'cpu_ticks_soft_irq', '2', '17', 'CPU ticks: Soft IRQ', '0', null, '17', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('42', '6', 'cpu_ticks_stolen', '2', '18', 'CPU ticks: Stolen', '0', null, '18', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('43', '6', 'pages_paged_in', '2', '19', 'Pages: Paged In', '0', null, '19', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('44', '6', 'pages_paged_out', '2', '20', 'Pages: Paged Out', '0', null, '20', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('45', '6', 'pages_swapped_in', '2', '21', 'Pages: Swapped In', '0', null, '21', null, null, null, null, null);
INSERT INTO `rrd_field` VALUES ('46', '6', 'pages_swapped_out', '2', '22', 'Pages: Swapped Out', '0', null, '22', null, null, null, null, null);
INSERT INTO `rrd_field_type` VALUES ('1', 'GAUGE', 'Used when it is a number that goes up an down, like a percent of CPU utilization');
INSERT INTO `rrd_field_type` VALUES ('2', 'COUNTER', 'Used when it is a number that increments, such as the number of packets received on a network interface.');
INSERT INTO `script` VALUES ('4', 'Site: Configure Machine from Site Control', 'Client script that configures this machine from site control.  Also ensures startup services are correct.', 'machine/machine_config.py');
INSERT INTO `script` VALUES ('7', 'Mon Server: Collect RRD data', 'Runs on the Monitoring machine (only monitor.tweetedia.com monitors), long running process that collects data.', 'rem/start_rem_poller');
INSERT INTO `script` VALUES ('22', 'Site: Verify Machine\'s service are working', 'Verify ports are listening, processes are running, command output matches expected results.', 'machine/machine_verify.py');
INSERT INTO `script` VALUES ('23', 'Site: REM Client', 'Local client that every machine in a REM realm runs to communicate with Site Control, which is what manages the realm.', '../rem_client.py');
INSERT INTO `script` VALUES ('24', 'Config: Internal DNS', null, 'config/config_dns.py');
INSERT INTO `script` VALUES ('25', 'Config: DRDB', null, 'config/config_drdb.py');
INSERT INTO `script` VALUES ('26', 'Config: HA Proxy', null, 'config/config_haproxy.py');
INSERT INTO `script` VALUES ('27', 'Config: Monit', null, 'config/config_monit.py');
INSERT INTO `script` VALUES ('28', 'Config: MySQL', null, 'config/config_mysql.py');
INSERT INTO `script` VALUES ('29', 'Config: Apache', null, 'config/config_apache.py');
INSERT INTO `script` VALUES ('30', 'Config: Machine', 'Not a service.  This sets up machine oriented things, that have to do with the site.', 'config/config_machine.py');
INSERT INTO `script` VALUES ('31', 'Site: Provision Machines', 'Provision EC2 instances, and decommission them.', 'provision/provision_machines.py');
INSERT INTO `script` VALUES ('32', 'Site: Provision Floating IPs', 'Provision EC2 floating IPs, so that they outside world connects to the correct machines.', 'provision/provision_floating_ips.py');
INSERT INTO `script` VALUES ('33', 'Site: Configure Floating IP: Edge', 'Determine Edge floating IP. (DISCONTINUED)', 'determine/determine_floating_ip_edge.py');
INSERT INTO `script` VALUES ('34', 'Site: Configure Floating IP: Internal DNS', 'Determine DNS floating IP.', 'determine/determine_floating_ip_dns.py');
INSERT INTO `script` VALUES ('35', 'Site: Allocate Machines', 'After Provisioning(2), we still dont have machine information.  This script acquires the data from EC2 and saves in machine, then promotes to Installing(3)', 'machine/machine_allocate.py');
INSERT INTO `script` VALUES ('36', 'Site: Activate Verified Machine', 'Activate machines that are verified.', 'machine/machine_activate.py');
INSERT INTO `script` VALUES ('37', 'Site: Site Control Configuration has changed', 'Deal with the changes in the Site Control database.  Back it up, and trigger machines to reload their configurations.', 'rem/rem_site_control_changed.py');
INSERT INTO `script` VALUES ('38', 'Site: Backup Site Control Database in S3', 'Script for backing up the Site Control database into S3', 'rem/rem_sitemaster_database_backup_into_s3.py');
INSERT INTO `script` VALUES ('39', 'Mon: RRD: Graph', 'Graph all the RRDs, and create HTML pages for them', 'rrd/rrd_grapher.py');
INSERT INTO `script` VALUES ('40', 'Storage: Handler: Config: EBS', 'Configure EBS volumes for Storages', 'config/config_storage_ebs.py');
INSERT INTO `script` VALUES ('41', 'Config: Nginx', null, 'config/config_nginx.py');
INSERT INTO `script` VALUES ('42', 'Site: Decomission Machines', 'Decomissions machines that have been terminated, shut down, or are missing from our our instances.', 'machine/machine_decommission.py');
INSERT INTO `script` VALUES ('43', 'Config: Jobs', 'Start Gearmand on job server', 'config/config_gearmand.py');
INSERT INTO `script` VALUES ('44', 'Site: Configure Floating IP: Monitoring Graphs', 'Determine Monitor floating IP.', 'determine/determine_floating_ip_monitor.py');
INSERT INTO `script` VALUES ('45', 'Config: Worker', 'Start enginectl script.  Grabs site code from S3 and configures the server.', 'config/config_enginectl.py');
INSERT INTO `script` VALUES ('46', 'Config: Elastic Load Balancer', 'Ensure all the HTTP machines are in the Load Balancer \'web\', if active.', 'config/config_elb.py');
INSERT INTO `service` VALUES ('1', 'HA Proxy', null, 'haproxy', null, '26', null);
INSERT INTO `service` VALUES ('2', 'Apache', null, 'httpd', null, '29', null);
INSERT INTO `service` VALUES ('3', 'App Listener', null, null, null, null, null);
INSERT INTO `service` VALUES ('4', 'Database', null, 'mysqld', null, '28', null);
INSERT INTO `service` VALUES ('5', 'Monitor Server', null, null, null, null, null);
INSERT INTO `service` VALUES ('6', 'Monitor Client', 'Same thing as Site Control client?  Sub-set?  Remove?', null, null, null, null);
INSERT INTO `service` VALUES ('7', 'Monitor: Last Resort', 'This will only handle provisioning for Disaster Recovery efforts.', null, null, null, null);
INSERT INTO `service` VALUES ('10', 'DNS: Internal', 'Internal DNS (Bind)', 'named', null, '24', null);
INSERT INTO `service` VALUES ('11', 'DRDB', 'Network disk redundancy', null, null, '25', null);
INSERT INTO `service` VALUES ('13', 'Site Control Client', 'Site Control owns this client, it reconfigures itself and runs cron.', null, null, '30', null);
INSERT INTO `service` VALUES ('14', 'EBS Management', 'EBS can be handled as a service, and just use the API calls, no reason to make integrated code for it.', null, null, null, null);
INSERT INTO `service` VALUES ('15', 'Site Control Master', 'Site Control Master controls everything.  Runs on MySQL and needs slaves, so good to paid with a MySQL Database pool.', null, null, null, null);
INSERT INTO `service` VALUES ('16', 'Nginx for Graphs', null, 'nginx', null, '41', null);
INSERT INTO `service` VALUES ('17', 'Syslog Server', null, 'syslogd', null, null, null);
INSERT INTO `service_config` VALUES ('1', '1', 'file_config', '/etc/haproxy/haproxy.cfg', null, 'Config file', null);
INSERT INTO `service_config` VALUES ('2', '4', 'db_set', '1', null, 'This is the Database Set to manage with this service.  All databases in the db_set will be brough up on each machine in this pool, with a write-master.  A secondary data center will be used as the Disaster Recovery machine for this service.', null);
INSERT INTO `service_required_service` VALUES ('1', '11', '14', 'DRDB is meant to keep two EBS volumes in sync.  If a pool is using DRDB, they need the EBS management service as well.');
INSERT INTO `service_rrd` VALUES ('1', '13', '1');
INSERT INTO `service_rrd` VALUES ('2', '13', '2');
INSERT INTO `service_rrd` VALUES ('3', '13', '3');
INSERT INTO `service_rrd` VALUES ('4', '13', '4');
INSERT INTO `service_rrd` VALUES ('5', '13', '5');
INSERT INTO `service_rrd` VALUES ('6', '13', '6');
INSERT INTO `service_script` VALUES ('3', '5', '7', '1', '5', 'Monitor: Ensure REM Poller is started.  REM Poller collects RRD data from REM listeners on all REM machines', '0', '60', null, null, null, null, '0');
INSERT INTO `service_script` VALUES ('6', '13', '4', '1', '5', 'SiteControl: Configure machine state.  Config files, and service startup.  Do nothing if already configured properly.', '0', '300', null, null, null, null, '0');
INSERT INTO `service_script` VALUES ('13', '1', '13', '1', '5', 'HA Proxy: Collect stats', '0', '60', null, null, null, null, '0');
INSERT INTO `service_script` VALUES ('16', '5', '15', '1', '5', 'Database: Collects MySQL stats', '0', '60', null, null, null, null, '0');
INSERT INTO `service_script` VALUES ('17', '13', '4', '1', '2', 'SiteControl: Configure services on a freshly provisioned machine.', '0', '60', null, null, null, null, '0');
INSERT INTO `service_script` VALUES ('18', '13', '23', '1', null, 'SiteControl: REM Client.', '1', null, null, null, null, null, '0');
INSERT INTO `service_script` VALUES ('19', '15', '31', '1', '5', 'SiteControl Master: Provision Machines', '0', '60', null, null, null, null, '0');
INSERT INTO `service_script` VALUES ('20', '15', '32', '1', '5', 'SiteControl Master: Provision Floating IPs', '0', '120', null, null, null, null, '0');
INSERT INTO `service_script` VALUES ('21', '15', '35', '1', '5', 'SiteControl Master: Allocate(2) Machines that have been Requested(1).  Allows them to be Installed(3)', '0', '30', null, null, null, null, '0');
INSERT INTO `service_script` VALUES ('22', '13', '22', '1', '3', 'SiteControl: Verify services are configured correctly.', '0', '30', null, null, null, null, '0');
INSERT INTO `service_script` VALUES ('23', '13', '36', '1', '4', 'SiteControl: Activate a machine that has passed verification.  Final stage to deny Activation, when this machine is LIVE.', '0', '30', null, null, null, null, '0');
INSERT INTO `service_script` VALUES ('24', '15', '38', '1', '5', 'SiteControl Master: Backup Site Control Master database into S3', '0', '600', null, null, null, null, '0');
INSERT INTO `service_script` VALUES ('25', '5', '39', '0', '5', 'Monitor: Graph the RRD files', '0', '120', null, null, null, null, '0');
INSERT INTO `service_script` VALUES ('26', '15', '42', '1', '5', 'SiteControl Master: Decomission Terminated/Missing machines', '0', '30', null, null, null, null, '0');
INSERT INTO `service_script` VALUES ('29', '15', '46', '1', '5', 'SiteControl Master: Elastic Load Balancer Addresses', '0', '90', null, null, null, null, '0');
INSERT INTO `site` VALUES ('1', '1', 'Red Eye Mon Test', 'www.redeyemon.org', 'www.redeyemon.org', 'www.redeyemon.org');
INSERT INTO `site_config` VALUES ('1', '1', 'path_script', '/usr/local/site_control/rem/rem_scripts', null, 'Absolute path where our scripts are kept', null);
INSERT INTO `site_config` VALUES ('2', '1', 'port_rpc', '3737', null, 'Port to connect/bind for our XML-RPC listener', null);
INSERT INTO `site_config` VALUES ('3', '1', 'run_delay_script_runner', '5', null, 'Seconds delay between our cron checking for service scripts to run', null);
INSERT INTO `site_config` VALUES ('4', '1', 'dns_site_control_format', 'sitecontrol%02d', null, 'The DNS format for the sitecontrol system.  This is the most important domain name of all, and ', null);
INSERT INTO `site_config` VALUES ('5', '1', 'script_disaster_recovery', '/root/scripts/rem_disaster_recovery.sh', null, 'Absolute path to REM Disaster Recovery script, that all machine\'s Script Runner processes will invoke if they lose access to Site Control', null);
INSERT INTO `site_config` VALUES ('6', '1', 'run_delay_machine_reconfigure', '300', null, 'Seconds delay between when machines will regularly reconfigure their site info', null);
INSERT INTO `site_config` VALUES ('7', '1', 'script_run_delay_default', '60', null, 'Seconds in run delay for scripts without it specified (cant run them constantly)', null);
INSERT INTO `site_config` VALUES ('8', '1', 's3_file_site_control_master', 's3://site_control/site_control.sql', null, 'This duplicates the hard coded version of this file in all REM Clients, which check this S3 file as soon as they start up to configure their internal DNS and find the Site Control master.', null);
INSERT INTO `site_config` VALUES ('9', '1', 's3_file_data_center_heartbeat', 's3://site_control/heartbeat/datacenter_%d', null, 'Format for the file name for a given data centers heartbeat.  The Site Control master in this data center will write it\'s time.time() every s3_data_center_heartbeat_delay seconds.  This way we can see if a DC has dropped off or if there is a network partition.', null);
INSERT INTO `site_config` VALUES ('10', '1', 's3_data_center_heartbeat_delay', '60', null, 'Delay to write heart beats for data center.', null);
INSERT INTO `site_config` VALUES ('11', '1', 'domain_internal', 'www.redeyemon.org', null, 'Internal DNS domain, for all our machine service names.', null);
INSERT INTO `site_config` VALUES ('12', '1', 'site_control_master', '107', null, 'machine.id for the site control master.  This is who is authoritative for site data, and pulls the puppet strings.', '2009-11-21 06:06:11');
INSERT INTO `site_config` VALUES ('13', '1', 'ec2_security_key', 'redeyemon', null, 'Security Key for EC2', null);
INSERT INTO `site_config` VALUES ('14', '1', 's3_file_rem_files', 's3://site_control/rem.tar.gz', null, null, null);
INSERT INTO `site_config` VALUES ('15', '1', 'site_freeze', '0', null, 'If 1, the REM site is \"frozen\", so it will not provision machines, or update configurations.  Only service_scripts that have freeze_exempt=1 will still run, so required scripts will keep the site running while REM maintenance is going on.', null);
INSERT INTO `site_config` VALUES ('16', '1', 'path_site_control', '/usr/local/site_control', null, 'Path to put Site Control related files.  REM is stored here, we put rem.log and the local YAML configuration cache here, and backup our Site Control database here.', null);
INSERT INTO `site_data_center` VALUES ('1', '1', '1', '1', '3', 'Primary data center');
INSERT INTO `site_data_center` VALUES ('2', '1', '1', '2', '2', 'Failover data center');
INSERT INTO `site_data_center` VALUES ('3', '1', '1', '3', '1', 'Last resort...');
INSERT INTO `site_data_center` VALUES ('4', '1', '1', '4', '4', 'Last resort...');
INSERT INTO `site_trigger` VALUES ('1', '1', 'config_changed', '0', null, null, null);
INSERT INTO `storage_backup_schedule` VALUES ('1', 'Hourly', null, '60', null);
INSERT INTO `storage_function` VALUES ('1', 'Snapshot', 'Take a snapshot of this storage\'s volumes.');
INSERT INTO `storage_function` VALUES ('2', 'Freeze', 'Freeze the storage.  If successful, no reads or writes will complete on the file system until Unfreeze is invoked.');
INSERT INTO `storage_function` VALUES ('3', 'Unfreeze', 'Unfreeze the storage.  Allows reads and writes to continue.');
INSERT INTO `storage_function` VALUES ('4', 'TestReadWrite', 'Test that read and write operations work on this storage.');
INSERT INTO `storage_function` VALUES ('5', 'TestKnownDataExists', 'Test that known good data exists (requires specification of known good data).');
INSERT INTO `storage_function` VALUES ('6', 'Create', 'Create storage.');
INSERT INTO `storage_function` VALUES ('7', 'Assign', 'Assign storage to a machine.');
INSERT INTO `storage_handler` VALUES ('1', 'Elastic Block Storage (EBS)', '40', null, null, null, null, 'Persistent SAN-ish storage');
INSERT INTO `storage_handler` VALUES ('2', 'Local file storage', null, null, null, null, null, 'Storage on the local file system');
INSERT INTO `storage_handler` VALUES ('3', 'Linux Volume Manager', null, null, null, null, null, 'Allows freezing, so snapshots can occur without chance of data loss, and all pending requests will wait with no configuration.  Snapshots should happen quickly enough EBS to make this a powerful combination.');
INSERT INTO `storage_handler` VALUES ('4', 'DRBD', null, null, null, null, null, 'Device mirroring.  Active/Passive RAID-1 mirroring between 2 machines.  Very useful for making sure an EBS volume will not go bad on us.  Current design is the Primary is the Main Site Master, and the Secondary is the Failover Site Disaster Recovery machine.');
INSERT INTO `storage_handler` VALUES ('5', 'ext3', null, null, null, null, null, 'ext3 File System.  Final handler.');
INSERT INTO `storage_handler_function` VALUES ('1', '1', '1', null, null, 'Snapshot: EBS calls the S3 snapshot');
INSERT INTO `storage_handler_function` VALUES ('2', '3', '1', null, null, 'Snapshot: LVM Freezes/Unfreezes the volume to make the snapshot safe and stall any device requests.');
INSERT INTO `storage_status` VALUES ('1', 'Initialized', 'The storage information has been initialized, but not requested.');
INSERT INTO `storage_status` VALUES ('2', 'Requested', 'We have requested this storage from the storage provider.');
INSERT INTO `storage_status` VALUES ('3', 'Assigned', 'We have assigned our storage to a machine.');
INSERT INTO `storage_status` VALUES ('4', 'Re-Assigning', 'This storage is currently being re-assigned to another machine.');
INSERT INTO `storage_volume_status` VALUES ('1', 'Initialized', 'Initial request for this storage volume.');
INSERT INTO `storage_volume_status` VALUES ('2', 'Requested', 'The volume has been requested from the cloud volume provider.');
INSERT INTO `storage_volume_status` VALUES ('3', 'Assigned', 'The volume has been mounted on it\'s target machine.');
INSERT INTO `storage_volume_status` VALUES ('4', 'Configured', 'The volume has been configured with any other volumes, as well as had any data previously on it restored.  All of this is wrapped in configuration.');
INSERT INTO `storage_volume_status` VALUES ('5', 'Verified', 'The volume integrity has been verified.');
INSERT INTO `storage_volume_status` VALUES ('6', 'Active', 'The volume is active.');
INSERT INTO `storage_volume_status` VALUES ('7', 'Repairing', 'The volume is in repair mode.');
INSERT INTO `storage_volume_status` VALUES ('8', 'Decommissioned', 'The volume has been decomissioned, and will be removed from the system.');
INSERT INTO `storage_volume_status` VALUES ('9', 'Paused', 'The volume has been paused.  Likely because another volume in it\'s set is in repair mode.');
INSERT INTO `zone` VALUES ('1', 'Everything', 'Everything goes in one zone.  We have a way to totally segment data with this.  Leaving so that this is understood.');
