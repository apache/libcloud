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

files=$(git diff --cached --name-status | grep -v ^D | awk '$1 $2 { print $2}' | grep -e .py$)
array=(${files/// })

for file in "${array[@]}"
do
    if [[ ${file} =~ "libcloud/test/" ]]; then
        flake8 --max-line-length=160 ${file}
    else
        flake8 ${file}
    fi
done
