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
# verifies that the SHA512 checksum of both archives matches.

VERSION=$1

if [ ! "${VERSION}" ]; then
    echo "Usage: ${0} <version name>"
    echo "For example: ${0} apache-libcloud-3.7.0"
    exit 1
fi

TMP_DIR=$(mktemp -d)

# TODO: Use json endpoint + jq to parse out the url
# https://pypi.org/pypi/apache-libcloud/3.4.0/json
EXTENSIONS[0]=".tar.gz"
EXTENSIONS[1]=".whl"

# Get the download URL for the given extension from PyPi JSON API
function get_pypi_url() {
    local extension=$1
    local pypi_version

    pypi_version=$(echo "${VERSION}" | sed -E "s/^apache[-_]libcloud-//")

    curl -s "https://pypi.org/pypi/apache-libcloud/${pypi_version}/json" | \
        jq -r  --arg ext "${extension}" \
        '.urls[] | select(.filename | endswith($ext)) | .url' | \
        head -n 1
}

# Get the download URL for the given extension from Apache mirror
function get_apache_url() {
    local extension=$1
    local apache_version

    apache_version=$(echo "${VERSION}" | sed -E "s/^apache[-_]libcloud-//")

    # List files from Apache directory and find the matching file
    curl -s "https://downloads.apache.org/libcloud/" | \
        grep -oP "href=\"\K[^\"]*-${apache_version}[^\"]*${extension}" | \
        head -n 1 | \
        sed "s|^|https://downloads.apache.org/libcloud/|"
}

# From http://tldp.org/LDP/abs/html/debugging.html#ASSERT
function assert ()                 #  If condition false,
{                         #+ exit from script
                          #+ with appropriate error message.
  E_PARAM_ERR=98
  E_ASSERT_FAILED=99


  if [ -z "$2" ]          #  Not enough parameters passed
  then                    #+ to assert() function.
    return $E_PARAM_ERR   #  No damage done.
  fi

  lineno=$2

  if [ ! "$1" ]
  then
    echo "Assertion failed:  \"$1\""
    echo "File \"$0\", line $lineno"    # Give name of file and line number.
    exit $E_ASSERT_FAILED
  fi
}


echo "Comparing checksums for version: ${VERSION}"
echo "Downloaded files will be stored in: ${TMP_DIR}"
echo ""

for (( i = 0 ; i < ${#EXTENSIONS[@]} ; i++ ))
do
    extension=${EXTENSIONS[$i]}
    file_name="${VERSION}${extension}"

    if [ "${extension}" = ".whl" ]; then
        # shellcheck disable=SC2001
        file_name=$(echo "${file_name}" | sed "s/apache-libcloud/apache_libcloud/g")
    fi

    apache_url=$(get_apache_url "${extension}")
    pypi_url=$(get_pypi_url "${extension}")

    if [ -z "${pypi_url}" ]; then
        echo "[ERR] Failed to resolve PyPi URL for ${file_name}"
        exit 2
    fi

    assert "${apache_url} != ${pypi_url}", "URLs must be different"

    file_name_apache="${file_name}-apache"
    file_name_pypi="${file_name}-pypi"

    assert "${file_name_apache} != ${file_name_pypi}", "file names must be different"

    file_path_apache="${TMP_DIR}/${file_name_apache}"
    file_path_pypi="${TMP_DIR}/${file_name_pypi}"

    echo "Comparing checksums for file: ${file_name}"

    echo "Downloading file from Apache mirror..."
    wget --quiet "${apache_url}" -O "${file_path_apache}"

    # shellcheck disable=SC2181
    if [ $? -ne 0 ]; then
        echo "[ERR] Failed to download file: ${apache_url}"
        exit 2
    fi

    echo "Downloading file from PyPi mirror..."
    wget --quiet "${pypi_url}" -O "${file_path_pypi}"

    # shellcheck disable=SC2181
    if [ $? -ne 0 ]; then
        echo "[ERR] Failed to download file: ${pypi_url}"
        exit 2
    fi

    sha512sum_apache=$(sha512sum "${file_path_apache}" | awk '{ print $1 }')
    sha512sum_pypi=$(sha512sum "${file_path_pypi}"| awk '{ print $1 }')

    if [ "${sha512sum_apache}" != "${sha512sum_pypi}" ]; then
       echo "[ERROR] SHA512 sum for file ${file_name} doesn't match"
       echo ""
       echo "${file_name_apache}: ${sha512sum_apache}"
       echo "${file_name_pypi}: ${sha512sum_pypi}"
       exit 1
   else
       echo "[OK] SHA512 sum for file ${file_name} matches"
    fi

    echo ""
done

exit 0
