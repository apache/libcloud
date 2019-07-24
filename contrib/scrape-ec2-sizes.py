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
"""
This script downloads and parses AWS EC2 from https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/index.json.
It writes a Python module with constants about EC2's sizes and regions.

Use it as following:
    $ python contrib/scrap-ec2-sizes.py > libcloud/compute/constants.py
"""

import re
import os
import json

import requests
import ijson  # pylint: disable=import-error

FILEPATH = os.environ.get('TMP_JSON', '/tmp/ec.json')
URL = "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/index.json"
IGNORED_FIELDS = ['locationType', 'operatingSystem']
REG_STORAGE = re.compile(r'(\d+) x ([0-9,]+)')
REG_BANDWIDTH = re.compile(r'\D*(\d+)\D*')
#  From <https://aws.amazon.com/marketplace/help/200777880>
REGION_DETAILS = {
    # America
    'US East (N. Virginia)': {
        'id': 'us-east-1',
        'endpoint': 'ec2.us-east-1.amazonaws.com',
        'api_name': 'ec2_us_east',
        'country': 'USA',
        'signature_version': '2',
    },
    'US East (Ohio)': {
        'id': 'us-east-2',
        'endpoint': 'ec2.us-east-2.amazonaws.com',
        'api_name': 'ec2_us_east_ohio',
        'country': 'USA',
        'signature_version': '4',
    },
    'US West (N. California)': {
        'id': 'us-west-1',
        'endpoint': 'ec2.us-west-1.amazonaws.com',
        'api_name': 'ec2_us_west',
        'country': 'USA',
        'signature_version': '2',
    },
    'US West (Oregon)': {
        'id': 'us-west-2',
        'endpoint': 'ec2.us-west-2.amazonaws.com',
        'api_name': 'ec2_us_west_oregon',
        'country': 'US',
        'signature_version': '2',
    },
    'Canada (Central)': {
        'id': 'ca-central-1',
        'endpoint': 'ec2.ca-central-1.amazonaws.com',
        'api_name': 'ec2_ca_central_1',
        'country': 'Canada',
        'signature_version': '4',
    },
    'South America (Sao Paulo)': {
        'id': 'sa-east-1',
        'endpoint': 'ec2.sa-east-1.amazonaws.com',
        'api_name': 'ec2_sa_east',
        'country': 'Brazil',
        'signature_version': '2',
    },
    'AWS GovCloud (US)': {
        'id': 'us-gov-west-1',
        'endpoint': 'ec2.us-gov-west-1.amazonaws.com',
        'api_name': 'ec2_us_govwest',
        'country': 'US',
        'signature_version': '2',
    },
    # EU
    'eu-west-1': {
        'id': 'eu-west-1',
        'endpoint': 'ec2.eu-west-1.amazonaws.com',
        'api_name': 'ec2_eu_west',
        'country': 'Ireland',
        'signature_version': '2',
    },
    'EU (Ireland)': {  # Duplicate from AWS' JSON
        'id': 'eu-west-1',
        'endpoint': 'ec2.eu-west-1.amazonaws.com',
        'api_name': 'ec2_eu_west',
        'country': 'Ireland',
        'signature_version': '2',
    },
    'EU (London)': {
        'id': 'eu-west-2',
        'endpoint': 'ec2.eu-west-2.amazonaws.com',
        'api_name': 'ec2_eu_west_london',
        'country': 'United Kingdom',
        'signature_version': '4',
    },
    'EU (Paris)': {
        'id': 'eu-west-3',
        'endpoint': 'ec2.eu-west-3.amazonaws.com',
        'api_name': 'ec2_eu_west_paris',
        'country': 'France',
        'signature_version': '4',
    },
    'EU (Frankfurt)': {
        'id': 'eu-central-1',
        'endpoint': 'ec2.eu-central-1.amazonaws.com',
        'api_name': 'ec2_eu_central',
        'country': 'Frankfurt',
        'signature_version': '4',
    },
    # Asia
    'Asia Pacific (Mumbai)': {
        'id': 'ap-south-1',
        'endpoint': 'ec2.ap-south-1.amazonaws.com',
        'api_name': 'ec2_ap_south_1',
        'country': 'India',
        'signature_version': '4',
    },
    'Asia Pacific (Singapore)': {
        'id': 'ap-southeast-1',
        'endpoint': 'ec2.ap-southeast-1.amazonaws.com',
        'api_name': 'ec2_ap_southeast',
        'country': 'Singapore',
        'signature_version': '2',
    },
    'Asia Pacific (Sydney)': {
        'id': 'ap-southeast-2',
        'endpoint': 'ec2.ap-southeast-2.amazonaws.com',
        'api_name': 'ec2_ap_southeast_2',
        'country': 'Australia',
        'signature_version': '2',
    },
    'Asia Pacific (Tokyo)': {
        'id': 'ap-northeast-1',
        'endpoint': 'ec2.ap-northeast-1.amazonaws.com',
        'api_name': 'ec2_ap_northeast',
        'country': 'Japan',
        'signature_version': '2',
    },
    'Asia Pacific (Seoul)': {
        'id': 'ap-northeast-2',
        'endpoint': 'ec2.ap-northeast-2.amazonaws.com',
        'api_name': 'ec2_ap_northeast',
        'country': 'South Korea',
        'signature_version': '4',
    },
    'Asia Pacific (Osaka-Local)': {
        'id': 'ap-northeast-3',
        'endpoint': 'ec2.ap-northeast-3.amazonaws.com',
        'api_name': 'ec2_ap_northeast',
        'country': 'Japan',
        'signature_version': '4',
    },
    # Not in JSON
    'China (Beijing)': {
        'id': 'cn-north-1',
        'endpoint': 'ec2.cn-north-1.amazonaws.com.cn',
        'api_name': 'ec2_cn_north',
        'country': 'China',
        'signature_version': '4',
    },
    'China (Ningxia)': {
        'id': 'cn-northwest-1',
        'endpoint': 'ec2.cn-northwest-1.amazonaws.com.cn',
        'api_name': 'ec2_cn_northwest',
        'country': 'China',
        'signature_version': '4',
    },
}


def download_json():
    response = requests.get(URL, stream=True)
    try:
        return open(FILEPATH, 'r')
    except IOError:
        with open(FILEPATH, 'wb') as fo:
            for chunk in response.iter_content(chunk_size=2**20):
                if chunk:
                    fo.write(chunk)
    return open(FILEPATH, 'r')


def get_json():
    try:
        return open(FILEPATH, 'r')
    except IOError:
        return download_json()


def filter_extras(extras):
    return {
        key: extras[key] for key in extras
        if key not in [
            'capacitystatus', 'ebsOptimized', 'operation', 'licenseModel',
            'preInstalledSw', 'tenancy', 'usagetype'
        ]
    }


def parse():
    # Set vars
    sizes = {}
    regions = {r['id']: r for r in REGION_DETAILS.values()}
    for region_id in regions:
        regions[region_id]['instance_types'] = []
    # Parse
    json_file = get_json()
    products_data = ijson.items(json_file, 'products')
    products_data = next(products_data)
    for sku in products_data:
        if products_data[sku]['productFamily'] != "Compute Instance":
            continue
        location = products_data[sku]['attributes'].pop('location')
        if location not in REGION_DETAILS:
            continue
        # Get region & size ID
        region_id = REGION_DETAILS[location]['id']
        instance_type = products_data[sku]['attributes']['instanceType']
        # Add size to region
        if instance_type not in regions[region_id]['instance_types']:
            regions[region_id]['instance_types'].append(instance_type)
        # Parse sizes
        if instance_type not in sizes:
            for field in IGNORED_FIELDS:
                products_data[sku]['attributes'].pop(field, None)
            # Compute RAM
            ram = int(float(products_data[sku]['attributes']['memory'].split()[0]
                      .replace(',', '')) * 1024)
            # Compute bandwdith
            bw_match = REG_BANDWIDTH.match(products_data[sku]['attributes']['networkPerformance'])
            if bw_match is not None:
                bandwidth = int(bw_match.groups()[0])
            else:
                bandwidth = None
            sizes[instance_type] = {
                'id': instance_type,
                'name': instance_type,
                'ram': ram,
                'bandwidth': bandwidth,
                'extra': filter_extras(products_data[sku]['attributes']),
            }
            if products_data[sku]['attributes'].get('storage') != "EBS only":
                disk_number, disk_size = REG_STORAGE.match(
                    products_data[sku]['attributes']['storage']).groups()
                disk_number, disk_size = int(disk_number), int(disk_size.replace(',', ''))
                sizes[instance_type]['disk'] = disk_number * disk_size
            else:
                sizes[instance_type]['disk'] = 0
            products_data[sku]['attributes']
    # Sort
    for region in regions:
        regions[region]['instance_types'] = sorted(regions[region]['instance_types'])
    return sizes, regions


def dump():
    sizes, regions = parse()
    print("# File generated by script")
    print("INSTANCE_TYPES = " + json.dumps(sizes, indent=4, sort_keys=True).replace('null', 'None'))
    print("REGION_DETAILS = " + json.dumps(regions, indent=4, sort_keys=True))


if __name__ == '__main__':
    dump()
