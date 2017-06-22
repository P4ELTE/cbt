import os
import subprocess
import time
from os import path
from math import sqrt

from plugin.base import VNFControl as Base

"""
Plugin to compile P4 program and start a T4P4S switch, fill the tables and stop the switch

It relies on the following config parameters:

"MAIN_ROOT": (absolute) path of nfpa.py
"control_path": (absolute) filename of launch
"control_mgmt": the remote hostname:controller:controller_args
"control_vnf_inport": (dpdk) inport number
"control_vnf_outport: (dpdk) outport number
"vnf_function": name of the P4 program.
                (filename:  $control_path/p4-ucs/$vnf_function/$vnf_function.p4)
"vnf_num_cores": T4P4S core configureation - coremask
"biDir": must be 0

"""

class VNFControl(Base):

  def __init__(self, config):
    super(VNFControl, self).__init__(config, __name__)
    self.launch_cmd = path.abspath(path.join(self.config['control_path'],
                                       'launch.sh'))
    self.base_path = config['MAIN_ROOT']
 
  def generate_portmap(inp, outp):
	return '0x%s' % format(2**inp+2**outp, 'x')

  def generate_core2portmapping(coremask):
	res = []
	corenum=0;
	binvect = format(int(coremask,16),'b')
	for i in range(-1,-1*(len(binvect)+1),-1):
		if binvect[i] == '1':
			corenum += 1;
			for p in range(2):
				res.append('(%d,%d,%d)' % (p, corenum - 1, -1*i-1) ) 
	return ','.join(res)
	
  def configure_remote_vnf(self, traffictype):
    '''
    Configure the remote vnf via pre-installed tools located on the
    same machine where NFPA is.

    :return: True - if success, False - if not
    '''
    log = self.log
    vnf_function = self.config['vnf_function'].lower()
	
	# Start the daemon
    p4_src = path.abspath(path.join(self.config['control_path'],
                                       'p4-ucs/%s/%s.p4' % (config['vnf_num_cores'],config['vnf_num_cores']) ) )
	[self.hostname, controller, controller_args] = config['control_mgmt'].split(':')
	coremask = config['vnf_num_cores']
	port_map = generate_portmap(int(config['control_vnf_inport']), int(config['control_vnf_outport']))
	p2c_mapping = generate_core2portmapping(coremask)
	
    cmd = ['ssh', self.hostname]
    cmd.append('sudo %s %s %s %s -- -c %s -n 4 --proc-type auto -- -p %s -P --config "%s"'	% 
	(self.launch_cmd, p4_src, controller, controller_args, coremask, port_map, p2c_mapping))
    self.logfile = open('/tmp/nfpa-t4p4s.log', 'w')
	
    try:
      self.daemon = subprocess.Popen(cmd, shell=False,
                                     stdout=self.logfile, stderr=self.logfile)
    except Exception as e:
      self.log.error('Failed to start daemon with %s' % cmd)
      raise e
    time.sleep(10)   # Wait for the daemon to start
                    # FIXME: Should read deamon output
										
    return True

  def stop_remote_vnf(self):
    # Check if it is enough...
    self.daemon.terminate()
    self.logfile.close()