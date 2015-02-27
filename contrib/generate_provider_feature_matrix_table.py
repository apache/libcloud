#!/usr/bin/env python
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
from __future__ import with_statement

import os
import sys
import inspect
from collections import OrderedDict
from os.path import join as pjoin

this_dir = os.path.abspath(os.path.split(__file__)[0])
sys.path.insert(0, os.path.join(this_dir, '../'))

from libcloud.compute .base import NodeDriver
from libcloud.compute.providers import get_driver as get_compute_driver
from libcloud.compute.providers import DRIVERS as COMPUTE_DRIVERS
from libcloud.compute.types import Provider as ComputeProvider

from libcloud.loadbalancer.base import Driver as LBDriver
from libcloud.loadbalancer.providers import get_driver as get_lb_driver
from libcloud.loadbalancer.providers import DRIVERS as LB_DRIVERS
from libcloud.loadbalancer.types import Provider as LBProvider

from libcloud.storage.base import StorageDriver
from libcloud.storage.providers import get_driver as get_storage_driver
from libcloud.storage.providers import DRIVERS as STORAGE_DRIVERS
from libcloud.storage.types import Provider as StorageProvider

from libcloud.dns.base import DNSDriver
from libcloud.dns.providers import get_driver as get_dns_driver
from libcloud.dns.providers import DRIVERS as DNS_DRIVERS
from libcloud.dns.types import Provider as DNSProvider

BASE_API_METHODS = {
    'compute_main': ['list_nodes', 'create_node', 'reboot_node',
                     'destroy_node', 'list_images', 'list_sizes',
                     'deploy_node'],
    'compute_image_management': ['list_images', 'get_image',
                                 'create_image', 'delete_image', 'copy_image'],
    'compute_block_storage': ['list_volumes', 'create_volume',
                              'destroy_volume',
                              'attach_volume', 'detach_volume',
                              'list_volume_snapshots',
                              'create_volume_snapshot'],
    'compute_key_pair_management': ['list_key_pairs', 'get_key_pair',
                                    'create_key_pair',
                                    'import_key_pair_from_string',
                                    'import_key_pair_from_file',
                                    'delete_key_pair'],
    'loadbalancer': ['create_balancer', 'list_balancers',
                     'balancer_list_members', 'balancer_attach_member',
                     'balancer_detach_member', 'balancer_attach_compute_node'],
    'storage_main': ['list_containers', 'list_container_objects',
                     'iterate_containers', 'iterate_container_objects',
                     'create_container', 'delete_container', 'upload_object',
                     'upload_object_via_stream', 'download_object',
                     'download_object_as_stream', 'delete_object'],
    'storage_cdn': ['enable_container_cdn', 'enable_object_cdn',
                    'get_container_cdn_url', 'get_object_cdn_url'],
    'dns': ['list_zones', 'list_records', 'iterate_zones', 'iterate_records',
            'create_zone', 'update_zone', 'create_record', 'update_record',
            'delete_zone', 'delete_record']
}

FRIENDLY_METHODS_NAMES = {
    'compute_main': {
        'list_nodes': 'list nodes',
        'create_node': 'create node',
        'reboot_node': 'reboot node',
        'destroy_node': 'destroy node',
        'list_images': 'list images',
        'list_sizes': 'list sizes',
        'deploy_node': 'deploy node'
    },
    'compute_image_management': {
        'list_images': 'list images',
        'get_image': 'get image',
        'create_image': 'create image',
        'copy_image': 'copy image',
        'delete_image': 'delete image'
    },
    'compute_block_storage': {
        'list_volumes': 'list volumes',
        'create_volume': 'create volume',
        'destroy_volume': 'destroy volume',
        'attach_volume': 'attach volume',
        'detach_volume': 'detach volume',
        'list_volume_snapshots': 'list snapshots',
        'create_volume_snapshot': 'create snapshot'
    },
    'compute_key_pair_management': {
        'list_key_pairs': 'list key pairs',
        'get_key_pair': 'get key pair',
        'create_key_pair': 'create key pair',
        'import_key_pair_from_string': 'import public key from string',
        'import_key_pair_from_file': 'import public key from file',
        'delete_key_pair': 'delete key pair'
    },
    'loadbalancer': {
        'create_balancer': 'create balancer',
        'list_balancers': 'list balancers',
        'balancer_list_members': 'list members',
        'balancer_attach_member': 'attach member',
        'balancer_detach_member': 'detach member',
        'balancer_attach_compute_node': 'attach compute node'
    },
    'storage_main': {
        'list_containers': 'list containers',
        'list_container_objects': 'list objects',
        'create_container': 'create container',
        'delete_container': 'delete container',
        'upload_object': 'upload object',
        'upload_object_via_stream': 'streaming object upload',
        'download_object': 'download object',
        'download_object_as_stream': 'streaming object download',
        'delete_object': 'delete object'
    },
    'storage_cdn': {
        'enable_container_cdn': 'enable container cdn',
        'enable_object_cdn': 'enable object cdn',
        'get_container_cdn_url': 'get container cdn URL',
        'get_object_cdn_url': 'get object cdn URL',
    },
    'dns': {
        'list_zones': 'list zones',
        'list_records': 'list records',
        'create_zone': 'create zone',
        'update_zone': 'update zone',
        'create_record': 'create record',
        'update_record': 'update record',
        'delete_zone': 'delete zone',
        'delete_record': 'delete record'
    },
}

IGNORED_PROVIDERS = [
    'dummy',
    'local',

    # Deprecated constants
    'cloudsigma_us',

    'cloudfiles_swift'
]


def get_provider_api_names(Provider):
    names = [key for key, value in Provider.__dict__.items() if
             not key.startswith('__')]
    return names


def generate_providers_table(api):
    result = {}

    if api in ['compute_main', 'compute_image_management',
               'compute_block_storage', 'compute_key_pair_management']:
        driver = NodeDriver
        drivers = COMPUTE_DRIVERS
        provider = ComputeProvider
        get_driver_method = get_compute_driver
    elif api == 'loadbalancer':
        driver = LBDriver
        drivers = LB_DRIVERS
        provider = LBProvider
        get_driver_method = get_lb_driver
    elif api in ['storage_main', 'storage_cdn']:
        driver = StorageDriver
        drivers = STORAGE_DRIVERS
        provider = StorageProvider
        get_driver_method = get_storage_driver
    elif api == 'dns':
        driver = DNSDriver
        drivers = DNS_DRIVERS
        provider = DNSProvider
        get_driver_method = get_dns_driver
    else:
        raise Exception('Invalid api: %s' % (api))

    names = get_provider_api_names(provider)

    result = OrderedDict()
    for name in names:
        enum = getattr(provider, name)

        try:
            cls = get_driver_method(enum)
        except:
            # Deprecated providers throw an exception
            continue

        # Hack for providers which expose multiple classes and support multiple
        # API versions
        # TODO: Make entry per version

        if name.lower() == 'cloudsigma':
            from libcloud.compute.drivers.cloudsigma import \
                CloudSigma_2_0_NodeDriver
            cls = CloudSigma_2_0_NodeDriver
        elif name.lower() == 'opennebula':
            from libcloud.compute.drivers.opennebula import \
                OpenNebula_3_8_NodeDriver
            cls = OpenNebula_3_8_NodeDriver

        if name.lower() in IGNORED_PROVIDERS:
            continue

        driver_methods = dict(inspect.getmembers(cls,
                                                 predicate=inspect.ismethod))
        base_methods = dict(inspect.getmembers(driver,
                                               predicate=inspect.ismethod))
        base_api_methods = BASE_API_METHODS[api]

        result[name] = {'name': cls.name, 'website': cls.website,
                        'constant': name, 'module': drivers[enum][0],
                        'class': drivers[enum][1],
                        'methods': {}}

        for method_name in base_api_methods:
            base_method = base_methods[method_name]
            driver_method = driver_methods[method_name]

            if method_name == 'deploy_node':
                features = getattr(cls, 'features', {}).get('create_node', [])
                is_implemented = len(features) >= 1
            else:
                is_implemented = (id(driver_method.im_func) !=
                                  id(base_method.im_func))

            result[name]['methods'][method_name] = is_implemented

    return result


def generate_rst_table(data):
    cols = len(data[0])
    col_len = [max(len(r[i]) for r in data) for i in range(cols)]
    formatter = ' '.join('{:<%d}' % c for c in col_len)

    header = formatter.format(*['=' * c for c in col_len])
    rows = [formatter.format(*row) for row in data]
    result = header + '\n' + rows[0] + '\n' + header + '\n' +\
        '\n'.join(rows[1:]) + '\n' + header

    return result


def generate_supported_methods_table(api, provider_matrix):
    base_api_methods = BASE_API_METHODS[api]
    data = []
    header = [FRIENDLY_METHODS_NAMES[api][method_name] for method_name in
              base_api_methods if not method_name.startswith('iterate_')]
    data.append(['Provider'] + header)

    for provider, values in sorted(provider_matrix.items()):
        provider_name = '`%s`_' % (values['name'])
        row = [provider_name]

        # TODO: Make it nicer
        # list_* methods don't need to be implemented if iterate_* methods are
        # implemented
        if api == 'storage_main':
            if values['methods']['iterate_containers']:
                values['methods']['list_containers'] = True

            if values['methods']['iterate_container_objects']:
                values['methods']['list_container_objects'] = True
        elif api == 'dns':
            # list_zones and list_records don't need to be implemented if
            if values['methods']['iterate_zones']:
                values['methods']['list_zones'] = True

            if values['methods']['iterate_records']:
                values['methods']['list_records'] = True

        for method in base_api_methods:
            # TODO: ghetto
            if method.startswith('iterate_'):
                continue

            supported = values['methods'][method]

            if supported:
                row.append('yes')
            else:
                row.append('no')
        data.append(row)

    result = generate_rst_table(data)

    result += '\n\n'
    for provider, values in sorted(provider_matrix.items()):
        result += '.. _`%s`: %s\n' % (values['name'], values['website'])
    return result


def generate_supported_providers_table(api, provider_matrix):
    data = []
    header = ['Provider', 'Documentation', 'Provider constant', 'Module',
              'Class Name']

    data.append(header)
    for provider, values in sorted(provider_matrix.items()):
        name_str = '`%s`_' % (values['name'])
        module_str = ':mod:`%s`' % (values['module'])
        class_str = ':class:`%s`' % (values['class'])

        params = {'api': api, 'provider': provider.lower()}
        driver_docs_path = pjoin(this_dir,
                                 '../docs/%(api)s/drivers/%(provider)s.rst'
                                 % params)

        if os.path.exists(driver_docs_path):
            docs_link = ':doc:`Click </%(api)s/drivers/%(provider)s>`' % params
        else:
            docs_link = ''

        row = [name_str, docs_link, values['constant'], module_str, class_str]
        data.append(row)

    result = generate_rst_table(data)

    result += '\n\n'
    for provider, values in sorted(provider_matrix.items()):
        result += '.. _`%s`: %s\n' % (values['name'], values['website'])
    return result


def generate_tables():
    apis = BASE_API_METHODS.keys()
    for api in apis:
        result = generate_providers_table(api)

        docs_dir = api

        if api.startswith('compute'):
            docs_dir = 'compute'
        elif api.startswith('storage'):
            docs_dir = 'storage'

        supported_providers = generate_supported_providers_table(docs_dir,
                                                                 result)
        supported_methods = generate_supported_methods_table(api, result)

        current_path = os.path.dirname(__file__)
        target_dir = os.path.abspath(pjoin(current_path,
                                           '../docs/%s/' % (docs_dir)))

        file_name_1 = '_supported_providers.rst'
        file_name_2 = '_supported_methods.rst'

        if api == 'compute_main':
            file_name_2 = '_supported_methods_main.rst'
        elif api == 'compute_image_management':
            file_name_2 = '_supported_methods_image_management.rst'
        elif api == 'compute_block_storage':
            file_name_2 = '_supported_methods_block_storage.rst'
        elif api == 'compute_key_pair_management':
            file_name_2 = '_supported_methods_key_pair_management.rst'
        elif api == 'storage_main':
            file_name_2 = '_supported_methods_main.rst'
        elif api == 'storage_cdn':
            file_name_2 = '_supported_methods_cdn.rst'

        supported_providers_path = pjoin(target_dir, file_name_1)
        supported_methods_path = pjoin(target_dir, file_name_2)

        with open(supported_providers_path, 'w') as fp:
            fp.write(supported_providers)

        with open(supported_methods_path, 'w') as fp:
            fp.write(supported_methods)

generate_tables()
