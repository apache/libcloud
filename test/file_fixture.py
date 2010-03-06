# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
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

FILE_FIXTURE_ROOT = 'fixtures'

class FileFixture:
    def __init__(self, root):
        self.root = os.path.join(FILE_FIXTURE_ROOT, root)

    def load(self, file):
        path = os.path.join(self.root, file)
        if os.path.exists(path):
            return open(path, 'r').read()
        else:
            raise IOError
