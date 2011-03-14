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
A class which handles loading the pricing files.
"""

try:
    import json
except:
    import simplejson as json

PRICING_FILE_PATH = 'data/pricing.json'

PRICING_DATA = {
    'compute': {},
    'storage': {}
}

def get_pricing(driver_type, driver_name, pricing_file_path=None):
    """
    Return pricing for the provided driver.

    @type driver_type: C{str}
    @param driver_type: Driver type ('compute' or 'storage')

    @type driver_name: C{str}
    @param driver_name: Driver name

    @return C{dict} Dictionary with pricing where a key name iz size ID and
                    the value is a price.
    """
    if not driver_type in [ 'compute', 'storage' ]:
        raise AttributeError('Invalid driver type: %s', driver_type)

    driver_name = driver_name.lower().replace('nodedriver', '')

    if driver_name in PRICING_DATA[driver_type]:
        return PRICING_DATA[driver_type][driver_name]

    if not pricing_file_path:
        pricing_file_path = PRICING_FILE_PATH

    with open(pricing_file_path) as fp:
        content = fp.read()

    pricing = json.loads(content)[driver_name]

    PRICING_DATA[driver_type][driver_name] = pricing
    return pricing

def invalidate_pricing_cache():
    PRICING_DATA['compute'] = {}
    PRICING_DATA['storage'] = {}

def invalidate_module_pricing_cache(driver_type, driver_name):
    if driver_name in PRICING_DATA[driver_type]:
        del PRICING_DATA[driver_type][driver_name]
