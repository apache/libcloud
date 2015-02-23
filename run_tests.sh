#!/bin/bash

vagrant up tests
vagrant ssh tests -c "cd /home/vagrant/libcloud; sudo tox"
vagrant destroy -f
