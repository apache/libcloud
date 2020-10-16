#!/usr/bin/env bash

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
