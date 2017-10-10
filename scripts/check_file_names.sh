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
#
# Script which checks there are no files which name is longer
# than the allowed limit
# ext4 support file name up to 255 characters long, but layering
# ecrypt on top of it drops the limit to 143 characters

FILE_NAME_LENGTH_LIMIT=143

FILES=$(find libcloud/ -regextype posix-egrep -regex ".*[^/]{${FILE_NAME_LENGTH_LIMIT},}")

if [ "${FILES}" ]; then
    echo "Found files which name is longer than ${FILE_NAME_LENGTH_LIMIT} characters"
    echo "${FILES}"
    exit 1
fi

exit 0
