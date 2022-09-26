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
Price scraper for GCE. An api key is required
(https://cloud.google.com/docs/authentication/api-keys).

Keep in mind that Cloud Billing API needs to be enabled for the account you use
to authenticate otherwise you will received 403 Forbidden error.

It can be enabled at https://console.cloud.google.com/apis/library/cloudbilling.googleapis.com.

Usage:

    python scrape-gce-prices.py APIKEY

or if it is the first time using it and no skus are saved:

    python scrape-gce-prices.py --all APIKEY
"""

import os
import copy
import json
import time
import argparse

from requests import request

GCE_SERVICE_ID = "6F81-5844-456A"
API_URL = "https://cloudbilling.googleapis.com/v1/services/" "{}/skus".format(GCE_SERVICE_ID)

API_KEY = os.environ.get("GCE_API_KEY", None)

usage_type_map = {
    "OnDemand": "on_demand",
    "Preemptible": "preemptible",
    "Commit1Yr": "1yr_commitment",
    "Commit3Yr": "3yr_commitment",
}
# compute -> gce_instances --> instance type -->
# usage type (On demand, preemptible, Commitment) -->
# region --> price/hour
compute = {
    "gce_instances": {
        "n1": {
            "cpu": {
                "description": "n1 predefined instance core",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
            "ram": {
                "description": "n1 predefined instance ram",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
        },
        "n1_custom": {
            "cpu": {
                "description": "custom instance core",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
            "ram": {
                "description": "custom instance ram",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
        },
        "n1_custom_extended": {
            "cpu": {},
            "ram": {
                "description": "custom extended instance ram",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
        },
        "n2": {
            "cpu": {
                "description": "n2 instance core",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
            "ram": {
                "description": "n2 instance ram",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
        },
        "n2_custom": {
            "cpu": {
                "description": "n2 custom instance core",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
            "ram": {
                "description": "n2 custom instance ram",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
        },
        "n2_custom_extended": {
            "cpu": {},
            "ram": {
                "description": "n2 custom extended instance ram",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
        },
        # E2 predefined and custom have same prices and no extended
        "e2": {
            "cpu": {
                "description": "e2 instance core",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
            "ram": {
                "description": "e2 instance ram",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
        },
        "e2_custom": {
            "cpu": {
                "description": "e2 instance core",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
            "ram": {
                "description": "e2 instance ram",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
        },
        "n2d": {
            "cpu": {
                "description": "n2d amd instance core",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
            "ram": {
                "description": "n2d amd instance ram",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
        },
        "n2d_custom": {
            "cpu": {
                "description": "n2d amd custom instance core",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
            "ram": {
                "description": "n2d amd custom instance ram",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
        },
        "n2d_custom_extended": {
            "cpu": {},
            "ram": {
                "description": "n2d amd custom extended instance ram",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
        },
        # M1 memory optimized, no custom
        "m1": {
            "cpu": {
                "description": "memory-optimized instance core",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
            "ram": {
                "description": "memory-optimized instance ram",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
        },
        "c2": {
            "cpu": {
                "description": "compute optimized core",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
            "ram": {
                "description": "compute optimized ram",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            },
        },
        "f1": {
            "cpu": {  # for consitency, this instance has only one price
                "description": "micro instance",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            }
        },
        "g1": {
            "cpu": {  # for consitency, this instance has only one price
                "description": "small instance",
                "on_demand": {},
                "preemptible": {},
                "1yr_commitment": {},
                "3yr_commitment": {},
            }
        },
    },
    "gce_disks": {
        "Standard": {"description": "storage pd capacity", "on_demand": {}},
        "SSD": {"description": "ssd backed pd", "on_demand": {}},
        "Regional Standard": {
            "description": "regional storage pd capacity",
            "on_demand": {},
        },
        "Regional SSD": {"description": "ssd backed pd capacity", "on_demand": {}},
        "Local SSD": {
            "description": "ssd backed local storage",
            "on_demand": {},
            "preemptible": {},
            "1yr_commitment": {},
            "3yr_commitment": {},
        },
    },
    #  The skus here have been hardcoded due to my inability of scraping them
    #  The SQL prices are also hardcoded since I couldn't even
    #  find the correct skus
    "gce_images": {
        "RHEL": {
            "description": "RHEL7",
            "4vcpu or less": {"price": 0, "sku": "57A4-6443-7F8D"},
            "6vcpu or more": {"price": 0, "sku": "9AAA-D8A1-1CA1"},
        },
        "RHEL with Update Services": {
            "description": "Red Hat Enterprise Linux for SAP with Update Services",
            "4vcpu or less": {"price": 0, "sku": "7E6E-54A7-319A"},
            "6vcpu or more": {"price": 0, "sku": "CB1D-70B4-22E0"},
        },
        "SLES": {
            "f1": {"price": 0, "sku": "0469-B817-410A"},
            "g1": {"price": 0, "sku": "739A-8A87-1E79"},
            "any": {"price": 0, "sku": "42E1-070C-7F4E"},
        },
        "SLES for SAP": {
            "6vcpu or more": {"price": 0, "sku": "5E02-C3BA-6290"},
            "3-4vcpu": {"price": 0, "sku": "86C1-64B7-1E72"},
            "1-2vcpu": {"price": 0, "sku": "EAF4-4289-40E6"},
        },
        "Windows Server": {
            "any": {"price": 0, "sku": "00B2-37B0-B8BB"},  # this is per core per hour
            "f1": {"price": 0, "sku": "151B-229F-68E1"},
            "g1": {"price": 0, "sku": "03F4-45F5-24A2"},
        },
        "SQL Server": {  # prices are per core per hour
            "enterprise": {"price": 0.399},
            "standard": {"price": 0.1645},
            "web": {"price": 0.011},
        },
    },
}

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
PRICING_FILE_PATH = os.path.join(BASE_PATH, "../libcloud/data/pricing.json")
PRICING_FILE_PATH = os.path.abspath(PRICING_FILE_PATH)


def get_all_skus(key):
    # a valid google cloud account API key should be provided
    # https://cloud.google.com/docs/authentication/api-keys
    url = API_URL
    params = {"key": key}
    data = []
    has_next_page = True
    while has_next_page:
        try:
            response = request(method="GET", url=url, params=params)
            response.raise_for_status()
        except Exception as e:
            msg = str(e)
            msg = msg.replace(key, "************")
            raise Exception(msg)

        data.extend(response.json().get("skus", {}))
        next_page = response.json().get("nextPageToken")

        if next_page:
            params["pageToken"] = next_page
        else:
            has_next_page = False

    return data


def scrape_sku_price_info(key):
    data = get_all_skus(key)
    dict_ = compute
    for sku in data:
        # to make sure I get the correct memory optimized
        if "Premium" in sku["description"]:
            continue
        for item in dict_["gce_instances"].values():
            for resource in {"cpu", "ram"}:
                if resource in item:
                    description = item[resource].get("description", "-----")
                else:
                    continue
                if description in sku["description"].lower():
                    location = sku["serviceRegions"][0]
                    usage_type = usage_type_map[sku["category"]["usageType"]]
                    price = price_from_sku(sku)
                    item[resource][usage_type][location] = {"price": price}
                    item[resource][usage_type][location]["sku"] = sku["skuId"]
    for sku in data:
        for item in dict_["gce_disks"].values():
            description = item["description"]
            if description in sku["description"].lower():
                if "regional" in sku["description"].lower() and "regional" not in description:
                    continue
                location = sku["serviceRegions"][0]
                usage_type = usage_type_map[sku["category"]["usageType"]]
                price = price_from_sku(sku)
                # disk price is per month /720 to make it per hour
                item[usage_type][location] = {"price": price / 720}
                item[usage_type][location]["sku"] = sku["skuId"]
    # images were done by hand

    return dict_


def scrape_only_prices(key):
    data = get_all_skus(key)
    with open(PRICING_FILE_PATH) as fp:
        content = fp.read()
    dict_ = json.loads(content)["compute"]
    for sku in data:
        skuId = sku["skuId"]
        for item in dict_["gce_instances"].values():
            for resource in item:
                for usage_type in item[resource]:
                    if usage_type == "description":
                        continue
                    for location in item[resource][usage_type]:
                        if item[resource][usage_type][location].get("sku") == skuId:
                            price = price_from_sku(sku)
                            item[resource][usage_type][location]["price"] = price
        for item in dict_["gce_disks"].values():
            for usage_type in item:
                if usage_type == "description":
                    continue
                for location in item[usage_type]:
                    if skuId == item[usage_type][location].get("sku"):
                        price = price_from_sku(sku)
                        # disk price is per month /720 to make it per hour
                        item[usage_type][location]["price"] = price / 720

        for item in dict_["gce_images"].values():
            for type_ in item:
                if type_ == "description":
                    continue
                if skuId == item[type_].get("sku"):
                    price = price_from_sku(sku)
                    item[type_]["price"] = price
    return dict_


def price_from_sku(sku):
    for tier_rate in sku["pricingInfo"][0]["pricingExpression"]["tieredRates"]:
        units = tier_rate["unitPrice"]["units"]
        nanos = tier_rate["unitPrice"]["nanos"]
        nano = str(nanos)
        nano = "0" * (9 - len(nano)) + nano
        units = str(units)
        price = units + "." + nano
        if float(price) != 0:
            break
    return float(price)


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
    content = json.dumps(data, indent=4)
    lines = content.splitlines()
    lines = [line.rstrip() for line in lines]
    content = "\n".join(lines)

    with open(pricing_file_path, "w") as fp:
        fp.write(content)


def main(key, skus=False):
    print("Scraping GCE pricing data (this may take a while)...")

    if skus:
        pricing_data = scrape_sku_price_info(key)
    else:
        pricing_data = scrape_only_prices(key)
    update_pricing_file(pricing_file_path=PRICING_FILE_PATH, pricing_data=pricing_data)

    print("Pricing data updated")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="scrape gce prices")
    help_msg = "If enabled both sku's and prices will be scraped"
    parser.add_argument("--all", action="store_true", help=help_msg)
    help_msg = "Google API key, visit https://cloud.google.com/" "docs/authentication/api-keys"
    parser.add_argument("key", help=help_msg, nargs="?", default=API_KEY)
    arg = parser.parse_args()

    if not arg.key:
        raise ValueError(
            "API key needs to provided either as a script "
            "argument or via GCE_API_KEY environment "
            "variable."
        )
    main(arg.key, skus=arg.all)
