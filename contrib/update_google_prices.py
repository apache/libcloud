#!/usr/bin/env python
#
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
Loads Google Cloud Platform prices and updates the `pricing.json` data file.
"""

# pylint: skip-file

import os
import sys
import json
import time

import urllib2

import utils

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
PRICING_FILE_PATH = os.path.join(BASE_PATH, "../libcloud/data/pricing.json")
PRICING_FILE_PATH = os.path.abspath(PRICING_FILE_PATH)

GOOGLE_CLOUD_PRICES = "https://cloudpricingcalculator.appspot.com/static/data/pricelist.json"


def main(argv):
    # Read the current pricing data.
    libcloud_data = {}
    with open(PRICING_FILE_PATH) as libcloud_in:
        libcloud_data = json.loads(libcloud_in.read())

    # Download the current Google Cloud Platform pricing.
    req = urllib2.Request(GOOGLE_CLOUD_PRICES, "")
    google_ext_prices = json.loads(urllib2.urlopen(req).read())
    if "gcp_price_list" not in google_ext_prices:
        sys.stderr.write('Google Cloud pricing data missing "gcp_price_list" node\n')
        sys.exit(1)

    # This is a map from regions used in the pricing JSON file to the regions as
    # reflected in the Google Cloud Platform documentation and APIs.
    pricing_to_region = {
        "us": "us",
        "eu": "europe",  # alias for 'europe'
        "europe": "europe",
        "apac": "asia",  # alias for 'asia'
        "asia": "asia",
        "au": "australia",  # alias for 'australia'
        "australia": "australia",
    }

    # Initialize Google Cloud Platform regions.
    for _, region in pricing_to_region.iteritems():
        libcloud_data["compute"]["google_%s" % region] = {}

    # Update Google Compute Engine pricing.
    gcp_price_list = google_ext_prices["gcp_price_list"]
    gce_vm_prefix = "CP-COMPUTEENGINE-VMIMAGE-"
    for name, prices in gcp_price_list.iteritems():
        if not name.startswith(gce_vm_prefix):
            continue
        short_name = name[len(gce_vm_prefix) :]
        machine_type = short_name.lower()
        for key, price in prices.iteritems():
            if key in pricing_to_region:
                region = pricing_to_region[key]
                libcloud_data["compute"]["google_%s" % region][machine_type] = price

    # Update last-modified timestamp.
    libcloud_data["updated"] = int(time.time())

    # Write updated price list.
    with open(PRICING_FILE_PATH, "w") as libcloud_out:
        json_str = json.dumps(
            libcloud_data, indent=4 * " ", item_sort_key=utils.sortKeysNumerically
        )
        libcloud_out.write(json_str)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
