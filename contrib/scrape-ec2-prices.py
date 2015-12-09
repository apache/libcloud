#!/usr/bin/env python
#
#  Licensed to the Apache Software Foundation (ASF) under one
#  or more contributor license agreements.  See the NOTICE file
#  distributed with this work for additional information
#  regarding copyright ownership.  The ASF licenses this file
#  to you under the Apache License, Version 2.0 (the
#  "License"); you may not use this file except in compliance
#  with the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing,
#  software distributed under the License is distributed on an
#  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#  KIND, either express or implied.  See the License for the
#  specific language governing permissions and limitations
#  under the License.

import os
import re
import json
import time
from collections import defaultdict, OrderedDict

import requests
import demjson

LINUX_PRICING_URLS = [
    # Deprecated instances (JSON format)
    'https://aws.amazon.com/ec2/pricing/json/linux-od.json',
    # Previous generation instances (JavaScript file)
    'https://a0.awsstatic.com/pricing/1/ec2/previous-generation/linux-od.min.js',
    # New generation instances (JavaScript file)
    'https://a0.awsstatic.com/pricing/1/ec2/linux-od.min.js'
]

EC2_REGIONS = [
    'us-east-1',
    'us-west-1',
    'us-west-2',
    'eu-west-1',
    'eu-central-1',
    'ap-southeast-1',
    'ap-southeast-2',
    'ap-northeast-1',
    'sa-east-1'
]

EC2_INSTANCE_TYPES = [
    't1.micro',
    'm1.small',
    'm1.medium',
    'm1.large',
    'm1.xlarge',
    'm2.xlarge',
    'm2.2xlarge',
    'm2.4xlarge',
    'm3.medium',
    'm3.large',
    'm3.xlarge',
    'm3.2xlarge',
    'c1.medium',
    'c1.xlarge',
    'cc1.4xlarge',
    'cc2.8xlarge',
    'c3.large',
    'c3.xlarge',
    'c3.2xlarge',
    'c3.4xlarge',
    'c3.8xlarge',
    'd2.xlarge',
    'd2.2xlarge',
    'd2.4xlarge',
    'd2.8xlarge',
    'cg1.4xlarge',
    'g2.2xlarge',
    'g2.8xlarge',
    'cr1.8xlarge',
    'hs1.4xlarge',
    'hs1.8xlarge',
    'i2.xlarge',
    'i2.2xlarge',
    'i2.4xlarge',
    'i2.8xlarge',
    'r3.large',
    'r3.xlarge',
    'r3.2xlarge',
    'r3.4xlarge',
    'r3.8xlarge',
    't2.micro',
    't2.small',
    't2.medium',
    't2.large'
]

# Maps EC2 region name to region name used in the pricing file
REGION_NAME_MAP = {
    'us-east': 'ec2_us_east',
    'us-east-1': 'ec2_us_east',
    'us-west': 'ec2_us_west',
    'us-west-1': 'ec2_us_west',
    'us-west-2': 'ec2_us_west_oregon',
    'eu-west-1': 'ec2_eu_west',
    'eu-ireland': 'ec2_eu_west',
    'eu-central-1': 'ec2_eu_central',
    'apac-sin': 'ec2_ap_southeast',
    'ap-southeast-1': 'ec2_ap_southeast',
    'apac-syd': 'ec2_ap_southeast_2',
    'ap-southeast-2': 'ec2_ap_southeast_2',
    'apac-tokyo': 'ec2_ap_northeast',
    'ap-northeast-1': 'ec2_ap_northeast',
    'sa-east-1': 'ec2_sa_east',
    'us-gov-west-1': 'ec2_us_govwest'
}

INSTANCE_SIZES = [
    'micro',
    'small',
    'medium',
    'large',
    'xlarge',
    'x-large',
    'extra-large'
]

RE_NUMERIC_OTHER = re.compile(r'(?:([0-9]+)|([-A-Z_a-z]+)|([^-0-9A-Z_a-z]+))')

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
PRICING_FILE_PATH = os.path.join(BASE_PATH, '../libcloud/data/pricing.json')
PRICING_FILE_PATH = os.path.abspath(PRICING_FILE_PATH)


def scrape_ec2_pricing():
    result = defaultdict(OrderedDict)

    for url in LINUX_PRICING_URLS:
        response = requests.get(url)

        if re.match('.*?\.json$', url):
            data = response.json()
        elif re.match('.*?\.js$', url):
            data = response.content
            match = re.match('^.*callback\((.*?)\);?$', data,
                             re.MULTILINE | re.DOTALL)
            data = match.group(1)
            # demjson supports non-strict mode and can parse unquoted objects
            data = demjson.decode(data)

        regions = data['config']['regions']

        for region_data in regions:
            region_name = region_data['region']
            libcloud_region_name = REGION_NAME_MAP[region_name]
            instance_types = region_data['instanceTypes']

            for instance_type in instance_types:
                sizes = instance_type['sizes']

                for size in sizes:
                    price = size['valueColumns'][0]['prices']['USD']
                    result[libcloud_region_name][size['size']] = price

    return result


def update_pricing_file(pricing_file_path, pricing_data):
    with open(pricing_file_path, 'r') as fp:
        content = fp.read()

    data = json.loads(content)
    data['updated'] = int(time.time())
    data['compute'].update(pricing_data)

    # Always sort the pricing info
    data = sort_nested_dict(data)

    content = json.dumps(data, indent=4)
    lines = content.splitlines()
    lines = [line.rstrip() for line in lines]
    content = '\n'.join(lines)

    with open(pricing_file_path, 'w') as fp:
        fp.write(content)


def sort_nested_dict(value):
    """
    Recursively sort a nested dict.
    """
    result = OrderedDict()

    for key, value in sorted(value.items(), key=sort_key_by_numeric_other):
        if isinstance(value, (dict, OrderedDict)):
            result[key] = sort_nested_dict(value)
        else:
            result[key] = value

    return result


def sort_key_by_numeric_other(key_value):
    """
    Split key into numeric, alpha and other part and sort accordingly.
    """
    return tuple((
        int(numeric) if numeric else None,
        INSTANCE_SIZES.index(alpha) if alpha in INSTANCE_SIZES else alpha,
        other
    ) for (numeric, alpha, other) in RE_NUMERIC_OTHER.findall(key_value[0]))


def main():
    print('Scraping EC2 pricing data')

    pricing_data = scrape_ec2_pricing()
    update_pricing_file(pricing_file_path=PRICING_FILE_PATH,
                        pricing_data=pricing_data)

    print('Pricing data updated')


if __name__ == '__main__':
    main()
