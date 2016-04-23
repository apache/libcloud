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
Script which checks a driver for for compliance against the base API.

Right now it checks for the following things:

1. Driver methods which are not part of the base API need to be prefixed with
   "ex_"
2. Additional arguments for the methods which are part of the standard API need
   to be prefixed with "ex_"
3. Method signature for the methods which are part of the standard API needs to
   match the signature of of the standard API (ignoring the extension arguments).
"""

import os
import argparse
import hashlib
import inspect

from collections import defaultdict

import libcloud

from libcloud.compute.providers import get_driver as get_compute_driver
from libcloud.compute.base import NodeDriver

import libcloud.dns.providers
from libcloud.dns.base import DNSDriver

import libcloud.loadbalancer.providers
from libcloud.loadbalancer.base import Driver as LBDriver

import libcloud.storage.providers
from libcloud.storage.base import StorageDriver


# Maps API to base classes
API_MAP = {
    'compute': {
        'get_driver_func': get_compute_driver,
        'driver_class': NodeDriver,
        'methods_specs': []
    }
}

# Global object which stores all the warnings so we can avoide duplicates
WARNINGS_SET = set()


def get_hash_for_dict(obj):
    result = hashlib.md5()

    for key, value in obj.items():
        result.update('%s-%s' % (key, value))

    result = result.hexdigest()
    return result


def get_warning_object(obj, message):
    source_file = os.path.relpath(inspect.getsourcefile(obj), os.path.dirname(libcloud.__file__))
    source_line = inspect.getsourcelines(obj)[1]

    result = {}
    result['source_file'] = source_file
    result['source_line'] = source_line
    result['message'] = message

    dict_hash = get_hash_for_dict(result)
    if dict_hash in WARNINGS_SET:
        # When the error is actually caused by a mixin or base class we can get dupes...
        return None

    WARNINGS_SET.add(dict_hash)
    return result


def get_method_list_for_base_apis():
    """
    Build a list of methods for all the base APIs.
    """
    result = defaultdict(dict)

    for api_name, values in API_MAP.items():
        driver_class = values['driver_class']
        base_class = driver_class
        core_api = {}

        base_class_methods = inspect.getmembers(base_class, inspect.ismethod)
        for name, method in base_class_methods:
            # Ignore "private" methods
            if name.startswith('_'):
                continue

            if name.startswith('ex_'):
                #warning(method, 'Core driver shouldn\'t have "ex_" methods')
                continue

            args = inspect.getargspec(method)
            core_api[name] = args

            for arg in args.args:
                if arg.startswith('ex_'):
                    pass
                    #warning(method, 'Core driver method shouldnt have ex_ arguments')

        result[api_name] = core_api

    return result


def get_warnings_driver_for_module(driver_constant, base_api):
    get_driver = base_api['get_driver_func']
    methods_specs = base_api['methods_specs']

    driver = get_driver(driver_constant)

    warnings = []
    for name, method in inspect.getmembers(driver, inspect.ismethod):
        # Skip "private" methods
        if name.startswith('_'):
            continue

        # Methods which are not part of the base API need to be prefixed with
        # "ex_"
        if not name.startswith('ex_') and name not in methods_specs:
            message = ('"%s" should be prefixed with ex_ or be private as it is not a core API' % (name))
            warning = get_warning_object(obj=method, message=message)
            warnings.append(warning)
            continue

        if name not in methods_specs:
            # Method is not part of the base API
            continue

        argspec = inspect.getargspec(method)

        core_args = set(methods_specs[name].args)
        driver_args = set(argspec.args)

        # TODO: Also check the argument order for the base API
        missing_args = (core_args - driver_args)
        for missing in missing_args:
            message = 'Core API function "%s" should support arg "%s" but doesn\'t' % (name, missing)
            warning = get_warning_object(obj=method, message=message)
            warnings.append(warning)

        extra_args = (driver_args - core_args)
        for extra in extra_args:
            if not extra.startswith('ex_'):
                message = "Core API function shouldn't take arg '%s'. Should it be prefixed with ex_?" % extra
                warning = get_warning_object(obj=method, message=message)
                warnings.append(warning)

    # Filter out empty warning objects (dupes)
    warnings = [warning for warning in warnings if warning is not None]
    return warnings


def generate_report_for_driver(warnings):
    result = []

    for warning in warnings:
        line = '%s:%s : %s' % (warning['source_file'], warning['source_line'],
                               warning['message'])
        result.append(line)

    result = '\n'.join(result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Compliance and quality check')
    parser.add_argument('--driver-api', action='store', required=True,
                        help='API of the driver to check')
    parser.add_argument('--driver-constant', action='store', required=True,
                        help='Name of the provider constant to check')
    args = parser.parse_args()

    driver_api = args.driver_api
    driver_constant = args.driver_constant

    base_methods_map = get_method_list_for_base_apis()

    base_methods = base_methods_map[driver_api]
    API_MAP[driver_api]['methods_specs'] = base_methods
    warnings = get_warnings_driver_for_module(driver_constant=driver_constant,
                                              base_api=API_MAP[driver_api])
    report = generate_report_for_driver(warnings=warnings)
    print(report)
