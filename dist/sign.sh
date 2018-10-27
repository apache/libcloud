#!/bin/sh
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
#
# sign.sh : sign the specified files
#
# USAGE: sign.sh -u user file1 file2 ...
#

user=""
case "$1" in
  -u)
    shift
    user="$1"
    shift
    ;;
esac

allfiles=$*



gpg="`which gpg 2> /dev/null | head -1`"
pgp="`which pgp 2> /dev/null | head -1`"

echo "---------------------------------------------------------------------"
echo ""
echo "Signing the files ..."
echo ""

# if found we use pgp for signing the files
if test -x "${pgp}"; then
  if test -n "${user}"; then
    args="-u ${user}"
  fi
  for file in ${allfiles}; do
    if test -f "${file}"; then
      echo "pgp: creating asc signature file for ${file} ..."
      ${pgp} -sba ${file} ${args}
    fi
  done
# no pgp found - check for gpg
elif test -x "${gpg}"; then
  if test -z "${user}"; then
    args="--default-key ${args}"
  else
    args="-u ${user} ${args}"
  fi
  for file in ${allfiles}; do
    if test -f "${file}"; then
      echo "gpg: creating asc signature file for ${file} ..."
      ${gpg} --armor ${args} --detach-sign ${file}
    fi
  done
else
  echo "PGP or GnuPG not found!  Not signing release!"
fi
