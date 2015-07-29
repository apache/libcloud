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

from libcloud.utils.py3 import httplib
from libcloud.common.base import ConnectionKey
from libcloud.common.types import ProviderError
from libcloud.storage.base import Object, Container, StorageDriver
from libcloud.storage.types import ContainerIsNotEmptyError
from libcloud.storage.types import ContainerDoesNotExistError
from libcloud.storage.types import ObjectDoesNotExistError
from libcloud.common.runabove import API_ROOT, RunAboveConnection
from libcloud.common.runabove import RunAboveResponse


class ContainerConnection(ConnectionKey):
    responseCls = RunAboveResponse

    def add_default_headers(self, headers):
        headers.update({
            'X-Auth-Token': self.key
        })
        return headers


class RunAboveContainer(Container):
    def get_object(self, object_name):
        return self.driver.get_object(container_name=self.name,
                                      object_name=object_name,
                                      ex_location=self.extra['region'])


class RunAboveStorageDriver(StorageDriver):
    """
    Libcloud driver for the RunAbove API

    For more information on the RunAbove API, read the official reference:

        https://api.runabove.com/console/
    """
    name = 'RunAbove'
    website = 'https://www.runabove.com/'
    connectionCls = RunAboveConnection
    containerConnectionCls = ContainerConnection
    hash_type = 'md5'
    supports_chunked_encoding = False
    ex_location = None

    def __init__(self, key, secret, ex_consumer_key=None, ex_location=None):
        """
        Instantiate the driver with the given API credentials.

        :param key: Your application key (required)
        :type key: ``str``

        :param secret: Your application secret (required)
        :type secret: ``str``

        :param ex_consumer_key: Your consumer key (required)
        :type ex_consumer_key: ``str``

        :rtype: ``None``
        """
        self.datacenter = None
        self.consumer_key = ex_consumer_key
        self.location = ex_location
        StorageDriver.__init__(self, key, secret,
                               ex_consumer_key=ex_consumer_key)
        response = self.connection.request(action='%s/token' % API_ROOT)\
            .object
        self.auth_token = response["X-Auth-Token"]
        self.auth_description = response['token']

    def iterate_containers(self):
        action = API_ROOT + '/storage'
        response = self.connection.request(action)
        return self._to_containers(response.object)

    def iterate_container_objects(self, container):
        action = '%s/storage/%s' % (API_ROOT, container.name)
        location = container.extra['region']
        data = {
            'region': location,
            'limit': 1000,
        }
        try:
            response = self.connection.request(action, data=data)
        except ProviderError as err:
            if err.http_code == httplib.NOT_FOUND:
                raise ContainerDoesNotExistError(value=None,
                                                 driver=self,
                                                 container_name=container.name)
            raise err
        json_response = response.object
        container = self._to_container(json_response, location)
        return self._to_objects(response.object['objects'],
                                container=container)

    def list_container_objects(self, container):
        return list(self.iterate_container_objects(container))

    def get_container(self, container_name, ex_location=None):
        """
        Return a container instance.

        :param container_name: Container name.
        :type container_name: ``str``

        :param ex_location: Region where to get
        :type ex_location: ``str``

        :return: :class:`Container` instance.
        :rtype: :class:`Container`
        """
        action = '%s/storage/%s' % (API_ROOT, container_name)
        location = self._check_location(ex_location)
        data = {
            'region': location,
        }
        try:
            response = self.connection.request(action, data=data)
        except ProviderError as err:
            if err.http_code == httplib.NOT_FOUND:
                raise ContainerDoesNotExistError(value=None,
                                                 driver=self,
                                                 container_name=container_name)
            raise err
        return self._to_container(response.object, location=location)

    def get_object(self, container_name, object_name, ex_location=None):
        # TODO: Remake with Swift request
        location = self._check_location(ex_location)
        action = '%s/storage/%s' % (API_ROOT, container_name)
        data = {
            'region': location,
            'limit': 1000,
        }
        try:
            response = self.connection.request(action, data=data)
            json_response = response.object
            container = self._to_container(json_response, location)
            obj = [o for o in json_response['objects']
                   if o['name'] == object_name][0]
        except ProviderError as err:
            if err.http_code == httplib.NOT_FOUND:
                raise ContainerDoesNotExistError(value=None,
                                                 driver=self,
                                                 container_name=container_name)
            raise err
        except IndexError:
            raise ObjectDoesNotExistError(object_name=object_name,
                                          value='', driver=self)
        return self._to_object(obj, container=container)

    def _put_data(self, location, action, data):
        """Common method for put data and except errors."""
        conn = self._get_container_connection(location)
        try:
            conn.request(action=action, data=data, method="PUT")
        except ProviderError as err:
            if err.http_code == httplib.NOT_FOUND:
                raise ContainerDoesNotExistError(value=None,
                                                 driver=self,
                                                 container_name=None)
            raise err

    def upload_object(self, file_path, container, object_name, extra=None,
                      verify_hash=True, headers=None):
        action = '/%s/%s' % (container.name, object_name)
        data = open(file_path, 'rb').read()
        self._put_data(container.extra['region'], action, data)
        return container.get_object(object_name)

    def upload_object_via_stream(self, iterator, container, object_name,
                                 extra=None, headers=None):
        action = '/%s/%s' % (container.name, object_name)
        data = iterator.read()
        self._put_data(container.extra['region'], action, data)
        return container.get_object(object_name)

    def delete_object(self, obj):
        action = '/%s/%s' % (obj.container.name, obj.name)
        conn = self._get_container_connection(obj.container.extra['region'])
        try:
            response = conn.request(action=action, method="DELETE")
        except ProviderError as err:
            if err.http_code == httplib.NOT_FOUND:
                raise ObjectDoesNotExistError(value=None,
                                              driver=self,
                                              object_name=obj.name)
            raise err
        return response.status == httplib.NO_CONTENT

    def create_container(self, container_name, ex_location=None):
        action = '%s/storage' % API_ROOT
        location = self._check_location(ex_location)
        data = {
            'region': location,
            'name': container_name
        }
        response = self.connection.request(action=action, data=data,
                                           method='POST')
        return self._to_container(response.object, location)

    def delete_container(self, container):
        action = '/%s' % container.name
        location = container.extra['region']
        conn = self._get_container_connection(location)
        try:
            conn.request(action, method='DELETE')
        except ProviderError as err:
            if err.http_code == httplib.NOT_FOUND:
                raise ContainerDoesNotExistError(value=None,
                                                 driver=self,
                                                 container_name=container.name)
            elif err.http_code == httplib.CONFLICT:
                value = 'Container must be empty before it can be deleted.',
                raise ContainerIsNotEmptyError(value=value,
                                               driver=self,
                                               container_name=container.name)
            raise err
        return True

    def download_object(self, obj, destination_path, overwrite_existing=False,
                        delete_on_failure=True):
        action = '/%s/%s' % (obj.container.name, obj.name)
        conn = self._get_container_connection(obj.container.extra['region'])
        response = conn.request(action, raw=True, method='GET')
        return self._get_object(
            obj=obj, callback=self._save_object, response=response,
            callback_kwargs={'response': response.response, 'obj': obj,
                             'destination_path': destination_path,
                             'overwrite_existing': overwrite_existing,
                             'delete_on_failure': delete_on_failure},
            success_status_code=httplib.OK)

    def _to_object(self, obj, container):
        json_obj = obj.copy()
        extra = {'region': container.extra['region']}
        meta_data = {
            'lastModified': json_obj['lastModified'],
            'contentType': json_obj['contentType']
        }
        return Object(name=json_obj['name'], size=json_obj['size'],
                      hash=None, extra=extra, meta_data=meta_data,
                      container=container, driver=self)

    def _to_objects(self, objs, container):
        return (self._to_object(obj, container) for obj in objs)

    def _to_container(self, obj, location=None):
        json_obj = obj.copy()
        name = json_obj.pop('name')
        json_obj.pop('objects', None)
        json_obj['region'] = json_obj.get('region', location)
        return RunAboveContainer(name=name, extra=json_obj, driver=self)

    def _to_containers(self, objs, location=None):
        return (self._to_container(con, location) for con in objs)

    def _ex_connection_class_kwargs(self):
        return {'ex_consumer_key': self.consumer_key}

    def _check_location(self, location):
        location = location or self.location
        if location is None:
            raise TypeError("You must provide a location at driver "
                            "instanciation or when using method with "
                            "'ex_location'.")
        return location

    def _get_container_connection(self, location):
        catalog = [e for e in self.auth_description['catalog']
                   if e['type'] == 'object-store'][0]
        endpoint = [e for e in catalog['endpoints']
                    if e['region'] == location][0]
        return self.containerConnectionCls(key=self.auth_token,
                                           url=endpoint['url'])
