"""
Module for handling LXC containers
"""
from pylxd import Client
from pylxd.exceptions import ClientConnectionFailed
from pylxd.exceptions import LXDAPIException
from libcloud.container.base import (Container, ContainerDriver, ContainerImage)
from libcloud.container.providers import Provider
from libcloud.container.types import ContainerState


class LXCContainerDriver(ContainerDriver):
    """
    Driver for LXC containers
    """
    type = Provider.LXC
    name = 'LXC'
    #website = 'http://docker.io'
    #connectionCls = DockerConnection
    supports_clusters = False
    version = '2.0'

    def __init__(self, key='', secret='', secure=False, 
                 host='localhost', port='8443', 
                 key_file=None,
                 cert_file=None, ca_cert=None, **kwargs):

        super(LXCContainerDriver, self).__init__(key=key,
                                                secret=secret,
                                                secure=secure, 
                                                host=host,
                                                port=port,
                                                key_file=key_file,
                                                cert_file=cert_file, 
                                                **kwargs)
        # the pylxd client
        # should we try to connect on instantiation?
        # for the moment try to do so...this may well fail
        try:
           self.client = Client(endpoint=host, cert=(cert_file, key_file), 
                                verify=kwargs.get('verify', False), 
                                timeout=kwargs.get('timeout', None),
                                version=kwargs.get('version', LXCContainerDriver.version))
        except ClientConnectionFailed as e: 
            raise Exception(str(e))
    
    def deploy_container(self, config, wait,name, image, cluster=None,
                         parameters=None, start=True):
       
        """
        Deploy an installed container image

        :param name: The name of the new container
        :type  name: ``str``

        :param image: The container image to deploy
        :type  image: :class:`.ContainerImage`

        :param cluster: The cluster to deploy to, None is default
        :type  cluster: :class:`.ContainerCluster`

        :param parameters: Container Image parameters
        :type  parameters: ``str``

        :param start: Start the container on deployment
        :type  start: ``bool``

        :rtype: :class:`.Container`
        """
        try: 

            lxc_container = self.client.containers.create(config=config, wait=wait)

            # TODO: what happens if wait=False then this is async call
            # perhaps we need to treat it differently
            state= ContainerState.UNKNOWN
            if start:
                lxc_container.start()
                state=ContainerState.RUNNING

            container = Container(id="some-id", driver=self, name="some-name", state=state, ip_addresses="some-ip", image="some-image")
        except LXDAPIException as e:
            raise LXDAPIException(e)

        return container

    def get_container(self, id):

        """
        Get a container by ID

        :param id: The ID of the container to get
        :type  id: ``str``

        :rtype: :class: pylxd.models.Container
        """

        # TODO: what happens if the id does not exist
        container = self.client.containers.get( id)
        return container

    def start_container(self, container):
        
        """
        Start a ontainer

        :param container: The container to start
        :type  container: :class:`libcloud.container.base.Container`

        :rtype: :class:`libcloud.container.base.Container`
        """

        if container is not None:
            # we perhaps want to log this
            # this may be None??
            lxc_container = self.get_container(id=container.name)
            # start the associated LXC container
            # docs: https://pylxd.readthedocs.io/en/latest/api.html#container
            # this seems to have a timeout of 30secs
            lxc_container.start()

        return container

    def stop_container(self, container):
        """
        Stop a container

        :param container: The container to be stopped
        :type  container: :class:`libcloud.container.base.Container`

        :return: The container refreshed with current data
        :rtype: :class:`libcloud.container.base.Container
        """
      
        if container is not None:

            # this may be None??
            lxc_container = self.get_container(id=container.name)

            # stop the associated lxc container
            # docs: https://pylxd.readthedocs.io/en/latest/api.html#container
            # this seems to have a timeout of 30secs
            lxc_container.stop()
        return container

    def list_containers(self, image=None, cluster=None):
        """
        List the deployed container images

        :param image: Filter to containers with a certain image
        :type  image: :class:`.ContainerImage`

        :param cluster: Filter to containers in a cluster
        :type  cluster: :class:`.ContainerCluster`

        :rtype: ``list`` of :class:`.Container`
        """
        raise NotImplementedError(
            'list_containers not implemented for this driver')

    def restart_container(self, container):
        """
        Restart a deployed container

        :param container: The container to restart
        :type  container: :class:`.Container`

        :rtype: :class:`.Container`
        """
        raise NotImplementedError(
            'restart_container not implemented for this driver')

    def destroy_container(self, container):
        """
        Destroy a deployed container

        :param container: The container to destroy
        :type  container: :class:`.Container`

        :rtype: :class:`.Container`
        """
        raise NotImplementedError(
            'destroy_container not implemented for this driver')