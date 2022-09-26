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
import glob
import atexit
import random
import shutil
import string
import tempfile
from unittest import mock

import pytest

from libcloud.storage.drivers.local import LocalStorageDriver


def make_tmp_file(content=None):
    content = content or b"1"

    fd, path = tempfile.mkstemp()

    with os.fdopen(fd, "wb") as fp:
        fp.write(content)

    return path


def clean_up_lock_files():
    for file_path in glob.glob("/tmp/*.lock"):
        os.remove(file_path)


# fmt: off
@pytest.mark.parametrize(
    "object_count",
    [
        100,
        1000,
        10000,
        10000,
        100000,
    ],
    ids=[
        "100",
        "1000",
        "10k",
        "100k",
        "1mil",
    ],
)
@pytest.mark.parametrize(
    "sort_objects",
    [
        True,
        False,
    ],
    ids=[
        "sort_objects",
        "no_sort",
    ],
)
# fmt: on
def test_list_objects_with_filtering(benchmark, object_count, sort_objects):
    """
    Micro benchmark which measures how long list_container_objects takes with a lot of objects.

    NOTE: To avoid issues with tons of lock files laying around we don't use locking for this
    benchmark since we are not woried about race conditions and we don't benchmark locking
    scenario.
    """
    base_path = tempfile.mkdtemp()

    def clean_up_base_path():
        if os.path.exists(base_path):
            shutil.rmtree(base_path)

    atexit.register(clean_up_base_path)
    atexit.register(clean_up_lock_files)

    driver = LocalStorageDriver(base_path, ex_use_locking=False)

    def run_benchmark():
        objects = driver.list_container_objects(container=container)
        assert len(objects) == object_count
        return objects

    # 1. Create mock objects
    container = driver.create_container("test_container_1")
    tmppath = make_tmp_file()

    for index in range(0, object_count):
        # To actually exercise overhead of sorting we use random objects name and not sequential
        # pre-sorted object names
        name = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
        obj = container.upload_object(tmppath, name)
        assert obj.name == name

    # 2. Run the actual benchmark
    try:
        if sort_objects:
            result = benchmark(run_benchmark)
        else:
            with mock.patch("libcloud.storage.drivers.local.sorted", lambda values, key: values):
                result = benchmark(run_benchmark)
        assert len(result) == object_count
    finally:
        clean_up_base_path()
        clean_up_lock_files()
