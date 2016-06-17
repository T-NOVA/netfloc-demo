# Copyright (c) 2016. Zuercher Hochschule fuer Angewandte Wissenschaften
#  All Rights Reserved.
#
#     Licensed under the Apache License, Version 2.0 (the "License"); you may
#     not use this file except in compliance with the License. You may obtain
#     a copy of the License at
#
#          http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#     WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#     License for the specific language governing permissions and limitations
#     under the License.

################################################################################
# Netfloc Server app: Creates OpenStack Neutron to OVS port mapping;
# Installs # (additional) flows on the bridges to enable Service Function Chain;
# Runs the VNFs. All is done from OpenStack Control node.
################################################################################

#!/usr/bin/python
__author__ = 'traj'

import requests
import json
import subprocess
import sys
import paramiko
import re
NEUTRON = 'localadmin@10.100.0.2'
NODE2 = 'localadmin@10.100.0.4'
SWITCH = 'localadmin@10.30.0.63'
COMMAND="sudo ovs-ofctl dump-ports-desc br-int"
keystoneHost = '10.100.0.3'
keystonePort = '5000'
neutronHost = '10.100.0.3'
neutronPort = '9696'
keystonUrl = '/v2.0/tokens'
neutronPortsUrl = '/v2.0/ports'
novaServers = '/api/nova-servers'
keystoneUser = 'admin'
keystoneTenant = 'admin'
token = ''
tenant_id = ''
portsList = []

class Server():
	def __init__(self):
		self.getToken()
		self.getNeutronPorts()

	def getToken(self):
		keystonePass = raw_input("Please enter the Keystone password: ")
		url = "%s%s:%s%s" % ('http://',keystoneHost,keystonePort,keystonUrl)
		headers = {'Content-type': 'application/json'}
		body = {
			"auth": {
					"passwordCredentials": {
					"password": keystonePass,
					"username": keystoneUser
				},
				"tenantName": 'admin'
			},
		}
		try:
			req = requests.post(url, data=json.dumps(body), headers=headers)
			#print "Request ", json.dumps(req.json(), indent=4, sort_keys=True)
			if req.json()['access']:
				global token
				global tenant_id
				token = req.json()['access']['token']['id']
				tenant_id = req.json()['access']['token']['tenant']['id']
				#print "Token ", json.dumps(token, indent=4, sort_keys=True)
				#print "Tenant id ", json.dumps(tenant_id, indent=4, sort_keys=True)
		except Exception as ex:
			print "Failed to authenticate with Keystone: ", ex

	def getNeutronPorts(self):
		#portsList = []
		url = "%s%s:%s%s" % ('http://',neutronHost,neutronPort,neutronPortsUrl)
		headers = {'X-Auth-Token': str(token)}
		try:
			req = requests.get(url, headers=headers)
			if req.json()["ports"]:
				ports = req.json()["ports"]
				for port in ports:
					portList = []
					port_name = str(port['name'])
					mac_address = str(port['mac_address'])
					ip_address = str(port['fixed_ips'][0]['ip_address'])
					# portsList contains the list of the SFC ports as mapped in Neutron
					if (port_name != '') & (port_name.find('_in_') != -1) | (port_name.find('_out_') != -1) | \
						(port_name.find('_out1_') != -1) | (port_name.find('_out2_') != -1):
						portList.append(port_name)
						portList.append(mac_address)
						portList.append(ip_address)
						portsList.append(portList)
			#print "portsList ", json.dumps(portsList, indent=4, sort_keys=True)
		except Exception as ex:
			print "Failed to fetch Neutron ports: ", ex

	def _putFlowsNode2(self,vTC_in_port):
		command1 = 'sudo ovs-ofctl add-flow br-int priority=14,in_port=1,dl_vlan=400,actions=output:'+vTC_in_port
		command2 = 'sudo ovs-ofctl add-flow br-int priority=14,in_port=1,dl_vlan=401,actions=output:'+vTC_in_port
		command3 = 'sudo ovs-ofctl dump-flows br-int | grep priority=14'
		command = "sudo %s; %s; %s" % (command1,command2,command3)
		#This looks ugly but loops if all commands in one. TODO: switch to other library maybe pexpect
		ssh1_Node2 = subprocess.Popen(["ssh", "%s" % NODE2, command1],
		                       shell=False,
		                       stdout=subprocess.PIPE,
		                       stderr=subprocess.PIPE)
		ssh2_Node2 = subprocess.Popen(["ssh", "%s" % NODE2, command2],
		                       shell=False,
		                       stdout=subprocess.PIPE,
		                       stderr=subprocess.PIPE)
		ssh3_Node2 = subprocess.Popen(["ssh", "%s" % NODE2, command3],
		                       shell=False,
		                       stdout=subprocess.PIPE,
		                       stderr=subprocess.PIPE)
		result = ssh3_Node2.stdout.read()
		#result = json.dumps(ssh3_Node2.stdout.read(), indent=4, sort_keys=True).replace('\\n', '\n').replace('"', '')
		if result == []:
		    error = ssh3_Node2.stderr.readlines()
		    print >>sys.stderr, "ERROR: %s" % error
		else:
			print "Node2 SFC flows installed successfully :)"
			print "-----------------------------------------"
			print result

	def getPortsPutFlowsNode2(self):
		portMappingList = []
		ssh_Node2 = subprocess.Popen(["ssh", "%s" % NODE2, COMMAND],
		                       shell=False,
		                       stdout=subprocess.PIPE,
		                       stderr=subprocess.PIPE)
		result = ssh_Node2.stdout.read()
		ports = json.dumps(result, indent=4, sort_keys=True).replace('\\n', '\n')
		#print ports
		if result == []:
		    error = ssh_Node2.stderr.readlines()
		    print >>sys.stderr, "ERROR: %s" % error
		else:
		    node2_ports = open('../port_mappings/node2_ovs_ports', 'w')
		    node2_ports.write(ports)
		    #print result
		# Check if the mac address (only 6 digits) appeares in the OVS ports ouptut
		for port_data in portsList:
			# Mac address in the filtered Neutron port list
			mac_address = port_data[1][3:]
			#print port_data
			# Output from the ovs-ofctl command with OVS ports description
			if mac_address in ports:
				port_index = ports.index(mac_address)
				#TODO: make this parsing more elegant
				port_number = "%s%s%s" % (ports[int(port_index)-29],ports[int(port_index)-28],ports[int(port_index)-27])
				port_data.append(port_number)
				portMappingList.append(port_data)
				# Record of the required mappings
		node2_port_mapping = open('../port_mappings/node2_port_mappings', 'w')
		node2_port_mapping.write(str(portMappingList))
		#print portMappingList
		for port_dict in portsList:
			if (port_dict[0].find('vTC_in_port') != -1):
				vTC_in_port = port_dict[3]
				#print vTC_in_port
				try:
					if vTC_in_port != '':
						self._putFlowsNode2(vTC_in_port)
				except Exception as ex:
					print "Can not call install flows on Node2: ", ex
				break

	def putFlowsSwitch(self):
		command1 = "sudo ./sfc-vlan-flows"
		command2 = 'sudo ovs-ofctl dump-flows br0 | grep priority=14'
		ssh1_Switch = subprocess.Popen(["ssh", "%s" % SWITCH, command1],
		                       shell=False,
		                       stdout=subprocess.PIPE,
		                       stderr=subprocess.PIPE)
		ssh2_Switch = subprocess.Popen(["ssh", "%s" % SWITCH, command2],
		                       shell=False,
		                       stdout=subprocess.PIPE,
		                       stderr=subprocess.PIPE)
		result = ssh2_Switch.stdout.read()
		if result == []:
			error = ssh2_Switch.stderr.readlines()
			print >>sys.stderr, "ERROR: %s" % error
		else:
			print "Switch SFC flows installed successfully :)"
			print "------------------------------------------"
			print result

	def _putFlowsControl(self,vSF_out_port):
		command1 = 'ovs-ofctl add-flow br-int priority=14,in_port='+vSF_out_port+',dl_vlan=401,actions=output:1'
		command2 = 'ovs-ofctl add-flow br-int priority=14,in_port='+vSF_out_port+',dl_vlan=400,actions=output:1'
		command3 = 'ovs-ofctl dump-flows br-int | grep priority=14'
		command4 = "sudo %s && %s && %s" % (command1,command2,command3)
		process = subprocess.Popen(["%s" % command4],
		                       shell=True,
		                       stdout=subprocess.PIPE,
		                       stderr=subprocess.PIPE)
		result = process.stdout.read()
		#result = json.dumps(process.stdout.read(), indent=4, sort_keys=True).replace('\\n', '\n').replace('"', '')
		if result == []:
			error = process.stderr.readlines()
			print >>sys.stderr, "ERROR: %s" % error
		else:
			print "Control SFC flows installed successfully :)"
			print "-------------------------------------------"
			print result

	def getPortsPutFlowsControl(self):
		portMappingList = []
		process = subprocess.Popen(["%s" % COMMAND],
		                       shell=True,
		                       stdout=subprocess.PIPE,
		                       stderr=subprocess.PIPE)
		result = process.stdout.read()
		ports = json.dumps(result, indent=4, sort_keys=True).replace('\\n', '\n')
		if result == []:
			error = process.stderr.readlines()
			print >>sys.stderr, "ERROR: %s" % error
		else:
			control_ports = open('../port_mappings/control_ovs_ports', 'w')
			control_ports.write(ports)
			#print result
		#Check if the mac address (only 6 digits) appeares in the OVS ports ouptut
		for port_data in portsList:
			# Mac address in the filtered Neutron port list
			mac_address = port_data[1][3:]
			#print port_data
			# Output from the ovs-ofctl command with OVS ports description
			if mac_address in ports:
				port_index = ports.index(mac_address)
				#TODO: make this parsing more elegant
				port_number = "%s%s%s" % (ports[int(port_index)-29],ports[int(port_index)-28],ports[int(port_index)-27])
				port_data.append(port_number)
				portMappingList.append(port_data)
				# Record of the required mappings
		control_port_mapping = open('../port_mappings/control_port_mappings', 'w')
		control_port_mapping.write(str(portMappingList))
		#print portMappingList
		for port_dict in portsList:
			if (port_dict[0].find('vSF_out_port') != -1):
				vSF_out_port = port_dict[3]
				#print vSF_out_port
				try:
					if vSF_out_port != '':
						self._putFlowsControl(vSF_out_port)
				except Exception as ex:
					print "Can not call install flows on Control: ", ex
				break

	def putFlowsServiceForwarder(self):
		SF = raw_input("Please enter user@IP of the Service Forwarder VNF: ")
		command = "sudo ./sfc-flows-sf"
		process = subprocess.Popen(["ssh", "%s" % SF, command],
		                       shell=False,
		                       stdout=subprocess.PIPE,
		                       stderr=subprocess.PIPE)
		result = process.stdout.read()
		if result == []:
			error = process.stderr.readlines()
			print >>sys.stderr, "ERROR: %s" % error
		else:
			print "Service Forwarder SFC flows installed successfully :)"
			print "-----------------------------------------------------"
			print result

	def run_vTC(self):
		vTC = raw_input("Please enter user@IP of the vTC VNF: ")
		command = "sudo ./run-vTC.sh"
		process = subprocess.Popen(["ssh", "%s" % vTC, command],
		                       shell=False,
		                       stdout=subprocess.PIPE,
		                       stderr=subprocess.PIPE)
		with process.stdout:
		    for line in iter(process.stdout.readline, b''):
		        print line
		        break
		#process.wait() # wait for the subprocess to exit

	def run_vTC_f(self):
		vTC_f = raw_input("Please enter user@IP of the vTC-f VNF: ")
		command = "sudo ./run-vTC-f.sh"
		process = subprocess.Popen(["ssh", "%s" % vTC_f, command],
		                       shell=False,
		                       stdout=subprocess.PIPE,
		                       stderr=subprocess.PIPE)
		with process.stdout:
		    for line in iter(process.stdout.readline, b''):
		        print line
		        break
		#process.wait() # wait for the subprocess to exit

if __name__ == "__main__":
    server = Server()
    server.getPortsPutFlowsNode2()
    server.getPortsPutFlowsControl()
    server.putFlowsSwitch()
    server.putFlowsServiceForwarder()
    server.run_vTC()
    server.run_vTC_f()