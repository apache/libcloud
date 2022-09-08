#!/usr/bin/env bash
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
set -e

# Script which fails if any of the import takes more than threshold ms
LIBCLOUD_CUMULATIVE_IMPORT_TIME_LIMIT_US=400000
EC2_DRIVER_CUMULATIVE_IMPORT_TIME_LIMIT_US=480000

# Clean up any cached files to ensure consistent and clean environment
find . -name "*.pyc" -print0 | xargs -0 rm

# Example line:
# import time:      1112 |      70127 | libcloud
LIBCLOUD_IMPORT_TIMINGS=$(python3.8 -X importtime -c "import libcloud" 2>&1)
LIBCLOUD_IMPORT_TIME_CUMULATIVE_US=$(echo -e "${LIBCLOUD_IMPORT_TIMINGS}" | tail -1 | grep "| libcloud" | awk '{print $5}')

echo "Import timings for \"libcloud\" module"
echo -e "${LIBCLOUD_IMPORT_TIMINGS}"

if [ "${LIBCLOUD_IMPORT_TIME_CUMULATIVE_US}" -gt "${LIBCLOUD_CUMULATIVE_IMPORT_TIME_LIMIT_US}" ]; then
    echo "Importing libcloud module took more than ${LIBCLOUD_CUMULATIVE_IMPORT_TIME_LIMIT_US} us (${LIBCLOUD_IMPORT_TIME_CUMULATIVE_US})"
    exit 1
fi

# Clean up any cached files to ensure consistent and clean environment
find . -name "*.pyc" -print0 | xargs -0 rm

EC2_DRIVER_IMPORT_TIMINGS=$(python3.8 -X importtime -c "import libcloud.compute.drivers.ec2" 2>&1)
EC2_DRIVER_IMPORT_TIME_CUMULATIVE_US=$(echo -e "$EC2_DRIVER_IMPORT_TIMINGS}" | tail -1 | grep "| libcloud.compute.drivers.ec2" | awk '{print $5}')

echo ""
echo "Import timings for \"libcloud.compute.drivers.ec2\" module"
echo -e "${EC2_DRIVER_IMPORT_TIMINGS}"

if [ "${EC2_DRIVER_IMPORT_TIME_CUMULATIVE_US}" -gt "${EC2_DRIVER_CUMULATIVE_IMPORT_TIME_LIMIT_US}" ]; then
    echo "Importing libcloud.compute.drivers.ec2 module took more than ${EC2_DRIVER_CUMULATIVE_IMPORT_TIME_LIMIT_US} us (${EC2_DRIVER_IMPORT_TIME_CUMULATIVE_US})"
    exit 1
fi

echo ""
echo "All checks passed"
exit 0
