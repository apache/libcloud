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

import re


def splitStringWithNumbers(string):
    """Splits input string into a list of items, numeric and otherwise.

    Returns a list of values, each either an interpreted number, or a substring
    of the original input.

    E.g., 'abc-123-def' => ['abc-', 123, '-def']
    """
    rawParts = re.split(r"(\d+)", string)

    # Filter out empty strings.
    nonEmptyParts = filter(None, rawParts)

    # Convert any numeric strings to numbers.
    def splitHelper(nonEmptyParts):
        for part in nonEmptyParts:
            if re.match(r"\d+", part):
                yield int(part)
            else:
                yield part

    return list(splitHelper(nonEmptyParts))


def sortKeysNumerically(key_value):
    key, value = key_value
    return splitStringWithNumbers(key)
