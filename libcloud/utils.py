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

import os
import mimetypes
import warnings
from httplib import HTTPResponse

SHOW_DEPRECATION_WARNING = True
OLD_API_REMOVE_VERSION = '0.6.0'

def read_in_chunks(iterator, chunk_size=None):
    """
    Return a generator which yields data in chunks.

    @type iterator: C{Iterator}
    @param response: An object which implements an iterator interface
                     or a File like object with read method.

    @type chunk_size: C{int}
    @param chunk_size: Optional chunk size (defaults to CHUNK_SIZE)
    """

    if isinstance(iterator, (file, HTTPResponse)):
        get_data = iterator.read
        args = (chunk_size, )
    else:
        get_data = iterator.next
        args = ()

    while True:
        chunk = str(get_data(*args))

        if len(chunk) == 0:
            raise StopIteration

        yield chunk

def guess_file_mime_type(file_path):
    filename = os.path.basename(file_path)
    (mimetype, encoding) = mimetypes.guess_type(filename)
    return mimetype, encoding

def deprecated_warning(module):
    if SHOW_DEPRECATION_WARNING:
        warnings.warn('This path has been deprecated and the module'
                       ' is now available at "libcloud.compute.%s".'
                       ' This path will be fully removed in libcloud %s.' % \
                       (module, OLD_API_REMOVE_VERSION),
                  category=DeprecationWarning)

def get_driver(drivers, provider):
    """
    Get a driver.

    @param drivers: Dictionary containing valid providers.
    @param provider: Id of provider to get driver
    @type provider: L{libcloud.types.Provider}
    """
    if provider in drivers:
        mod_name, driver_name = drivers[provider]
        _mod = __import__(mod_name, globals(), locals(), [driver_name])
        return getattr(_mod, driver_name)

    raise AttributeError('Provider %s does not exist' % (provider))
