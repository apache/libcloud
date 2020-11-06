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

from __future__ import with_statement

import os
import sys
import platform
import shutil
import unittest
import time
import tempfile
import multiprocessing

from libcloud.common.types import LibcloudError
from libcloud.storage.base import Container
from libcloud.storage.base import Object
from libcloud.storage.types import ContainerDoesNotExistError
from libcloud.storage.types import ContainerAlreadyExistsError
from libcloud.storage.types import ContainerIsNotEmptyError
from libcloud.storage.types import InvalidContainerNameError
from libcloud.utils.files import exhaust_iterator

try:
    from libcloud.storage.drivers.local import LocalStorageDriver
    from libcloud.storage.drivers.local import LockLocalStorage
    import fasteners
except ImportError:
    print('fasteners library is not available, skipping local_storage tests...')
    LocalStorageDriver = None


class LocalTests(unittest.TestCase):
    driver_type = LocalStorageDriver

    @classmethod
    def create_driver(self):
        self.key = tempfile.mkdtemp()
        return self.driver_type(self.key, None)

    def setUp(self):
        self.driver = self.create_driver()

    def tearDown(self):
        shutil.rmtree(self.key)
        self.key = None

    def make_tmp_file(self, content=None):
        if not content:
            content = b'blah' * 1024
        _, tmppath = tempfile.mkstemp()
        with open(tmppath, 'wb') as fp:
            fp.write(content)
        return tmppath

    def remove_tmp_file(self, tmppath):
        try:
            os.unlink(tmppath)
        except Exception as e:
            msg = str(e)
            if 'being used by another process' in msg and platform.system().lower() == 'windows':
                return
            raise e

    @unittest.skipIf(platform.system().lower() == 'windows', 'Unsupported on Windows')
    def test_lock_local_storage(self):
        # 1. Acquire succeeds
        lock = LockLocalStorage("/tmp/a")
        with lock:
            self.assertTrue(True)

        # 2. Acquire fails because lock is already acquired
        lock = LockLocalStorage("/tmp/b", timeout=0.5)
        with lock:
            expected_msg = "Failed to acquire thread lock"
            self.assertRaisesRegex(LibcloudError, expected_msg, lock.__enter__)

        # 3. Multiprocessing scenario where IPC lock is involved
        def acquire_lock_in_subprocess(pid, success):
            # For first process acquire should succeed and for the second it should fail

            lock = LockLocalStorage("/tmp/c", timeout=0.5)

            if pid == 1:
                with lock:
                    time.sleep(1)

                success.value = 1
            elif pid == 2:
                expected_msg = "Failed to acquire IPC lock"
                self.assertRaisesRegex(LibcloudError, expected_msg, lock.__enter__)
                success.value = 1
            else:
                raise ValueError("Invalid pid")

        success_1  = multiprocessing.Value('i', 0)
        success_2  = multiprocessing.Value('i', 0)

        p1 = multiprocessing.Process(target=acquire_lock_in_subprocess, args=(1, success_1,))
        p1.start()

        p2 = multiprocessing.Process(target=acquire_lock_in_subprocess, args=(2, success_2,))
        p2.start()

        p1.join()
        p2.join()

        self.assertEqual(bool(success_1.value), True, "Check didn't pass")
        self.assertEqual(bool(success_2.value), True, "Second check didn't pass")

    def test_list_containers_empty(self):
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 0)

    def test_containers_success(self):
        self.driver.create_container('test1')
        self.driver.create_container('test2')
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 2)

        container = containers[1]

        self.assertTrue('creation_time' in container.extra)
        self.assertTrue('modify_time' in container.extra)
        self.assertTrue('access_time' in container.extra)

        objects = self.driver.list_container_objects(container=container)
        self.assertEqual(len(objects), 0)

        objects = container.list_objects()
        self.assertEqual(len(objects), 0)

        for container in containers:
            self.driver.delete_container(container)

    def test_objects_success(self):
        tmppath = self.make_tmp_file()

        container = self.driver.create_container('test3')
        obj1 = container.upload_object(tmppath, 'object1')
        obj2 = container.upload_object(tmppath, 'path/object2')
        obj3 = container.upload_object(tmppath, 'path/to/object3')
        obj4 = container.upload_object(tmppath, 'path/to/object4.ext')
        with open(tmppath, 'rb') as tmpfile:
            obj5 = container.upload_object_via_stream(tmpfile, 'object5')

        objects = self.driver.list_container_objects(container=container)
        self.assertEqual(len(objects), 5)

        prefix = os.path.join('path', 'to')
        objects = self.driver.list_container_objects(container=container,
                                                     prefix=prefix)
        self.assertEqual(len(objects), 2)

        for obj in objects:
            self.assertNotEqual(obj.hash, None)
            self.assertEqual(obj.size, 4096)
            self.assertEqual(obj.container.name, 'test3')
            self.assertTrue('creation_time' in obj.extra)
            self.assertTrue('modify_time' in obj.extra)
            self.assertTrue('access_time' in obj.extra)

        obj1.delete()
        obj2.delete()

        objects = container.list_objects()
        self.assertEqual(len(objects), 3)

        container.delete_object(obj3)
        container.delete_object(obj4)
        container.delete_object(obj5)

        objects = container.list_objects()
        self.assertEqual(len(objects), 0)

        container.delete()
        self.remove_tmp_file(tmppath)

    def test_get_container_doesnt_exist(self):
        try:
            self.driver.get_container(container_name='container1')
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_get_container_success(self):
        self.driver.create_container('test4')
        container = self.driver.get_container(container_name='test4')
        self.assertTrue(container.name, 'test4')
        container.delete()

    def test_get_object_container_doesnt_exist(self):
        try:
            self.driver.get_object(container_name='test-inexistent',
                                   object_name='test')
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_get_object_success(self):
        tmppath = self.make_tmp_file()
        container = self.driver.create_container('test5')
        container.upload_object(tmppath, 'test')

        obj = self.driver.get_object(container_name='test5',
                                     object_name='test')

        self.assertEqual(obj.name, 'test')
        self.assertEqual(obj.container.name, 'test5')
        self.assertEqual(obj.size, 4096)
        self.assertNotEqual(obj.hash, None)
        self.assertTrue('creation_time' in obj.extra)
        self.assertTrue('modify_time' in obj.extra)
        self.assertTrue('access_time' in obj.extra)

        obj.delete()
        container.delete()
        self.remove_tmp_file(tmppath)

    def test_create_container_invalid_name(self):
        try:
            self.driver.create_container(container_name='new/container')
        except InvalidContainerNameError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_create_container_already_exists(self):
        container = self.driver.create_container(
            container_name='new-container')
        try:
            self.driver.create_container(container_name='new-container')
        except ContainerAlreadyExistsError:
            pass
        else:
            self.fail('Exception was not thrown')

        # success
        self.driver.delete_container(container)

    def test_create_container_success(self):
        name = 'new_container'
        container = self.driver.create_container(container_name=name)
        self.assertEqual(container.name, name)
        self.driver.delete_container(container)

    def test_delete_container_doesnt_exist(self):
        container = Container(name='new_container', extra=None,
                              driver=self.driver)
        try:
            self.driver.delete_container(container=container)
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_delete_container_not_empty(self):
        tmppath = self.make_tmp_file()
        container = self.driver.create_container('test6')
        obj = container.upload_object(tmppath, 'test')

        try:
            self.driver.delete_container(container=container)
        except ContainerIsNotEmptyError:
            pass
        else:
            self.fail('Exception was not thrown')

        # success
        obj.delete()
        self.remove_tmp_file(tmppath)
        self.assertTrue(self.driver.delete_container(container=container))

    def test_delete_container_not_found(self):
        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        try:
            self.driver.delete_container(container=container)
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Container does not exist but an exception was not' +
                      'thrown')

    def test_delete_container_success(self):
        container = self.driver.create_container('test7')
        self.assertTrue(self.driver.delete_container(container=container))

    def test_download_object_success(self):
        tmppath = self.make_tmp_file()
        container = self.driver.create_container('test6')
        obj = container.upload_object(tmppath, 'test')

        destination_path = tmppath + '.temp'
        result = self.driver.download_object(obj=obj,
                                             destination_path=destination_path,
                                             overwrite_existing=False,
                                             delete_on_failure=True)

        self.assertTrue(result)

        obj.delete()
        container.delete()
        self.remove_tmp_file(tmppath)
        os.unlink(destination_path)

    def test_download_object_and_overwrite(self):
        tmppath = self.make_tmp_file()
        container = self.driver.create_container('test6')
        obj = container.upload_object(tmppath, 'test')

        destination_path = tmppath + '.temp'
        result = self.driver.download_object(obj=obj,
                                             destination_path=destination_path,
                                             overwrite_existing=False,
                                             delete_on_failure=True)

        self.assertTrue(result)

        try:
            self.driver.download_object(obj=obj,
                                        destination_path=destination_path,
                                        overwrite_existing=False,
                                        delete_on_failure=True)
        except LibcloudError:
            pass
        else:
            self.fail('Exception was not thrown')

        result = self.driver.download_object(obj=obj,
                                             destination_path=destination_path,
                                             overwrite_existing=True,
                                             delete_on_failure=True)

        self.assertTrue(result)

        # success
        obj.delete()
        container.delete()
        self.remove_tmp_file(tmppath)
        os.unlink(destination_path)

    def test_download_object_as_stream_success(self):
        tmppath = self.make_tmp_file()
        container = self.driver.create_container('test6')
        obj = container.upload_object(tmppath, 'test')

        stream = self.driver.download_object_as_stream(obj=obj,
                                                       chunk_size=1024)

        self.assertTrue(hasattr(stream, '__iter__'))

        data = b''.join(stream)
        self.assertTrue(len(data), 4096)

        obj.delete()
        container.delete()
        self.remove_tmp_file(tmppath)

    def test_download_object_range_success(self):
        content = b'0123456789123456789'
        tmppath = self.make_tmp_file(content=content)
        container = self.driver.create_container('test6')
        obj = container.upload_object(tmppath, 'test')

        destination_path = tmppath + '.temp'

        # 1. Only start_bytes provided
        result = self.driver.download_object_range(obj=obj,
                                             destination_path=destination_path,
                                             start_bytes=4,
                                             overwrite_existing=True,
                                             delete_on_failure=True)
        self.assertTrue(result)

        with open(destination_path, 'rb') as fp:
            written_content = fp.read()

        self.assertEqual(written_content, b'456789123456789')
        self.assertEqual(written_content, content[4:])

        # 2. start_bytes and end_bytes is provided
        result = self.driver.download_object_range(obj=obj,
                                             destination_path=destination_path,
                                             start_bytes=4,
                                             end_bytes=6,
                                             overwrite_existing=True,
                                             delete_on_failure=True)
        self.assertTrue(result)

        with open(destination_path, 'rb') as fp:
            written_content = fp.read()

        self.assertEqual(written_content, b'45')
        self.assertEqual(written_content, content[4:6])

        result = self.driver.download_object_range(obj=obj,
                                             destination_path=destination_path,
                                             start_bytes=0,
                                             end_bytes=1,
                                             overwrite_existing=True,
                                             delete_on_failure=True)
        self.assertTrue(result)

        with open(destination_path, 'rb') as fp:
            written_content = fp.read()

        self.assertEqual(written_content, b'0')
        self.assertEqual(written_content, content[0:1])

        result = self.driver.download_object_range(obj=obj,
                                             destination_path=destination_path,
                                             start_bytes=0,
                                             end_bytes=2,
                                             overwrite_existing=True,
                                             delete_on_failure=True)
        self.assertTrue(result)

        with open(destination_path, 'rb') as fp:
            written_content = fp.read()

        self.assertEqual(written_content, b'01')
        self.assertEqual(written_content, content[0:2])

        result = self.driver.download_object_range(obj=obj,
                                             destination_path=destination_path,
                                             start_bytes=0,
                                             end_bytes=len(content),
                                             overwrite_existing=True,
                                             delete_on_failure=True)
        self.assertTrue(result)

        with open(destination_path, 'rb') as fp:
            written_content = fp.read()

        self.assertEqual(written_content, b'0123456789123456789')
        self.assertEqual(written_content, content[0:len(content)])

        obj.delete()
        container.delete()
        self.remove_tmp_file(tmppath)
        os.unlink(destination_path)

    def test_download_object_range_as_stream_success(self):
        content = b'0123456789123456789'
        tmppath = self.make_tmp_file(content=content)
        container = self.driver.create_container('test6')
        obj = container.upload_object(tmppath, 'test')

        # 1. Only start_bytes provided
        stream = self.driver.download_object_range_as_stream(obj=obj,
                                                             start_bytes=4,
                                                             chunk_size=1024)
        written_content = b''.join(stream)

        self.assertEqual(written_content, b'456789123456789')
        self.assertEqual(written_content, content[4:])

        # 2. start_bytes and end_bytes is provided
        stream = self.driver.download_object_range_as_stream(obj=obj,
                                                             start_bytes=4,
                                                             end_bytes=7,
                                                             chunk_size=1024)
        written_content = b''.join(stream)

        self.assertEqual(written_content, b'456')
        self.assertEqual(written_content, content[4:7])

        stream = self.driver.download_object_range_as_stream(obj=obj,
                                                             start_bytes=0,
                                                             end_bytes=1,
                                                             chunk_size=1024)
        written_content = b''.join(stream)

        self.assertEqual(written_content, b'0')
        self.assertEqual(written_content, content[0:1])

        stream = self.driver.download_object_range_as_stream(obj=obj,
                                                             start_bytes=1,
                                                             end_bytes=3,
                                                             chunk_size=1024)
        written_content = b''.join(stream)

        self.assertEqual(written_content, b'12')
        self.assertEqual(written_content, content[1:3])

        stream = self.driver.download_object_range_as_stream(obj=obj,
                                                             start_bytes=0,
                                                             end_bytes=len(content),
                                                             chunk_size=1024)
        written_content = b''.join(stream)

        self.assertEqual(written_content, b'0123456789123456789')
        self.assertEqual(written_content, content[0:len(content)])

        obj.delete()
        container.delete()
        self.remove_tmp_file(tmppath)

    def test_download_object_range_invalid_values(self):
        obj = Object('a', 500, '', {}, {}, None, None)
        tmppath = self.make_tmp_file(content='')

        expected_msg = 'start_bytes must be greater than 0'
        self.assertRaisesRegex(ValueError, expected_msg,
            self.driver.download_object_range, obj=obj,
            destination_path=tmppath,
            start_bytes=-1)

        expected_msg = 'start_bytes must be smaller than end_bytes'
        self.assertRaisesRegex(ValueError, expected_msg,
            self.driver.download_object_range, obj=obj,
            destination_path=tmppath,
            start_bytes=5,
            end_bytes=4)

        expected_msg = 'start_bytes and end_bytes can\'t be the same'
        self.assertRaisesRegex(ValueError, expected_msg,
            self.driver.download_object_range, obj=obj,
            destination_path=tmppath,
            start_bytes=5,
            end_bytes=5)

    def test_download_object_range_as_stream_invalid_values(self):
        content = b'0123456789123456789'
        tmppath = self.make_tmp_file(content=content)
        container = self.driver.create_container('test6')
        obj = container.upload_object(tmppath, 'test')

        expected_msg = 'start_bytes must be greater than 0'
        stream = self.driver.download_object_range_as_stream(
            obj=obj,
            start_bytes=-1,
            end_bytes=None,
            chunk_size=1024)
        self.assertRaisesRegex(ValueError, expected_msg, exhaust_iterator,
                               stream)

        expected_msg = 'start_bytes must be smaller than end_bytes'
        stream = self.driver.download_object_range_as_stream(
            obj=obj,
            start_bytes=5,
            end_bytes=4,
            chunk_size=1024)
        self.assertRaisesRegex(ValueError, expected_msg, exhaust_iterator,
                               stream)

        expected_msg = 'end_bytes is larger than file size'
        stream = self.driver.download_object_range_as_stream(
            obj=obj,
            start_bytes=5,
            end_bytes=len(content) + 1,
            chunk_size=1024)

        expected_msg = 'start_bytes and end_bytes can\'t be the same'
        stream = self.driver.download_object_range_as_stream(
            obj=obj,
            start_bytes=5,
            end_bytes=5,
            chunk_size=1024)

        obj.delete()
        container.delete()
        self.remove_tmp_file(tmppath)


if not LocalStorageDriver:
    class LocalTests(unittest.TestCase):  # NOQA
        pass


if __name__ == '__main__':
    sys.exit(unittest.main())
