#!/bin/bash
# licensed to the apache software foundation (asf) under one or more
# contributor license agreements.  see the notice file distributed with
# this work for additional information regarding copyright ownership.
# the asf licenses this file to you under the apache license, version 2.0
# (the "license"); you may not use this file except in compliance with
# the license.  you may obtain a copy of the license at
#
#     http://www.apache.org/licenses/license-2.0
#
# unless required by applicable law or agreed to in writing, software
# distributed under the license is distributed on an "as is" basis,
# without warranties or conditions of any kind, either express or implied.
# see the license for the specific language governing permissions and
# limitations under the license.

# This script downloads release artifacts from Apache server and PyPi server and
# verifies that the MD5 checksum of both archives matches.

VERSION=$1

if [ ! ${VERSION} ]; then
    echo "Usage: ${0} <version name>"
    echo "For example: ${0} apache-libcloud-0.13.2"
    exit 1
fi

TMP_DIR=`mktemp -d`

EXTENSIONS[0]="tar.gz"
EXTENSIONS[1]="tar.bz2"

APACHE_MIRROR_URL="http://www.apache.org/dist/libcloud"
PYPI_MIRROR_URL="https://pypi.python.org/packages/source/a/apache-libcloud"

echo "Comparing checksums for version: ${VERSION}"
echo "Downloaded files will be stored in: ${TMP_DIR}"
echo ""

for (( i = 0 ; i < ${#EXTENSIONS[@]} ; i++ ))
do
    extension=${EXTENSIONS[$i]}
    file_name="${VERSION}.${extension}"

    apache_url="${APACHE_MIRROR_URL}/${file_name}"
    pypi_url="${PYPI_MIRROR_URL}/${file_name}"

    file_name_apache="${file_name}-apache"
    file_name_pypi="${file_name}-pypi"

    file_path_apache="${TMP_DIR}/${file_name_apache}"
    file_path_pypi="${TMP_DIR}/${file_name_pypi}"

    echo "Comparing checksums for file: ${file_name}"

    echo "Downloading file from Apache mirror..."
    wget --quiet "${apache_url}" -O "${file_path_apache}"

    echo "Downloading file from PyPi mirror..."
    wget --quiet "${pypi_url}" -O "${file_path_pypi}"

    md5sum_apache=$(md5sum "${file_path_apache}" | awk '{ print $1 }')
    md5sum_pypi=$(md5sum "${file_path_pypi}"| awk '{ print $1 }')

    if [ ${md5sum_apache} != ${md5sum_pypi} ]; then
       echo "[ERROR] MD5 sum for file ${file_name} doesn\'t match"
       echo ""
       echo "${file_name_apache}: ${md5sum_apache}"
       echo "${file_name_pypi}: ${md5sum_pypi}"
       exit 1
   else
       echo "[OK] MD5 sum for file ${file_name} matches"
    fi

    echo ""
done

exit 0
