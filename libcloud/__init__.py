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
libcloud provides a unified interface to the cloud computing resources.

:var __version__: Current version of libcloud
"""
import os
import codecs

from libcloud.backup.providers import Provider as BackupProvider
from libcloud.backup.providers import get_driver as get_backup_driver

from libcloud.compute.providers import Provider as ComputeProvider
from libcloud.compute.providers import get_driver as get_compute_driver

from libcloud.container.providers import Provider as ContainerProvider
from libcloud.container.providers import get_driver as get_container_driver

from libcloud.dns.providers import Provider as DnsProvider
from libcloud.dns.providers import get_driver as get_dns_driver

from libcloud.loadbalancer.providers import Provider as LoadBalancerProvider
from libcloud.loadbalancer.providers import get_driver as \
    get_loadbalancer_driver

from libcloud.storage.providers import Provider as StorageProvider
from libcloud.storage.providers import get_driver as get_storage_driver


__all__ = ['__version__', 'enable_debug']
__version__ = '1.0.0'

try:
    import paramiko
    have_paramiko = True
except ImportError:
    have_paramiko = False


def enable_debug(fo):
    """
    Enable library wide debugging to a file-like object.

    :param fo: Where to append debugging information
    :type fo: File like object, only write operations are used.
    """
    from libcloud.common.base import (Connection,
                                      LoggingHTTPConnection,
                                      LoggingHTTPSConnection)
    LoggingHTTPSConnection.log = fo
    LoggingHTTPConnection.log = fo
    Connection.conn_classes = (LoggingHTTPConnection,
                               LoggingHTTPSConnection)


def _init_once():
    """
    Utility function that is ran once on Library import.

    This checks for the LIBCLOUD_DEBUG environment variable, which if it exists
    is where we will log debug information about the provider transports.
    """
    path = os.getenv('LIBCLOUD_DEBUG')
    if path:
        mode = 'a'

        # Special case for /dev/stderr and /dev/stdout on Python 3.
        from libcloud.utils.py3 import PY3

        # Opening those files in append mode will throw "illegal seek"
        # exception there.
        # Late import to avoid setup.py related side affects
        if path in ['/dev/stderr', '/dev/stdout'] and PY3:
            mode = 'w'

        fo = codecs.open(path, mode, encoding='utf8')
        enable_debug(fo)

        if have_paramiko:
            paramiko.common.logging.basicConfig(level=paramiko.common.DEBUG)

_init_once()


class DriverType:
    """ Backup-as-a-service driver """
    BACKUP = BackupProvider

    """ Compute-as-a-Service driver """
    COMPUTE = ComputeProvider

    """ Container-as-a-Service driver """
    CONTAINER = ContainerProvider

    """ DNS service provider driver """
    DNS = DnsProvider

    """ Load balancer provider-driver """
    LOADBALANCER = LoadBalancerProvider

    """ Storage-as-a-Service driver """
    STORAGE = StorageProvider


DriverTypeFactoryMap = {
    DriverType.BACKUP: get_backup_driver,
    DriverType.COMPUTE: get_compute_driver,
    DriverType.CONTAINER: get_container_driver,
    DriverType.DNS: get_dns_driver,
    DriverType.LOADBALANCER: get_loadbalancer_driver,
    DriverType.STORAGE: get_storage_driver
}


def get_driver(type, provider):
    """
    Get a driver
    """
    return DriverTypeFactoryMap[type](provider)
