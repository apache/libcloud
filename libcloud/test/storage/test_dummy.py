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

import pytest

from libcloud.storage.drivers.dummy import DummyStorageDriver


@pytest.fixture
def driver():
    return DummyStorageDriver('key', 'id')


@pytest.fixture
def container_with_contents(driver):
    container_name = 'test'
    object_name = 'test.dat'
    container = driver.create_container(container_name=container_name)
    driver.upload_object(
        __file__, container=container, object_name=object_name
    )
    return container_name, object_name


def test_list_container_objects(driver, container_with_contents):
    container_name, object_name = container_with_contents
    container = driver.get_container(container_name)

    objects = driver.list_container_objects(container=container)

    assert any(o for o in objects if o.name == object_name)


def test_list_container_objects_filter_by_prefix(
    driver, container_with_contents
):
    container_name, object_name = container_with_contents
    container = driver.get_container(container_name)

    objects = driver.list_container_objects(
        container=container, prefix=object_name[:3]
    )
    assert any(o for o in objects if o.name == object_name)

    objects = driver.list_container_objects(
        container=container, prefix='does-not-exist.dat'
    )
    assert not objects
