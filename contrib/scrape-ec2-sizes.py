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
This script downloads and parses AWS EC2 from
https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/index.json.
It writes a Python module with constants about EC2's sizes and regions.

Use it as following (run it in the root of the repo directory):
    $ python contrib/scrape-ec2-sizes.py
"""

import os
import re
import json
import atexit

import tqdm  # pylint: disable=import-error
import ijson  # pylint: disable=import-error
import requests

FILEPATH = os.environ.get("TMP_JSON", "/tmp/ec.json")
URL = "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/index.json"
IGNORED_FIELDS = ["locationType", "operatingSystem"]
REG1_STORAGE = re.compile(r"(\d+) x ([0-9,]+)")
REG2_STORAGE = re.compile(r"(\d+) GB.*?")
REG_BANDWIDTH = re.compile(r"\D*(\d+)\D*")
#  From <https://aws.amazon.com/marketplace/help/200777880>
REGION_DETAILS = {
    # America
    "US East (N. Virginia)": {
        "id": "us-east-1",
        "endpoint": "ec2.us-east-1.amazonaws.com",
        "api_name": "ec2_us_east",
        "country": "USA",
        "signature_version": "2",
    },
    "US East (Ohio)": {
        "id": "us-east-2",
        "endpoint": "ec2.us-east-2.amazonaws.com",
        "api_name": "ec2_us_east_ohio",
        "country": "USA",
        "signature_version": "4",
    },
    "US West (N. California)": {
        "id": "us-west-1",
        "endpoint": "ec2.us-west-1.amazonaws.com",
        "api_name": "ec2_us_west",
        "country": "USA",
        "signature_version": "2",
    },
    "US West (Oregon)": {
        "id": "us-west-2",
        "endpoint": "ec2.us-west-2.amazonaws.com",
        "api_name": "ec2_us_west_oregon",
        "country": "US",
        "signature_version": "2",
    },
    "Canada (Central)": {
        "id": "ca-central-1",
        "endpoint": "ec2.ca-central-1.amazonaws.com",
        "api_name": "ec2_ca_central_1",
        "country": "Canada",
        "signature_version": "4",
    },
    "South America (Sao Paulo)": {
        "id": "sa-east-1",
        "endpoint": "ec2.sa-east-1.amazonaws.com",
        "api_name": "ec2_sa_east",
        "country": "Brazil",
        "signature_version": "2",
    },
    "AWS GovCloud (US)": {
        "id": "us-gov-west-1",
        "endpoint": "ec2.us-gov-west-1.amazonaws.com",
        "api_name": "ec2_us_govwest",
        "country": "US",
        "signature_version": "2",
    },
    # Africa
    "af-south-1": {
        "id": "af-south-1",
        "endpoint": "ec2.af-south-1.amazonaws.com",
        "api_name": "ec2_af_south",
        "country": "South Africa",
        "signature_version": "4",
    },
    # EU
    "eu-west-1": {
        "id": "eu-west-1",
        "endpoint": "ec2.eu-west-1.amazonaws.com",
        "api_name": "ec2_eu_west",
        "country": "Ireland",
        "signature_version": "2",
    },
    "EU (Ireland)": {  # Duplicate from AWS' JSON
        "id": "eu-west-1",
        "endpoint": "ec2.eu-west-1.amazonaws.com",
        "api_name": "ec2_eu_west",
        "country": "Ireland",
        "signature_version": "2",
    },
    "EU (London)": {
        "id": "eu-west-2",
        "endpoint": "ec2.eu-west-2.amazonaws.com",
        "api_name": "ec2_eu_west_london",
        "country": "United Kingdom",
        "signature_version": "4",
    },
    "EU (Milan)": {
        "id": "eu-south-1",
        "endpoint": "ec2.eu-south-1.amazonaws.com",
        "api_name": "ec2_eu_south",
        "country": "Italy",
        "signature_version": "4",
    },
    "EU (Paris)": {
        "id": "eu-west-3",
        "endpoint": "ec2.eu-west-3.amazonaws.com",
        "api_name": "ec2_eu_west_paris",
        "country": "France",
        "signature_version": "4",
    },
    "EU (Frankfurt)": {
        "id": "eu-central-1",
        "endpoint": "ec2.eu-central-1.amazonaws.com",
        "api_name": "ec2_eu_central",
        "country": "Frankfurt",
        "signature_version": "4",
    },
    "EU (Stockholm)": {
        "id": "eu-north-1",
        "endpoint": "ec2.eu-north-1.amazonaws.com",
        "api_name": "ec2_eu_north_stockholm",
        "country": "Stockholm",
        "signature_version": "4",
    },
    # Asia
    "Asia Pacific (Mumbai)": {
        "id": "ap-south-1",
        "endpoint": "ec2.ap-south-1.amazonaws.com",
        "api_name": "ec2_ap_south_1",
        "country": "India",
        "signature_version": "4",
    },
    "Asia Pacific (Singapore)": {
        "id": "ap-southeast-1",
        "endpoint": "ec2.ap-southeast-1.amazonaws.com",
        "api_name": "ec2_ap_southeast",
        "country": "Singapore",
        "signature_version": "2",
    },
    "Asia Pacific (Sydney)": {
        "id": "ap-southeast-2",
        "endpoint": "ec2.ap-southeast-2.amazonaws.com",
        "api_name": "ec2_ap_southeast_2",
        "country": "Australia",
        "signature_version": "2",
    },
    "Asia Pacific (Tokyo)": {
        "id": "ap-northeast-1",
        "endpoint": "ec2.ap-northeast-1.amazonaws.com",
        "api_name": "ec2_ap_northeast",
        "country": "Japan",
        "signature_version": "2",
    },
    "Asia Pacific (Seoul)": {
        "id": "ap-northeast-2",
        "endpoint": "ec2.ap-northeast-2.amazonaws.com",
        "api_name": "ec2_ap_northeast",
        "country": "South Korea",
        "signature_version": "4",
    },
    "Asia Pacific (Osaka-Local)": {
        "id": "ap-northeast-3",
        "endpoint": "ec2.ap-northeast-3.amazonaws.com",
        "api_name": "ec2_ap_northeast",
        "country": "Japan",
        "signature_version": "4",
    },
    "Asia Pacific (Hong Kong)": {
        "id": "ap-east-1",
        "endpoint": "ec2.ap-east-1.amazonaws.com",
        "api_name": "ec2_ap_east",
        "country": "Hong Kong",
        "signature_version": "2",
    },
    # Not in JSON
    "China (Beijing)": {
        "id": "cn-north-1",
        "endpoint": "ec2.cn-north-1.amazonaws.com.cn",
        "api_name": "ec2_cn_north",
        "country": "China",
        "signature_version": "4",
    },
    "China (Ningxia)": {
        "id": "cn-northwest-1",
        "endpoint": "ec2.cn-northwest-1.amazonaws.com.cn",
        "api_name": "ec2_cn_northwest",
        "country": "China",
        "signature_version": "4",
    },
}

FILE_HEADER = """
# File generated by contrib/scrape-ec2-sizes.py script - DO NOT EDIT manually
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
""".strip()


def download_json():
    if os.path.isfile(FILEPATH):
        print("Using data from existing cached file %s" % (FILEPATH))
        return open(FILEPATH)

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

    return open(FILEPATH)


def get_json():
    if not os.path.isfile(FILEPATH):
        return download_json(), False

    print("Using data from existing cached file %s" % (FILEPATH))
    return open(FILEPATH), True


def filter_extras(extras):
    return {
        key: extras[key]
        for key in extras
        if key
        not in [
            "capacitystatus",
            "ebsOptimized",
            "operation",
            "licenseModel",
            "preInstalledSw",
            "tenancy",
            "usagetype",
        ]
    }


def parse():
    # Set vars
    sizes = {}
    regions = {r["id"]: r for r in REGION_DETAILS.values()}
    for region_id in regions:
        regions[region_id]["instance_types"] = []
    # Parse
    json_file, from_file = get_json()
    products_data = ijson.items(json_file, "products")

    try:
        products_data = next(products_data)
    except ijson.common.IncompleteJSONError as e:
        # This likely indicates that the cached file is incomplete or corrupt so we delete it and re
        # download data
        if from_file:
            os.remove(FILEPATH)
            json_file, from_file = get_json()
            products_data = ijson.items(json_file, "products")
            products_data = next(products_data)
        else:
            raise e

    for sku in products_data:
        if products_data[sku].get("productFamily", "unknown") != "Compute Instance":
            continue
        location = products_data[sku]["attributes"].pop("location")
        if location not in REGION_DETAILS:
            continue
        # Get region & size ID
        region_id = REGION_DETAILS[location]["id"]
        instance_type = products_data[sku]["attributes"]["instanceType"]
        # Add size to region
        if instance_type not in regions[region_id]["instance_types"]:
            regions[region_id]["instance_types"].append(instance_type)
        # Parse sizes
        if instance_type not in sizes:
            for field in IGNORED_FIELDS:
                products_data[sku]["attributes"].pop(field, None)
            # Compute RAM
            ram = int(
                float(products_data[sku]["attributes"]["memory"].split()[0].replace(",", "")) * 1024
            )
            # Compute bandwdith
            bw_match = REG_BANDWIDTH.match(products_data[sku]["attributes"]["networkPerformance"])
            if bw_match is not None:
                bandwidth = int(bw_match.groups()[0])
            else:
                bandwidth = None
            sizes[instance_type] = {
                "id": instance_type,
                "name": instance_type,
                "ram": ram,
                "bandwidth": bandwidth,
                "extra": filter_extras(products_data[sku]["attributes"]),
            }
            if products_data[sku]["attributes"].get("storage") != "EBS only":
                match = REG1_STORAGE.match(products_data[sku]["attributes"]["storage"])
                if match:
                    disk_number, disk_size = match.groups()
                else:
                    match = REG2_STORAGE.match(products_data[sku]["attributes"]["storage"])
                    if match:
                        disk_number, disk_size = 1, match.groups()[0]
                    else:
                        disk_number, disk_size = 0, "0"
                disk_number, disk_size = (
                    int(disk_number),
                    int(disk_size.replace(",", "")),
                )
                sizes[instance_type]["disk"] = disk_number * disk_size
            else:
                sizes[instance_type]["disk"] = 0
            products_data[sku]["attributes"]
    # Sort
    for region in regions:
        regions[region]["instance_types"] = sorted(regions[region]["instance_types"])
    return sizes, regions


def dump():
    print("Scraping size data, this may take up to 10-15 minutes...")

    sizes, regions = parse()

    separators = (",", ": ")

    # 1. Write file with instance types constants
    file_path = "libcloud/compute/constants/ec2_instance_types.py"
    with open(file_path, "w") as fp:
        fp.write(FILE_HEADER + "\n")
        fp.write("\n")
        fp.write(
            "INSTANCE_TYPES = "
            + json.dumps(sizes, indent=4, sort_keys=True, separators=separators).replace(
                "null", "None"
            )
        )

    print("")
    print("Data written to %s" % (file_path))
    print("")

    # 2. Write file with full details for each region
    file_path = "libcloud/compute/constants/ec2_region_details_complete.py"
    with open(file_path, "w") as fp:
        fp.write(FILE_HEADER + "\n")
        fp.write("\n")
        fp.write(
            "REGION_DETAILS = "
            + json.dumps(regions, indent=4, sort_keys=True, separators=separators).replace(
                "null", "None"
            )
        )

    print("Data written to %s" % (file_path))
    print("")

    # 3. Write file with partial region details (everything except instance_types attribute)
    regions_partial = {}
    keys_to_keep = ["api_name", "country", "id", "endpoint", "signature_version"]

    for region_name, region_details in regions.items():
        regions_partial[region_name] = {}

        for key, value in region_details.items():
            if key not in keys_to_keep:
                continue

            regions_partial[region_name][key] = value

    file_path = "libcloud/compute/constants/ec2_region_details_partial.py"

    with open(file_path, "w") as fp:
        fp.write(FILE_HEADER + "\n")
        fp.write("\n")
        fp.write(
            "REGION_DETAILS = "
            + json.dumps(regions_partial, indent=4, sort_keys=True, separators=separators).replace(
                "null", "None"
            )
        )

    print("Data written to %s" % (file_path))
    print("")


if __name__ == "__main__":
    dump()
