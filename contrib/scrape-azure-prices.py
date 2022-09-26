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
import json
import time

import requests

PRICES_URL = "https://azure.microsoft.com/api/v3/pricing/" "virtual-machines/calculator/"
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
PRICING_FILE_PATH = os.path.join(BASE_PATH, "../libcloud/data/pricing.json")
PRICING_FILE_PATH = os.path.abspath(PRICING_FILE_PATH)


def get_azure_prices():
    prices_raw = requests.get(PRICES_URL).json()
    region_map = {}
    regions = []
    for region in prices_raw["regions"]:
        regions.append(region["slug"])
        region_map[region["slug"]] = region["displayName"]

    result = {"windows": {}, "linux": {}}
    parsed_sizes = {"lowpriority", "basic", "standard"}
    for offer, value in prices_raw["offers"].items():

        size_raw = offer.split("-")
        #  Servers that go by the core with global price are not yet added
        if len(size_raw) != 3 or size_raw[2] not in parsed_sizes:
            continue
        if size_raw[0] not in {"linux", "windows"}:
            continue
        size = size_raw[2] + size_raw[1]
        prices = {}
        if not value["prices"].get("perhour"):
            continue
        for reg, price in value["prices"]["perhour"].items():
            region = region_map[reg].lower().replace(" ", "")
            region = region.replace("(public)", "")  # for germany
            region = region.replace("(sovereign)", "")  # for germany
            prices[region] = price["value"]
        result[size_raw[0]][size] = prices

    return result


def write_azure_prices(file_path, prices):
    with open(file_path) as f:
        content = f.read()

    data = json.loads(content)
    data["updated"] = int(time.time())
    data["compute"]["azure_linux"] = prices["linux"]
    data["compute"]["azure_windows"] = prices["windows"]

    content = json.dumps(data, indent=4)
    lines = content.splitlines()
    lines = [line.rstrip() for line in lines]
    content = "\n".join(lines)

    with open(file_path, "w") as fp:
        fp.write(content)


def main():
    res = get_azure_prices()
    write_azure_prices(PRICING_FILE_PATH, res)


if __name__ == "__main__":
    main()
