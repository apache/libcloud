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

from __future__ import with_statement

from typing import Dict
from typing import Optional
from typing import Union

import os.path
from os.path import join as pjoin

try:
    import simplejson as json
    try:
        JSONDecodeError = json.JSONDecodeError
    except AttributeError:
        # simplejson < 2.1.0 does not have the JSONDecodeError exception class
        JSONDecodeError = ValueError  # type: ignore
except ImportError:
    import json  # type: ignore
    JSONDecodeError = ValueError  # type: ignore

__all__ = [
    'get_pricing',
    'get_size_price',
    'set_pricing',
    'clear_pricing_data',
    'download_pricing_file'
]

# Default URL to the pricing file in a git repo
DEFAULT_FILE_URL_GIT = 'https://git-wip-us.apache.org/repos/asf?p=libcloud.git;a=blob_plain;f=libcloud/data/pricing.json'  # NOQA

DEFAULT_FILE_URL_S3_BUCKET = 'https://libcloud-pricing-data.s3.amazonaws.com/pricing.json'  # NOQA

CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PRICING_FILE_PATH = pjoin(CURRENT_DIRECTORY, 'data/pricing.json')
CUSTOM_PRICING_FILE_PATH = os.path.expanduser('~/.libcloud/pricing.json')

# Pricing data cache
PRICING_DATA = {
    'compute': {},
    'storage': {}
}  # type: Dict[str, Dict]

VALID_PRICING_DRIVER_TYPES = ['compute', 'storage']

# Set this to True to cache all the pricing data in memory instead of just the
# one for the drivers which are used
CACHE_ALL_PRICING_DATA = False


def get_pricing_file_path(file_path=None):
    # type: (Optional[str]) -> str
    if os.path.exists(CUSTOM_PRICING_FILE_PATH) and \
       os.path.isfile(CUSTOM_PRICING_FILE_PATH):
        # Custom pricing file is available, use it
        return CUSTOM_PRICING_FILE_PATH

    return DEFAULT_PRICING_FILE_PATH


def get_pricing(driver_type, driver_name, pricing_file_path=None,
                cache_all=False):
    # type: (str, str, Optional[str], bool) -> Optional[dict]
    """
    Return pricing for the provided driver.

    NOTE: This method will also cache data for the requested driver
    memory.

    We intentionally only cache data for the requested driver and not all the
    pricing data since the whole pricing data is quite large (~2 MB). This
    way we avoid unncessary memory overhead.

    :type driver_type: ``str``
    :param driver_type: Driver type ('compute' or 'storage')

    :type driver_name: ``str``
    :param driver_name: Driver name

    :type pricing_file_path: ``str``
    :param pricing_file_path: Custom path to a price file. If not provided
                              it uses a default path.

    :type cache_all: ``bool``
    :param cache_all: True to cache pricing data in memory for all the drivers
                      and not just for the requested one.

    :rtype: ``dict``
    :return: Dictionary with pricing where a key name is size ID and
             the value is a price.
    """
    cache_all = cache_all or CACHE_ALL_PRICING_DATA

    if driver_type not in VALID_PRICING_DRIVER_TYPES:
        raise AttributeError('Invalid driver type: %s', driver_type)

    if driver_name in PRICING_DATA[driver_type]:
        return PRICING_DATA[driver_type][driver_name]

    if not pricing_file_path:
        pricing_file_path = get_pricing_file_path(file_path=pricing_file_path)

    with open(pricing_file_path, "r") as fp:
        content = fp.read()

    pricing_data = json.loads(content)
    driver_pricing = pricing_data[driver_type][driver_name]

    # NOTE: We only cache prices in memory for the the requested drivers.
    # This way we avoid storing massive pricing data for all the drivers in
    # memory

    if cache_all:
        for driver_type in VALID_PRICING_DRIVER_TYPES:
            # pylint: disable=maybe-no-member
            pricing = pricing_data.get(driver_type, None)

            if not pricing:
                continue

            PRICING_DATA[driver_type] = pricing
    else:
        set_pricing(driver_type=driver_type, driver_name=driver_name,
                    pricing=driver_pricing)

    return driver_pricing


def set_pricing(driver_type, driver_name, pricing):
    # type: (str, str, dict) -> None
    """
    Populate the driver pricing dictionary.

    :type driver_type: ``str``
    :param driver_type: Driver type ('compute' or 'storage')

    :type driver_name: ``str``
    :param driver_name: Driver name

    :type pricing: ``dict``
    :param pricing: Dictionary where a key is a size ID and a value is a price.
    """

    PRICING_DATA[driver_type][driver_name] = pricing


def get_size_price(driver_type, driver_name, size_id, region=None):
    # type: (str, str, Union[str,int], Optional[str]) -> Optional[float]
    """
    Return price for the provided size.

    :type driver_type: ``str``
    :param driver_type: Driver type ('compute' or 'storage')

    :type driver_name: ``str``
    :param driver_name: Driver name

    :type size_id: ``str`` or ``int``
    :param size_id: Unique size ID (can be an integer or a string - depends on
                    the driver)

    :rtype: ``float``
    :return: Size price.
    """
    pricing = get_pricing(driver_type=driver_type, driver_name=driver_name)
    assert pricing is not None

    price = None  # Type: Optional[float]

    try:
        if region is None:
            price = float(pricing[size_id])
        else:
            price = float(pricing[size_id][region])
    except KeyError:
        # Price not available
        price = None

    return price


def invalidate_pricing_cache():
    # type: () -> None
    """
    Invalidate pricing cache for all the drivers.
    """
    PRICING_DATA['compute'] = {}
    PRICING_DATA['storage'] = {}


def clear_pricing_data():
    # type: () -> None
    """
    Invalidate pricing cache for all the drivers.

    Note: This method does the same thing as invalidate_pricing_cache and is
    here for backward compatibility reasons.
    """
    invalidate_pricing_cache()


def invalidate_module_pricing_cache(driver_type, driver_name):
    # type: (str, str) -> None
    """
    Invalidate the cache for the specified driver.

    :type driver_type: ``str``
    :param driver_type: Driver type ('compute' or 'storage')

    :type driver_name: ``str``
    :param driver_name: Driver name
    """
    if driver_name in PRICING_DATA[driver_type]:
        del PRICING_DATA[driver_type][driver_name]


def download_pricing_file(file_url=DEFAULT_FILE_URL_S3_BUCKET,
                          file_path=CUSTOM_PRICING_FILE_PATH):
    # type: (str, str) -> None
    """
    Download pricing file from the file_url and save it to file_path.

    :type file_url: ``str``
    :param file_url: URL pointing to the pricing file.

    :type file_path: ``str``
    :param file_path: Path where a download pricing file will be saved.
    """
    from libcloud.utils.connection import get_response_object

    dir_name = os.path.dirname(file_path)

    if not os.path.exists(dir_name):
        # Verify a valid path is provided
        msg = ('Can\'t write to %s, directory %s, doesn\'t exist' %
               (file_path, dir_name))
        raise ValueError(msg)

    if os.path.exists(file_path) and os.path.isdir(file_path):
        msg = ('Can\'t write to %s file path because it\'s a'
               ' directory' % (file_path))
        raise ValueError(msg)

    response = get_response_object(file_url)
    body = response.body

    # Verify pricing file is valid
    try:
        data = json.loads(body)
    except JSONDecodeError:
        msg = 'Provided URL doesn\'t contain valid pricing data'
        raise Exception(msg)

    # pylint: disable=maybe-no-member
    if not data.get('updated', None):
        msg = 'Provided URL doesn\'t contain valid pricing data'
        raise Exception(msg)

    # No need to stream it since file is small
    with open(file_path, 'w') as file_handle:
        file_handle.write(body)
