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

###########################################################################
# Script to deploy OpenStack VNFs and Service Funciton Chain using Netfloc.
# Requires Netfloc plugin for Heat installed and Netfloc as SDN controller
###########################################################################

__author__ = 'traj'

#from oslo_LOG import LOG as LOGging
from heat.engine import properties
from heat.engine import resource
from gettext import gettext as _
import requests
import json
import time
from time import sleep

#LOG = #LOGging.get#LOGger(__name__)
class ChainCreate(resource.Resource):
    PROPERTIES = (
        PORT1,
        PORT2,
        PORT3,
        PORT4,
        ODL_USERNAME,
        ODL_PASSWORD,
        NETFLOC_IP_PORT) = (
        'port1',
        'port2',
        'port3',
        'port4',
        'odl_username',
        'odl_password',
        'netfloc_ip_port')

    properties_schema = {
        PORT1: properties.Schema(
            data_type=properties.Schema.STRING,
            description=_('SFC port of VNF'),
            required=True
        ),
        PORT2: properties.Schema(
            data_type=properties.Schema.STRING,
            description=_('SFC port of VNF'),
            required=True
        ),
        PORT3: properties.Schema(
            data_type=properties.Schema.STRING,
            description=_('SFC port of VNF'),
            required=True
        ),
        PORT4: properties.Schema(
            data_type=properties.Schema.STRING,
            description=_('SFC port of VNF'),
            required=True
        ),
        ODL_USERNAME: properties.Schema(
            data_type=properties.Schema.STRING,
            description=_('User name to be configured for ODL Restconf access'),
            required=True
        ),
        ODL_PASSWORD: properties.Schema(
            data_type=properties.Schema.STRING,
            description=_('Password to be set for ODL Restconf access'),
            required=True
        ),
        NETFLOC_IP_PORT: properties.Schema(
            data_type=properties.Schema.STRING,
            description=_('IP and port of the Netfloc node'),
            required=True
        )
    }

    def handle_create(self):
        # Time until dependent resources are created.
        # Can vary for different environments (preliminary).
        time.sleep(30)
        chain_ids = []
        odl_username = self.properties.get(self.ODL_USERNAME)
        odl_password = self.properties.get(self.ODL_PASSWORD)
        netfloc_ip_port = self.properties.get(self.NETFLOC_IP_PORT)
        port1 = self.properties.get(self.PORT1)
        port2 = self.properties.get(self.PORT2)
        port3 = self.properties.get(self.PORT3)
        port4 = self.properties.get(self.PORT4)

        ports = "%s,%s,%s,%s" % (port1, port2, port3, port4)
        create_url = 'restconf/operations/netfloc:create-service-chain'
        url = "%s%s:%s@%s/%s" % ('http://',odl_username,odl_password,netfloc_ip_port,create_url)
        ports_dict = {"input": {"neutron-ports": str(ports)}}
        headers = {'Content-type': 'application/json'}
        #LOG.debug('CHAIN_PORTS %s', ports_dict)
        try:
            req = requests.post(url, data=json.dumps(ports_dict), headers=headers)
            if req.json()['output']:
                chainID = req.json()['output']['service-chain-id']
                self.resource_id_set(chainID)
                #LOG.debug('chainID %s', chainID)
                return chainID
        except Exception as ex:
            pass
            #LOG.warn("Failed to fetch chain ID: %s", ex)

class ChainDelete(resource.Resource):
    PROPERTIES = (
        CHAIN_ID,
        ODL_USERNAME,
        ODL_PASSWORD,
        NETFLOC_IP_PORT) = (
        'chain_id',
        'odl_username',
        'odl_password',
        'netfloc_ip_port')

    properties_schema = {
        CHAIN_ID: properties.Schema(
            data_type=properties.Schema.STRING,
            description=_('ID of the created chain'),
            required=True
        ),
        ODL_USERNAME: properties.Schema(
            data_type=properties.Schema.STRING,
            description=_('User name to be configured for ODL Restconf access'),
            required=True
        ),
        ODL_PASSWORD: properties.Schema(
            data_type=properties.Schema.STRING,
            description=_('Password to be set for ODL Restconf access'),
            required=True
        ),
        NETFLOC_IP_PORT: properties.Schema(
            data_type=properties.Schema.STRING,
            description=_('IP and port of the Netfloc node'),
            required=True
        )
    }

    def handle_create(self):
        chain_id = self.properties.get(self.CHAIN_ID)
        odl_username = self.properties.get(self.ODL_USERNAME)
        odl_password = self.properties.get(self.ODL_PASSWORD)
        netfloc_ip_port = self.properties.get(self.NETFLOC_IP_PORT)
        delete_url = 'restconf/operations/netfloc:delete-service-chain'
        url = "%s%s:%s@%s/%s" % ('http://',odl_username,odl_password,netfloc_ip_port,delete_url)
        headers = {'Content-type': 'application/json'}
        body = {"input": {"service-chain-id": str(chain_id)}}
        try:
            req = requests.post(url, data=json.dumps(body), headers=headers)
            if req.json()['output']:
                chainID = req.json()['output']['service-chain-id']
                return req.status_code
        except Exception as ex:
            pass
             #LOG.warn("Failed to delete chain: %s", ex)

def resource_mapping():
    mappings = {}
    mappings['Netfloc::Chain::Create'] = ChainCreate
    mappings['Netfloc::Chain::Delete'] = ChainDelete
    return mappings