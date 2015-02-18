# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

$provision_script = <<SCRIPT
add-apt-repository ppa:fkrull/deadsnakes
apt-get update

apt-get -y install python2.5 python2.6 python2.7 python3.2 python3.3 python3.4
apt-get -y install python-dev python2.5-dev python2.6-dev python2.7-dev python3.2-dev python3.3-dev python3.4-dev
apt-get -y install python-pip

wget https://bitbucket.org/pypy/pypy/downloads/pypy-2.5.0-linux64.tar.bz2
tar xf ./pypy-2.5.0-linux64.tar.bz2 -C /opt
ln -s /opt/pypy-2.5.0-linux64/bin/pypy /usr/local/bin/pypy

cp -r /vagrant /home/vagrant/libcloud
cd /home/vagrant/libcloud

pip install tox
pip install mock
pip install lockfile
pip install coverage
SCRIPT

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = "ubuntu/trusty64"

  config.vm.define "tests" do |db|
    config.vm.provision :shell, :inline => $provision_script
  end

  config.vm.provider :virtualbox do |vb|
    vb.customize ["modifyvm", :id, "--memory", "2048"]
  end

end
