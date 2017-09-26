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
import json
import time

from libcloud.common.exceptions import BaseHTTPError
from libcloud.common.types import LibcloudError


class UpcloudTimeoutException(LibcloudError):
    pass


class UpcloudCreateNodeRequestBody(object):
    """
    Body of the create_node request

    Takes the create_node arguments (**kwargs) and constructs the request body

    :param      user_id: required for authentication (required)
    :type       user_id: ``str``

    :param      name: Name of the created server (required)
    :type       name: ``str``

    :param      size: The size of resources allocated to this node.
    :type       size: :class:`.NodeSize`

    :param      image: OS Image to boot on node.
    :type       image: :class:`.NodeImage`

    :param      location: Which data center to create a node in. If empty,
                        undefined behavior will be selected. (optional)
    :type       location: :class:`.NodeLocation`

    :param      auth: Initial authentication information for the node
                            (optional)
    :type       auth: :class:`.NodeAuthSSHKey`

    """

    def __init__(self, user_id, name, size, image, location, auth=None):
        self.body = {
            'server': {
                'title': name,
                'hostname': 'localhost',
                'plan': size.id,
                'zone': location.id,
                'login_user': _LoginUser(user_id, auth).to_dict(),
                'storage_devices': _StorageDevice(image, size).to_dict()
            }
        }

    def to_json(self):
        """
        Serializes the body to json

        :return: JSON string
        :rtype: ``str``
        """
        return json.dumps(self.body)


class UpcloudNodeDestroyer(object):
    """
    Helper class for destroying node.
    Node must be first stopped and then it can be
    destroyed

    :param  upcloud_node_operations: UpcloudNodeOperations instance
    :type   upcloud_node_operations: :class:`.UpcloudNodeOperations`

    :param  sleep_func: Callable function, which sleeps.
        Takes int argument to sleep in seconds (optional)
    :type   sleep_func: ``function``

    """

    WAIT_AMOUNT = 2
    SLEEP_COUNT_TO_TIMEOUT = 20

    def __init__(self, upcloud_node_operations, sleep_func=None):
        self._operations = upcloud_node_operations
        self._sleep_func = sleep_func or time.sleep
        self._sleep_count = 0

    def destroy_node(self, node_id):
        """
        Destroys the given node.

        :param  node_id: Id of the Node.
        :type   node_id: ``int``
        """
        self._stop_called = False
        self._sleep_count = 0
        return self._do_destroy_node(node_id)

    def _do_destroy_node(self, node_id):
        state = self._operations.get_node_state(node_id)
        if state == 'stopped':
            self._operations.destroy_node(node_id)
            return True
        elif state == 'error':
            return False
        elif state == 'started':
            if not self._stop_called:
                self._operations.stop_node(node_id)
                self._stop_called = True
            else:
                # Waiting for started state to change and
                # not calling stop again
                self._sleep()
            return self._do_destroy_node(node_id)
        elif state == 'maintenance':
            # Lets wait maintenace state to go away and retry destroy
            self._sleep()
            return self._do_destroy_node(node_id)
        elif state is None:  # Server not found any more
            return True

    def _sleep(self):
        if self._sleep_count > self.SLEEP_COUNT_TO_TIMEOUT:
            raise UpcloudTimeoutException("Timeout, could not destroy node")
        self._sleep_count += 1
        self._sleep_func(self.WAIT_AMOUNT)


class UpcloudNodeOperations(object):
    """
    Helper class to start and stop node.

    :param  conneciton: Connection instance
    :type   connection: :class:`.UpcloudConnection`
    """

    def __init__(self, connection):
        self.connection = connection

    def stop_node(self, node_id):
        """
        Stops the node

        :param  node_id: Id of the Node
        :type   node_id: ``int``
        """
        body = {
            'stop_server': {
                'stop_type': 'hard'
            }
        }
        self.connection.request('1.2/server/{0}/stop'.format(node_id),
                                method='POST',
                                data=json.dumps(body))

    def get_node_state(self, node_id):
        """
        Get the state of the node.

        :param  node_id: Id of the Node
        :type   node_id: ``int``

        :rtype: ``str``
        """

        action = '1.2/server/{0}'.format(node_id)
        try:
            response = self.connection.request(action)
            return response.object['server']['state']
        except BaseHTTPError as e:
            if e.code == 404:
                return None
            raise

    def destroy_node(self, node_id):
        """
        Destroys the node.

        :param  node_id: Id of the Node
        :type   node_id: ``int``
        """
        self.connection.request('1.2/server/{0}'.format(node_id),
                                method='DELETE')


class _LoginUser(object):

    def __init__(self, user_id, auth=None):
        self.user_id = user_id
        self.auth = auth

    def to_dict(self):
        login_user = {'username': self.user_id}
        if self.auth is not None:
            login_user['ssh_keys'] = {
                'ssh_key': [self.auth.pubkey]
            }
        else:
            login_user['create_password'] = 'yes'

        return login_user


class _StorageDevice(object):

    def __init__(self, image, size):
        self.image = image
        self.size = size

    def to_dict(self):
        extra = self.image.extra
        if extra['type'] == 'template':
            return self._storage_device_for_template_image()
        elif extra['type'] == 'cdrom':
            return self._storage_device_for_cdrom_image()

    def _storage_device_for_template_image(self):
        storage_devices = {
            'storage_device': [{
                'action': 'clone',
                'title': self.image.name,
                'storage': self.image.id
            }]
        }
        return storage_devices

    def _storage_device_for_cdrom_image(self):
        storage_devices = {
            'storage_device': [
                {
                    'action': 'create',
                    'title': self.image.name,
                    'size': self.size.disk,
                    'tier': self.size.extra['storage_tier']

                },
                {
                    'action': 'attach',
                    'storage': self.image.id,
                    'type': 'cdrom'
                }
            ]
        }
        return storage_devices
