import base64
import datetime
import shlex
import re

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
    # Holding off on this for now. Only Environment API interaction enabled.
    supports_clusters = False
    # As in the /v1/
    version = '1'

    def __init__(self, key, secret, secure=False, host='localhost',
                 port=80, key_file=None, cert_file=None):
        """
        :param    key: API key or username to used (required)
        :type     key: ``str``

        :param    secret: Secret password to be used (required)
        :type     secret: ``str``

        :param    secure: Whether to use HTTPS or HTTP. Note: Some providers
                only support HTTPS, and it is on by default.
        :type     secure: ``bool``

        :param    host: Override hostname used for connections.
        :type     host: ``str``

        :param    port: Override port used for connections.
        :type     port: ``int``

        :param    key_file: Path to private key for TLS connection (optional)
        :type     key_file: ``str``

        :param    cert_file: Path to public key for TLS connection (optional)
        :type     cert_file: ``str``

        :return: ``None``
        """
        super(RancherContainerDriver, self).__init__(key=key, secret=secret,
                                                     secure=secure, host=host,
                                                     port=port,
                                                     key_file=key_file,
                                                     cert_file=cert_file)
        if host.startswith('https://'):
            secure = True

        # strip the prefix
        prefixes = ['http://', 'https://']
        for prefix in prefixes:
            if host.startswith(prefix):
                host = host.strip(prefix)
        """
        if key_file or cert_file:
            # docker tls authentication-
            # https://docs.docker.com/articles/https/
            # We pass two files, a key_file with the
            # private key and cert_file with the certificate
            # libcloud will handle them through LibcloudHTTPSConnection
            if not (key_file and cert_file):
                raise Exception(
                    'Needs both private key file and '
                    'certificate file for tls authentication')
            self.connection.key_file = key_file
            self.connection.cert_file = cert_file
            self.connection.secure = True
        else:
            self.connection.secure = secure
        """

        self.connection.host = host
        self.connection.port = port

        # We only support environment api keys, meaning none of this:
        # self.baseuri = "/v%s/projects/%s" % (self.version, project_id)
        self.baseuri = "/v%s" % self.version

    def ex_list_environments(self):
        """
        List the deployed container images
        :param image: Filter to containers with a certain image
        :type  image: :class:`libcloud.container.base.ContainerImage`
        :param all: Show all container (including stopped ones)
        :type  all: ``bool``
        :rtype: ``list`` of :class:`libcloud.container.base.Container`
        """

        result = self.connection.request("%s/environments" % self.baseuri).object
        return result['data']

    def ex_deploy_environment(self, name, description=None, dockercompose=None,
                              environment=None, externalid=None, outputs=None,
                              previousenvironment=None, previousexternalid=None,
                              ranchercompose=None, start=True):

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

    def ex_get_environment(self, env_id):
        """
        Get a service by ID
        :param env_id: The environment to be obtained.
        :return: The API dict object returned for the new service.
        """
        result = self.connection.request("%s/environments/%s" %
                                         (self.baseuri, env_id)).object

        return result

    def ex_destroy_environment(self, env_id):

        result = self.connection.request('%s/environments/%s' % (
                                         self.baseuri, env_id), method='DELETE')
        if result.status in VALID_RESPONSE_CODES:
            return result.status in VALID_RESPONSE_CODES
        else:
            raise RancherException(result.status,
                                   'failed to destroy environment')

    def ex_activate_environment(self, env_id):

        result = self.connection.request('%s/environments/%s?action=activateservices' %
                                         (self.baseuri, env_id),
                                         method='POST')
        if result.status in VALID_RESPONSE_CODES:
            return result.status in VALID_RESPONSE_CODES
        else:
            raise RancherException(result.status,
                                   'failed to activate environment')

    def ex_deactivate_environment(self, env_id):

        result = self.connection.request('%s/environments/%s?action=deactivateservices' %
                                         (self.baseuri, env_id),
                                         method='POST')
        if result.status in VALID_RESPONSE_CODES:
            return result.status in VALID_RESPONSE_CODES
        else:
            raise RancherException(result.status,
                                   'failed to deactivate environment')

    def build_payload(self, image, start=True, name=None, image_type="docker",
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

    def ex_list_services(self):
        """
        List the deployed container images
        :param image: Filter to containers with a certain image
        :type  image: :class:`libcloud.container.base.ContainerImage`
        :param all: Show all container (including stopped ones)
        :type  all: ``bool``
        :rtype: ``list`` of :class:`libcloud.container.base.Container`
        """

        result = self.connection.request("%s/services" % self.baseuri).object
        return result['data']

    def ex_deploy_service(self, name, image, environmentid, start=True,
                          assignserviceipaddress=None, service_description=None,
                          externalid=None, metadata=None, retainip=None,
                          scale=None, scalepolicy=None,
                          secondarylaunchconfigs=None, selectorcontainer=None,
                          selectorlink=None,
                          vip=None, datavolumesfromlaunchconfigs=None,
                          disks=None, kind=None, memorymb=None,
                          networklaunchconfig=None, requsetedipaddress=None,
                          userdata=None, vcpu=None, **kwargs):
        """
        Deploy a Rancher Service under a stack.
        :param name: Name of the service.
        :param image: ContainerImage object of image to utilize.
        :param environmentid: The environment/stack ID this service is tied to.
        :param kwargs: The Launchconfig provided as top-level options,
        similar to deploy_container.
        :return: The API object returned on proper service creation.
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
        launchconfig = self.build_payload(image, start, **kwargs)
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
        :param service_id: The service to be obtained.
        :return: The API dict object returned for the new service.
        """
        result = self.connection.request("%s/services/%s" %
                                         (self.baseuri, service_id)).object

        return result

    def ex_destroy_service(self, service_id):
        """
        Delete a service.
        :param service_id: The service to be destroyed
        :return: True if the destroy was successful, False otherwise.
        :rtype: ``bool``
        """
        result = self.connection.request('%s/services/%s' % (self.baseuri,
                                         service_id), method='DELETE')
        if result.status in VALID_RESPONSE_CODES:
            return result.status in VALID_RESPONSE_CODES
        else:
            raise RancherException(result.status,
                                   'failed to destroy service')

    def ex_activate_service(self, service_id):

        result = self.connection.request('%s/services/%s?action=activate' %
                                         (self.baseuri, service_id),
                                         method='POST')
        if result.status in VALID_RESPONSE_CODES:
            return result.status in VALID_RESPONSE_CODES
        else:
            raise RancherException(result.status,
                                   'failed to activate service')

    def ex_deactivate_service(self, service_id):

        result = self.connection.request('%s/services/%s?action=deactivate' %
                                         (self.baseuri, service_id),
                                         method='POST')
        if result.status in VALID_RESPONSE_CODES:
            return result.status in VALID_RESPONSE_CODES
        else:
            raise RancherException(result.status,
                                   'failed to deactivate service')

    def list_containers(self, image=None, all=True):
        """
        List the deployed container images
        :param image: Filter to containers with a certain image
        :type  image: :class:`libcloud.container.base.ContainerImage`
        :param all: Show all container (including stopped ones)
        :type  all: ``bool``
        :rtype: ``list`` of :class:`libcloud.container.base.Container`
        """

        result = self.connection.request("%s/containers" % self.baseuri).object
        containers = [self._to_container(value) for value in result['data']]
        return containers

    def deploy_container(self, name, image, parameters=None, start=True,
                         **kwargs):
        """
        Deploy an installed container image
        For details on the additional parameters see : http://bit.ly/1PjMVKV
        :param name: The name of the new container
        :type  name: ``str``
        :param image: The container image to deploy
        :type  image: :class:`libcloud.container.base.ContainerImage`
        :param parameters: Container Image parameters
        :type  parameters: ``str``
        :param start: Start the container on deployment
        :type  start: ``bool``
        :rtype: :class:`Container`
        """
        payload = self.build_payload(name, image, start, **kwargs)
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
            raise RancherException(result.status,
                                  'failed to stop container')

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
        if result.status in VALID_RESPONSE_CODES:
            return self.get_container(container.id)
        else:
            raise RancherException(result.status,
                                  'failed to destroy container')

    def _gen_image(self, imageuuid):
        """
        This function converts a valid Rancher `imageUuid` string to a valid
        image object. Only supports docker based images hence `docker:` must
        prefix!!

        For a imageuuid:
            docker:<hostname>:<port>/<namespace>/<imagename>:<version>

        The following applies:
            id = <imagename>
            name = <imagename>
            path = <hostname>:<port>/<namespace>/<imagename>
            version = <version>

        :param imageUuid: A valid Rancher image string
        i.e. `docker:rlister/hastebin:8.0`
        :return: Proper ContainerImage object.
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

        # Includes the most used items atm. Eventually, everything ;)
        extra = {
            "state": rancher_state,
            "command": data['command'],
            "created": data['created'],
            "dataVolumes": data['dataVolumes'],
            "dns": data['dns'],
            "dnsSearch": data['dnsSearch'],
            "domainName": data['domainName'],
            "entryPoint": data['entryPoint'],
            "environment": data['environment'],
            "expose": data['expose'],
            "healthState": data['healthState'],
            "hostId": data['hostId'],
            "hostname": data['hostname'],
            "labels": data['labels'],
            "networkMode": data['networkMode'],
            "ports": data['ports'],
            "primaryIpAddress": data['primaryIpAddress'],
            "privileged": data['privileged'],
            "restartPolicy": data['restartPolicy'],
            "stdinOpen": data['stdinOpen'],
            "tty": data['tty'],
            "uuid": data['uuid'],
            "workingDir": data['workingDir']
        }

        return Container(
            id=data['id'],
            name=data['name'],
            image=self._gen_image(data['imageUuid']),
            ip_addresses=[data['primaryIpAddress']],
            state=state,
            driver=self.connection.driver,
            extra=extra)


def ts_to_str(timestamp):
    """
    Return a timestamp as a nicely formated datetime string.
    """
    date = datetime.datetime.fromtimestamp(timestamp)
    date_string = date.strftime("%d/%m/%Y %H:%M %Z")
    return date_string
