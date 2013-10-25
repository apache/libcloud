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

from libcloud.compute.providers import Provider
from libcloud.compute.base import Node, NodeImage, NodeSize
from libcloud.compute.drivers.cloudstack import CloudStackNodeDriver


class KTUCloudNodeDriver(CloudStackNodeDriver):
    "Driver for KTUCloud Compute platform."

    type = Provider.KTUCLOUD
    name = 'KTUCloud'
    website = 'https://ucloudbiz.olleh.com/'

    def list_images(self, location=None):
        args = {
            'templatefilter': 'executable'
        }
        if location is not None:
            args['zoneid'] = location.id

        imgs = self._sync_request('listAvailableProductTypes')
        images = []

        for img in imgs['producttypes']:
            images.append(
                NodeImage(
                    img['serviceofferingid'],
                    img['serviceofferingdesc'],
                    self,
                    {'hypervisor': '',
                     'format': '',
                     'os': img['templatedesc'],
                     'templateid': img['templateid'],
                     'zoneid': img['zoneid']}
                )
            )

        return images

    def list_sizes(self, location=None):
        szs = self._sync_request('listAvailableProductTypes')
        sizes = []
        for sz in szs['producttypes']:
            sizes.append(NodeSize(
                sz['diskofferingid'],
                sz['diskofferingdesc'],
                0, 0, 0, 0, self)
            )
        return sizes

    def create_node(self, name, size, image, location=None, **kwargs):
        extra_args = {}
        usageplantype = kwargs.pop('usageplantype', None)
        if usageplantype is None:
            extra_args['usageplantype'] = 'hourly'
        else:
            extra_args['usageplantype'] = usageplantype

        result = self._async_request(
            'deployVirtualMachine',
            displayname=name,
            serviceofferingid=image.id,
            diskofferingid=size.id,
            templateid=str(image.extra['templateid']),
            zoneid=str(image.extra['zoneid']),
            **extra_args
        )

        node = result['virtualmachine']

        return Node(
            id=node['id'],
            name=node['displayname'],
            state=self.NODE_STATE_MAP[node['state']],
            public_ips=[],
            private_ips=[],
            driver=self,
            extra={
                'zoneid': image.extra['zoneid'],
                'ip_addresses': [],
                'forwarding_rules': [],
            }
        )
