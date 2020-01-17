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
from libcloud.container.base import Container, ContainerImage


def work_with_containers():
    print("Working with containers...")

    # LXD API specification can be found at:
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
    api_end_points = conn.ex_get_api_endpoints()
    print(api_end_points)

    # this API call is allowed for everyone (but result varies)
    api_version = conn.ex_get_server_configuration()
    print(api_version)

    # get the list of the containers
    containers = conn.list_containers()
    num_containers = len(containers)

    if num_containers == 0:
        print("\tNo containers have been created")
    else:
        print("\tNumber of containers: %s" % len(containers))
        for container in containers:
            print("\t\tContainer: %s is: %s" % (container.name, container.state))

    if num_containers != 0:
        container = containers[0]

        # start the first container
        print("\tStarting container: %s" % container.name)
        container = conn.start_container(container=container)
        print("\tContainer: %s is at state: %s" % (container.name, container.state))

        # restart the container
        print("\tRestarting container: %s" % container.name)
        container = conn.restart_container(container=container)
        print("\tContainer: %s is at state: %s" % (container.name, container.state))

        # freeze the container.
        print("\tFreezing container: %s" % container.name)
        container = conn.ex_freeze_container(container=container)
        print("\tContainer: %s is at state: %s" % (container.name, container.state))

        # unfreeze the container. A frozen container cannot be started/restarted/stopped
        # it has to be unfrozen first
        print("\tUnfreezing container: %s" % container.name)
        container = conn.ex_unfreeze_container(container=container)
        print("\tContainer: %s is at state: %s" % (container.name, container.state))

        # stop the container returned
        print("\tStopping container: %s" % container.name)
        container = conn.stop_container(container=container)
        print("\tContainer: %s is at state: %s" % (container.name, container.state))

    # let's try to create a new container
    # we need an image for this let's see what is installed
    images = conn.list_images()

    print("Number of images: ", len(images))

    for image in images:
        print("Image: ", image.name)
        print("\tPath ", image.path)
        print("\tVersion ", image.version)

    # let's use the first found
    if len(images) != 0:

        img_parameters = '{"source": {"type": "image", "fingerprint":"7ed08b435c92cd8a8a884c88e8722f2e7546a51e891982a90ea9c15619d7df9b"}}' #% images[0].name
        ex_devices = {"root": {"path": "/",
                                 "type": "disk",
                               'size': '7GB'
                                },
                      }

        container_name = "a-second-new-lxd-container"

        container = conn.deploy_container(name=container_name,
                                          image=None,
                                          parameters=img_parameters,
                                          ex_ephemeral=False,
                                          ex_devices=None)

        # make sure that we created a new container
        containers = conn.list_containers()

        if num_containers == len(containers):
            print("\tContainer %s has not been created " % container_name)
        else:

            # ok let's destroy the container
            # we first must stop it
            container = conn.stop_container(container=container)
            print("\tDeleting container: %s" % container.name)
            container = conn.destroy_container(container=container)
            print("\tContainer: %s is at state: %s" % (container.name, container.state))

            # make sure that we created a new container
            containers = conn.list_containers()

            if num_containers != len(containers):
                print("\tContainer %s could not be deleted. Is it running?" % container_name)

def work_with_images():

    print("Working with images...")

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

    # get the images this LXD server is publishing
    images = conn.list_images()

    print("Number of images: ", len(images))

    for image in images:
        print("Image: ", image.name)
        print("\tPath ", image.path)
        print("\tVersion ", image.version)

    conn.create_image()

def work_with_storage_pools():
    print("Working with storage pools...")

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

    # get the images this LXD server is publishing
    pools = conn.ex_list_storage_pools()

    print("Number of storage pools: ", len(pools))

    for pool in pools:
        print("\tPool: ",pool.name)
        print("\t\tDriver: ", pool.driver)
        print("\t\tUsed by: ", pool.used_by)
        print("\t\tConfig: ", pool.config)

    #conn.ex_delete_storage_pool(id="Pool100")

    definition={
        "driver": "zfs",
        "name": "Pool100",
        "config":{
            "size":"70MB"
        }
    }

    #conn.ex_create_storage_pool(definition=definition)


    #conn.ex_delete_storage_pool_volume(pool_id="Pool100", type="custom", name="FirstUIVolume")

    volumes = conn.ex_list_storage_pool_volumes(pool_id="Pool100")

    for volume in volumes:
        print(volume.name)

    definition={"config":
                    { "block.filesystem": "ext4",
                      "block.mount_options": "discard",
                        "size": "10",
                        "size_type":"GB"
                    },

                "name": "FirstUIVolume",
                "type": "custom"}
    #volume = conn.ex_create_storage_pool_volume(pool_id="Pool100", definition=definition)

    print("Volume name: ", volume.name)
    print("Volume size: ", volume.size)

    definition = {"config": {"size": "8737418240"} }
    #volume = conn.ex_replace_storage_volume_config(pool_id="Pool100",
    #                                               type="custom", name="FirstUIVolume", definition=definition)

    #print("Volume name: ", volume.name)
    #print("Volume size: ", volume.size)
    container = conn.get_container(id="second-lxd-container")
    container = conn.stop_container(container=container)
    print("\tContainer: %s is at state: %s" % (container.name, container.state))

    conn.ex_attach_storage_volume_to_container(container_id="second-lxd-container", pool_id="Pool100",
                                               volume_id="FirstUIVolume")


if __name__ == '__main__':

    #work_with_containers()
    #work_with_images()
    work_with_storage_pools()