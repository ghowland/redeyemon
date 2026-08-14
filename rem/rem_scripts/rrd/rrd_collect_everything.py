#!/usr/bin/python

#Author: Geoff Howland
#Project: Red Eye Monitoring (REM)   http://redeyemon.sourceforge.net/
#Licensed under the MIT License:     http://en.wikipedia.org/wiki/MIT_License


"""
RRD: Collect Everything from the local system

This are the commands that are run to collect information about this machine
for RRD storage and graphing.

CollectEverything() is the command that returns a dict of all our data.

If you want to add more things to collect, just add a function, putting any
command line scripts up top, and adding a function to call and parse the CLI
and finally add an entry to CollectEverything() that calls your function and
puts it in the return dict.

Make sure things are XML-RPC compliant, so use primitives: ints, floats,
    strings, dicts and lists.

Convert numbers to their primitives before passing, so the data at the other
end is immediately usable.  Likely its just going back into RRD as a string, but
in case someone wants to code against this data, make it valuable without
processing.

NOTE(g): The reason I didn't use SNMP for this, is that all the SNMP MIBs I
found dont really have the data formatted the way I like.  Specifically, the
CPU usage % shows up very low because it doesnt do a long poll, it just polls
the immediate CPU and always returns near-zero results.  (And whats the point
of using something pre-rolled if it's defaults suck and everything has to be
re-done.  SNMP still has it's place: network devices.)

Using commands that do multi-second polling is a bit more intensive, but
actually gives useful data, so SNMP is nice, but without the accuracy desired
it's pointless and other tools can be more easily configured to give what we
want, with precision.
"""


import commands
import re


# -- Command line instructions stored here for easy review

# CPU usage on a machine
CPU_USAGE = '''/usr/bin/mpstat -P ALL 1 1 | /bin/grep all | /bin/grep Average'''

DISK_IO = '/usr/bin/iostat -dk'

DISK_SPACE = '/bin/df -l | /bin/grep -v "Mounted on" | grep -v /dev/shm'

DISK_INODES = '/bin/df -li | /bin/grep -v "Mounted on" | grep -v /dev/shm'

NETWORK_INTERFACES = '/sbin/ifconfig'

MEM_PAGE_SWAP_TICKS = '/usr/bin/vmstat -s'


# -- Utility functions

def Run(cmd):
  output = commands.getoutput(cmd)
  
  output = output.replace('\t', ' ')
  
  while '  ' in output:
    output = output.replace('  ', ' ')
  
  lines = output.rstrip().split('\n')
  
  return lines


# -- Collection functions


def GetCpuUsage():
  """
Average:     all   20.60    0.00   26.88    0.00    0.25    1.26   51.01   6335.05
  """
  lines = Run(CPU_USAGE)
  
  pieces = lines[0].split(' ')
  
  cpu_user = pieces[2]
  cpu_system = pieces[4]
  cpu_idle = pieces[8]
  cpu_wait = pieces[5]
  
  
  cpu_interrupts_per_second = pieces[9]
  cpu_irq = pieces[6]
  cpu_soft = pieces[7]
  
  data = {'user':cpu_user, 'system':cpu_system, 'idle':cpu_idle, 'wait':cpu_wait,
          'interrupts_per_second':cpu_interrupts_per_second, 'irq':cpu_irq,
          'soft':cpu_soft}
  
  return data
  


def GetDiskSpace():
  """
/dev/mapper/VolGroup00-LogVol00
                      11611360   3099308   8394228  27% /
/dev/sda1               194442     20917    163486  12% /boot
tmpfs                   127028        76    126952   1% /dev/shm
  """
  lines = Run(DISK_SPACE)
  
  # Keyed off mount point (/dev/ mount points ignored)
  disks = {}
  
  for count in range(0,len(lines)):
    line = lines[count]
    
    # If this device name is too long, prepend it to the next row and continue
    if ' ' not in line:
      lines[count+1] = '%s%s' % (line, lines[count+1])
      continue
    
    (device, size_total, size_used, size_available, percent_used, mount_point) = line.split(' ')
    
    if not mount_point.startswith('/dev/') and device.startswith('/dev/'):
      disks[mount_point] = {'device':device, 'total':size_total,
                            'used':size_used, 'available':size_available,
                            'percent_used':percent_used[:-1]}
  
  return disks


def GetDiskInodes():
  """
/dev/mapper/VolGroup00-LogVol00
                      737280   90942  646338   13% /
/dev/sda1              50200      41   50159    1% /boot
tmpfs                  31757       2   31755    1% /dev/shm
  """
  lines = Run(DISK_INODES)
  
  # Keyed off mount point (/dev/ mount points ignored)
  disk_inodes = {}
  
  for count in range(0,len(lines)):
    line = lines[count]
    
    # If this device name is too long, prepend it to the next row and continue
    if ' ' not in line:
      lines[count+1] = '%s%s' % (line, lines[count+1])
      continue
    
    (device, inodes_total, inodes_used, inodes_available, percent_used, mount_point) = line.split(' ')
    
    if not mount_point.startswith('/dev/'):
      disk_inodes[mount_point] = {'device':device, 'total':inodes_total,
                                  'used':inodes_used, 'available':inodes_available,
                                  'percent_used':percent_used[:-1]}
  
  return disk_inodes


def GetDiskIO():
  """
Linux 2.6.9-67.ELsmp (lapp16b)  03/30/2009

Device:            tps    kB_read/s    kB_wrtn/s    kB_read    kB_wrtn
sda               0.32         0.22        15.53     884059   61989536
sda1              3.90         0.22        15.53     883113   61987700
sda2              0.00         0.00         0.00        454          0
  """
  lines = Run(DISK_IO)
  
  # Cut off top cruft
  lines = lines[3:]
  
  disk_io = {}
  
  for line in lines:
    if not line:
      continue
    
    (device, tps, kb_read_per_s, kb_write_per_s, kb_read, kb_write) = line.split(' ')
    
    disk_io[device] = {'tps':tps, 'kb_read_per_s':kb_read_per_s,
                       'kb_write_per_s':kb_write_per_s,
                       'kb_read':kb_read, 'kb_write':kb_write}
  
  return disk_io


def GetNetworkUsage():
  """
eth0      Link encap:Ethernet  HWaddr 00:15:C5:E7:47:40
          inet addr:192.168.20.26  Bcast:192.168.20.255  Mask:255.255.255.0
          inet6 addr: fe80::215:c5ff:fee7:4740/64 Scope:Link
          UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
          RX packets:5833474972 errors:0 dropped:0 overruns:0 frame:0
          TX packets:1945417817 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:1000
          RX bytes:3260329340723 (2.9 TiB)  TX bytes:215016483856 (200.2 GiB)
          Interrupt:169 Memory:f8000000-f8012100

lo        Link encap:Local Loopback
          inet addr:127.0.0.1  Mask:255.0.0.0
          inet6 addr: ::1/128 Scope:Host
          UP LOOPBACK RUNNING  MTU:16436  Metric:1
          RX packets:61566 errors:0 dropped:0 overruns:0 frame:0
          TX packets:61566 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:0
          RX bytes:40907198 (39.0 MiB)  TX bytes:40907198 (39.0 MiB)
  """
  lines = Run(NETWORK_INTERFACES)
  
  current_if = None
  
  interfaces = {}
  
  for line in lines:
    # Find interface changes
    if line and line[0] != ' ':
      current_if = line.split(' ')[0]
      interfaces[current_if] = {}
      #print 'Found interface: %s' % current_if
    
    # Skip processing anything if we dont have a selected interface
    if not current_if:
      continue
    
    # IP
    result = re.findall('addr:([0-9\.]+)', line)
    if result:
      interfaces[current_if]['ip'] = result[0]
    
    # Netmask
    result = re.findall('Mask:([0-9\.]+)', line)
    if result:
      interfaces[current_if]['netmask'] = result[0]
    
    # Received Packets
    result = re.findall('RX packets:([0-9]+)', line)
    if result:
      interfaces[current_if]['rx_packets'] = result[0]
    
    # Received Packets
    result = re.findall('TX packets:([0-9]+)', line)
    if result:
      interfaces[current_if]['tx_packets'] = result[0]
    
    # Received bytes
    result = re.findall('RX bytes:([0-9]+)', line)
    if result:
      interfaces[current_if]['rx_bytes'] = result[0]
    
    # Received bytes
    result = re.findall('TX bytes:([0-9]+)', line)
    if result:
      interfaces[current_if]['tx_bytes'] = result[0]
  
  return interfaces


def GetVMUsage():
  """Get all VM data.  Includes memory, pages, swaps, ticks, forks, interrupts,
  and CPU context switches.  Very in-depth.
  """
  lines = Run(MEM_PAGE_SWAP_TICKS)
  
  data = {}
  
  for line in lines:
    # Remove leading spaces, irrelevant
    line = line.strip()
    
    if 'total memory' in line:
      data['memory_total'] = str(line.split(' ')[0])
    elif 'used memory' in line:
      data['memory_used'] = str(line.split(' ')[0])
    elif 'active memory' in line:
      data['memory_active'] = str(line.split(' ')[0])
    elif 'inactive memory' in line:
      data['memory_inactive'] = str(line.split(' ')[0])
    elif 'free memory' in line:
      data['memory_free'] = str(line.split(' ')[0])
    elif 'buffer memory' in line:
      data['memory_buffer'] = str(line.split(' ')[0])
    
    elif 'swap cache' in line:
      data['swap_cache'] = str(line.split(' ')[0])
    elif 'total swap' in line:
      data['swap_total'] = str(line.split(' ')[0])
    elif 'used swap' in line:
      data['swap_used'] = str(line.split(' ')[0])
    elif 'free swap' in line:
      data['swap_free'] = str(line.split(' ')[0])
    
    elif 'non-nice user cpu ticks' in line:
      data['cpu_ticks_non_nice'] = str(line.split(' ')[0])
    elif 'nice user cpu ticks' in line:
      data['cpu_ticks_nice'] = str(line.split(' ')[0])
    
    elif 'system cpu ticks' in line:
      data['cpu_ticks_system'] = str(line.split(' ')[0])
    elif 'idle cpu ticks' in line:
      data['cpu_ticks_idle'] = str(line.split(' ')[0])
    elif 'IO-wait cpu ticks' in line:
      data['cpu_ticks_io_wait'] = str(line.split(' ')[0])
    elif 'IRQ cpu ticks' in line:
      data['cpu_ticks_irq'] = str(line.split(' ')[0])
    elif 'softirq cpu ticks' in line:
      data['cpu_ticks_soft_irq'] = str(line.split(' ')[0])
    elif 'stolen cpu ticks' in line:
      data['cpu_ticks_stolen'] = str(line.split(' ')[0])
  
    elif 'pages paged in' in line:
      data['pages_paged_in'] = str(line.split(' ')[0])
    elif 'pages paged out' in line:
      data['pages_paged_out'] = str(line.split(' ')[0])
    elif 'pages swapped in' in line:
      data['pages_swapped_in'] = str(line.split(' ')[0])
    elif 'pages swapped out' in line:
      data['pages_swapped_out'] = str(line.split(' ')[0])

    elif 'interrupts' in line:
      data['interrupts'] = str(line.split(' ')[0])
    elif 'CPU context switches' in line:
      data['cpu_context_switches'] = str(line.split(' ')[0])
    #NOTE(g): Skipping boot time.  Dont care.
    #TODO(g): Tracking reboots would be interesting though, but not
    #   with a running statistic...
    elif 'forks' in line:
      data['forks'] = str(line.split(' ')[0])
  
  return data


def CollectEverything():
  """This function returns all our interesting machine information.
  
  This is what the Monitoring Poller calls to get it's data.  This is what
  the Monitoring Listener returns.
  """
  data = {}
  
  data['cpu_usage'] = GetCpuUsage()
  data['disk_space'] = GetDiskSpace()
  data['disk_inodes'] = GetDiskInodes()
  data['disk_io'] = GetDiskIO()
  data['network_usage'] = GetNetworkUsage()
  data['vm_usage'] = GetVMUsage()
  
  return data


def main():
  """Prints in pprint format, so that just running this at CLI is useful."""
  import pprint
  everything = CollectEverything()
  
  pprint.pprint(everything)


if __name__ == '__main__':
  main()
