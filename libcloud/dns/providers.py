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

from libcloud.utils.misc import get_driver as get_provider_driver
from libcloud.utils.misc import set_driver as set_provider_driver
from libcloud.dns.types import Provider

DRIVERS = {
    Provider.DUMMY:
    ('libcloud.dns.drivers.dummy', 'DummyDNSDriver'),
    Provider.LINODE:
    ('libcloud.dns.drivers.linode', 'LinodeDNSDriver'),
    Provider.ZERIGO:
    ('libcloud.dns.drivers.zerigo', 'ZerigoDNSDriver'),
    Provider.RACKSPACE:
    ('libcloud.dns.drivers.rackspace', 'RackspaceDNSDriver'),
    Provider.HOSTVIRTUAL:
    ('libcloud.dns.drivers.hostvirtual', 'HostVirtualDNSDriver'),
    Provider.ROUTE53:
    ('libcloud.dns.drivers.route53', 'Route53DNSDriver'),
    Provider.GANDI:
    ('libcloud.dns.drivers.gandi', 'GandiDNSDriver'),
    Provider.GOOGLE: ('libcloud.dns.drivers.google', 'GoogleDNSDriver'),
    Provider.SOFTLAYER:
    ('libcloud.dns.drivers.softlayer', 'SoftLayerDNSDriver'),
    Provider.DIGITAL_OCEAN:
    ('libcloud.dns.drivers.digitalocean', 'DigitalOceanDNSDriver'),
    Provider.WORLDWIDEDNS:
    ('libcloud.dns.drivers.worldwidedns', 'WorldWideDNSDriver'),
    Provider.DNSIMPLE:
    ('libcloud.dns.drivers.dnsimple', 'DNSimpleDNSDriver'),
    Provider.POINTDNS:
    ('libcloud.dns.drivers.pointdns', 'PointDNSDriver'),
    Provider.VULTR:
    ('libcloud.dns.drivers.vultr', 'VultrDNSDriver'),
    Provider.LIQUIDWEB:
    ('libcloud.dns.drivers.liquidweb', 'LiquidWebDNSDriver'),
    Provider.ZONOMI:
    ('libcloud.dns.drivers.zonomi', 'ZonomiDNSDriver'),
    Provider.DURABLEDNS:
    ('libcloud.dns.drivers.durabledns', 'DurableDNSDriver'),
    Provider.AURORADNS:
    ('libcloud.dns.drivers.auroradns', 'AuroraDNSDriver'),
    Provider.GODADDY:
    ('libcloud.dns.drivers.godaddy', 'GoDaddyDNSDriver'),
    Provider.CLOUDFLARE:
    ('libcloud.dns.drivers.cloudflare', 'CloudFlareDNSDriver'),

    # Deprecated
    Provider.RACKSPACE_US:
    ('libcloud.dns.drivers.rackspace', 'RackspaceUSDNSDriver'),
    Provider.RACKSPACE_UK:
    ('libcloud.dns.drivers.rackspace', 'RackspaceUKDNSDriver')
}


def get_driver(provider):
    return get_provider_driver(DRIVERS, provider)


def set_driver(provider, module, klass):
    return set_provider_driver(DRIVERS, provider, module, klass)
