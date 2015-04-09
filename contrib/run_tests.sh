#!/usr/bin/env bash
#
#  Licensed to the Apache Software Foundation (ASF) under one
#  or more contributor license agreements.  See the NOTICE file
#  distributed with this work for additional information
#  regarding copyright ownership.  The ASF licenses this file
#  to you under the Apache License, Version 2.0 (the
#  "License"); you may not use this file except in compliance
#  with the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing,
#  software distributed under the License is distributed on an
#  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#  KIND, either express or implied.  See the License for the
#  specific language governing permissions and limitations
#  under the License.
#
# Script which spawns a virtual instance using vagrant and a
# backend provider i.e. VirtualBox, install pypy, pip,
# python versions 2.5, 2.6, 2.7, 3.2, 3.3, 3.4 (corresponding
# dev packages as well) and run tox tests in the virtual instance

cd ../
vagrant up tests
vagrant ssh tests -c "cd /home/vagrant/libcloud; sudo tox"
vagrant destroy -f
