#!/bin/bash

add-apt-repository ppa:fkrull/deadsnakes
apt-get update

apt-get -y install python2.5 python2.6 python2.7 python3.2 python3.3 python3.4
apt-get -y install python-dev python2.5-dev python2.6-dev python2.7-dev python3.2-dev python3.3-dev python3.4-dev
apt-get -y install python-pip

wget https://bitbucket.org/pypy/pypy/downloads/pypy-2.5.0-linux64.tar.bz2
tar xf ./pypy-2.5.0-linux64.tar.bz2 -C /opt
ln -s /opt/pypy-2.5.0-linux64/bin/pypy /usr/local/bin/pypy

cp -rf /vagrant /home/vagrant/libcloud
cd /vagrant /home/vagrant/libcloud

pip install tox
pip install mock
pip install lockfile
pip install coverage
