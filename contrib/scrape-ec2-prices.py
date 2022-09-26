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
import copy
import json
import time
import atexit
from collections import OrderedDict, defaultdict

import tqdm  # pylint: disable=import-error
import ijson  # pylint: disable=import-error
import requests

# Buffer size for ijson.parse() function. Larger buffer size results in increased memory
# consumption, but faster parsing.
IJSON_BUF_SIZE = 10 * 65536

# same URL as the one used by scrape-ec2-sizes.py, now it has official data on pricing
URL = "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/index.json"

RE_NUMERIC_OTHER = re.compile(r"(?:([0-9]+)|([-A-Z_a-z]+)|([^-0-9A-Z_a-z]+))")

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
PRICING_FILE_PATH = os.path.join(BASE_PATH, "../libcloud/data/pricing.json")
PRICING_FILE_PATH = os.path.abspath(PRICING_FILE_PATH)

FILEPATH = os.environ.get("TMP_JSON", "/tmp/ec.json")

INSTANCE_SIZES = [
    "micro",
    "small",
    "medium",
    "large",
    "xlarge",
    "x-large",
    "extra-large",
]


def download_json():
    if os.path.isfile(FILEPATH):
        mtime_str = time.strftime("%Y-%m-%d %H:%I:%S UTC", time.gmtime(os.path.getmtime(FILEPATH)))
        print("Using data from existing cached file {} (mtime={})".format(FILEPATH, mtime_str))
        return open(FILEPATH), True

    def remove_partial_cached_file():
        if os.path.isfile(FILEPATH):
            os.remove(FILEPATH)

    # File not cached locally, download data and cache it
    with requests.get(URL, stream=True) as response:
        atexit.register(remove_partial_cached_file)

        total_size_in_bytes = int(response.headers.get("content-length", 0))
        progress_bar = tqdm.tqdm(total=total_size_in_bytes, unit="iB", unit_scale=True)

        chunk_size = 10 * 1024 * 1024

        with open(FILEPATH, "wb") as fp:
            # NOTE: We use shutil.copyfileobj with large chunk size instead of
            # response.iter_content with large chunk size since data we
            # download is massive and copyfileobj is more efficient.
            # shutil.copyfileobj(response.raw, fp, 10 * 1024 * 1024)
            for chunk_data in response.iter_content(chunk_size):
                progress_bar.update(len(chunk_data))
                fp.write(chunk_data)

        progress_bar.close()
        atexit.unregister(remove_partial_cached_file)

    return FILEPATH, False


def get_json():
    if not os.path.isfile(FILEPATH):
        return download_json()[0], False

    mtime_str = time.strftime("%Y-%m-%d %H:%I:%S UTC", time.gmtime(os.path.getmtime(FILEPATH)))
    print("Using data from existing cached file {} (mtime={})".format(FILEPATH, mtime_str))
    return FILEPATH, True


# Prices and sizes are in different dicts and categorized by sku
def get_all_prices():
    # return variable
    # prices = {sku : {price: int, unit: string}}
    prices = {}
    current_sku = ""
    current_rate_code = ""
    amazonEC2_offer_code = "JRTCKXETXF"
    json_file, from_file = get_json()
    with open(json_file) as f:
        print("Starting to parse pricing data, this could take up to 15 minutes...")
        parser = ijson.parse(f, buf_size=IJSON_BUF_SIZE)
        # use parser because file is very large
        for prefix, event, value in tqdm.tqdm(parser):
            if "products" in prefix:
                continue
            if (prefix, event) == ("terms.OnDemand", "map_key"):
                current_sku = value
                prices[current_sku] = {}
            elif (prefix, event) == (
                f"terms.OnDemand.{current_sku}.{current_sku}.{amazonEC2_offer_code}.priceDimensions",
                "map_key",
            ):
                current_rate_code = value
            elif (prefix, event) == (
                f"terms.OnDemand.{current_sku}.{current_sku}.{amazonEC2_offer_code}.priceDimensions"
                f".{current_rate_code}.unit",
                "string",
            ):
                prices[current_sku]["unit"] = value
            elif (prefix, event) == (
                f"terms.OnDemand.{current_sku}.{current_sku}.{amazonEC2_offer_code}.priceDimensions"
                f".{current_rate_code}.pricePerUnit.USD",
                "string",
            ):
                prices[current_sku]["price"] = value
    return prices


# For each combination of location - size - os the file has a different sku.
# For each sku we have a price
def scrape_ec2_pricing():
    skus = {}
    prices = get_all_prices()
    json_file, from_file = get_json()
    with open(json_file) as f:
        print("Starting to parse pricing data, this could take up to 15 minutes...")
        # use parser because file is very large
        parser = ijson.parse(f, buf_size=IJSON_BUF_SIZE)
        current_sku = ""

        for prefix, event, value in tqdm.tqdm(parser):
            if "terms" in prefix:
                break
            if (prefix, event) == ("products", "map_key"):
                current_sku = value
                skus[current_sku] = {"sku": value}
            elif (prefix, event) == (f"products.{current_sku}.productFamily", "string"):
                skus[current_sku]["family"] = value
            elif (prefix, event) == (
                f"products.{current_sku}.attributes.location",
                "string",
            ):
                skus[current_sku]["locationName"] = value
            elif (prefix, event) == (
                f"products.{current_sku}.attributes.locationType",
                "string",
            ):
                skus[current_sku]["locationType"] = value
            elif (prefix, event) == (
                f"products.{current_sku}.attributes.instanceType",
                "string",
            ):
                skus[current_sku]["size"] = value
            elif (prefix, event) == (
                f"products.{current_sku}.attributes.operatingSystem",
                "string",
            ):
                skus[current_sku]["os"] = value
            elif (prefix, event) == (
                f"products.{current_sku}.attributes.usagetype",
                "string",
            ):
                skus[current_sku]["usage_type"] = value
            elif (prefix, event) == (
                f"products.{current_sku}.attributes.preInstalledSw",
                "string",
            ):
                skus[current_sku]["preInstalledSw"] = value
            elif (prefix, event) == (
                f"products.{current_sku}.attributes.regionCode",
                "string",
            ):
                skus[current_sku]["location"] = value
            # only get prices of compute instances atm
            elif (prefix, event) == (f"products.{current_sku}", "end_map"):
                if (
                    "Compute Instance" not in skus[current_sku]["family"]
                    and "Dedicated Host" not in skus[current_sku]["family"]
                ):
                    del skus[current_sku]

    ec2_linux = defaultdict(OrderedDict)
    ec2_windows = defaultdict(OrderedDict)
    ec2_rhel = defaultdict(OrderedDict)
    ec2_rhel_ha = defaultdict(OrderedDict)
    ec2_suse = defaultdict(OrderedDict)

    os_map = {
        "Linux": ec2_linux,
        "Windows": ec2_windows,
        "RHEL": ec2_rhel,
        "SUSE": ec2_suse,
        "Red Hat Enterprise Linux with HA": ec2_rhel_ha,
    }
    for sku in skus:
        if skus[sku]["locationType"] != "AWS Region":
            continue
        # skip any SQL
        if skus[sku]["preInstalledSw"] != "NA":
            continue

        os = skus[sku]["os"]
        if os == "NA":
            continue
        os_dict = os_map.get(os)
        # new OS, until it is documented skip it
        if os_dict is None:
            print(f"Unexpected OS {os}")
            continue
        size = skus[sku]["size"]
        location = skus[sku]["location"]
        # size is first seen
        if not os_dict.get(size):
            os_dict[size] = {}

        # if price already exists pick the BoxUsage usage type which means on demand
        if os_dict.get(size, {}).get(location) and "BoxUsage" not in skus[sku]["usage_type"]:
            continue

        # if price is not a number then label it as not available
        try:
            price = float(prices[sku]["price"])
            os_dict[size][location] = price
        except ValueError:
            os_dict[size][location] = "n/a"
        except KeyError:
            # size is available only reserved
            del os_dict[size]
    return {
        "ec2_linux": ec2_linux,
        "ec2_windows": ec2_windows,
        "ec2_rhel": ec2_rhel,
        "ec2_suse": ec2_suse,
        "ec2_rhel_ha": ec2_rhel_ha,
    }


def update_pricing_file(pricing_file_path, pricing_data):
    with open(pricing_file_path) as fp:
        content = fp.read()

    data = json.loads(content)
    original_data = copy.deepcopy(data)

    data["compute"].update(pricing_data)

    if data == original_data:
        # Nothing has changed, bail out early and don't update "updated" attribute
        print("Nothing has changed, skipping update.")
        return

    data["updated"] = int(time.time())

    # Always sort the pricing info
    data = sort_nested_dict(data)

    content = json.dumps(data, indent=4)
    lines = content.splitlines()
    lines = [line.rstrip() for line in lines]
    content = "\n".join(lines)

    with open(pricing_file_path, "w") as fp:
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
    result = []

    for (numeric, alpha, other) in RE_NUMERIC_OTHER.findall(key_value[0]):
        numeric = int(numeric) if numeric else -1
        alpha = INSTANCE_SIZES.index(alpha) if alpha in INSTANCE_SIZES else alpha
        alpha = str(alpha)
        item = tuple([numeric, alpha, other])
        result.append(item)

    return tuple(result)


def main():
    print(
        "Scraping EC2 pricing data (if this runs for the first time "
        "it has to download a 3GB file, depending on your bandwith "
        "it might take a while)...."
    )

    pricing_data = scrape_ec2_pricing()
    update_pricing_file(pricing_file_path=PRICING_FILE_PATH, pricing_data=pricing_data)

    print("Pricing data updated")


if __name__ == "__main__":
    main()
