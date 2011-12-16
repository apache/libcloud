#!/bin/bash
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
# Script for migrating from the old style libcloud paths (pre 0.5) to the new
# ones.
# THIS SCRIPT WILL MODIFY FILES IN PLACE. BE SURE TO BACKUP THEM BEFORE RUNNING
# IT. LIBCLOUD TEAM CANNOT BE RESPONSIBLE FOR ANY DAMAGE CAUSED BY THIS SCRIPT.
# Note: If you are on OS X / FreeBSD, you need to install GNU sed.

DIRECTORY=$1

SED=`which gsed gnused sed`

for value in $SED
do
    SED=${value}
    break
done

if [ ! $DIRECTORY ]; then
    echo "Usage: ./migrate_paths.sh <directory with your code>"
    exit 1
fi

OLD_PATHS[0]="libcloud.base"
OLD_PATHS[1]="libcloud.deployment"
OLD_PATHS[2]="libcloud.drivers"
OLD_PATHS[3]="libcloud.ssh"
OLD_PATHS[4]="libcloud.types"
OLD_PATHS[5]="libcloud.providers"

UPDATED_PATHS[0]="libcloud.compute.base"
UPDATED_PATHS[1]="libcloud.compute.deployment"
UPDATED_PATHS[2]="libcloud.compute.drivers"
UPDATED_PATHS[3]="libcloud.compute.ssh"
UPDATED_PATHS[4]="libcloud.compute.types"
UPDATED_PATHS[5]="libcloud.compute.providers"

for (( i = 0 ; i < ${#OLD_PATHS[@]} ; i++ ))
do
    old_path=${OLD_PATHS[$i]}
    new_path=${UPDATED_PATHS[$i]}

    cmd1="find ${DIRECTORY} -name '*.py' -type f -print0 | xargs -0 ${SED} -i -e 's/^from ${old_path} import/from ${new_path} import/g'"
    cmd2="find ${DIRECTORY} -name '*.py' -type f -print0 | xargs -0 ${SED} -i -e 's/^import ${old_path}/import ${new_path}/g'"

    echo "Migrating: ${old_path} -> ${new_path}"
    eval "$cmd1"
    eval "$cmd2"
done
