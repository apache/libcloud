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
"""
A class which handles loading the pricing files.
"""

try:
    import simplejson as json
except ImportError:
    import json

import os.path
from os.path import join as pjoin

PRICING_FILE_PATH = 'data/pricing.json'

PRICING_DATA = {}

VALID_PRICING_DRIVER_TYPES = ['compute', 'storage']


def clear_pricing_data():
    PRICING_DATA.clear()
    PRICING_DATA.update({
        'compute': {},
        'storage': {},
    })
clear_pricing_data()


def get_pricing_file_path(file_path=None):
    pricing_directory = os.path.dirname(os.path.abspath(__file__))
    pricing_file_path = pjoin(pricing_directory, PRICING_FILE_PATH)

    return pricing_file_path

def get_pricing(driver_type, driver_name, pricing_file_path=None):
    """
    Return pricing for the provided driver.

    @type driver_type: C{str}
    @param driver_type: Driver type ('compute' or 'storage')

    @type driver_name: C{str}
    @param driver_name: Driver name

    @rtype: C{dict}
    @return: Dictionary with pricing where a key name is size ID and
             the value is a price.
    """
    if not driver_type in VALID_PRICING_DRIVER_TYPES:
        raise AttributeError('Invalid driver type: %s', driver_type)

    if driver_name in PRICING_DATA[driver_type]:
        return PRICING_DATA[driver_type][driver_name]

    if not pricing_file_path:
        pricing_file_path = get_pricing_file_path(file_path=pricing_file_path)

    with open(pricing_file_path) as fp:
        content = fp.read()

    pricing_data = json.loads(content)
    size_pricing = pricing_data[driver_type][driver_name]

    for driver_type in VALID_PRICING_DRIVER_TYPES:
        pricing = pricing_data.get(driver_type, None)
        if pricing:
            PRICING_DATA[driver_type] = pricing

    return size_pricing

def set_pricing(driver_type, driver_name, pricing):
    """
    Populate the driver pricing dictionary.

    @type driver_type: C{str}
    @param driver_type: Driver type ('compute' or 'storage')

    @type driver_name: C{str}
    @param driver_name: Driver name

    @type pricing: C{dict}
    @param pricing: Dictionary where a key is a size ID and a value is a price.
    """

    PRICING_DATA[driver_type][driver_name] = pricing

def get_size_price(driver_type, driver_name, size_id):
    """
    Return price for the provided size.

    @type driver_type: C{str}
    @param driver_type: Driver type ('compute' or 'storage')

    @type driver_name: C{str}
    @param driver_name: Driver name

    @type size_id: C{int/str}
    @param size_id: Unique size ID (can be an integer or a string - depends on
                    the driver)

    @rtype: C{int}
    @return: Size price.
    """
    pricing = get_pricing(driver_type=driver_type, driver_name=driver_name)
    price = float(pricing[size_id])
    return price

def invalidate_pricing_cache():
    """
    Invalidate the cache for all the drivers.
    """
    PRICING_DATA['compute'] = {}
    PRICING_DATA['storage'] = {}

def invalidate_module_pricing_cache(driver_type, driver_name):
    """
    Invalidate the cache for the specified driver.

    @type driver_type: C{str}
    @param driver_type: Driver type ('compute' or 'storage')

    @type driver_name: C{str}
    @param driver_name: Driver name
    """
    if driver_name in PRICING_DATA[driver_type]:
        del PRICING_DATA[driver_type][driver_name]
