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
from pylxd import Client
import requests


def pylxdFunc():

    # LXD host change accordingly
    endpoint = 'https://192.168.2.4:8443'

    cert = ('lxd.crt', 'lxd.key')

    client = Client(endpoint=endpoint, cert=cert, verify=False)

    containers = client.containers.all()

    print("Number of containers: ", len(containers))

    for container in containers:
        print("Container name: ", container.name)

    new_container = 'fourth-lxd-container'


    if new_container not in [container.name for container in containers]:
        config = {'name': new_container, 'source': {'type': 'none',
                                                         #"properties": {                                          # Properties
                                                         #                   "os": "ubuntu",
                                                         #                   "release": "18.04",
                                                         #                   "architecture": "amd64"
                                                        }}#}

        container = client.containers.create(config, wait=True)

    # get all images
    images = client.images.all()
    print("Number of images: ",len(images))

    for image in images:
        print("Image name: ", image.filename)


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

    if len(containers) == 0:
        print("No containers have been created")
    else:
        print("Number of containers: %s" % len(containers))
        for container in containers:
            print("Container: %s is: %s" % (container.name, container.state))


    # start the first container
    print("Starting container: %s" % containers[0].name)
    container = conn.start_container(container=containers[0])
    print("Container: %s is: %s" % (container.name, container.state))

    # stop the container returned
    print("Stopping container: %s" % containers[0].name)
    container = conn.stop_container(container=container)
    print("Container: %s is: %s" % (container.name, container.state))

    # restart the container
    print("Restarting container: %s" % container.name)
    container = conn.restart_container(container=container)
    print("Container: %s is: %s" % (container.name, container.state))

    if len(containers) == 2:

        # delete the second container
        print("Deleting container: %s" % containers[1].name)
        response = conn.destroy_container(container=containers[1])
        print("Response from attempting to delete container %s " % (containers[1].name), " ", response)

    # create a new container
    name = 'third-lxd-container'

    if name not in [container.name for container in containers]:

        print("Creating container: %s" % name)
        container = conn.deploy_container(name=name, image=None)
        print("Response from attempting to create container: ", container)

        # get the list of the containers
        containers = conn.list_containers()

        if len(containers) == 0:
            print("No containers have been created")
        else:
            print("Number of containers: %s" % len(containers))
            for container in containers:
                print("Container: %s is: %s" % (container.name, container.state))

    # get the images this LXD server is publishing
    images = conn.list_images()

    print("Number of images: ", len(images))

    for image in images:
        print("Image: ", image.name)
        print("\tPath ",image.path)
        print("\tVersion ", image.version)

    #container_id = containers[0].name
    #container_url = '%s:%s/1.0/containers/%s/state' % ('https://192.168.2.4', port_id, container_id)
    #cert=('lxd.crt', 'lxd.key' )
    #data = {"action":'start', "timeout":30, "statefule":True}
    #r = requests.put(container_url, json=data, verify=False, cert=cert)
    #print("put of 1.0/containers/%s/state returned: "%(container_id) + r.text)

    #data['action'] = 'stop'
    #r = requests.put(container_url, json=data, verify=False, cert=cert)
    #print("put of 1.0/containers/%s/state returned: " % (container_id) + r.text)


    # start a container
    #container = conn.start_container(container=containers[0])
    #print(container)

    # stop the container


if __name__ == '__main__':
    #pylxdFunc()
    main()