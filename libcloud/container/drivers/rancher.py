import base64
import shlex

try:
    import simplejson as json
except:
    import json

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import b

from libcloud.common.base import JsonResponse, ConnectionUserAndKey
from libcloud.common.types import InvalidCredsError

from libcloud.container.base import (Container, ContainerDriver,
                                     ContainerImage)

from libcloud.container.providers import Provider
from libcloud.container.types import ContainerState

VALID_RESPONSE_CODES = [httplib.OK, httplib.ACCEPTED, httplib.CREATED,
                        httplib.NO_CONTENT]


class RancherResponse(JsonResponse):

    def parse_body(self):
        if len(self.body) == 0 and not self.parse_zero_length_body:
            return self.body
        valid_content_types = ['application/json',
                               'application/json; charset=utf-8']
        content_type = self.headers.get('content-type')
        if content_type in valid_content_types:
            return json.loads(self.body)

    def parse_error(self):
        if self.status == 401:
            raise InvalidCredsError('Invalid credentials')
        return self.body

    def success(self):
        return self.status in VALID_RESPONSE_CODES


class RancherException(Exception):

    def __init__(self, code, message):
        self.code = code
        self.message = message
        self.args = (code, message)

    def __str__(self):
        return "%s %s" % (self.code, self.message)

    def __repr__(self):
        return "RancherException %s %s" % (self.code, self.message)


class RancherConnection(ConnectionUserAndKey):

    responseCls = RancherResponse
    timeout = 30

    def add_default_headers(self, headers):
        """
        Add parameters that are necessary for every request
        If user and password are specified, include a base http auth
        header
        """
        headers['Content-Type'] = 'application/json'
        headers['Accept'] = 'application/json'
        if self.key and self.user_id:
            user_b64 = base64.b64encode(b('%s:%s' % (self.user_id, self.key)))
            headers['Authorization'] = 'Basic %s' % (user_b64.decode('utf-8'))
        return headers


class RancherContainerDriver(ContainerDriver):

    type = Provider.RANCHER
    name = 'Rancher'
    website = 'http://rancher.com'
    connectionCls = RancherConnection
    # Holding off on cluster support for now.
    # Only Environment API interaction enabled.
    supports_clusters = False
    # As in the /v1/
    version = '1'

    def __init__(self, key, secret, secure=True, host='localhost', port=443):
        """
        Rancher Container driver class.

        Example:

        >>> from libcloud.container.providers import get_driver
        >>> from libcloud.container.types import Provider

        >>> driver = get_driver(Provider.RANCHER)
        >>> connection = driver(key="ACCESS_KEY_HERE",
        secret="SECRET_KEY_HERE", host="172.30.0.100", port=8080)

        >>> image = ContainerImage("hastebin", "hastebin", "rlister/hastebin",
        "latest", driver=None)
        >>> newcontainer = connection.deploy_container("myawesomepastebin",
        image, environment={"STORAGE_TYPE": "file"})

        :param    key: API key or username to used (required)
        :type     key: ``str``

        :param    secret: Secret password to be used (required)
        :type     secret: ``str``

        :param    secure: Whether to use HTTPS or HTTP.
        :type     secure: ``bool``

        :param    host: Override hostname used for connections.
        :type     host: ``str``

        :param    port: Override port used for connections.
        :type     port: ``int``


        :return: ``None``
        """
        super(RancherContainerDriver, self).__init__(key=key, secret=secret,
                                                     secure=secure, host=host,
                                                     port=port)
        if host.startswith('http://'):
            secure = False

        # strip the prefix
        prefixes = ['http://', 'https://']
        for prefix in prefixes:
            if host.startswith(prefix):
                host = host.strip(prefix)

        self.connection.host = host
        self.connection.port = port
        self.connection.secure = secure

        # We only support environment api keys, meaning none of this:
        # self.baseuri = "/v%s/projects/%s" % (self.version, project_id)
        self.baseuri = "/v%s" % self.version

    def ex_list_stacks(self):
        """
        List all Rancher Stacks

        http://docs.rancher.com/rancher/v1.2/en/api/api-resources/environment/

        :rtype: ``list`` of ``dict``
        """

        result = self.connection.request(
            "%s/environments" % self.baseuri).object
        return result['data']

    def ex_deploy_stack(self, name, description=None, dockercompose=None,
                              environment=None, externalid=None, outputs=None,
                              previousenvironment=None,
                              previousexternalid=None, ranchercompose=None,
                              start=True):
        """
        Deploy a new stack.

        http://docs.rancher.com/rancher/v1.2/en/api/api-resources/environment/#create

        :param name: The desired name of the stack.
        :type name: ``str``

        :param description: A desired description for the stack.
        :type description: ``str``

        :param dockercompose: The Docker Compose configuration to use.
        :type dockercompose: ``str``

        :param environment: Environment K/V specific to this stack.
        :type environment: ``dict``

        :param externalid: The externalId of the stack.
        :type externalid: ``str``

        :param outputs: Any outputs the stack should contain.
        :type outputs: ``dict``

        :param previousenvironment: The previousEnvironment for this env.
        :type previousenvironment: ``dict``

        :param previousexternalid: The previousExternalId for this env.
        :type previousexternalid: ``str``

        :param ranchercompose: The Rancher Compose configuration for this env.
        :type ranchercompose: ``str``

        :param start: Whether to start this stack on creation.
        :type start: ``bool``

        :return: The newly created stack.
        :rtype: ``dict``
        """

        payload = {
            "description": description,
            "dockerCompose": dockercompose,
            "environment": environment,
            "externalId": externalid,
            "name": name,
            "outputs": outputs,
            "previousEnvironment": previousenvironment,
            "previousExternalId": previousexternalid,
            "rancherCompose": ranchercompose,
            "startOnCreate": start
        }
        data = json.dumps({k: v for k, v in payload.items() if v is not None})
        result = self.connection.request('%s/environments' %
                                         self.baseuri, data=data,
                                         method='POST').object

        return result

    def ex_get_stack(self, env_id):
        """
        Get a stack by ID

        :param env_id: The stack to be obtained.
        :type env_id: ``str``

        :rtype: ``dict``
        """
        result = self.connection.request("%s/environments/%s" %
                                         (self.baseuri, env_id)).object

        return result

    def ex_destroy_stack(self, env_id):
        """
        Destroy a stack by ID

        http://docs.rancher.com/rancher/v1.2/en/api/api-resources/environment/#delete

        :param env_id: The stack to be destroyed.
        :type env_id: ``str``

        :return: True if destroy was successful, False otherwise.
        :rtype: ``bool``
        """
        result = self.connection.request('%s/environments/%s' % (
                                         self.baseuri, env_id),
                                         method='DELETE')
        return result.status in VALID_RESPONSE_CODES

    def ex_activate_stack(self, env_id):
        """
        Activate Services for a stack.

        http://docs.rancher.com/rancher/v1.2/en/api/api-resources/environment/#activateservices

        :param env_id: The stack to activate services for.
        :type env_id: ``str``

        :return: True if activate was successful, False otherwise.
        :rtype: ``bool``
        """
        result = self.connection.request(
            '%s/environments/%s?action=activateservices' % (
                self.baseuri, env_id), method='POST'
        )
        return result.status in VALID_RESPONSE_CODES

    def ex_deactivate_stack(self, env_id):
        """
        Deactivate Services for a stack.

        http://docs.rancher.com/rancher/v1.2/en/api/api-resources/environment/#deactivateservices

        :param env_id: The stack to deactivate services for.
        :type env_id: ``str``

        :return: True if deactivate was successful, False otherwise.
        :rtype: ``bool``
        """

        result = self.connection.request(
            '%s/environments/%s?action=deactivateservices' % (
                self.baseuri, env_id), method='POST'
        )
        return result.status in VALID_RESPONSE_CODES

    def ex_list_services(self):
        """
        List all Rancher Services

        http://docs.rancher.com/rancher/v1.2/en/api/api-resources/service/

        :rtype: ``list`` of ``dict``
        """

        result = self.connection.request("%s/services" % self.baseuri).object
        return result['data']

    def ex_deploy_service(self, name, image, environmentid,
                          start=True, assignserviceipaddress=None,
                          service_description=None, externalid=None,
                          metadata=None, retainip=None, scale=None,
                          scalepolicy=None, secondarylaunchconfigs=None,
                          selectorcontainer=None, selectorlink=None,
                          vip=None, datavolumesfromlaunchconfigs=None,
                          disks=None, kind=None, memorymb=None,
                          networklaunchconfig=None, requsetedipaddress=None,
                          userdata=None, vcpu=None, **kwargs):
        """
        Deploy a Rancher Service under a stack.

        http://docs.rancher.com/rancher/v1.2/en/api/api-resources/service/#create

        :param name: The desired name of the service.
        :type name: ``str``

        :param image: The Image object to deploy.
        :type image: :class:`libcloud.container.base.ContainerImage`

        :param environmentid: The environment/stack ID this service is tied to.
        :type environmentid: ``str``

        :param start: Whether to start the service/container on creation.
        :type start: ``bool``

        :param assignserviceipaddress: The IP address to assign the service.
        :type assignserviceipaddress: ``bool``

        :param service_description: The service description.
        :type service_description: ``str``

        :param externalid: The externalId for this service.
        :type externalid: ``str``

        :param metadata: K/V Metadata for this service.
        :type metadata: ``dict``

        :param retainip: Whether this service should retain its IP.
        :type retainip: ``bool``

        :param scale: The scale of containers in this service.
        :type scale: ``int``

        :param scalepolicy: The scaling policy for this service.
        :type scalepolicy: ``dict``

        :param secondarylaunchconfigs: Secondary container launch configs.
        :type secondarylaunchconfigs: ``list``

        :param selectorcontainer: The selectorContainer for this service.
        :type selectorcontainer: ``str``

        :param selectorlink: The selectorLink for this service.
        :type selectorlink: ``type``

        :param vip: The VIP to assign to this service.
        :type vip: ``str``

        :param datavolumesfromlaunchconfigs: The dataVolumesFromLaunchConfigs.
        :type datavolumesfromlaunchconfigs: ``list``

        :param disks: The disks to associate with this container/service.
        :type disks: ``list``

        :param kind: The kind of object to deploy.
        :type kind: ``str``

        :param memorymb: The memoryMb to allow this container/service.
        :type memorymb: ``int``

        :param networklaunchconfig: The networkLaunchConfig for this container.
        :type networklaunchconfig: ``str``

        :param requsetedipaddress: The requested IP address for this container.
        :type requsetedipaddress: ``str``

        :param userdata: User data to associate with this container.
        :type userdata: ``str``

        :param vcpu: Virtual host cpu's to assign to allow this container.
        :type vcpu: ``int``

        :param blkiodeviceoptions: The blkioDeviceOptions for the container.
        :type blkiodeviceoptions: ``dict``

        :param build: Build details for the container.
        :type build: ``dict``

        :param capadd: Linux Capabilities to enable for this container.
        :type capadd: ``list``

        :param capdrop: Linux capabilities to disable for this container.
        :type capdrop: ``list``

        :param command: The command to execute when this container is run.
        :type command: ``list``

        :param count: The number of containers of this nature to launch.
        :type count: ``int``

        :param cpuset: Memory nodes in which to allow execution.
        :type cpuset: ``str``

        :param cpushares: Relative weight cpu shares to allow.
        :type cpushares: ``int``

        :param datavolumemounts: Data volume mountes this container should have
        :type datavolumemounts: ``dict``

        :param datavolumes: Data volumes to associate with this container.
        :type datavolumes: ``list``

        :param datavolumesfrom: Data volumes to inherit.
        :type datavolumesfrom: ``list``

        :param description: Description for this container.
        :type description: ``str``

        :param devices: Devices inside the container without privliged mode.
        :type devices: ``list``

        :param dns: DNS servers the container should utilize.
        :type dns: ``list``

        :param dnssearch: DNS search domains the container should utilize.
        :type dnssearch: ``list``

        :param domainname: The domain name the container should have.
        :type domainname: ``str``

        :param entrypoint: The entrypoint the container should have.
        :type entrypoint: ``list``

        :param environment: Environment variables the container should have.
        :type environment: ``dict``

        :param expose: Ports which should be exposed in the container.
        :type expose: ``list``

        :param extrahosts: Extra hosts file entries this container should have.
        :type extrahosts: ``list``

        :param healthcheck: Health check parameters for this container.
        :type healthcheck: ``dict``

        :param hostname: The hostname this container should have.
        :type hostname: ``str``

        :param instancelinks: Instance links the container should have.
        :type instancelinks: ``dict``

        :param labels: Labels to associate with this container.
        :type labels: ``dict``

        :param logconfig: Log configuration for this container.
        :type logconfig: ``dict``

        :param lxcconf: lxcConf specific to this container.
        :type lxcconf: ``dict``

        :param memory: The memory limit for this container.
        :type memory: ``int``

        :param memoryswap: Total memory limit for this container.
        :type memoryswap: ``int``

        :param networkcontainerrid: A Network container Id for this container.
        :type networkcontainerrid: ``dict``

        :param networkids: NetworkIds this container should contain.
        :type networkids: ``list``

        :param networkmode: The networkMode to enable for this container.
        :type networkmode: ``str``

        :param pidmode: The pidMode for this container.
        :type pidmode: ``str``

        :param ports: The ports to publicize for this container.
        :type ports: ``list``

        :param privileged: Whether to enable privileged mode for this container
        :type privileged: ``bool``

        :param publishallports: Publish all ports in container.
        :type publishallports: ``bool``

        :param readonly: Whether this container should be readOnly.
        :type readonly: ``bool``

        :param registrycredentialid: Registry credentials to use.
        :type registrycredentialid: ``dict``

        :param requestedhostid: Id of the requested host to run this container.
        :type requestedhostid: ``dict``

        :param restartpolicy: The container restart policy.
        :type restartpolicy: ``dict``

        :param securityopt: Security options to provide for this container.
        :type securityopt: ``list``

        :param stdinopen: Whether to keep stdin open.
        :type stdinopen: ``bool``

        :param tty: Enable a tty for this container.
        :type tty: ``bool``

        :param user: User this container should be tied to.
        :type user: ``str``

        :param volumedriver: The volume driver to use for this container.
        :type volumedriver: ``str``

        :param workingdir: The workingDir this container should start in.
        :type workingdir: ``str``

        :return: The newly created service.
        :rtype: ``dict``
        """

        service_specific_container_config = {
            "dataVolumesFromLaunchConfigs": datavolumesfromlaunchconfigs,
            "disks": disks,
            "kind": kind,
            "memoryMb": memorymb,
            "networkLaunchConfig": networklaunchconfig,
            "requestedIpAddress": requsetedipaddress,
            "userdata": userdata,
            "vcpu": vcpu
        }

        # Build the de-facto container payload
        # Note that we don't need to remove "name" since its None by default.
        launchconfig = self._build_payload(image, start, **kwargs)
        # Add in extra service configuration
        launchconfig.update(service_specific_container_config)
        launchconfig = json.dumps({k: v for k, v in launchconfig.items()
                                   if v is not None})
        service_payload = {
            "assignServiceIpAddress": assignserviceipaddress,
            "description": service_description,
            "environmentId": environmentid,
            "externalId": externalid,
            "launchConfig": json.loads(launchconfig),
            "metadata": metadata,
            "name": name,
            "retainIp": retainip,
            "scale": scale,
            "scalePolicy": scalepolicy,
            "secondaryLaunchConfigs": secondarylaunchconfigs,
            "selectorContainer": selectorcontainer,
            "selectorLink": selectorlink,
            "startOnCreate": start,
            "vip": vip
        }

        data = json.dumps({k: v for k, v in service_payload.items()
                           if v is not None})
        result = self.connection.request('%s/services' % self.baseuri,
                                         data=data, method='POST').object

        return result

    def ex_get_service(self, service_id):
        """
        Get a service by ID

        :param service_id: The service_id to be obtained.
        :type service_id: ``str``

        :rtype: ``dict``
        """
        result = self.connection.request("%s/services/%s" %
                                         (self.baseuri, service_id)).object

        return result

    def ex_destroy_service(self, service_id):
        """
        Destroy a service by ID

        http://docs.rancher.com/rancher/v1.2/en/api/api-resources/service/#delete

        :param service_id: The service to be destroyed.
        :type service_id: ``str``

        :return: True if destroy was successful, False otherwise.
        :rtype: ``bool``
        """
        result = self.connection.request('%s/services/%s' % (self.baseuri,
                                         service_id), method='DELETE')
        return result.status in VALID_RESPONSE_CODES

    def ex_activate_service(self, service_id):
        """
        Activate a service.

        http://docs.rancher.com/rancher/v1.2/en/api/api-resources/service/#activate

        :param service_id: The service to activate services for.
        :type service_id: ``str``

        :return: True if activate was successful, False otherwise.
        :rtype: ``bool``
        """
        result = self.connection.request('%s/services/%s?action=activate' %
                                         (self.baseuri, service_id),
                                         method='POST')
        return result.status in VALID_RESPONSE_CODES

    def ex_deactivate_service(self, service_id):
        """
        Deactivate a service.

        http://docs.rancher.com/rancher/v1.2/en/api/api-resources/service/#deactivate

        :param service_id: The service to deactivate services for.
        :type service_id: ``str``

        :return: True if deactivate was successful, False otherwise.
        :rtype: ``bool``
        """
        result = self.connection.request('%s/services/%s?action=deactivate' %
                                         (self.baseuri, service_id),
                                         method='POST')
        return result.status in VALID_RESPONSE_CODES

    def list_containers(self):
        """
        List the deployed containers.

        http://docs.rancher.com/rancher/v1.2/en/api/api-resources/container/

        :rtype: ``list`` of :class:`libcloud.container.base.Container`
        """

        result = self.connection.request("%s/containers" % self.baseuri).object
        containers = [self._to_container(value) for value in result['data']]
        return containers

    def deploy_container(self, name, image, parameters=None, start=True,
                         **kwargs):
        """
        Deploy a new container.

        http://docs.rancher.com/rancher/v1.2/en/api/api-resources/container/#create

        **The following is the Image format used for ``ContainerImage``**

        *For a ``imageuuid``*:

        - ``docker:<hostname>:<port>/<namespace>/<imagename>:<version>``

        *The following applies*:

        - ``id`` = ``<imagename>``
        - ``name`` = ``<imagename>``
        - ``path`` = ``<hostname>:<port>/<namespace>/<imagename>``
        - ``version`` = ``<version>``

        :param name: The desired name of the container.
        :type name: ``str``

        :param image: The Image object to deploy.
        :type image: :class:`libcloud.container.base.ContainerImage`

        :param parameters: Container Image parameters (unused)
        :type  parameters: ``str``

        :param start: Whether to start the container on creation.
        :type start: ``bool``

        :param blkiodeviceoptions: The blkioDeviceOptions for the container.
        :type blkiodeviceoptions: ``dict``

        :param build: Build details for the container.
        :type build: ``dict``

        :param capadd: Linux Capabilities to enable for this container.
        :type capadd: ``list``

        :param capdrop: Linux capabilities to disable for this container.
        :type capdrop: ``list``

        :param command: The command to execute when this container is run.
        :type command: ``list``

        :param count: The number of containers of this nature to launch.
        :type count: ``int``

        :param cpuset: Memory nodes in which to allow execution.
        :type cpuset: ``str``

        :param cpushares: Relative weight cpu shares to allow.
        :type cpushares: ``int``

        :param datavolumemounts: Data volume mountes this container should have
        :type datavolumemounts: ``dict``

        :param datavolumes: Data volumes to associate with this container.
        :type datavolumes: ``list``

        :param datavolumesfrom: Data volumes to inherit.
        :type datavolumesfrom: ``list``

        :param description: Description for this container.
        :type description: ``str``

        :param devices: Devices inside the container without privliged mode.
        :type devices: ``list``

        :param dns: DNS servers the container should utilize.
        :type dns: ``list``

        :param dnssearch: DNS search domains the container should utilize.
        :type dnssearch: ``list``

        :param domainname: The domain name the container should have.
        :type domainname: ``str``

        :param entrypoint: The entrypoint the container should have.
        :type entrypoint: ``list``

        :param environment: Environment variables the container should have.
        :type environment: ``dict``

        :param expose: Ports which should be exposed in the container.
        :type expose: ``list``

        :param extrahosts: Extra hosts file entries this container should have.
        :type extrahosts: ``list``

        :param healthcheck: Health check parameters for this container.
        :type healthcheck: ``dict``

        :param hostname: The hostname this container should have.
        :type hostname: ``str``

        :param instancelinks: Instance links the container should have.
        :type instancelinks: ``dict``

        :param labels: Labels to associate with this container.
        :type labels: ``dict``

        :param logconfig: Log configuration for this container.
        :type logconfig: ``dict``

        :param lxcconf: lxcConf specific to this container.
        :type lxcconf: ``dict``

        :param memory: The memory limit for this container.
        :type memory: ``int``

        :param memoryswap: Total memory limit for this container.
        :type memoryswap: ``int``

        :param networkcontainerrid: A Network container Id for this container.
        :type networkcontainerrid: ``dict``

        :param networkids: NetworkIds this container should contain.
        :type networkids: ``list``

        :param networkmode: The networkMode to enable for this container.
        :type networkmode: ``str``

        :param pidmode: The pidMode for this container.
        :type pidmode: ``str``

        :param ports: The ports to publicize for this container.
        :type ports: ``list``

        :param privileged: Whether to enable privileged mode for this container
        :type privileged: ``bool``

        :param publishallports: Publish all ports in container.
        :type publishallports: ``bool``

        :param readonly: Whether this container should be readOnly.
        :type readonly: ``bool``

        :param registrycredentialid: Registry credentials to use.
        :type registrycredentialid: ``dict``

        :param requestedhostid: Id of the requested host to run this container.
        :type requestedhostid: ``dict``

        :param restartpolicy: The container restart policy.
        :type restartpolicy: ``dict``

        :param securityopt: Security options to provide for this container.
        :type securityopt: ``list``

        :param stdinopen: Whether to keep stdin open.
        :type stdinopen: ``bool``

        :param tty: Enable a tty for this container.
        :type tty: ``bool``

        :param user: User this container should be tied to.
        :type user: ``str``

        :param volumedriver: The volume driver to use for this container.
        :type volumedriver: ``str``

        :param workingdir: The workingDir this container should start in.
        :type workingdir: ``str``

        :rtype: :class:`Container`
        """
        payload = self._build_payload(name, image, start, **kwargs)
        data = json.dumps({k: v for k, v in payload.items() if v is not None})

        result = self.connection.request('%s/containers' % self.baseuri,
                                         data=data, method='POST').object

        return self._to_container(result)

    def get_container(self, id):
        """
        Get a container by ID

        :param id: The ID of the container to get
        :type  id: ``str``

        :rtype: :class:`libcloud.container.base.Container`
        """
        result = self.connection.request("%s/containers/%s" %
                                         (self.baseuri, id)).object

        return self._to_container(result)

    def stop_container(self, container):
        """
        Stop a container

        :param container: The container to be stopped
        :type  container: :class:`libcloud.container.base.Container`

        :return: The container refreshed with current data
        :rtype: :class:`libcloud.container.base.Container`
        """
        result = self.connection.request('%s/containers/%s?action=stop' %
                                         (self.baseuri, container.id),
                                         method='POST')
        if result.status in VALID_RESPONSE_CODES:
            return self.get_container(container.id)
        else:
            raise RancherException(result.status, 'failed to stop container')

    def destroy_container(self, container):
        """
        Remove a container

        :param container: The container to be destroyed
        :type  container: :class:`libcloud.container.base.Container`

        :return: True if the destroy was successful, False otherwise.
        :rtype: ``bool``
        """
        result = self.connection.request('%s/containers/%s' % (self.baseuri,
                                         container.id), method='DELETE')
        return result.status in VALID_RESPONSE_CODES

    def _gen_image(self, imageuuid):
        """
        This function converts a valid Rancher ``imageUuid`` string to a valid
        image object. Only supports docker based images hence `docker:` must
        prefix!!

        Please see the deploy_container() for details on the format.

        :param imageuuid: A valid Rancher image string
            i.e. ``docker:rlister/hastebin:8.0``
        :type imageuuid: ``str``

        :return: Converted ContainerImage object.
        :rtype: :class:`libcloud.container.base.ContainerImage`
        """
        # Obtain just the name(:version) for parsing
        if '/' not in imageuuid:
            # String looks like `docker:mysql:8.0`
            image_name_version = imageuuid.partition(':')[2]
        else:
            # String looks like `docker:oracle/mysql:8.0`
            image_name_version = imageuuid.rpartition("/")[2]
        # Parse based on ':'
        if ':' in image_name_version:
            version = image_name_version.partition(":")[2]
            id = image_name_version.partition(":")[0]
            name = id
        else:
            version = 'latest'
            id = image_name_version
            name = id
        # Get our path based on if there was a version
        if version != 'latest':
            path = imageuuid.partition(':')[2].rpartition(':')[0]
        else:
            path = imageuuid.partition(':')[2]

        return ContainerImage(
            id=id,
            name=name,
            path=path,
            version=version,
            driver=self.connection.driver,
            extra={
                "imageUuid": imageuuid
            }
        )

    def _to_container(self, data):
        """
        Convert container in proper Container instance object
        ** Updating is NOT supported!!

        :param data: API data about container i.e. result.object
        :return: Proper Container object:
         see http://libcloud.readthedocs.io/en/latest/container/api.html

        """
        rancher_state = data['state']
        if 'running' in rancher_state:
            state = ContainerState.RUNNING
        elif 'stopped' in rancher_state:
            state = ContainerState.STOPPED
        elif 'restarting' in rancher_state:
            state = ContainerState.REBOOTING
        elif 'error' in rancher_state:
            state = ContainerState.ERROR
        elif 'removed' or 'purged' in rancher_state:
            # A Removed container is purged after x amt of time.
            # Both of these render the container dead (can't be started later)
            state = ContainerState.TERMINATED
        elif rancher_state.endswith('ing'):
            # Best we can do for current actions
            state = ContainerState.PENDING
        else:
            state = ContainerState.UNKNOWN

        # Everything contained in the json response is dumped in extra
        extra = data

        return Container(
            id=data['id'],
            name=data['name'],
            image=self._gen_image(data['imageUuid']),
            ip_addresses=[data['primaryIpAddress']],
            state=state,
            driver=self.connection.driver,
            extra=extra)

    def _build_payload(self, image, start=True, name=None, image_type="docker",
                       blkiodeviceoptions=None, build=None,
                       capadd=None,
                       capdrop=None, command=None,
                       count=None, cpuset=None, cpushares=None,
                       datavolumemounts=None, datavolumes=None,
                       datavolumesfrom=None, description=None, devices=None,
                       dns=None, dnssearch=None, domainname=None,
                       entrypoint=None, environment=None, expose=None,
                       extrahosts=None, healthcheck=None, hostname=None,
                       instancelinks=None, labels=None, logconfig=None,
                       lxcconf=None, memory=None, memoryswap=None,
                       networkcontainerrid=None, networkids=None,
                       networkmode=None, pidmode=None, ports=None,
                       privileged=None, publishallports=None,
                       readonly=None, registrycredentialid=None,
                       requestedhostid=None, restartpolicy=None,
                       securityopt=None,
                       stdinopen=None, tty=None, user=None,
                       volumedriver=None, workingdir=None):
        """

        :param image: The Image object to deploy.
        :type image: :class:`libcloud.container.base.ContainerImage`

        :param start: Whether to start the container on creation.
        :type start: ``bool``

        :param name: The desired name of the container.
        :type name: ``str``

        :param image_type: The image format of the desired image to deploy.
        :type image_type: ``str``

        :param blkiodeviceoptions: The blkioDeviceOptions for the container.
        :type blkiodeviceoptions: ``dict``

        :param build: Build details for the container.
        :type build: ``dict``

        :param capadd: Linux Capabilities to enable for this container.
        :type capadd: ``list``

        :param capdrop: Linux capabilities to disable for this container.
        :type capdrop: ``list``

        :param command: The command to execute when this container is run.
        :type command: ``list``

        :param count: The number of containers of this nature to launch.
        :type count: ``int``

        :param cpuset: Memory nodes in which to allow execution.
        :type cpuset: ``str``

        :param cpushares: Relative weight cpu shares to allow.
        :type cpushares: ``int``

        :param datavolumemounts: Data volume mountes this container should have
        :type datavolumemounts: ``dict``

        :param datavolumes: Data volumes to associate with this container.
        :type datavolumes: ``list``

        :param datavolumesfrom: Data volumes to inherit.
        :type datavolumesfrom: ``list``

        :param description: Description for this container.
        :type description: ``str``

        :param devices: Devices inside the container without privliged mode.
        :type devices: ``list``

        :param dns: DNS servers the container should utilize.
        :type dns: ``list``

        :param dnssearch: DNS search domains the container should utilize.
        :type dnssearch: ``list``

        :param domainname: The domain name the container should have.
        :type domainname: ``str``

        :param entrypoint: The entrypoint the container should have.
        :type entrypoint: ``list``

        :param environment: Environment variables the container should have.
        :type environment: ``dict``

        :param expose: Ports which should be exposed in the container.
        :type expose: ``list``

        :param extrahosts: Extra hosts file entries this container should have.
        :type extrahosts: ``list``

        :param healthcheck: Health check parameters for this container.
        :type healthcheck: ``dict``

        :param hostname: The hostname this container should have.
        :type hostname: ``str``

        :param instancelinks: Instance links the container should have.
        :type instancelinks: ``dict``

        :param labels: Labels to associate with this container.
        :type labels: ``dict``

        :param logconfig: Log configuration for this container.
        :type logconfig: ``dict``

        :param lxcconf: lxcConf specific to this container.
        :type lxcconf: ``dict``

        :param memory: The memory limit for this container.
        :type memory: ``int``

        :param memoryswap: Total memory limit for this container.
        :type memoryswap: ``int``

        :param networkcontainerrid: A Network container Id for this container.
        :type networkcontainerrid: ``dict``

        :param networkids: NetworkIds this container should contain.
        :type networkids: ``list``

        :param networkmode: The networkMode to enable for this container.
        :type networkmode: ``str``

        :param pidmode: The pidMode for this container.
        :type pidmode: ``str``

        :param ports: The ports to publicize for this container.
        :type ports: ``list``

        :param privileged: Whether to enable privileged mode for this container
        :type privileged: ``bool``

        :param publishallports: Publish all ports in container.
        :type publishallports: ``bool``

        :param readonly: Whether this container should be readOnly.
        :type readonly: ``bool``

        :param registrycredentialid: Registry credentials to use.
        :type registrycredentialid: ``dict``

        :param requestedhostid: Id of the requested host to run this container.
        :type requestedhostid: ``dict``

        :param restartpolicy: The container restart policy.
        :type restartpolicy: ``dict``

        :param securityopt: Security options to provide for this container.
        :type securityopt: ``list``

        :param stdinopen: Whether to keep stdin open.
        :type stdinopen: ``bool``

        :param tty: Enable a tty for this container.
        :type tty: ``bool``

        :param user: User this container should be tied to.
        :type user: ``str``

        :param volumedriver: The volume driver to use for this container.
        :type volumedriver: ``str``

        :param workingdir: The workingDir this container should start in.
        :type workingdir: ``str``

        :return:
        """

        if command is not None:
            command = shlex.split(str(command))

        if image.version is not None:
            imageuuid = image_type + ':' + image.path + ':' + image.version
        else:
            imageuuid = image_type + ':' + image.path

        payload = {
            "blkioDeviceOptions": blkiodeviceoptions,
            "build": build,
            "capAdd": capadd,
            "capDrop": capdrop,
            "command": command,
            "count": count,
            "cpuSet": cpuset,
            "cpuShares": cpushares,
            "dataVolumeMounts": datavolumemounts,
            "dataVolumes": datavolumes,
            "dataVolumesFrom": datavolumesfrom,
            "description": description,
            "devices": devices,
            "dns": dns,
            "dnsSearch": dnssearch,
            "domainName": domainname,
            "entryPoint": entrypoint,
            "environment": environment,
            "expose": expose,
            "extraHosts": extrahosts,
            "healthCheck": healthcheck,
            "hostname": hostname,
            "imageUuid": imageuuid,
            "instanceLinks": instancelinks,
            "labels": labels,
            "logConfig": logconfig,
            "lxcConf": lxcconf,
            "memory": memory,
            "memorySwap": memoryswap,
            "name": name,
            "networkContainerId": networkcontainerrid,
            "networkIds": networkids,
            "networkMode": networkmode,
            "pidMode": pidmode,
            "ports": ports,
            "privileged": privileged,
            "publishAllPorts": publishallports,
            "readOnly": readonly,
            "registryCredentialId": registrycredentialid,
            "requestedHostId": requestedhostid,
            "restartPolicy": restartpolicy,
            "securityOpt": securityopt,
            "startOnCreate": start,
            "stdinOpen": stdinopen,
            "tty": tty,
            "user": user,
            "volumeDriver": volumedriver,
            "workingdir": workingdir
        }

        return payload
