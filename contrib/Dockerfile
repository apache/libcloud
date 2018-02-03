FROM ubuntu:16.04

RUN set -e && \
  apt-get update && \
  apt-get install -y \
    software-properties-common \
    wget \
    ssh && \
  add-apt-repository ppa:deadsnakes/ppa && \
  apt-get update && \
  apt-get -y install \
    python2.7 \
    python3.4 \
    python3.5 \
    python3.6 \
    python-dev \
    python2.7-dev \
    python3.4-dev \
    python3.5-dev \
    python3.6-dev \
    pypy \
    python-pip

RUN set -e && \
  pip install tox \
    mock \
    lockfile \
    coverage

COPY . /libcloud
WORKDIR /libcloud
CMD tox -e py2.7,pypypy,py3.4,py3.5,py3.6,lint
