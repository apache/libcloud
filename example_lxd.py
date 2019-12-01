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

from libcloud.container.types import Provider
from libcloud.container.providers import get_driver


def main():

    #   LXD API specification can be found at:
    # https://github.com/lxc/lxd/blob/master/doc/rest-api.md#10containersnamemetadata

    # LXD host change accordingly
    host_lxd = 'https://192.168.2.4'

    # port that LXD server is listening at
    # change this according to your configuration
    port_id = 8443

    # get the libcloud LXD driver
    lxd_driver = get_driver(Provider.LXD)

    # acquire the connection.
    # certificates should  have been  added to the LXD server
    # here we assume they are on the same directory change
    # accordingly
    conn = lxd_driver(key='', secret='', secure=False,
                      host=host_lxd, port=port_id, key_file='lxd.key', cert_file='lxd.crt')

    # this API call does not require authentication
    api_end_points = conn.get_api_endpoints()
    print(api_end_points.parse_body())

    # this API call is allowed for everyone (but result varies)
    api_version = conn.get_to_version()
    print(api_version.parse_body())

    # get the list of the containers
    containers = conn.list_containers()
    print(containers)


if __name__ == '__main__':
    main()