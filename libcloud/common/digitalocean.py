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

"""
Common settings and connection objects for DigitalOcean Cloud
"""

from libcloud.utils.py3 import httplib

from libcloud.common.base import BaseDriver
from libcloud.common.base import ConnectionUserAndKey, ConnectionKey
from libcloud.common.base import JsonResponse
from libcloud.common.types import InvalidCredsError

__all__ = [
    'DigitalOcean_v1_Response',
    'DigitalOcean_v1_Connection',
    'DigitalOcean_v2_Response',
    'DigitalOcean_v2_Connection',
    'DigitalOceanBaseDriver'
]


class DigitalOcean_v1_Response(JsonResponse):
    def parse_error(self):
        if self.status == httplib.FOUND and '/api/error' in self.body:
            # Hacky, but DigitalOcean error responses are awful
            raise InvalidCredsError(self.body)
        elif self.status == httplib.UNAUTHORIZED:
            body = self.parse_body()
            raise InvalidCredsError(body['message'])
        else:
            body = self.parse_body()

            if 'error_message' in body:
                error = '%s (code: %s)' % (body['error_message'], self.status)
            else:
                error = body
            return error


class DigitalOcean_v1_Connection(ConnectionUserAndKey):
    """
    Connection class for the DigitalOcean (v1) driver.
    """

    host = 'api.digitalocean.com'
    responseCls = DigitalOcean_v1_Response

    def add_default_params(self, params):
        """
        Add parameters that are necessary for every request

        This method adds ``client_id`` and ``api_key`` to
        the request.
        """
        params['client_id'] = self.user_id
        params['api_key'] = self.key
        return params


class DigitalOcean_v2_Response(JsonResponse):
    valid_response_codes = [httplib.OK, httplib.ACCEPTED, httplib.CREATED,
                            httplib.NO_CONTENT]

    def parse_error(self):
        if self.status == httplib.UNAUTHORIZED:
            body = self.parse_body()
            raise InvalidCredsError(body['message'])
        else:
            body = self.parse_body()
            if 'message' in body:
                error = '%s (code: %s)' % (body['message'], self.status)
            else:
                error = body
            return error

    def success(self):
        return self.status in self.valid_response_codes


class DigitalOcean_v2_Connection(ConnectionKey):
    """
    Connection class for the DigitalOcean (v2) driver.
    """

    host = 'api.digitalocean.com'
    responseCls = DigitalOcean_v2_Response

    def add_default_headers(self, headers):
        """
        Add headers that are necessary for every request

        This method adds ``token`` to the request.
        """
        headers['Authorization'] = 'Bearer %s' % (self.key)
        headers['Content-Type'] = 'application/json'
        return headers


class DigitalOceanConnection(DigitalOcean_v2_Connection):
    """
    Connection class for the DigitalOcean driver.
    """
    pass


class DigitalOceanResponse(DigitalOcean_v2_Response):
    pass


class DigitalOceanBaseDriver(BaseDriver):
    """
    DigitalOcean BaseDriver
    """
    name = 'DigitalOcean'
    website = 'https://www.digitalocean.com'

    def __new__(cls, key, secret=None, api_version='v2', **kwargs):
        if cls is DigitalOceanBaseDriver:
            if api_version == 'v1' or secret is not None:
                cls = DigitalOcean_v1_BaseDriver
            elif api_version == 'v2':
                cls = DigitalOcean_v2_BaseDriver
            else:
                raise NotImplementedError('Unsupported API version: %s' %
                                          (api_version))
        return super(DigitalOceanBaseDriver, cls).__new__(cls, **kwargs)

    def ex_account_info(self):
        raise NotImplementedError(
            'ex_account_info not implemented for this driver')

    def ex_list_events(self):
        raise NotImplementedError(
            'ex_list_events not implemented for this driver')

    def ex_get_event(self, event_id):
        raise NotImplementedError(
            'ex_get_event not implemented for this driver')

    def _paginated_request(self, url, obj):
        raise NotImplementedError(
            '_paginated_requests not implemented for this driver')


class DigitalOcean_v1_BaseDriver(DigitalOceanBaseDriver):
    """
    DigitalOcean BaseDriver using v1 of the API.
    """
    connectionCls = DigitalOcean_v1_Connection

    def ex_get_event(self, event_id):
        """
        Get an event object

        :param      event_id: Event id (required)
        :type       event_id: ``str``
        """
        return self.connection.request('/v1/events/%s' % event_id).object


class DigitalOcean_v2_BaseDriver(DigitalOceanBaseDriver):
    """
    DigitalOcean BaseDriver using v2 of the API.
    """
    connectionCls = DigitalOcean_v2_Connection

    def ex_account_info(self):
        return self.connection.request('/v2/account').object['account']

    def ex_list_events(self):
        return self._paginated_request('/v2/actions', 'actions')

    def ex_get_event(self, event_id):
        """
        Get an event object

        :param      event_id: Event id (required)
        :type       event_id: ``str``
        """
        params = {}
        return self.connection.request('/v2/actions/%s' % event_id,
                                       params=params).object['action']

    def _paginated_request(self, url, obj):
        """
        Perform multiple calls in order to have a full list of elements when
        the API responses are paginated.

        :param url: API endpoint
        :type url: ``str``

        :param obj: Result object key
        :type obj: ``str``

        :return: ``list`` of API response objects
        """
        params = {}
        data = self.connection.request(url)
        try:
            pages = data.object['links']['pages']['last'].split('=')[-1]
            values = data.object[obj]
            for page in range(2, int(pages) + 1):
                params.update({'page': page})
                new_data = self.connection.request(url, params=params)

                more_values = new_data.object[obj]
                for value in more_values:
                    values.append(value)
            data = values
        except KeyError:  # No pages.
            data = data.object[obj]

        return data
