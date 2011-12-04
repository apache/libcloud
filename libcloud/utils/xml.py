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


def fixxpath(xpath, namespace=None):
    # ElementTree wants namespaces in its xpaths, so here we add them.
    if not namespace:
        return xpath

    return '/'.join(['{%s}%s' % (namespace, e) for e in xpath.split('/')])


def findtext(element, xpath, namespace=None):
    return element.findtext(fixxpath(xpath=xpath, namespace=namespace))


def findattr(element, xpath, namespace=None):
    return element.findtext(fixxpath(xpath=xpath, namespace=namespace))


def findall(element, xpath, namespace=None):
    return element.findall(fixxpath(xpath=xpath, namespace=namespace))
