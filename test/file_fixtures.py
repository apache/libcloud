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

# Helper class for loading large fixture data

import os

FIXTURES_ROOT = 'fixtures'

class FileFixtures:
    def __init__(self, sub_dir=''):
        script_dir = os.path.abspath(os.path.split(__file__)[0])
        self.root = os.path.join(script_dir, FIXTURES_ROOT, sub_dir)

    def load(self, file):
        path = os.path.join(self.root, file)
        if os.path.exists(path):
            return open(path, 'r').read()
        else:
            raise IOError
