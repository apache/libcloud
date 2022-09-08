#!/usr/bin/python
#
# Copyright 2015 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
################################################################################

# pylint: skip-file

import json
import unittest

import utils


class SplitStringToAlphaNumTest(unittest.TestCase):
    def testInitial(self):
        self.assertEqual(utils.splitStringWithNumbers("12-abc"), [12, "-abc"])

    def testMiddle(self):
        self.assertEqual(utils.splitStringWithNumbers("abc-345-def"), ["abc-", 345, "-def"])

    def testFinal(self):
        self.assertEqual(utils.splitStringWithNumbers("xyz-42"), ["xyz-", 42])

    def testMultiple(self):
        self.assertEqual(
            utils.splitStringWithNumbers("Aaa-123-Bbb-456-Ccc"),
            ["Aaa-", 123, "-Bbb-", 456, "-Ccc"],
        )


class SortKeysNumericallyTest(unittest.TestCase):
    def testSimple(self):
        input = {
            "a-1": 1,
            "a-12": 12,
            "a-2": 2,
        }
        output = """\
{
    "a-1": 1,
    "a-2": 2,
    "a-12": 12
}\
"""
        self.assertEqual(
            json.dumps(input, indent=4 * " ", item_sort_key=utils.sortKeysNumerically),
            output,
        )


if __name__ == "__main__":
    unittest.main()
