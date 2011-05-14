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
SHOW_IN_DEVELOPMENT_WARNING = True
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
                      ' This path will be fully removed in libcloud %s.' %
                      (module, OLD_API_REMOVE_VERSION),
                      category=DeprecationWarning)

def in_development_warning(module):
    if SHOW_IN_DEVELOPMENT_WARNING:
        warnings.warn('The module %s is in development and your are advised '
                      'against using it in production.' % (module),
                      category=FutureWarning)

def str2dicts(data):
    """
    Create a list of dictionaries from a whitespace and newline delimited text.

    For example, this:
    cpu 1100
    ram 640

    cpu 2200
    ram 1024

    becomes:
    [{'cpu': '1100', 'ram': '640'}, {'cpu': '2200', 'ram': '1024'}]
    """
    list_data = []
    list_data.append({})
    d = list_data[-1]

    lines = data.split('\n')
    for line in lines:
        line = line.strip()

        if not line:
            d = {}
            list_data.append(d)
            d = list_data[-1]
            continue

        whitespace = line.find(' ')

        if not whitespace:
            continue

        key = line[0:whitespace]
        value = line[whitespace + 1:]
        d.update({key: value})

    list_data = [value for value in list_data if value != {}]
    return list_data

def str2list(data):
    """
    Create a list of values from a whitespace and newline delimited text (keys are ignored).

    For example, this:
    ip 1.2.3.4
    ip 1.2.3.5
    ip 1.2.3.6

    becomes:
    ['1.2.3.4', '1.2.3.5', '1.2.3.6']
    """
    list_data = []

    for line in data.split('\n'):
        line = line.strip()

        if not line:
            continue

        try:
            splitted = line.split(' ')
            # key = splitted[0]
            value = splitted[1]
        except Exception:
            continue

        list_data.append(value)

    return list_data

def dict2str(data):
    """
    Create a string with a whitespace and newline delimited text from a dictionary.

    For example, this:
    {'cpu': '1100', 'ram': '640', 'smp': 'auto'}

    becomes:
    cpu 1100
    ram 640
    smp auto

    cpu 2200
    ram 1024
    """
    result = ''
    for k in data:
        if data[k] != None:
            result += '%s %s\n' % (str(k), str(data[k]))
        else:
            result += '%s\n' % str(k)

    return result

def fixxpath(xpath, namespace):
    # ElementTree wants namespaces in its xpaths, so here we add them.
    return '/'.join(['{%s}%s' % (namespace, e) for e in xpath.split('/')])

def findtext(element, xpath, namespace):
    return element.findtext(fixxpath(xpath=xpath, namespace=namespace))

def findattr(element, xpath, namespace):
    return element.findtext(fixxpath(xpath=xpath, namespace=namespace))

def findall(element, xpath, namespace):
    return element.findall(fixxpath(xpath=xpath, namespace=namespace))

def reverse_dict(dictionary):
    return dict([ (value, key) for key, value in dictionary.iteritems() ])

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
