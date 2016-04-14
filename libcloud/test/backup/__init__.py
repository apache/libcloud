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

from libcloud.backup.base import BackupTarget, BackupTargetType


class TestCaseMixin(object):

    def get_supported_target_types(self):
        targets = self.driver.get_supported_target_types()
        self.assertTrue(isinstance(targets, list))
        for target in targets:
            self.assertTrue(isinstance(target, BackupTargetType))

    def test_list_targets_response(self):
        targets = self.driver.list_targets()
        self.assertTrue(isinstance(targets, list))
        for target in targets:
            self.assertTrue(isinstance(target, BackupTarget))


if __name__ == "__main__":
    import doctest
    doctest.testmod()
