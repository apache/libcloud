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
FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

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
      python3.9 \
      python3.10 \
      python3.11 \
      python3.12 \
      python3.13 \
      python3-dev \
      python3.9-dev \
      python3.10-dev \
      python3.11-dev \
      python3.12-dev \
      python3.13-dev \
      # Uses 3.10
      pypy3 \
      pypy3-dev \
      python3-pip \
      python3-distutils \
      python3.9-distutils \
      libvirt-dev \
      # Needed by libvirt driver
      pkg-config


COPY . /libcloud

RUN if [ ! -f "/libcloud/README.rst" ]; then echo "libcloud/README.rst file not found, you are likely not running docker build from the repository root directory"; exit 1; fi

WORKDIR /libcloud

RUN set -e && \
    python3.9 -m pip install --no-cache-dir -r requirements-ci.txt

CMD ["tox", "-e", "lint,isort-check,black-check,bandit,py3.9,py3.10,py3.11,py3.12,py3.13,pypypy3.10"]
