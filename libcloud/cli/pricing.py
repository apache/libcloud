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

try:
    import simplejson as json
except ImportError:
    import json


from libcloud.pricing import CUSTOM_PRICING_FILE_PATH
from libcloud.utils.connection import get_response_object

__all__ = [
    'add_subparser',
    'update_pricing'
]

# Default URL to the pricing file
DEFAULT_FILE_URL = 'https://git-wip-us.apache.org/repos/asf?p=libcloud.git;a=blob_plain;f=libcloud/data/pricing.json'


def add_subparser(subparsers):
    parser = subparsers.add_parser('update-pricing',
                                   help='Update Libcloud pricing file')
    parser.add_argument('--file-path', dest='file_path', action='store',
                        default=CUSTOM_PRICING_FILE_PATH,
                        help='Path where the file will be saved')
    parser.add_argument('--file-url', dest='file_url', action='store',
                        default=DEFAULT_FILE_URL,
                        help='URL to the pricing file')
    return parser


def update_pricing(file_url, file_path):
    dir_name = os.path.dirname(file_path)

    if not os.path.exists(dir_name):
        # Verify a valid path is provided
        sys.stderr.write('Can\'t write to %s, directory %s, doesn\'t exist\n' %
                         (file_path, dir_name))
        sys.exit(2)

    if os.path.exists(file_path) and os.path.isdir(file_path):
        sys.stderr.write('Can\'t write to %s file path because it\'s a'
                         ' directory\n' %
                         (file_path))
        sys.exit(2)

    response = get_response_object(file_url)
    body = response.body

    # Verify pricing file is valid
    try:
        data = json.loads(body)
    except json.decoder.JSONDecodeError:
        sys.stderr.write('Provided URL doesn\'t contain valid pricing'
                         ' data\n')
        sys.exit(3)

    if not data.get('updated', None):
        sys.stderr.write('Provided URL doesn\'t contain valid pricing'
                         ' data\n')
        sys.exit(3)

    # No need to stream it since file is small
    with open(file_path, 'w') as file_handle:
        file_handle.write(response.body)

    print('Pricing file saved to %s' % (file_path))
