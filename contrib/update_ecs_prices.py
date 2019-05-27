#!/usr/bin/env python

"""
Loads Aliyun ECS prices and updates the `pricing.json` data file.
"""

import os
import json
import simplejson
import sys
import time
import urllib2
import utils
import requests

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
PRICING_FILE_PATH = os.path.join(BASE_PATH, '../libcloud/data/pricing.json')
PRICING_FILE_PATH = os.path.abspath(PRICING_FILE_PATH)

ALIYUN_ECS_PRICES = 'https://g.alicdn.com/aliyun/ecs-price-info-intl/2.0.15/price/download/instancePrice.json'


def main(argv):
    # Read the current pricing data.
    libcloud_data = {}
    with open(PRICING_FILE_PATH, 'r') as libcloud_in:
        libcloud_data = json.loads(libcloud_in.read())

    # Download the current Aliyun ECS pricing.
    res = requests.get(ALIYUN_ECS_PRICES)
    if 'pricingInfo' not in res.json().keys():
        sys.stderr.write('Pricing info is missing \n')
        sys.exit(1)

    pricing_info = res.json().get('pricingInfo')
    for key, values in pricing_info.iteritems():
        attributes = key.split('::')
        location = attributes[0]
        size = attributes[1]
        os_type = attributes[3]

        price = {"pay_as_you_go": values.get('hours')[0].get('price')}
        price.update({"prepaid": values.get('months')[0].get('price')})
 
        try:
            libcloud_data['compute']['ecs-' + location][size].update({os_type:  price })
        except KeyError:
            try:
                libcloud_data['compute']['ecs-' + location].update({size: {os_type: price}})
            except KeyError:
                libcloud_data['compute']['ecs-' + location] = {size: {os_type: price}}

    # Update last-modified timestamp.
    libcloud_data['updated'] = int(time.time())

    # Write updated price list.
    with open(PRICING_FILE_PATH, 'w') as libcloud_out:
        json_str = simplejson.dumps(libcloud_data, indent=4 * ' ',
                                    item_sort_key=utils.sortKeysNumerically)
        libcloud_out.write(json_str)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
