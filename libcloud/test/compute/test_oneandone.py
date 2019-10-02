# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys

from libcloud.compute.base import NodeImage, NodeAuthPassword, NodeLocation
from libcloud.utils.py3 import httplib
from libcloud.test import unittest, MockHttp
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.compute.types import Provider, NodeState
from libcloud.test.secrets import ONEANDONE_PARAMS
from libcloud.compute.providers import get_driver


class OneAndOneTests(unittest.TestCase):
    def setUp(self):
        oneAndOne = get_driver(Provider.ONEANDONE)
        oneAndOne.connectionCls.conn_class = OneAndOneMockHttp
        self.driver = oneAndOne(ONEANDONE_PARAMS)

    '''
    Function tests for listing items
    '''

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 4)

    def test_list_locations(self):
        sizes = self.driver.list_locations()
        self.assertEqual(len(sizes), 4)

    def test_list_images(self):
        appliances = self.driver.list_images("IMAGE")
        self.assertEqual(len(appliances), 102)

    def test_get_image(self):
        appliance = self.driver.get_image('img_1')
        self.assertNotEqual(appliance, None)

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 5)

        counter = 0

        for node in nodes:
            if counter == 0:
                self.assertEqual(node.id, '8A7D5122BDC173B6E52223878CEF2748')
                self.assertEqual(node.name, 'Docs Content Ubuntu 16.04-1')
                self.assertEqual(node.state, NodeState.RUNNING)
                self.assertEqual(node.public_ips, ['50.21.182.126'])
                self.assertEqual(node.private_ips, [])
            if counter == 1:
                self.assertEqual(node.id, 'E7D36EC025C73796035BF4F171379025')
                self.assertEqual(node.name,
                                 'Docs Content Test Server: CentOS 7-1')
                self.assertEqual(node.state, NodeState.RUNNING)
                self.assertEqual(node.public_ips, ['62.151.179.99'])
                self.assertEqual(node.private_ips, [])
            if counter == 2:
                self.assertEqual(node.id, 'DDDC4CCA34AAB08132FA1E40F9FEAC25')
                self.assertEqual(node.name, 'App Dev Server 5')
                self.assertEqual(node.state, NodeState.RUNNING)
                self.assertEqual(node.public_ips, ['70.35.206.196'])
                self.assertEqual(node.private_ips, [])
            if counter == 3:
                self.assertEqual(node.id, 'D5C5C1D01249DE9B88BE3DAE973AA090')
                self.assertEqual(node.name, 'Docs Test Server: CentOS 7-2')
                self.assertEqual(node.state, NodeState.RUNNING)
                self.assertEqual(node.public_ips, ['74.208.88.88'])
                self.assertEqual(node.private_ips, [])
            if counter == 4:
                self.assertEqual(node.id, 'FB1765588A90364835782061CE48BA8E')
                self.assertEqual(node.name,
                                 'Docs Content Test Server Ubuntu 16.04-2')
                self.assertEqual(node.state, NodeState.RUNNING)
                self.assertEqual(node.public_ips, ['70.35.206.233'])
                self.assertEqual(node.private_ips, [])
            counter += 1

    def test_create_node(self):
        node = self.driver.create_node(name="name",
                                       image=NodeImage(
                                           id="image_id",
                                           name=None,
                                           driver=self.driver),
                                       ex_fixed_instance_size_id="instance_id",
                                       location=NodeLocation(
                                           "datacenter_id",
                                           name="name",
                                           country="GB",
                                           driver=self.driver),
                                       auth=NodeAuthPassword("password"),
                                       ex_ip="1.1.1.1",
                                       ex_monitoring_policy_id="mp_id",
                                       ex_firewall_policy_id="fw_id",
                                       ex_loadbalancer_id="lb_id",
                                       ex_description="description",
                                       ex_power_on="SHUTDOWN")

        self.assertEqual(node.id, "E7D36EC025C73796035BF4F171379025")
        self.assertEqual(node.name, "Docs Content Test Server: CentOS 7-1")
        self.assertEqual(node.extra["description"], "My server description")

        self.assertIsNone(node.extra["status"]["percent"])
        self.assertEqual(node.extra["status"]["state"], "POWERED_ON")

        self.assertEqual(node.extra["image"]["id"],
                         "B5F778B85C041347BCDCFC3172AB3F3C")
        self.assertEqual(node.extra["image"]["name"], "centos7-64std")

        self.assertEqual(node.extra["datacenter"]["id"],
                         "908DC2072407C94C8054610AD5A53B8C")
        self.assertEqual(node.extra["datacenter"]["country_code"], "US")
        self.assertEqual(node.extra["datacenter"]["location"],
                         "United States of America")

        self.assertEqual(node.extra["hardware"]["fixed_instance_size_id"],
                         "65929629F35BBFBA63022008F773F3EB")
        self.assertEqual(node.extra["hardware"]["vcore"], 1)
        self.assertEqual(node.extra["hardware"]["hdds"][0]["id"],
                         "CDB278D95A92CB4C379A9CAAD6759F02")
        self.assertEqual(node.extra["hardware"]["hdds"][0]["size"], 40)
        self.assertEqual(node.extra["hardware"]["hdds"][0]["is_main"], True)
        self.assertEqual(node.extra["hardware"]["cores_per_processor"], 1)
        self.assertEqual(node.extra["hardware"]["vcore"], 1)
        self.assertEqual(node.extra["hardware"]["ram"], 1)

        self.assertEqual(node.extra["ips"][0]["id"],
                         "FDBE99EDD57F8596CBF71B6B64BD0A92")
        self.assertEqual(node.extra["ips"][0]["ip"], "62.151.179.99")

        self.assertIsNone(node.extra["monitoring_policy"])
        self.assertEqual(node.extra["alerts"], [])
        self.assertIsNone(node.extra["snapshot"])
        self.assertIsNone(node.extra["dvd"])
        self.assertIsNone(node.extra["private_networks"])

    def test_ex_list_datacenters(self):
        datacenters = self.driver.ex_list_datacenters()

        self.assertEqual(len(datacenters), 4)

    def test_ex_shutdown_server(self):
        server = self.driver.ex_shutdown_server("srv_1")
        self.assertNotEqual(server, None)

    def test_reboot_node(self):
        node = self.driver.ex_get_server("srv_1")
        node = self.driver.reboot_node(node)
        self.assertNotEqual(node, None)

    def test_ex_get_server(self):
        server = self.driver.ex_get_server("srv_1")
        self.assertNotEqual(server, None)

    def test_destroy_node(self):
        server = self.driver.ex_get_server("srv_1")

        node = self.driver.destroy_node(server)
        self.assertNotEqual(node, None)

    def test_get_server_hardware(self):
        hardware = self.driver.ex_get_server_hardware("srv_1")
        self.assertNotEqual(hardware, None)
        self.assertEqual(hardware['vcore'], 1)
        self.assertEqual(hardware['cores_per_processor'], 1)
        self.assertEqual(hardware['ram'], 2)
        self.assertEqual(hardware['fixed_instance_size_id'], 0)
        self.assertNotEqual(hardware['hdds'], None)
        self.assertEqual(hardware['hdds'][0]['id'],
                         '8C626C1A7005D0D1F527143C413D461E')
        self.assertEqual(hardware['hdds'][0]['is_main'], True)
        self.assertEqual(hardware['hdds'][0]['size'], 40)

    def test_rename_server(self):
        server = self.driver.ex_rename_server("srv_1", "name")
        self.assertNotEqual(server, None)

    def test_ex_modify_server_hardware(self):
        node = self.driver.ex_modify_server_hardware("srv_1", vcore=1)
        self.assertNotEqual(node, None)

    def test_add_hdd(self):
        node = self.driver.ex_add_hdd("srv_1", 1, True)
        self.assertNotEqual(node, None)

    def test_modify_hdd(self):
        node = self.driver.ex_modify_server_hardware("srv_1", "hdd_id", 50)
        self.assertNotEqual(node, None)

    def test_remove_hdd(self):
        node = self.driver.ex_remove_hdd("srv_1", "hdd_id")
        self.assertNotEqual(node, None)

    def test_ex_get_server_image(self):
        image = self.driver.ex_get_server_image("srv_1")
        self.assertNotEqual(image, None)
        self.assertEqual(image['id'], "76EBF29C1250167C8754B2B3D1C05F68")
        self.assertEqual(image['name'], "centos7-64std")

    def test_ex_reinstall_server_image(self):
        node = self.driver.ex_reinstall_server_image("srv_1", "img_id",
                                                     "password")
        self.assertNotEqual(node, None)

    def test_ex_list_server_ips(self):
        ips = self.driver.ex_list_server_ips("srv_1")
        self.assertEqual(len(ips), 1)

    def test_ex_get_server_ip(self):
        ip = self.driver.ex_get_server_ip("srv_1", "ip_id")
        self.assertNotEqual(ip, None)

    def test_ex_assign_server(self):
        node = self.driver.ex_assign_server_ip("srv_1", "IPV$")
        self.assertNotEqual(node, None)

    def test_ex_remove_server_ip(self):
        node = self.driver.ex_remove_server_ip("srv_1", "ip_id", keep_ip=True)
        self.assertNotEqual(node, None)

    def test_ex_create_firewall_policy(self):
        rules = [
            {
                "protocol": "TCP",
                "port_from": 80,
                "port_to": 80,
                "source": "0.0.0.0"
            },
            {
                "protocol": "TCP",
                "port_from": 443,
                "port_to": 443,
                "source": "0.0.0.0"
            }
        ]
        firewall = self.driver \
            .ex_create_firewall_policy("name", rules,
                                       description="desc")

        self.assertNotEqual(firewall, None)

    def test_ex_list_firewall_policies(self):
        firewall = self.driver.ex_list_firewall_policies()
        self.assertNotEqual(firewall, None)
        self.assertEqual(len(firewall), 2)

    def test_ex_get_firewall_policy(self):
        firewall = self.driver.ex_get_firewall_policy("fw_id")
        self.assertNotEqual(firewall, None)

    def test_ex_delete_firewall_policy(self):
        firewall = self.driver.ex_delete_firewall_policy("fw_id")
        self.assertNotEqual(firewall, None)

    def test_ex_get_server_firewall_policies(self):
        firewall = self.driver \
            .ex_get_server_firewall_policies("srv_id", "ip_id")
        self.assertNotEqual(firewall, None)

    def test_ex_add_server_firewall_policy(self):
        node = self.driver \
            .ex_add_server_firewall_policy("srv_id", "ip_id", "fw_id")
        self.assertNotEqual(node, None)

    def test_ex_list_shared_storages(self):
        storages = self.driver.ex_list_shared_storages()
        self.assertEqual(len(storages), 3)

    def test_ex_get_shared_storage(self):
        storage = self.driver.ex_get_shared_storage('storage_1')

        self.assertNotEqual(storage, None)
        self.assertEqual(storage['id'], "6AD2F180B7B666539EF75A02FE227084")
        self.assertEqual(storage['size'], 200)
        self.assertEqual(storage['state'], 'ACTIVE')
        self.assertEqual(storage['description'],
                         'My shared storage test description')
        self.assertEqual(storage['datacenter']['id'],
                         'D0F6D8C8ED29D3036F94C27BBB7BAD36')
        self.assertEqual(storage['datacenter']['location'], 'USA')
        self.assertEqual(storage['datacenter']['country_code'], 'US')
        self.assertEqual(storage['cloudpanel_id'], 'vid35780')
        self.assertEqual(storage['size_used'], '0.00')
        self.assertEqual(storage["cifs_path"], "vid50995.nas1.lanvid50995")
        self.assertEqual(storage["nfs_path"], "vid50995.nas1.lan/:vid50995")
        self.assertEqual(storage["name"], "My shared storage test")
        self.assertEqual(storage["creation_date"], "2015-05-06T08:33:25+00:00")
        self.assertEqual(storage['servers'][0]['id'],
                         '638ED28205B1AFD7ADEF569C725DD85F')
        self.assertEqual(storage['servers'][0]["name"], "My server 1")
        self.assertEqual(storage['servers'][0]["rights"], "RW")

    def test_ex_create_shared_storage(self):
        storage = self.driver.ex_create_shared_storage(
            name='TEST', size=2, datacenter_id='dc_id')
        self.assertNotEqual(storage, None)

    def test_ex_delete_shared_storage(self):
        storage = self.driver.ex_delete_shared_storage('storage_1')
        self.assertNotEqual(storage, None)

    def test_ex_attach_server_to_shared_storage(self):
        storage = self.driver.ex_attach_server_to_shared_storage(
            'storage_1', 'srv_1', 'RW')
        self.assertNotEqual(storage, None)

    def test_ex_get_shared_storage_server(self):
        storage = self.driver.ex_get_shared_storage_server(
            'storage_1', 'srv_1')
        self.assertNotEqual(storage, None)

    def test_ex_detach_server_from_shared_storage(self):
        storage = self.driver.ex_detach_server_from_shared_storage(
            'storage_1', 'srv_1')
        self.assertNotEqual(storage, None)

    def test_ex_create_load_balancers(self):
        rules = [
            {
                "protocol": "TCP",
                "port_balancer": 80,
                "port_server": 80,
                "source": "0.0.0.0"
            },
            {
                "protocol": "TCP",
                "port_balancer": 9999,
                "port_server": 8888,
                "source": "0.0.0.0"
            }
        ]
        load_balancer = self.driver. \
            ex_create_load_balancer(name='name',
                                    method='ROUNDROBIN',
                                    rules=rules,
                                    persistence=True,
                                    persistence_time=1)

        self.assertNotEqual(load_balancer, None)

    def test_ex_list_load_balancers(self):
        load_balancers = self.driver.ex_list_load_balancers()
        self.assertEqual(len(load_balancers), 2)

    def test_update_load_balancer(self):
        load_balancer = self.driver. \
            ex_update_load_balancer("lb_1", name='new name')
        self.assertNotEqual(load_balancer, None)

    def test_ex_add_servers_to_load_balancer(self):
        load_balancer = self.driver. \
            ex_add_servers_to_load_balancer('lb_1', server_ips=["1.1.1.1"])
        self.assertNotEqual(load_balancer, None)

    def test_ex_remove_server_from_load_balancer(self):
        load_balancer = self.driver. \
            ex_remove_server_from_load_balancer('lb_1', server_ip="srv_1")
        self.assertNotEqual(load_balancer, None)

    def test_ex_add_load_balancer_rule(self):
        load_balancer = self.driver. \
            ex_add_load_balancer_rule('lb_1', protocol='TCP', port_balancer=82,
                                      port_server=81, source='0.0.0.0')
        self.assertNotEqual(load_balancer, None)

    def test_ex_remove_load_balancer_rule(self):
        load_balancer = self.driver. \
            ex_remove_load_balancer_rule('lb_1', 'rule_1')
        self.assertNotEqual(load_balancer, None)

    def test_ex_get_load_balancer(self):
        load_balancer = self.driver. \
            ex_get_load_balancer('lb_1')
        self.assertNotEqual(load_balancer, None)

    def test_ex_get_load_balancer_server_ip(self):
        server_ip = self.driver. \
            ex_get_load_balancer_server_ip('lb_1', 'srv_1')
        self.assertNotEqual(server_ip, None)

    def test_ex_list_load_balancer_rules(self):
        rules = self.driver. \
            ex_list_load_balancer_rules('lb_1')
        self.assertNotEqual(rules, None)
        self.assertEqual(len(rules), 2)

    def test_ex_get_load_balancer_rule(self):
        rule = self.driver. \
            ex_get_load_balancer_rule('lb_1', 'rule_1')
        self.assertNotEqual(rule, None)

    def test_ex_delete_load_balancer(self):
        load_balancer = self.driver. \
            ex_delete_load_balancer('lb_1')
        self.assertNotEqual(load_balancer, None)

    def test_ex_list_public_ips(self):
        ips = self.driver.ex_list_public_ips()
        self.assertNotEqual(ips, None)
        self.assertEqual(len(ips), 3)

    def test_ex_create_public_ip(self):
        ip = self.driver.ex_create_public_ip('IPv4')
        self.assertNotEqual(ip, None)

    def test_ex_get_public_ip(self):
        ip = self.driver.ex_get_public_ip('ip_1')
        self.assertNotEqual(ip, None)

    def test_ex_delete_public_ip(self):
        ip = self.driver.ex_delete_public_ip('ip_1')
        self.assertNotEqual(ip, None)

    def test_ex_update_public_ip(self):
        ip = self.driver.ex_update_public_ip('ip_1', "reverse.dns")
        self.assertNotEqual(ip, None)

    def test_ex_create_monitoring_policy(self):
        thresholds = {
            "cpu": {
                "warning": {
                    "value": 90,
                    "alert": False
                },
                "critical": {
                    "value": 95,
                    "alert": False
                }
            },
            "ram": {
                "warning": {
                    "value": 90,
                    "alert": False
                },
                "critical": {
                    "value": 95,
                    "alert": False
                }
            },
            "disk": {
                "warning": {
                    "value": 80,
                    "alert": False
                },
                "critical": {
                    "value": 90,
                    "alert": False
                }
            },
            "transfer": {
                "warning": {
                    "value": 1000,
                    "alert": False
                },
                "critical": {
                    "value": 2000,
                    "alert": False
                }
            },
            "internal_ping": {
                "warning": {
                    "value": 50,
                    "alert": False
                },
                "critical": {
                    "value": 100,
                    "alert": False
                }
            }
        }

        ports = [
            {
                "protocol": "TCP",
                "port": "22",
                "alert_if": "RESPONDING",
                "email_notification": True
            }
        ]

        processes = [
            {
                "process": "test",
                "alert_if": "NOT_RUNNING",
                "email_notification": True
            }
        ]

        policy = self.driver. \
            ex_create_monitoring_policy(name='test_name',
                                        thresholds=thresholds,
                                        ports=ports,
                                        processes=processes,
                                        description='description',
                                        email='test@domain.com',
                                        agent=True)
        self.assertNotEqual(policy, None)

    def test_ex_list_monitoring_policies(self):
        policies = self.driver.ex_list_monitoring_policies()
        self.assertNotEqual(policies, None)
        self.assertEqual(len(policies), 2)

    def test_ex_get_monitoring_policy(self):
        policy = self.driver.ex_get_monitoring_policy('pol_1')
        self.assertNotEqual(policy, None)

    def test_ex_update_monitoring_policy(self):
        thresholds = {
            "cpu": {
                "warning": {
                    "value": 90,
                    "alert": False
                },
                "critical": {
                    "value": 95,
                    "alert": False
                }
            },
            "ram": {
                "warning": {
                    "value": 90,
                    "alert": False
                },
                "critical": {
                    "value": 95,
                    "alert": False
                }
            },
            "disk": {
                "warning": {
                    "value": 80,
                    "alert": False
                },
                "critical": {
                    "value": 90,
                    "alert": False
                }
            },
            "transfer": {
                "warning": {
                    "value": 1000,
                    "alert": False
                },
                "critical": {
                    "value": 2000,
                    "alert": False
                }
            },
            "internal_ping": {
                "warning": {
                    "value": 50,
                    "alert": False
                },
                "critical": {
                    "value": 100,
                    "alert": False
                }
            }
        }

        policy = self.driver. \
            ex_update_monitoring_policy('pol_1', email='test@domain.com',
                                        thresholds=thresholds,
                                        name='new name',
                                        description='new description')
        self.assertNotEqual(policy, None)

    def test_ex_get_monitoring_policy_ports(self):
        ports = self.driver. \
            ex_get_monitoring_policy_ports('pol_1')
        self.assertNotEqual(ports, None)
        self.assertEqual(len(ports), 2)

    def test_ex_get_monitoring_policy_port(self):
        port = self.driver. \
            ex_get_monitoring_policy_port('pol_1', 'port_1')
        self.assertNotEqual(port, None)

    def test_ex_remove_monitoring_policy_port(self):
        port = self.driver. \
            ex_remove_monitoring_policy_port('pol_1', 'port_1')
        self.assertNotEqual(port, None)

    def test_ex_add_monitoring_policy_ports(self):
        new_ports = [
            {
                "protocol": "TCP",
                "port": "80",
                "alert_if": "RESPONDING",
                "email_notification": True
            }
        ]
        ports = self.driver. \
            ex_add_monitoring_policy_ports('pol_1', new_ports)
        self.assertNotEqual(ports, None)
        self.assertEqual(len(ports), 2)

    def test_ex_get_monitoring_policy_processes(self):
        processes = self.driver. \
            ex_get_monitoring_policy_processes('pol_1')
        self.assertNotEqual(processes, None)

    def test_ex_get_monitoring_policy_process(self):
        process = self.driver. \
            ex_get_monitoring_policy_process('pol_1', 'proc_1')
        self.assertNotEqual(process, None)

    def test_ex_remove_monitoring_policy_process(self):
        policy = self.driver. \
            ex_remove_monitoring_policy_process('pol_1', 'proc_1')
        self.assertNotEqual(policy, None)

    def test_ex_add_monitoring_policy_processes(self):
        processes = {
            "processes": [
                {
                    "process": "taskmmgr",
                    "alert_if": "RUNNING",
                    "email_notification": True
                }
            ]
        }
        processes = self.driver. \
            ex_add_monitoring_policy_processes(policy_id='pol_1',
                                               processes=processes)
        self.assertNotEqual(processes, None)
        self.assertEqual(len(processes), 2)

    def test_ex_list_monitoring_policy_servers(self):
        servers = self.driver.ex_list_monitoring_policy_servers('pol_1')
        self.assertNotEqual(servers, None)
        self.assertEqual(len(servers), 2)

    def test_ex_add_servers_to_monitoring_policy(self):
        servers = self.driver. \
            ex_add_servers_to_monitoring_policy('pol_1', 'serv_1')
        self.assertNotEqual(servers, None)
        self.assertEqual(len(servers), 2)

    def test_ex_remove_server_from_monitoring_policy(self):
        policy = self.driver. \
            ex_remove_server_from_monitoring_policy('pol_1', 'serv_1')
        self.assertNotEqual(policy, None)


class OneAndOneMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('oneandone')

    '''
    Operation on Server Appliances

    GET - Fetches Server Appliances
    '''

    def _v1_server_appliances(self, method, url, body, headers):
        body = self.fixtures.load('list_images.json')
        return (
            httplib.OK,
            body,
            {},
            httplib.responses[httplib.OK]
        )

    def _v1_server_appliances_img_1(self, method, url, body, headers):
        body = self.fixtures.load('get_image.json')
        return (
            httplib.OK,
            body,
            {},
            httplib.responses[httplib.OK]
        )

    def _v1_servers(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('list_servers.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )
        if method == "POST":
            body = self.fixtures.load('create_node.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    def _v1_create_node(self, method, url, body_headers):

        body = self.fixtures.load('list_servers.json')

        return (
            httplib.ACCEPTED,
            {},
            body,
            httplib.responses[httplib.ACCEPTED]
        )

    def _v1_datacenters(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('ex_list_datacenters.json')
            return (
                httplib.OK,
                body,
                {'content-type': 'application/json'},
                httplib.responses[httplib.OK]
            )

    def _v1_servers_srv_1(
        self, method, url, body, headers
    ):
        pass

        if method == 'PUT':
            body = self.fixtures.load('describe_server.json')
            return (
                httplib.OK,
                body,
                {'content-type': 'application/json'},
                httplib.responses[httplib.OK]
            )
        if method == 'GET':
            body = self.fixtures.load('describe_server.json')
            return (
                httplib.OK,
                body,
                {'content-type': 'application/json'},
                httplib.responses[httplib.OK]
            )
        if method == 'DELETE':
            body = self.fixtures.load('describe_server.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

    def _v1_servers_srv_1_status_action(self, method, url, body_headers, id):
        body = self.fixtures.load('describe_server.json')

        return (
            httplib.ACCEPTED,
            body,
            {},
            httplib.responses[httplib.ACCEPTED]
        )

    def _v1_servers_srv_1_hardware(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('server_hardware.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )
        if method == 'PUT':
            body = self.fixtures.load('describe_server.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    def _v1_servers_srv_1_hardware_hdds(
        self, method, url, body, headers
    ):
        if method == 'POST':
            body = self.fixtures.load('describe_server.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )
        if method == 'PUT':
            body = self.fixtures.load('describe_server.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    def _v1_servers_srv_1_hardware_hdds_hdd_id(
        self, method, url, body, headers
    ):
        if method == 'DELETE':
            body = self.fixtures.load('describe_server.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )
        if method == 'PUT':
            body = self.fixtures.load('describe_server.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    def _v1_servers_srv_1_image(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('get_server_image.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )
        if method == 'PUT':
            body = self.fixtures.load('describe_server.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

    def _v1_servers_srv_1_ips(
        self, method, url, body, headers
    ):

        if method == 'GET':
            body = self.fixtures.load('server_ips.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )
        if method == 'POST':
            body = self.fixtures.load('describe_server.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

    def _v1_servers_srv_1_ips_ip_id(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('server_ip.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )
        if method == 'DELETE':
            body = self.fixtures.load('describe_server.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

    def _v1_firewall_policies(
        self, method, url, body, headers
    ):

        if method == 'POST':
            body = self.fixtures.load('describe_firewall_policy.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        if method == 'GET':
            body = self.fixtures.load('list_firewall_policies.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

    def _v1_firewall_policy_fw_id(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('describe_firewall_policy.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        if method == 'DELETE':
            body = self.fixtures.load('describe_firewall_policy.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

    def _v1_servers_srv_id_ips_ip_id_firewall_policy(
        self, method, url, body, header
    ):
        if method == 'GET':
            body = self.fixtures.load('describe_id_firewall_policy.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )
        if method == 'DELETE':
            body = self.fixtures.load('describe_server.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )
        if method == 'POST':
            body = self.fixtures.load('describe_server.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

    def _v1_shared_storages(
        self, method, url, body, header
    ):
        if method == 'GET' or method == 'POST':
            body = self.fixtures.load('list_shared_storages.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

    def _v1_shared_storages_storage_1(
        self, method, url, body, header
    ):
        if method == 'GET' or method == 'DELETE':
            body = self.fixtures.load('shared_storage.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

    def _v1_shared_storages_storage_1_servers(
        self, method, url, body, header
    ):
        if method == 'POST' or method == 'DELETE':
            body = self.fixtures.load('shared_storage.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

    def _v1_shared_storages_storage_1_servers_srv_1(
        self, method, url, body, header
    ):
        if method == 'GET' or method == 'DELETE':
            body = self.fixtures.load('shared_storage.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

    def _v1_load_balancers(
        self, method, url, body, header
    ):
        if method == 'POST':
            body = self.fixtures.load('load_balancer.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )
        if method == 'GET':
            body = self.fixtures.load('list_load_balancer.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

    def _v1_load_balancers_lb_1(
        self, method, url, body, header
    ):

        body = self.fixtures.load('load_balancer.json')
        return (
            httplib.OK,
            body,
            {},
            httplib.responses[httplib.OK]
        )

    def _v1_load_balancers_lb_1_server_ips(
        self, method, url, body, header
    ):
        if method == 'GET':
            body = self.fixtures.load('load_balancer_server_ips.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        if method == 'POST':
            body = self.fixtures.load('load_balancer.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

    def _v1_load_balancers_lb_1_rules(
        self, method, url, body, header
    ):
        if method == 'POST':
            body = self.fixtures.load('load_balancer.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )
        if method == 'GET':
            body = self.fixtures.load('load_balancer_rules.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

    def _v1_load_balancers_lb_1_server_ips_srv_1(
        self, method, url, body, header
    ):
        if method == 'DELETE':
            body = self.fixtures.load('load_balancer.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        if method == 'GET':
            body = self.fixtures.load('load_balancer_server_ip.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

    def _v1_load_balancers_lb_1_rules_rule_1(
        self, method, url, body, header
    ):
        if method == 'DELETE':
            body = self.fixtures.load('load_balancer.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )
        if method == 'GET':
            body = self.fixtures.load('load_balancer_rule.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

    def _v1_public_ips(
        self, method, url, body, header
    ):
        if method == 'GET':
            body = self.fixtures.load('list_public_ips.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )
        if method == 'POST':
            body = self.fixtures.load('public_ip.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

    def _v1_public_ips_ip_1(
        self, method, url, body, header
    ):
        body = self.fixtures.load('public_ip.json')
        return (
            httplib.OK,
            body,
            {},
            httplib.responses[httplib.OK]
        )

    def _v1_monitoring_policies(
        self, method, url, body, header
    ):
        if method == 'POST':
            body = self.fixtures.load('monitoring_policy.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )
        if method == 'GET':
            body = self.fixtures.load('list_monitoring_policies.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

    def _v1_monitoring_policies_pol_1(
        self, method, url, body, header
    ):
        body = self.fixtures.load('monitoring_policy.json')
        return (
            httplib.OK,
            body,
            {},
            httplib.responses[httplib.OK]
        )

    def _v1_monitoring_policies_pol_1_ports(
        self, method, url, body, header
    ):
        body = self.fixtures.load('monitoring_policy_ports.json')
        return (
            httplib.OK,
            body,
            {},
            httplib.responses[httplib.OK]
        )

    def _v1_monitoring_policies_pol_1_ports_port_1(
        self, method, url, body, header
    ):
        if method == 'GET':
            body = self.fixtures.load('monitoring_policy_port.json')
        elif method == 'POST':
            body = self.fixtures.load('monitoring_policy.json')

        return (
            httplib.OK,
            body,
            {},
            httplib.responses[httplib.OK]
        )

    def _v1_monitoring_policies_pol_1_processes(
        self, method, url, body, header
    ):
        body = self.fixtures.load('monitoring_policy_processes.json')
        return (
            httplib.OK,
            body,
            {},
            httplib.responses[httplib.OK]
        )

    def _v1_monitoring_policies_pol_1_processes_proc_1(
        self, method, url, body, header
    ):
        if method == 'GET':
            body = self.fixtures.load('monitoring_policy_process.json')
        elif method == 'POST':
            body = self.fixtures.load('monitoring_policy.json')

        return (
            httplib.OK,
            body,
            {},
            httplib.responses[httplib.OK]
        )

    def _v1_monitoring_policies_pol_1_servers(
        self, method, url, body, header
    ):
        body = self.fixtures.load('monitoring_policy_servers.json')
        return (
            httplib.OK,
            body,
            {},
            httplib.responses[httplib.OK]
        )

    def _v1_monitoring_policies_pol_1_servers_serv_1(
        self, method, url, body, header
    ):
        if method == 'GET':
            body = self.fixtures.load('monitoring_policy_servers.json')
        elif method == 'POST':
            body = self.fixtures.load('monitoring_policy.json')

        return (
            httplib.OK,
            body,
            {},
            httplib.responses[httplib.OK]
        )

    def _v1_servers_fixed_instance_sizes(
        self, method, url, body, header
    ):
        body = self.fixtures.load('fixed_instance_sizes.json')
        return (
            httplib.OK,
            body,
            {},
            httplib.responses[httplib.OK]
        )


if __name__ == '__main__':
    sys.exit(unittest.main())
