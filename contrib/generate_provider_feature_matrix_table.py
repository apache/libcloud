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


import os
import sys
import inspect
from os.path import join as pjoin
from collections import OrderedDict

# Add parent dir of this file's dir to sys.path (OS-agnostically)
BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), os.path.pardir))
sys.path.append(BASE_DIR)

# isort:skip pragma is needed to make sure those imports are not moved above
# sys.path manipulation code (https://github.com/PyCQA/isort/issues/468)
from libcloud.dns.base import DNSDriver  # isort:skip
from libcloud.dns.types import Provider as DNSProvider  # isort:skip
from libcloud.backup.base import BackupDriver  # isort:skip
from libcloud.backup.types import Provider as BackupProvider  # isort:skip
from libcloud.compute.base import NodeDriver  # isort:skip
from libcloud.storage.base import StorageDriver  # isort:skip
from libcloud.compute.types import Provider as ComputeProvider  # isort:skip
from libcloud.dns.providers import DRIVERS as DNS_DRIVERS  # isort:skip
from libcloud.dns.providers import get_driver as get_dns_driver  # isort:skip
from libcloud.storage.types import Provider as StorageProvider  # isort:skip
from libcloud.container.base import ContainerDriver  # isort:skip
from libcloud.container.types import Provider as ContainerProvider  # isort:skip
from libcloud.backup.providers import DRIVERS as BACKUP_DRIVERS  # isort:skip
from libcloud.backup.providers import get_driver as get_backup_driver  # isort:skip
from libcloud.compute.providers import DRIVERS as COMPUTE_DRIVERS  # isort:skip
from libcloud.compute.providers import get_driver as get_compute_driver  # isort:skip
from libcloud.loadbalancer.base import Driver as LBDriver  # isort:skip
from libcloud.storage.providers import DRIVERS as STORAGE_DRIVERS  # isort:skip
from libcloud.storage.providers import get_driver as get_storage_driver  # isort:skip
from libcloud.loadbalancer.types import Provider as LBProvider  # isort:skip
from libcloud.container.providers import DRIVERS as CONTAINER_DRIVERS  # isort:skip
from libcloud.loadbalancer.providers import DRIVERS as LB_DRIVERS  # isort:skip
from libcloud.loadbalancer.providers import get_driver as get_lb_driver  # isort:skip
from libcloud.container.providers import get_driver as get_container_driver  # isort:skip

HEADER = (
    ".. NOTE: This file has been generated automatically using "
    "generate_provider_feature_matrix_table.py script, don't manually "
    "edit it"
)

BASE_API_METHODS = {
    "compute_main": [
        "list_nodes",
        "create_node",
        "reboot_node",
        "destroy_node",
        "start_node",
        "stop_node",
        "list_images",
        "list_sizes",
        "deploy_node",
    ],
    "compute_image_management": [
        "list_images",
        "get_image",
        "create_image",
        "delete_image",
        "copy_image",
    ],
    "compute_block_storage": [
        "list_volumes",
        "create_volume",
        "destroy_volume",
        "attach_volume",
        "detach_volume",
        "list_volume_snapshots",
        "create_volume_snapshot",
    ],
    "compute_key_pair_management": [
        "list_key_pairs",
        "get_key_pair",
        "create_key_pair",
        "import_key_pair_from_string",
        "import_key_pair_from_file",
        "delete_key_pair",
    ],
    "loadbalancer": [
        "create_balancer",
        "list_balancers",
        "balancer_list_members",
        "balancer_attach_member",
        "balancer_detach_member",
        "balancer_attach_compute_node",
    ],
    "storage_main": [
        "list_containers",
        "list_container_objects",
        "iterate_containers",
        "iterate_container_objects",
        "create_container",
        "delete_container",
        "upload_object",
        "upload_object_via_stream",
        "download_object",
        "download_object_range",
        "download_object_as_stream",
        "download_object_range_as_stream",
        "delete_object",
    ],
    "storage_cdn": [
        "enable_container_cdn",
        "enable_object_cdn",
        "get_container_cdn_url",
        "get_object_cdn_url",
    ],
    "dns": [
        "list_zones",
        "list_records",
        "iterate_zones",
        "iterate_records",
        "create_zone",
        "update_zone",
        "create_record",
        "update_record",
        "delete_zone",
        "delete_record",
    ],
    "container": [
        "install_image",
        "list_images",
        "deploy_container",
        "get_container",
        "start_container",
        "stop_container",
        "restart_container",
        "destroy_container",
        "list_containers",
        "list_locations",
        "create_cluster",
        "destroy_cluster",
        "list_clusters",
    ],
    "backup": [
        "get_supported_target_types",
        "list_targets",
        "create_target",
        "create_target_from_node",
        "create_target_from_storage_container",
        "update_target",
        "delete_target",
        "list_recovery_points",
        "recover_target",
        "recover_target_out_of_place",
        "list_target_jobs",
        "create_target_job",
        "resume_target_job",
        "suspend_target_job",
        "cancel_target_job",
    ],
}

FRIENDLY_METHODS_NAMES = {
    "compute_main": {
        "list_nodes": "list nodes",
        "create_node": "create node",
        "reboot_node": "reboot node",
        "start_node": "start node",
        "stop_node": "stop node",
        "destroy_node": "destroy node",
        "list_images": "list images",
        "list_sizes": "list sizes",
        "deploy_node": "deploy node",
    },
    "compute_image_management": {
        "list_images": "list images",
        "get_image": "get image",
        "create_image": "create image",
        "copy_image": "copy image",
        "delete_image": "delete image",
    },
    "compute_block_storage": {
        "list_volumes": "list volumes",
        "create_volume": "create volume",
        "destroy_volume": "destroy volume",
        "attach_volume": "attach volume",
        "detach_volume": "detach volume",
        "list_volume_snapshots": "list snapshots",
        "create_volume_snapshot": "create snapshot",
    },
    "compute_key_pair_management": {
        "list_key_pairs": "list key pairs",
        "get_key_pair": "get key pair",
        "create_key_pair": "create key pair",
        "import_key_pair_from_string": "import public key from string",
        "import_key_pair_from_file": "import public key from file",
        "delete_key_pair": "delete key pair",
    },
    "loadbalancer": {
        "create_balancer": "create balancer",
        "list_balancers": "list balancers",
        "balancer_list_members": "list members",
        "balancer_attach_member": "attach member",
        "balancer_detach_member": "detach member",
        "balancer_attach_compute_node": "attach compute node",
    },
    "storage_main": {
        "list_containers": "list containers",
        "list_container_objects": "list objects",
        "create_container": "create container",
        "delete_container": "delete container",
        "upload_object": "upload object",
        "upload_object_via_stream": "streaming object upload",
        "download_object": "download object",
        "download_object_as_stream": "streaming object download",
        "download_object_range": "download part of an object",
        "download_object_range_as_stream": "streaming partial object download",
        "delete_object": "delete object",
    },
    "storage_cdn": {
        "enable_container_cdn": "enable container cdn",
        "enable_object_cdn": "enable object cdn",
        "get_container_cdn_url": "get container cdn URL",
        "get_object_cdn_url": "get object cdn URL",
    },
    "dns": {
        "list_zones": "list zones",
        "list_records": "list records",
        "create_zone": "create zone",
        "update_zone": "update zone",
        "create_record": "create record",
        "update_record": "update record",
        "delete_zone": "delete zone",
        "delete_record": "delete record",
    },
    "container": {
        "install_image": "install image",
        "list_images": "list images",
        "deploy_container": "deploy container",
        "get_container": "get container",
        "list_containers": "list containers",
        "start_container": "start container",
        "stop_container": "stop container",
        "restart_container": "restart container",
        "destroy_container": "destroy container",
        "list_locations": "list locations",
        "create_cluster": "create cluster",
        "destroy_cluster": "destroy cluster",
        "list_clusters": "list clusters",
    },
    "backup": {
        "get_supported_target_types": "get supported target types",
        "list_targets": "list targets",
        "create_target": "create target",
        "create_target_from_node": "create target from node",
        "create_target_from_storage_container": "create target from storage container",
        "update_target": "update target",
        "delete_target": "delete target",
        "list_recovery_points": "list recovery points",
        "recover_target": "recover target",
        "recover_target_out_of_place": "recover target out of place",
        "list_target_jobs": "list target jobs",
        "create_target_job": "create target job",
        "resume_target_job": "resume target job",
        "suspend_target_job": "suspend target job",
        "cancel_target_job": "cancel target job",
    },
}

IGNORED_PROVIDERS = [
    "dummy",
    # Deprecated constants
    "cloudsigma_us",
    "cloudfiles_swift",
]


def get_provider_api_names(Provider):
    names = [key for key, value in Provider.__dict__.items() if not key.startswith("__")]
    return names


def generate_providers_table(api):
    result = {}

    if api in [
        "compute_main",
        "compute_image_management",
        "compute_block_storage",
        "compute_key_pair_management",
    ]:
        driver = NodeDriver
        drivers = COMPUTE_DRIVERS
        provider = ComputeProvider
        get_driver_method = get_compute_driver
    elif api == "loadbalancer":
        driver = LBDriver
        drivers = LB_DRIVERS
        provider = LBProvider
        get_driver_method = get_lb_driver
    elif api in ["storage_main", "storage_cdn"]:
        driver = StorageDriver
        drivers = STORAGE_DRIVERS
        provider = StorageProvider
        get_driver_method = get_storage_driver
    elif api == "dns":
        driver = DNSDriver
        drivers = DNS_DRIVERS
        provider = DNSProvider
        get_driver_method = get_dns_driver
    elif api == "container":
        driver = ContainerDriver
        drivers = CONTAINER_DRIVERS
        provider = ContainerProvider
        get_driver_method = get_container_driver
    elif api == "backup":
        driver = BackupDriver
        drivers = BACKUP_DRIVERS
        provider = BackupProvider
        get_driver_method = get_backup_driver
    else:
        raise Exception("Invalid api: %s" % (api))

    names = get_provider_api_names(provider)

    result = OrderedDict()
    for name in names:
        enum = getattr(provider, name)

        try:
            cls = get_driver_method(enum)
        except Exception as e:
            # Deprecated providers throw an exception
            print('Ignoring deprecated constant "{}": {}'.format(enum, str(e)))
            continue

        # Hack for providers which expose multiple classes and support multiple
        # API versions
        # TODO: Make entry per version
        if name.lower() == "cloudsigma":
            from libcloud.compute.drivers.cloudsigma import CloudSigma_2_0_NodeDriver

            cls = CloudSigma_2_0_NodeDriver
        elif name.lower() == "opennebula":
            from libcloud.compute.drivers.opennebula import OpenNebula_3_8_NodeDriver

            cls = OpenNebula_3_8_NodeDriver
        elif name.lower() == "digital_ocean" and api.startswith("compute"):
            from libcloud.compute.drivers.digitalocean import DigitalOcean_v2_NodeDriver

            cls = DigitalOcean_v2_NodeDriver
        elif name.lower() == "linode" and api.startswith("compute"):
            from libcloud.compute.drivers.linode import LinodeNodeDriverV4

            cls = LinodeNodeDriverV4
        elif name.lower() == "linode" and api.startswith("dns"):
            from libcloud.dns.drivers.linode import LinodeDNSDriverV4

            cls = LinodeDNSDriverV4
        elif name.lower() == "vultr" and api.startswith("compute"):
            from libcloud.compute.drivers.vultr import VultrNodeDriverV2

            cls = VultrNodeDriverV2
        elif name.lower() == "vultr" and api.startswith("dns"):
            from libcloud.dns.drivers.vultr import VultrDNSDriverV2

            cls = VultrDNSDriverV2

        if name.lower() in IGNORED_PROVIDERS:
            continue

        def is_function_or_method(*args, **kwargs):
            return inspect.isfunction(*args, **kwargs) or inspect.ismethod(*args, **kwargs)

        driver_methods = dict(inspect.getmembers(cls, predicate=is_function_or_method))
        base_methods = dict(inspect.getmembers(driver, predicate=is_function_or_method))
        base_api_methods = BASE_API_METHODS[api]

        result[name] = {
            "name": cls.name,
            "website": cls.website,
            "constant": name,
            "module": drivers[enum][0],
            "class": drivers[enum][1],
            "cls": cls,
            "methods": {},
        }

        print("Generating tables for provider: %s" % (name))

        for method_name in base_api_methods:
            base_method = base_methods[method_name]

            if method_name == "deploy_node":
                features = getattr(cls, "features", {}).get("create_node", [])
                is_implemented = len(features) >= 1
            else:
                if method_name not in driver_methods:
                    is_implemented = False
                else:
                    driver_method = driver_methods[method_name]
                    # NOTE: id() is not safe
                    # is_implemented = (id(driver_method) != id(base_method))
                    is_implemented = driver_method != base_method

            result[name]["methods"][method_name] = is_implemented

    return result


def generate_rst_table(data):
    cols = len(data[0])
    col_len = [max(len(r[i]) for r in data) for i in range(cols)]
    formatter = " ".join("{:<%d}" % c for c in col_len)

    header = formatter.format(*["=" * c for c in col_len])
    rows = [formatter.format(*row) for row in data]
    result = header + "\n" + rows[0] + "\n" + header + "\n" + "\n".join(rows[1:]) + "\n" + header

    return result


def generate_supported_methods_table(api, provider_matrix):
    base_api_methods = BASE_API_METHODS[api]
    data = []
    header = [
        FRIENDLY_METHODS_NAMES[api][method_name]
        for method_name in base_api_methods
        if not method_name.startswith("iterate_")
    ]
    data.append(["Provider"] + header)

    for provider, values in sorted(provider_matrix.items()):
        provider_name = "`%s`_" % (values["name"])
        row = [provider_name]

        # TODO: Make it nicer
        # list_* methods don't need to be implemented if iterate_* methods are
        # implemented
        if api == "storage_main":
            if values["methods"]["iterate_containers"]:
                values["methods"]["list_containers"] = True

            if values["methods"]["iterate_container_objects"]:
                values["methods"]["list_container_objects"] = True
        elif api == "dns":
            # list_zones and list_records don't need to be implemented if
            if values["methods"]["iterate_zones"]:
                values["methods"]["list_zones"] = True

            if values["methods"]["iterate_records"]:
                values["methods"]["list_records"] = True

        for method in base_api_methods:
            # TODO: ghetto
            if method.startswith("iterate_"):
                continue

            supported = values["methods"][method]

            if supported:
                row.append("yes")
            else:
                row.append("no")
        data.append(row)

    result = generate_rst_table(data)

    result += "\n\n"
    for provider, values in sorted(provider_matrix.items()):
        result += ".. _`{}`: {}\n".format(values["name"], values["website"])
    return result


def generate_supported_providers_table(api, provider_matrix):
    data = []
    header = [
        "Provider",
        "Documentation",
        "Provider Constant",
        "Supported Regions",
        "Module",
        "Class Name",
    ]

    data.append(header)
    for provider, values in sorted(provider_matrix.items()):
        name_str = "`%s`_" % (values["name"])
        module_str = ":mod:`%s`" % (values["module"])
        class_str = ":class:`%s`" % (values["class"])

        # Ignore old deprecated driver class per region S3 drivers
        if "Amazon S3 (" in values["name"]:
            continue

        params = {"api": api, "provider": provider.lower()}
        driver_docs_path = pjoin(BASE_DIR, "docs/%(api)s/drivers/%(provider)s.rst" % params)

        if os.path.exists(driver_docs_path):
            docs_link = ":doc:`Click </%(api)s/drivers/%(provider)s>`" % params
        else:
            docs_link = ""

        cls = values["cls"]
        supported_regions = cls.list_regions() if hasattr(cls, "list_regions") else None

        if supported_regions:
            # Sort the regions to achieve stable output
            supported_regions = sorted(supported_regions)
            supported_regions = ", ".join(supported_regions)
        else:
            supported_regions = "single region driver"

        row = [
            name_str,
            docs_link,
            values["constant"],
            supported_regions,
            module_str,
            class_str,
        ]
        data.append(row)

    result = generate_rst_table(data)

    result += "\n\n"
    for provider, values in sorted(provider_matrix.items()):
        result += ".. _`{}`: {}\n".format(values["name"], values["website"])
    return result


def generate_tables():
    apis = BASE_API_METHODS.keys()
    for api in apis:
        result = generate_providers_table(api)

        docs_dir = api

        if api.startswith("compute"):
            docs_dir = "compute"
        elif api.startswith("storage"):
            docs_dir = "storage"

        supported_providers = generate_supported_providers_table(docs_dir, result)
        supported_methods = generate_supported_methods_table(api, result)

        current_path = os.path.dirname(__file__)
        target_dir = os.path.abspath(pjoin(current_path, "../docs/%s/" % (docs_dir)))

        file_name_1 = "_supported_providers.rst"
        file_name_2 = "_supported_methods.rst"

        if api == "compute_main":
            file_name_2 = "_supported_methods_main.rst"
        elif api == "compute_image_management":
            file_name_2 = "_supported_methods_image_management.rst"
        elif api == "compute_block_storage":
            file_name_2 = "_supported_methods_block_storage.rst"
        elif api == "compute_key_pair_management":
            file_name_2 = "_supported_methods_key_pair_management.rst"
        elif api == "storage_main":
            file_name_2 = "_supported_methods_main.rst"
        elif api == "storage_cdn":
            file_name_2 = "_supported_methods_cdn.rst"

        supported_providers_path = pjoin(target_dir, file_name_1)
        supported_methods_path = pjoin(target_dir, file_name_2)

        with open(supported_providers_path, "w") as fp:
            fp.write(HEADER + "\n\n")
            fp.write(supported_providers)

        with open(supported_methods_path, "w") as fp:
            fp.write(HEADER + "\n\n")
            fp.write(supported_methods)


generate_tables()
