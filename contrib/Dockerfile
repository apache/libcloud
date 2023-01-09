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

# Docker image used for running tests the under all the supported Python
# versions
FROM ubuntu:20.04

RUN set -e && \
    apt-get update && \
    apt-get install -y \
      software-properties-common \
      wget \
      ssh && \
    add-apt-repository ppa:deadsnakes/ppa && \
    add-apt-repository ppa:pypy/ppa && \
    apt-get update && \
    apt-get -y install \
      python3.6 \
      python3.7 \
      python3.8 \
      python3.9 \
      python3.10 \
      python-dev \
      python3.6-dev \
      python3.7-dev \
      python3.8-dev \
      python3.9-dev \
      python3.10-dev \
      python3.6-distutils \
      python3.7-distutils \
      python3.8-distutils \
      pypy3 \
      pypy3-dev \
      python3-pip \
      libvirt-dev \
      # Needed by libvirt driver
      pkg-config \
      # Needed by cryptography library for pypy
      libssl-dev

# Workaround for zipp import error issue - https://github.com/pypa/virtualenv/issues/1630
RUN python3.8 -m pip install --upgrade pip

RUN set -e && \
    python3.8 -m pip install --no-cache-dir "tox==3.27.1"

COPY . /libcloud

RUN if [ ! -f "/libcloud/README.rst" ]; then echo "libcloud/README.rst file not found, you are likely not running docker build from the repository root directory"; exit 1; fi

WORKDIR /libcloud

CMD ["tox", "-e", "lint,black-check,bandit,,py3.6,py3.7,py3.8,py3.9,py3.10,pypypy-3.8"]
