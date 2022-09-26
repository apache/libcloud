#!/usr/bin/python
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

# Based on
# https://github.com/ssorj/scripts/blob/master/check-asf-license-headers


import os
import sys
import codecs

root_dir = sys.argv[1]

MIN_FILE_SIZE = 1
IGNORED_PATHS = [
    '.git',
    '.svn',
    '.tox',
    '.eggs',

    'build',
    'dist',
    'docs',
    'venv/',

    'libcloud/utils/iso8601.py'
]

fingerprint_1a = "Licensed to the Apache Software Foundation"
fingerprint_1b = "Licensed under the Apache License"
fingerprint_2 = "http://www.apache.org/licenses/LICENSE-2.0"

files_not_decoded = set()
files_without_licenses = set()


def ignore_path(path):
    if not path.endswith('.py'):
        return True

    path_split = path.split('/')
    path_split = [c for c in path_split if c]

    for path_name in IGNORED_PATHS:
        if path_name in path_split or path_name in path:
            return True

    return False


for root, dirs, files in os.walk(root_dir):
    for file_ in files:
        path = os.path.join(root, file_)

        if ignore_path(path):
            continue

        print("Checking {}".format(path))

        try:
            with codecs.open(path, encoding="utf-8", mode="r") as f:
                content = f.read()
        except UnicodeDecodeError:
            files_not_decoded.add(path)
            continue

        if len(content) < MIN_FILE_SIZE:
            # File is too small or empty, skip it
            continue

        if (fingerprint_1a in content or fingerprint_1b in content) \
                and fingerprint_2 in content:
            continue

        files_without_licenses.add(path)

for path in sorted(files_not_decoded):
    print("Couldn't decode {}".format(path))

if len(files_without_licenses) >= 1:
    print('')
    print('The following files are missing Apache 2.0 license headers:')

    for path in sorted(files_without_licenses):
        print(path)

    sys.exit(1)
