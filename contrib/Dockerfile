FROM ubuntu:16.04

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
      python3.5 \
      python3.6 \
      python3.7 \
      python3.8 \
      python-dev \
      python3.5-dev \
      python3.6-dev \
      python3.7-dev \
      python3.8-dev \
      pypy3 \
      python-pip \
      libvirt-dev \
      # Needed by libvirt driver
      pkg-config

# Workaround for zipp import error issue - https://github.com/pypa/virtualenv/issues/1630
RUN pip install --upgrade pip

RUN set -e && \
    pip install --no-cache-dir "tox==3.14.2"

COPY . /libcloud

WORKDIR /libcloud

CMD ["tox", "-e", "py3.5", "py3.6", "py3.7", "py3.8", "pypypy3", "lint"]
