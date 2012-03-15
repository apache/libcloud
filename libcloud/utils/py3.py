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
# Some methods bellow are taken from Django PYK3 port which is licensed under 3
# clause BSD license
# https://bitbucket.org/loewis/django-3k

from __future__ import absolute_import

import sys
import types

PY3 = False
PY2 = False
PY25 = False

if sys.version_info >= (3, 0):
    PY3 = True
    import http.client as httplib
    from io import StringIO
    import urllib
    import urllib as urllib2
    import urllib.parse as urlparse
    import xmlrpc.client as xmlrpclib
    from urllib.parse import quote as urlquote
    from urllib.parse import urlencode as urlencode

    basestring = str

    def method_type(callable, instance, klass):
        return types.MethodType(callable, instance or klass())

    bytes = __builtins__['bytes']
    def b(s):
        if isinstance(s, str):
            return s.encode('utf-8')
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
    PY2 = True
    import httplib
    from StringIO import StringIO
    import urllib
    import urllib2
    import urlparse
    import xmlrpclib
    from urllib import quote as urlquote
    from urllib import urlencode as urlencode

    basestring = unicode = str

    method_type = types.MethodType

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
