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

# Libcloud Python 2.x and 3.x compatibility layer

import sys

PY3 = False
PY25 = False

if sys.version_info >= (3, 0):
    PY3 = True
    import http.client as httplib
    from io import StringIO
    import urllib as urllib2
    import urllib.parse as urlparse

    import urllib
    urllib.quote = urlparse.quote
    urllib.urlencode = urlparse.urlencode

    basestring = str

    # Taken from django.utils.py3
    bytes = __builtins__['bytes']
    def b(s):
        if isinstance(s, str):
            return s.encode("ascii")
        elif isinstance(s, bytes):
            return s
        else:
            raise TypeError("Invalid argument %r for b()" % (s,))
    def byte(n):
        # assume n is a Latin-1 string of length 1
        return ord(n)
    u = str
    next = __builtins__['next']
    def dictvalues(d):
        return list(d.values())
else:
    import httplib
    from StringIO import StringIO
    import urllib
    import urllib2
    import urlparse

    basestring = unicode = str

    # Taken from django.utils.py3
    b = bytes = str
    def byte(n):
        return n
    u = unicode
    def next(i):
        return i.next()
    def dictvalues(d):
        return d.values()

if sys.version_info >= (2, 5) and sys.version_info <= (2, 6):
    PY25 = True
