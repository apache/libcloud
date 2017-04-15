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
libcloud linter

This script checks the libcloud codebase for registered drivers that don't
comply to libcloud API guidelines.
"""

import inspect
import os

import libcloud

import libcloud.compute.providers
from libcloud.compute.base import NodeDriver

import libcloud.dns.providers
from libcloud.dns.base import DNSDriver

import libcloud.loadbalancer.providers
from libcloud.loadbalancer.base import Driver

import libcloud.storage.providers
from libcloud.storage.base import StorageDriver


modules = [
    (libcloud.compute.providers, NodeDriver),
    (libcloud.dns.providers, DNSDriver),
    (libcloud.loadbalancer.providers, Driver),
    (libcloud.storage.providers, StorageDriver),
    ]


warnings = set()

def warning(obj, warning):
    source_file = os.path.relpath(inspect.getsourcefile(obj), os.path.dirname(libcloud.__file__))
    source_line = inspect.getsourcelines(obj)[1]
    if (source_file, source_line, warning) in warnings:
        # When the error is actually caused by a mixin or base class we can get dupes...
        return
    warnings.add((source_file, source_line, warning))
    print source_file, source_line, warning

for providers, base, in modules:
    core_api = {}
    for name, value in inspect.getmembers(base, inspect.ismethod):
        if name.startswith("_"):
            continue

        if name.startswith("ex_"):
            warning(value, "Core driver shouldn't haveex_ methods")
            continue

        args = core_api[name] = inspect.getargspec(value)

        for arg in args.args:
            if arg.startswith("ex_"):
                warning(value, "Core driver method shouldnt have ex_ arguments")


    for driver_id in providers.DRIVERS.keys():
        driver = providers.get_driver(driver_id)    

        for name, value in inspect.getmembers(driver, inspect.ismethod):
            if name.startswith("_"):
                continue

            if not name.startswith("ex_") and not name in core_api:
                warning(value, "'%s' should be prefixed with ex_ or be private as it is not a core API" % name)
                continue


            # Only validate arguments of core API's
            if name.startswith("ex_"):
                continue

            argspec = inspect.getargspec(value)

            core_args = set(core_api[name].args)
            driver_args = set(argspec.args)

            for missing in core_args - driver_args:
                warning(value, "Core API function should support arg '%s' but doesn't" % missing)

            for extra in driver_args - core_args:
                if not extra.startswith("ex_"):
                    warning(value, "Core API function shouldn't take arg '%s'. Should it be prefixed with ex_?" % extra)

