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
#
# Maintainer: Jed Smith <jed@linode.com>
# Based upon code written by Alex Polvi <polvi@cloudkick.com>
#

import sys
import unittest
from libcloud.utils.py3 import httplib

from libcloud.compute.drivers.linode import LinodeNodeDriver
from libcloud.compute.base import Node, NodeAuthPassword, NodeAuthSSHKey

from test import MockHttp
from test.compute import TestCaseMixin

class LinodeTest(unittest.TestCase, TestCaseMixin):
    # The Linode test suite

    def setUp(self):
        LinodeNodeDriver.connectionCls.conn_classes = (None, LinodeMockHttp)
        LinodeMockHttp.use_param = 'api_action'
        self.driver = LinodeNodeDriver('foo')

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 1)
        node = nodes[0]
        self.assertEqual(node.id, "8098")
        self.assertEqual(node.name, 'api-node3')
        self.assertTrue('75.127.96.245' in node.public_ips)
        self.assertEqual(node.private_ips, [])

    def test_reboot_node(self):
        # An exception would indicate failure
        node = self.driver.list_nodes()[0]
        self.driver.reboot_node(node)

    def test_destroy_node(self):
        # An exception would indicate failure
        node = self.driver.list_nodes()[0]
        self.driver.destroy_node(node)

    def test_create_node_password_auth(self):
        # Will exception on failure
        self.driver.create_node(name="Test",
                                location=self.driver.list_locations()[0],
                                size=self.driver.list_sizes()[0],
                                image=self.driver.list_images()[6],
                                auth=NodeAuthPassword("test123"))

    def test_create_node_ssh_key_auth(self):
        # Will exception on failure
        self.driver.create_node(name="Test",
                                location=self.driver.list_locations()[0],
                                size=self.driver.list_sizes()[0],
                                image=self.driver.list_images()[6],
                                auth=NodeAuthSSHKey('foo'))

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 10)
        for size in sizes:
            self.assertEqual(size.ram, int(size.name.split(" ")[1]))

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertEqual(len(images), 22)

    def test_create_node_response(self):
        # should return a node object
        node = self.driver.create_node(name="node-name",
                         location=self.driver.list_locations()[0],
                         size=self.driver.list_sizes()[0],
                         image=self.driver.list_images()[0],
                         auth=NodeAuthPassword("foobar"))
        self.assertTrue(isinstance(node[0], Node))


class LinodeMockHttp(MockHttp):
    def _avail_datacenters(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"avail.datacenters","DATA":[{"DATACENTERID":2,"LOCATION":"Dallas, TX, USA"},{"DATACENTERID":3,"LOCATION":"Fremont, CA, USA"},{"DATACENTERID":4,"LOCATION":"Atlanta, GA, USA"},{"DATACENTERID":6,"LOCATION":"Newark, NJ, USA"}]}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _avail_linodeplans(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"avail.linodeplans","DATA":[{"AVAIL":{"2":27,"3":0,"4":0,"6":0},"DISK":16,"PRICE":19.95,"PLANID":1,"LABEL":"Linode 360","RAM":360,"XFER":200},{"AVAIL":{"2":0,"3":0,"4":0,"6":0},"DISK":24,"PRICE":29.95,"PLANID":2,"LABEL":"Linode 540","RAM":540,"XFER":300},{"AVAIL":{"2":0,"3":0,"4":0,"6":0},"DISK":32,"PRICE":39.95,"PLANID":3,"LABEL":"Linode 720","RAM":720,"XFER":400},{"AVAIL":{"2":0,"3":0,"4":0,"6":0},"DISK":48,"PRICE":59.95,"PLANID":4,"LABEL":"Linode 1080","RAM":1080,"XFER":600},{"AVAIL":{"2":0,"3":0,"4":0,"6":0},"DISK":64,"PRICE":79.95,"PLANID":5,"LABEL":"Linode 1440","RAM":1440,"XFER":800},{"AVAIL":{"2":0,"3":0,"4":0,"6":0},"DISK":128,"PRICE":159.95,"PLANID":6,"LABEL":"Linode 2880","RAM":2880,"XFER":1600},{"AVAIL":{"2":0,"3":0,"4":0,"6":0},"DISK":256,"PRICE":319.95,"PLANID":7,"LABEL":"Linode 5760","RAM":5760,"XFER":2000},{"AVAIL":{"2":0,"3":0,"4":0,"6":0},"DISK":384,"PRICE":479.95,"PLANID":8,"LABEL":"Linode 8640","RAM":8640,"XFER":2000},{"AVAIL":{"2":0,"3":0,"4":0,"6":0},"DISK":512,"PRICE":639.95,"PLANID":9,"LABEL":"Linode 11520","RAM":11520,"XFER":2000},{"AVAIL":{"2":0,"3":0,"4":0,"6":0},"DISK":640,"PRICE":799.95,"PLANID":10,"LABEL":"Linode 14400","RAM":14400,"XFER":2000}]}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _avail_distributions(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"avail.distributions","DATA":[{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Arch Linux 2007.08","MINIMAGESIZE":436,"DISTRIBUTIONID":38,"CREATE_DT":"2007-10-24 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Centos 5.0","MINIMAGESIZE":594,"DISTRIBUTIONID":32,"CREATE_DT":"2007-04-27 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Centos 5.2","MINIMAGESIZE":950,"DISTRIBUTIONID":46,"CREATE_DT":"2008-11-30 00:00:00.0"},{"REQUIRESPVOPSKERNEL":1,"IS64BIT":1,"LABEL":"Centos 5.2 64bit","MINIMAGESIZE":980,"DISTRIBUTIONID":47,"CREATE_DT":"2008-11-30 00:00:00.0"},{"REQUIRESPVOPSKERNEL":1,"IS64BIT":0,"LABEL":"Debian 4.0","MINIMAGESIZE":200,"DISTRIBUTIONID":28,"CREATE_DT":"2007-04-18 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":1,"LABEL":"Debian 4.0 64bit","MINIMAGESIZE":220,"DISTRIBUTIONID":48,"CREATE_DT":"2008-12-02 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Debian 5.0","MINIMAGESIZE":200,"DISTRIBUTIONID":50,"CREATE_DT":"2009-02-19 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":1,"LABEL":"Debian 5.0 64bit","MINIMAGESIZE":300,"DISTRIBUTIONID":51,"CREATE_DT":"2009-02-19 00:00:00.0"},{"REQUIRESPVOPSKERNEL":1,"IS64BIT":0,"LABEL":"Fedora 8","MINIMAGESIZE":740,"DISTRIBUTIONID":40,"CREATE_DT":"2007-11-09 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Fedora 9","MINIMAGESIZE":1175,"DISTRIBUTIONID":43,"CREATE_DT":"2008-06-09 15:15:21.0"},{"REQUIRESPVOPSKERNEL":1,"IS64BIT":0,"LABEL":"Gentoo 2007.0","MINIMAGESIZE":1800,"DISTRIBUTIONID":35,"CREATE_DT":"2007-08-29 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Gentoo 2008.0","MINIMAGESIZE":1500,"DISTRIBUTIONID":52,"CREATE_DT":"2009-03-20 00:00:00.0"},{"REQUIRESPVOPSKERNEL":1,"IS64BIT":1,"LABEL":"Gentoo 2008.0 64bit","MINIMAGESIZE":2500,"DISTRIBUTIONID":53,"CREATE_DT":"2009-04-04 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"OpenSUSE 11.0","MINIMAGESIZE":850,"DISTRIBUTIONID":44,"CREATE_DT":"2008-08-21 08:32:16.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Slackware 12.0","MINIMAGESIZE":315,"DISTRIBUTIONID":34,"CREATE_DT":"2007-07-16 00:00:00.0"},{"REQUIRESPVOPSKERNEL":1,"IS64BIT":0,"LABEL":"Slackware 12.2","MINIMAGESIZE":500,"DISTRIBUTIONID":54,"CREATE_DT":"2009-04-04 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Ubuntu 8.04 LTS","MINIMAGESIZE":400,"DISTRIBUTIONID":41,"CREATE_DT":"2008-04-23 15:11:29.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":1,"LABEL":"Ubuntu 8.04 LTS 64bit","MINIMAGESIZE":350,"DISTRIBUTIONID":42,"CREATE_DT":"2008-06-03 12:51:11.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Ubuntu 8.10","MINIMAGESIZE":220,"DISTRIBUTIONID":45,"CREATE_DT":"2008-10-30 23:23:03.0"},{"REQUIRESPVOPSKERNEL":1,"IS64BIT":1,"LABEL":"Ubuntu 8.10 64bit","MINIMAGESIZE":230,"DISTRIBUTIONID":49,"CREATE_DT":"2008-12-02 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":0,"LABEL":"Ubuntu 9.04","MINIMAGESIZE":350,"DISTRIBUTIONID":55,"CREATE_DT":"2009-04-23 00:00:00.0"},{"REQUIRESPVOPSKERNEL":0,"IS64BIT":1,"LABEL":"Ubuntu 9.04 64bit","MINIMAGESIZE":350,"DISTRIBUTIONID":56,"CREATE_DT":"2009-04-23 00:00:00.0"}]}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_create(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.create","DATA":{"LinodeID":8098}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_disk_createfromdistribution(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.disk.createFromDistribution","DATA":{"JobID":1298,"DiskID":55647}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_delete(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.delete","DATA":{"LinodeID":8098}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_update(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.update","DATA":{"LinodeID":8098}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_reboot(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.reboot","DATA":{"JobID":1305}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _avail_kernels(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"avail.kernels","DATA":[{"LABEL":"Latest 2.6 Stable (2.6.18.8-linode19)","ISXEN":1,"KERNELID":60},{"LABEL":"2.6.18.8-linode19","ISXEN":1,"KERNELID":103},{"LABEL":"2.6.30.5-linode20","ISXEN":1,"KERNELID":105},{"LABEL":"Latest 2.6 Stable (2.6.18.8-x86_64-linode7)","ISXEN":1,"KERNELID":107},{"LABEL":"2.6.18.8-x86_64-linode7","ISXEN":1,"KERNELID":104},{"LABEL":"2.6.30.5-x86_64-linode8","ISXEN":1,"KERNELID":106},{"LABEL":"pv-grub-x86_32","ISXEN":1,"KERNELID":92},{"LABEL":"pv-grub-x86_64","ISXEN":1,"KERNELID":95},{"LABEL":"Recovery - Finnix (kernel)","ISXEN":1,"KERNELID":61},{"LABEL":"2.6.18.8-domU-linode7","ISXEN":1,"KERNELID":81},{"LABEL":"2.6.18.8-linode10","ISXEN":1,"KERNELID":89},{"LABEL":"2.6.18.8-linode16","ISXEN":1,"KERNELID":98},{"LABEL":"2.6.24.4-linode8","ISXEN":1,"KERNELID":84},{"LABEL":"2.6.25-linode9","ISXEN":1,"KERNELID":88},{"LABEL":"2.6.25.10-linode12","ISXEN":1,"KERNELID":90},{"LABEL":"2.6.26-linode13","ISXEN":1,"KERNELID":91},{"LABEL":"2.6.27.4-linode14","ISXEN":1,"KERNELID":93},{"LABEL":"2.6.28-linode15","ISXEN":1,"KERNELID":96},{"LABEL":"2.6.28.3-linode17","ISXEN":1,"KERNELID":99},{"LABEL":"2.6.29-linode18","ISXEN":1,"KERNELID":101},{"LABEL":"2.6.16.38-x86_64-linode2","ISXEN":1,"KERNELID":85},{"LABEL":"2.6.18.8-x86_64-linode1","ISXEN":1,"KERNELID":86},{"LABEL":"2.6.27.4-x86_64-linode3","ISXEN":1,"KERNELID":94},{"LABEL":"2.6.28-x86_64-linode4","ISXEN":1,"KERNELID":97},{"LABEL":"2.6.28.3-x86_64-linode5","ISXEN":1,"KERNELID":100},{"LABEL":"2.6.29-x86_64-linode6","ISXEN":1,"KERNELID":102}]}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_disk_create(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.disk.create","DATA":{"JobID":1299,"DiskID":55648}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_boot(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.boot","DATA":{"JobID":1300}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_config_create(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.config.create","DATA":{"ConfigID":31239}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_list(self, method, url, body, headers):
        body = '{"ACTION": "linode.list", "DATA": [{"ALERT_DISKIO_ENABLED": 1, "BACKUPWEEKLYDAY": 0, "LABEL": "api-node3", "DATACENTERID": 5, "ALERT_BWOUT_ENABLED": 1, "ALERT_CPU_THRESHOLD": 10, "TOTALHD": 100, "ALERT_BWQUOTA_THRESHOLD": 81, "ALERT_BWQUOTA_ENABLED": 1, "TOTALXFER": 200, "STATUS": 2, "ALERT_BWIN_ENABLED": 1, "ALERT_BWIN_THRESHOLD": 5, "ALERT_DISKIO_THRESHOLD": 200, "WATCHDOG": 1, "LINODEID": 8098, "BACKUPWINDOW": 1, "TOTALRAM": 540, "LPM_DISPLAYGROUP": "", "ALERT_BWOUT_THRESHOLD": 5, "BACKUPSENABLED": 1, "ALERT_CPU_ENABLED": 1}], "ERRORARRAY": []}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_ip_list(self, method, url, body, headers):
        body = '{"ACTION": "linode.ip.list", "DATA": [{"RDNS_NAME": "li22-54.members.linode.com", "ISPUBLIC": 1, "IPADDRESS": "75.127.96.54", "IPADDRESSID": 5384, "LINODEID": 8098}, {"RDNS_NAME": "li22-245.members.linode.com", "ISPUBLIC": 1, "IPADDRESS": "75.127.96.245", "IPADDRESSID": 5575, "LINODEID": 8098}], "ERRORARRAY": []}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _batch(self, method, url, body, headers):
        body = '[{"ACTION": "linode.ip.list", "DATA": [{"RDNS_NAME": "li22-54.members.linode.com", "ISPUBLIC": 1, "IPADDRESS": "75.127.96.54", "IPADDRESSID": 5384, "LINODEID": 8098}, {"RDNS_NAME": "li22-245.members.linode.com", "ISPUBLIC": 1, "IPADDRESS": "75.127.96.245", "IPADDRESSID": 5575, "LINODEID": 8098}], "ERRORARRAY": []}]'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
