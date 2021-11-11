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
    echo "For example: ${0} apache-libcloud-3.4.0"
    exit 1
fi

TMP_DIR=$(mktemp -d)

# TODO: Use json endpoint + jq to parse out the url
# https://pypi.org/pypi/apache-libcloud/3.4.0/json
EXTENSIONS[0]=".tar.gz"
EXTENSIONS[1]="-py2.py3-none-any.whl"

APACHE_MIRROR_URL="http://www.apache.org/dist/libcloud"
PYPI_MIRROR_URL_SOURCE="https://pypi.python.org/packages/source/a/apache-libcloud"
PYPI_MIRROR_URL_WHEEL="https://files.pythonhosted.org/packages/py2.py3/a/apache-libcloud"

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

    if [ "${extension}" = "-py2.py3-none-any.whl" ]; then
        file_name=$(echo ${file_name} | sed "s/apache-libcloud/apache_libcloud/g")
    fi

    apache_url="${APACHE_MIRROR_URL}/${file_name}"
    pypi_url="${PYPI_MIRROR_URL}/${file_name}"

    if [ "${extension}" = "-py2.py3-none-any.whl" ]; then
        pypi_url="${PYPI_MIRROR_URL_WHEEL}/${file_name}"
    else
        pypi_url="${PYPI_MIRROR_URL_SOURCE}/${file_name}"
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

    if [ $? -ne 0 ]; then
        echo "[ERR] Failed to download file: ${apache_url}"
        exit 2
    fi

    echo "Downloading file from PyPi mirror..."
    wget --quiet "${pypi_url}" -O "${file_path_pypi}"

    if [ $? -ne 0 ]; then
        echo "[ERR] Failed to download file: ${pypi_url}"
        exit 2
    fi

    sha512sum_apache=$(sha512sum "${file_path_apache}" | awk '{ print $1 }')
    sha512sum_pypi=$(sha512sum "${file_path_pypi}"| awk '{ print $1 }')

    if [ ${sha512sum_apache} != ${sha512sum_pypi} ]; then
       echo "[ERROR] SHA512 sum for file ${file_name} doesn\'t match"
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
