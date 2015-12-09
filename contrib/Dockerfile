FROM ubuntu:14.04

RUN set -e && \
  apt-get update && \
  apt-get install -y \
    software-properties-common \
    wget \
    ssh && \
  add-apt-repository ppa:fkrull/deadsnakes && \
  apt-get update && \
  apt-get -y install \
    python2.6 \
    python2.7 \
    python3.2 \
    python3.3 \
    python3.4 \
    python3.5 \
    python-dev \
    python2.6-dev \
    python2.7-dev \
    python3.2-dev \
    python3.3-dev \
    python3.4-dev \
    python3.5-dev \
    python-pip

RUN set -e && \
  wget https://bitbucket.org/pypy/pypy/downloads/pypy-2.5.0-linux64.tar.bz2 && \
  tar xf ./pypy-2.5.0-linux64.tar.bz2 -C /opt && \
  ln -s /opt/pypy-2.5.0-linux64/bin/pypy /usr/local/bin/pypy

RUN set -e && \
  pip install tox \
    mock \
    lockfile \
    coverage

COPY . /libcloud
WORKDIR /libcloud
CMD tox -e py2.6,py2.7,pypypy,py3.2,py3.3,py3.4,py3.5,lint
