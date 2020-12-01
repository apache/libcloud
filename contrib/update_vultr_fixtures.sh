#!/usr/bin/env bash
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

set -e
# set -x
# make sure:
# - you installed curl
# - you installed jq

API_POINT="api.vultr.com"
FIXTURES_PATH="./libcloud/test/compute/fixtures/vultr"
[ ! -d "$FIXTURES_PATH" ] && echo "Please run command from root dir of project" && exit

if ! [ -x "$(command -v curl)" ]; then
    echo 'Error: curl is not installed.' >&2
    exit 1
fi
if ! [ -x "$(command -v jq)" ]; then
    echo 'Error: jq is not installed.' >&2
    exit 1
fi
#unauthenticated_endpoints = {  # {action: methods}
#        '/v1/app/list': ['GET'],
#        '/v1/os/list': ['GET'],
#        '/v1/plans/list': ['GET'],
#        '/v1/plans/list_vc2': ['GET'],
#        '/v1/plans/list_vdc2': ['GET'],
#        '/v1/regions/availability': ['GET'],
#        '/v1/regions/list': ['GET']
#    }

curl "https://$API_POINT/v1/os/list" | jq >"$FIXTURES_PATH/list_images.json"
curl "https://$API_POINT/v1/plans/list" | jq >"$FIXTURES_PATH/list_sizes.json"
curl "https://$API_POINT/v1/regions/list" | jq >"$FIXTURES_PATH/list_locations.json"
