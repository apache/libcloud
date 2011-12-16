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


def merge_valid_keys(params, valid_keys, extra):
    """
    Merge valid keys from extra into params dictionary and return
    dictionary with keys which have been merged.

    Note: params is modified in place.
    """
    merged = {}
    if not extra:
        return merged

    for key in valid_keys:
        if key in extra:
            params[key] = extra[key]
            merged[key] = extra[key]

    return merged


def get_new_obj(obj, klass, attributes):
    """
    Pass attributes from the existing object 'obj' and attributes
    dictionary to a 'klass' constructor.
    Attributes from 'attributes' dictionary are only passed to the
    constructor if they are not None.
    """
    kwargs = {}
    for key, value in list(obj.__dict__.items()):
        if isinstance(value, dict):
            kwargs[key] = value.copy()
        elif isinstance(value, (tuple, list)):
            kwargs[key] = value[:]
        else:
            kwargs[key] = value

    for key, value in list(attributes.items()):
        if value is None:
            continue

        if isinstance(value, dict):
            kwargs_value = kwargs.get(key, {})
            for key1, value2 in list(value.items()):
                if value2 is None:
                    continue

                kwargs_value[key1] = value2
            kwargs[key] = kwargs_value
        else:
            kwargs[key] = value

    return klass(**kwargs)


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
    Create a list of values from a whitespace and newline delimited text
    (keys are ignored).

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
    Create a string with a whitespace and newline delimited text from a
    dictionary.

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


def reverse_dict(dictionary):
    return dict([(value, key) for key, value in list(dictionary.items())])


def lowercase_keys(dictionary):
    return dict(((k.lower(), v) for k, v in dictionary.items()))
