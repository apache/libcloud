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
# hash-sign.sh : hash and sign the specified files
#
# USAGE: hash-sign.sh file1 file2 ...
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


split="---------------------------------------------------------------------"

echo $split
echo ""
echo "Generating MD5/SHA1 checksum files ..."
echo ""

# check for executables
gpg="`which gpg 2> /dev/null | head -1`"
pgp="`which pgp 2> /dev/null | head -1`"
openssl="`which openssl 2> /dev/null | head -1`"
md5sum="`which md5sum 2> /dev/null | head -1`"
sha1sum="`which sha1sum 2> /dev/null | head -1`"
md5="`which md5 2> /dev/null | head -1`"
sha1="`which sha1 2> /dev/null | head -1`"

# if found we use openssl for generating the checksums
# and convert the results into machine-readable format.
if test -x "${openssl}"; then
  for file in ${allfiles}; do
    if test -f "${file}"; then
      echo "openssl: creating md5 checksum file for ${file} ..."
      ${openssl} md5 ${file} |\
          sed -e 's#^MD5(\(.*\))= \([0-9a-f]*\)$#\2 *\1#' > ${file}.md5
      echo "openssl: creating sha1 checksum file for ${file} ..."
      ${openssl} sha1 ${file} |\
          sed -e 's#^SHA1(\(.*\))= \([0-9a-f]*\)$#\2 *\1#' > ${file}.sha1
    fi
  done
# no openssl found - check if we have gpg
elif test -x "${gpg}"; then
  for file in ${allfiles}; do
    if test -f "${file}"; then
      echo "gpg: creating md5 checksum file for ${file} ..."
      ${gpg} --print-md md5 ${file} |\
          sed -e '{N;s#\n##;}' |\
          sed -e 's#\(.*\): \(.*\)#\2::\1#;s#[\r\n]##g;s# ##g' \
              -e 'y#ABCDEF#abcdef#;s#::# *#' > ${file}.md5
      echo "gpg: creating sha1 checksum file for ${file} ..."
      ${gpg} --print-md sha1 ${file} |\
          sed -e '{N;s#\n##;}' |\
          sed -e 's#\(.*\): \(.*\)#\2::\1#;s#[\r\n]##g;s# ##g' \
              -e 'y#ABCDEF#abcdef#;s#::# *#' > ${file}.sha1
    fi
  done
else
  # no openssl or gpg found - check for md5sum
  if test -x "${md5sum}"; then
    for file in ${allfiles}; do
      if test -f "${file}"; then
        echo "md5sum: creating md5 checksum file for ${file} ..."
        ${md5sum} -b ${file} > ${file}.md5
      fi
    done
  # no openssl or gpg found - check for md5
  elif test -x "${md5}"; then
    for file in ${allfiles}; do
      if test -f "${file}"; then
        echo "md5: creating md5 checksum file for ${file} ..."
        ${md5} -r ${file} | sed -e 's# # *#' > ${file}.md5
      fi
    done
  fi
  # no openssl or gpg found - check for sha1sum
  if test -x "${sha1sum}"; then
    for file in ${allfiles}; do
      if test -f "${file}"; then
        echo "sha1sum: creating sha1 checksum file for ${file} ..."
        ${sha1sum} -b ${file} > ${file}.sha1
      fi
    done
  # no openssl or gpg found - check for sha1
  elif test -x "${sha1}"; then
    for file in ${allfiles}; do
      if test -f "${file}"; then
        echo "sha1: creating sha1 checksum file for ${file} ..."
        ${sha1} -r ${file} | sed -e 's# # *#' > ${file}.sha1
      fi
    done
  fi
fi

echo $split
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
