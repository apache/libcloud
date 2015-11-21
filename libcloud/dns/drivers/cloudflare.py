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

__all__ = [
    'CloudFlareDNSDriver'
]

import copy

from libcloud.common.base import JsonResponse, ConnectionUserAndKey
from libcloud.common.types import InvalidCredsError, LibcloudError
from libcloud.utils.py3 import httplib
from libcloud.dns.base import DNSDriver, Zone, Record
from libcloud.dns.types import Provider
from libcloud.dns.types import ZoneDoesNotExistError, RecordDoesNotExistError

API_URL = 'https://www.cloudflare.com/api_json.html'
API_HOST = 'www.cloudflare.com'
API_PATH = '/api_json.html'

ZONE_EXTRA_ATTRIBUTES = [
    'display_name',
    'zone_status',
    'zone_type',
    'host_id',
    'host_pubname',
    'host_website',
    'fqdns',
    'vtxt',
    'step',
    'zone_status_class',
    'zone_status_desc',
    'orig_registrar',
    'orig_dnshost',
    'orig_ns_names'
]

RECORD_EXTRA_ATTRIBUTES = [
    'rec_tag',
    'display_name',
    'pro',
    'display_content',
    'ttl_ceil',
    'ssl_id',
    'ssl_status',
    'ssl_expires_on',
    'auto_ttl',
    'service_mode'
]


class CloudFlareDNSResponse(JsonResponse):
    def success(self):
        return self.status in [httplib.OK, httplib.CREATED, httplib.ACCEPTED]

    def parse_body(self):
        body = super(CloudFlareDNSResponse, self).parse_body()
        result = body.get('result', None)
        error_code = body.get('err_code', None)
        msg = body.get('msg', None)

        if error_code == 'E_UNAUTH':
            raise InvalidCredsError(msg)
        elif result == 'error' or error_code is not None:
            msg = 'Request failed: %s' % (self.body)
            raise LibcloudError(value=msg, driver=self.connection.driver)

        return body


class CloudFlareDNSConnection(ConnectionUserAndKey):
    host = API_HOST
    secure = True
    responseCls = CloudFlareDNSResponse

    def request(self, action, params=None, data=None, headers=None,
                method='GET'):
        params = params or {}
        data = data or {}

        base_params = {
            'email': self.user_id,
            'tkn': self.key,
            'a': action
        }
        params = copy.deepcopy(params)
        params.update(base_params)

        return super(CloudFlareDNSConnection, self).request(action=API_PATH,
                                                            params=params,
                                                            data=None,
                                                            method=method,
                                                            headers=headers)


class CloudFlareDNSDriver(DNSDriver):
    type = Provider.CLOUDFLARE
    name = 'CloudFlare DNS'
    website = 'https://www.cloudflare.com'
    connectionCls = CloudFlareDNSConnection

    def iterate_zones(self):
        # TODO: Support pagination
        result = self.connection.request(action='zone_load_multi').object
        zones = self._to_zones(data=result['response']['zones']['objs'])

        return zones

    def iterate_records(self, zone):
        # TODO: Support pagination
        params = {'z': zone.domain}
        result = self.connection.request(action='rec_load_all', params=params).object
        records = self._to_records(zone=zone, data=result['response']['recs']['objs'])
        return records

    def ex_get_zone_stats(self, zone, interval=30):
        params = {'z': zone.domain, 'interval': interval}
        result = self.connection.request(action='stats', params=params).object
        result = result['response']['result']['objs']
        return result

    def ex_zone_check(self, zones):
        zone_domains = [zone.domain for zone in zones]
        zone_domains = ','.join(zone_domains)
        params = {'zones': zone_domains}
        result = self.connection.request(action='zone_check', params=params).object
        result = result['response']['zones']
        return result

    def ex_get_ip_threat_score(self, ip):
        """
        Retrieve current threat score for a given IP. Note that scores are on
        a logarithmic scale, where a higher score indicates a higher threat.
        """
        params = {'ip': ip}
        result = self.connection.request(action='ip_lkup', params=params).object
        result = result['response']
        return result

    def ex_get_zone_settings(self, zone):
        """
        Retrieve all current settings for a given zone.
        """
        params = {'z': zone.domain}
        result = self.connection.request(action='zone_settings', params=params).object
        result = result['response']['result']['objs'][0]
        return result

    def ex_set_zone_security_level(self, zone, level):
        """
        Set the zone Basic Security Level to I'M UNDER ATTACK! / HIGH / MEDIUM /
        LOW / ESSENTIALLY OFF.

        :param level: Security level. Valid values are: help, high, med, low,
                      eoff.
        :type level: ``str``
        """
        params = {'z': zone.domain, 'v': level}
        result = self.connection.request(action='sec_lvl', params=params).object
        return result.get('result', None) == 'success'

    def ex_set_zone_cache_level(self, zone, level):
        """
        Set the zone caching level.

        :param level: Caching level. Valid values are: agg (aggresive), basic.
        :type level: ``str``
        """
        params = {'z': zone.domain, 'v': level}
        result = self.connection.request(action='cache_lvl', params=params).object
        return result.get('result', None) == 'success'

    def ex_enable_development_mode(self, zone):
        """
        Enable development mode. When Development Mode is on the cache is
        bypassed. Development mode remains on for 3 hours or until when it is
        toggled back off.
        """
        params = {'z': zone.domain, 'v': 1}
        result = self.connection.request(action='devmode', params=params).object
        return result.get('result', None) == 'success'

    def ex_disable_development_mode(self, zone):
        """
        Disable development mode.
        """
        params = {'z': zone.domain, 'v': 0}
        result = self.connection.request(action='devmode', params=params).object
        return result.get('result', None) == 'success'

    def ex_purge_cache_files(self, zone):
        """
        Purge CloudFlare of any cached files.
        """
        params = {'z': zone.domain, 'v': 1}
        result = self.connection.request(action='fpurge_ts', params=params).object
        return result.get('result', None) == 'success'

    def ex_purge_cache_file(self, zone, url):
        """
        Purgle single file from CloudFlare's cache.

        :param url: URL to the file to purge from cache.
        :type url: ``str``
        """
        params = {'z': zone.domain, 'url': url}
        result = self.connection.request(action='zone_file_purge', params=params).object
        return result.get('result', None) == 'success'

    def ex_whitelist_ip(self, zone, ip):
        """
        Whitelist the provided IP.
        """
        params = {'z': zone.domain, 'key': ip}
        result = self.connection.request(action='wl', params=params).object
        return result.get('result', None) == 'success'

    def ex_blacklist_ip(self, zone, ip):
        """
        Blacklist the provided IP.
        """
        params = {'z': zone.domain, 'key': ip}
        result = self.connection.request(action='ban', params=params).object
        return result.get('result', None) == 'success'

    def ex_unlist_ip(self, zone, ip):
        """
        Remove provided ip from the whitelist and blacklist.
        """
        params = {'z': zone.domain, 'key': ip}
        result = self.connection.request(action='nul', params=params).object
        return result.get('result', None) == 'success'

    def ex_enable_ipv6_support(self, zone):
        """
        Enable IPv6 support for the provided zone.
        """
        params = {'z': zone.domain, 'v': 3}
        result = self.connection.request(action='ipv46', params=params).object
        return result.get('result', None) == 'success'

    def ex_disable_ipv6_support(self, zone):
        """
        Disable IPv6 support for the provided zone.
        """
        params = {'z': zone.domain, 'v': 0}
        result = self.connection.request(action='ipv46', params=params).object
        return result.get('result', None) == 'success'


    def _to_zones(self, data):
        zones = []

        for item in data:
            zone = self._to_zone(item=item)
            zones.append(zone)

        return zones

    def _to_zone(self, item):
        type = 'master' if item.get('zone_type', '').lower() == 'p' else 'slave'

        extra = {}
        extra['props'] = item.get('props', {})
        extra['confirm_code'] = item.get('confirm_code', {})
        extra['allow'] = item.get('allow', {})
        for attribute in ZONE_EXTRA_ATTRIBUTES:
            value = item.get(attribute, None)
            extra[attribute] = value

        zone = Zone(id=str(item['zone_id']), domain=item['zone_name'], type=type,
                    ttl=None, driver=self, extra=extra)
        return zone

    def _to_records(self, zone, data):
        records = []

        for item in data:
            record = self._to_record(zone=zone, item=item)
            records.append(record)

        return records

    def _to_record(self, zone, item):
        name = self._get_record_name(item=item)
        type = item['type']
        data = item['content']

        extra = {}
        extra['ttl'] = item['ttl']
        extra['props'] = item.get('props', {})
        for attribute in RECORD_EXTRA_ATTRIBUTES:
            value = item.get(attribute, None)
            extra[attribute] = value

        record = Record(id=str(item['rec_id']), name=name, type=type,
                        data=data, zone=zone, driver=self, extra=extra)
        return record

    def _get_record_name(self, item):
        name = item['name'].replace('.' + item['zone_name'], '') or None
        if name:
            name = name.replace(item['zone_name'], '') or None
        return name
