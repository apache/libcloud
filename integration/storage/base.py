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

import io
import os
import re
import sys
import gzip
import time
import atexit
import random
import socket
import string
import tempfile
import unittest

import requests

import libcloud.http
from libcloud.storage import types, providers
from libcloud.common.types import LibcloudError

try:
    import docker
except ImportError:
    docker = None


libcloud.http.DEFAULT_REQUEST_TIMEOUT = 10


MB = 1024 * 1024


def get_content_iter_with_chunk_size(content, chunk_size=1024):
    """
    Return iterator for the provided content which will return chunks of the specified size.

    For performance reasons, larger chunks should be used with very large content to speed up the
    tests (since in some cases each iteration may result in an TCP send).
    """
    # Ensure we still use multiple chunks and iterations
    assert (len(content) / chunk_size) >= 10
    content = iter([content[i : i + chunk_size] for i in range(0, len(content), chunk_size)])
    return content


class Integration:
    class TestBase(unittest.TestCase):
        provider = None
        account = None
        secret = None

        container_name_prefix = "lcsit"
        container_name_max_length = 63

        def setUp(self):
            for required in "provider", "account", "secret":
                value = getattr(self, required, None)
                if value is None:
                    raise unittest.SkipTest("config {} not set".format(required))

            kwargs = {"key": self.account, "secret": self.secret}

            for optional in "host", "port", "secure":
                value = getattr(self, optional, None)
                if value is not None:
                    kwargs[optional] = value

            driver_class = providers.get_driver(self.provider)
            self.driver = driver_class(**kwargs)

        def tearDown(self):
            for container in self.driver.list_containers():
                if not container.name.startswith(self.container_name_prefix):
                    continue

                for obj in container.list_objects():
                    try:
                        obj.delete()
                    except LibcloudError as ex:
                        print(
                            "Unable to delete object {} in container {}: {}."
                            "Delete it manually.".format(obj.name, container.name, ex),
                            file=sys.stderr,
                        )

                try:
                    container.delete()
                except LibcloudError as ex:
                    print(
                        "Unable to delete container {}: {}."
                        "Delete it manually.".format(container.name, ex),
                        file=sys.stderr,
                    )

        def test_containers(self):
            # make a new container
            container_name = self._random_container_name()
            container = self.driver.create_container(container_name)
            self.assertEqual(container.name, container_name)
            container = self.driver.get_container(container_name)
            self.assertEqual(container.name, container_name)

            self.assert_existing_container_cannot_be_recreated(container)

            # check that the new container can be listed
            containers = self.driver.list_containers()
            self.assertIn(container_name, [c.name for c in containers])

            # delete the container
            self.driver.delete_container(container)

            # check that a deleted container can't be looked up
            with self.assertRaises(types.ContainerDoesNotExistError):
                self.driver.get_container(container_name)

            # check that the container is deleted
            containers = self.driver.list_containers()
            self.assertNotIn(container_name, [c.name for c in containers])

        def _test_objects(self, do_upload, do_download, size=1 * MB):
            content = os.urandom(size)
            blob_name = "testblob"
            container = self.driver.create_container(self._random_container_name())

            # upload a file
            obj = do_upload(container, blob_name, content)
            self.assertEqual(obj.name, blob_name)
            obj = self.driver.get_object(container.name, blob_name)

            # check that the file can be listed
            blobs = self.driver.list_container_objects(container)
            self.assertEqual([blob.name for blob in blobs], [blob_name])

            # upload another file and check it's excluded in prefix listing
            do_upload(container, blob_name[::-1], content[::-1])
            blobs = self.driver.list_container_objects(container, prefix=blob_name[0:3])
            self.assertEqual([blob.name for blob in blobs], [blob_name])

            # check that the file can be read back
            downloaded_content = do_download(obj)
            self.assertEqual(len(downloaded_content), size)
            self.assertEqual(downloaded_content, content)

            # delete the file
            self.driver.delete_object(obj)

            # check that a missing file can't be deleted or looked up
            self.assert_file_is_missing(container, obj)

            # check that the file is deleted
            blobs = self.driver.list_container_objects(container)
            self.assertEqual([blob.name for blob in blobs], [blob_name[::-1]])

        def assert_existing_container_cannot_be_recreated(self, container):
            with self.assertRaises(types.ContainerAlreadyExistsError):
                self.driver.create_container(container.name)

        def assert_file_is_missing(self, container, obj):
            with self.assertRaises(types.ObjectDoesNotExistError):
                self.driver.delete_object(obj)
            with self.assertRaises(types.ObjectDoesNotExistError):
                self.driver.get_object(container.name, obj.name)

        def test_objects(self, size=1 * MB):
            def do_upload(container, blob_name, content):
                infile = self._create_tempfile(content=content)
                return self.driver.upload_object(infile, container, blob_name)

            def do_download(obj):
                outfile = self._create_tempfile()
                self.driver.download_object(obj, outfile, overwrite_existing=True)
                with open(outfile, "rb") as fobj:
                    return fobj.read()

            self._test_objects(do_upload, do_download, size)

        def test_objects_range_downloads(self):
            blob_name = "testblob-range"
            content = b"0123456789"
            container = self.driver.create_container(self._random_container_name())

            obj = self.driver.upload_object(
                self._create_tempfile(content=content), container, blob_name
            )
            self.assertEqual(obj.name, blob_name)
            self.assertEqual(obj.size, len(content))

            obj = self.driver.get_object(container.name, blob_name)
            self.assertEqual(obj.name, blob_name)
            self.assertEqual(obj.size, len(content))

            values = [
                {"start_bytes": 0, "end_bytes": 1, "expected_content": b"0"},
                {"start_bytes": 1, "end_bytes": 5, "expected_content": b"1234"},
                {"start_bytes": 5, "end_bytes": None, "expected_content": b"56789"},
                {"start_bytes": 5, "end_bytes": len(content), "expected_content": b"56789"},
                {"start_bytes": 0, "end_bytes": None, "expected_content": b"0123456789"},
                {"start_bytes": 0, "end_bytes": len(content), "expected_content": b"0123456789"},
            ]

            for value in values:
                # 1. download_object_range
                start_bytes = value["start_bytes"]
                end_bytes = value["end_bytes"]
                outfile = self._create_tempfile()

                result = self.driver.download_object_range(
                    obj,
                    outfile,
                    start_bytes=start_bytes,
                    end_bytes=end_bytes,
                    overwrite_existing=True,
                )
                self.assertTrue(result)

                with open(outfile, "rb") as fobj:
                    downloaded_content = fobj.read()

                if end_bytes is not None:
                    expected_content = content[start_bytes:end_bytes]
                else:
                    expected_content = content[start_bytes:]

                msg = 'Expected "{}", got "{}" for values: {}'.format(
                    expected_content,
                    downloaded_content,
                    str(value),
                )
                self.assertEqual(downloaded_content, expected_content, msg)
                self.assertEqual(downloaded_content, value["expected_content"], msg)

                # 2. download_object_range_as_stream
                downloaded_content = read_stream(
                    self.driver.download_object_range_as_stream(
                        obj, start_bytes=start_bytes, end_bytes=end_bytes
                    )
                )
                self.assertEqual(downloaded_content, expected_content)

        @unittest.skipUnless(os.getenv("LARGE_FILE_SIZE_MB"), "config not set")
        def test_objects_large(self):
            size = int(float(os.environ["LARGE_FILE_SIZE_MB"]) * MB)
            self.test_objects(size)

        def test_objects_stream_io(self):
            def do_upload(container, blob_name, content):
                content = io.BytesIO(content)
                return self.driver.upload_object_via_stream(content, container, blob_name)

            def do_download(obj):
                return read_stream(self.driver.download_object_as_stream(obj))

            self._test_objects(do_upload, do_download)

        def test_objects_stream_iterable(self):
            def do_upload(container, blob_name, content):
                # NOTE: We originally used a chunk size of 1 which resulted in many requests and as
                # such, very slow tests. To speed things up, we use a longer chunk size.
                assert (len(content) / 1024) >= 500
                content = get_content_iter_with_chunk_size(content, 1024)
                return self.driver.upload_object_via_stream(content, container, blob_name)

            def do_download(obj):
                return read_stream(self.driver.download_object_as_stream(obj))

            self._test_objects(do_upload, do_download)

        def test_upload_via_stream_with_content_encoding(self):
            object_name = "content_encoding.gz"
            content = gzip.compress(os.urandom(MB // 100))
            container = self.driver.create_container(self._random_container_name())
            self.driver.upload_object_via_stream(
                get_content_iter_with_chunk_size(content, 1000),
                container,
                object_name,
                headers={"Content-Encoding": "gzip"},
            )

            obj = self.driver.get_object(container.name, object_name)

            self.assertEqual(obj.extra.get("content_encoding"), "gzip")

        def test_cdn_url(self):
            content = os.urandom(MB // 100)
            container = self.driver.create_container(self._random_container_name())
            content_iter = get_content_iter_with_chunk_size(content, 1000)
            obj = self.driver.upload_object_via_stream(content_iter, container, "cdn")

            response = requests.get(self.driver.get_object_cdn_url(obj))
            response.raise_for_status()

            self.assertEqual(response.content, content)

        def _create_tempfile(self, prefix="", content=b""):
            fobj, path = tempfile.mkstemp(prefix=prefix, text=False)

            try:
                os.write(fobj, content)
            finally:
                os.close(fobj)

            self.addCleanup(os.remove, path)
            return path

        @classmethod
        def _random_container_name(cls):
            suffix = random_string(cls.container_name_max_length)
            name = cls.container_name_prefix + suffix
            name = re.sub("[^a-z0-9-]", "-", name)
            name = re.sub("-+", "-", name)
            name = name[: cls.container_name_max_length]
            name = name.lower()
            return name

    class ContainerTestBase(TestBase):
        image = None
        version = "latest"
        environment = {}
        command = None
        ready_message = None

        host = "localhost"
        port = None
        secure = False

        client = None
        container = None
        verbose = False

        container_ready_timeout = 20

        @classmethod
        def setUpClass(cls):
            if docker is None:
                raise unittest.SkipTest("missing docker library")

            try:
                cls.client = docker.from_env()
            except docker.errors.DockerException:
                raise unittest.SkipTest("unable to create docker client")

            for required in "image", "port":
                value = getattr(cls, required, None)
                if value is None:
                    raise unittest.SkipTest("config {} not set".format(required))

            cls.container = cls.client.containers.run(
                "{}:{}".format(cls.image, cls.version),
                command=cls.command,
                detach=True,
                auto_remove=True,
                ports={cls.port: cls.port},
                environment=cls.environment,
            )

            # We register atexit handler to ensure container is always killed, even if for some
            # reason tearDownClass is sometimes not called (happened locally a couple of times)
            atexit.register(cls._kill_container)

            wait_for(cls.port, cls.host)

            container_ready = cls.ready_message is None

            start_ts = int(time.time())
            timeout_ts = start_ts + cls.container_ready_timeout

            while not container_ready:
                time.sleep(1)

                container_ready = any(
                    cls.ready_message in line for line in cls.container.logs().splitlines()
                )

                now_ts = int(time.time())

                if now_ts >= timeout_ts:
                    raise ValueError(
                        "Container %s failed to start and become ready in %s seconds "
                        '(did not find "%s" message in container logs).\n\n'
                        "Container Logs:\n%s"
                        % (
                            cls.container.short_id,
                            cls.container_ready_timeout,
                            cls.ready_message.decode("utf-8"),
                            cls.container.logs().decode("utf-8"),
                        )
                    )

        @classmethod
        def tearDownClass(cls):
            cls._kill_container()
            atexit.unregister(cls._kill_container)

        @classmethod
        def _kill_container(cls):
            if cls.verbose:
                print("Killing / stopping container with id %s..." % (cls.container.short_id))

            if cls.verbose:
                for line in cls.container.logs().splitlines():
                    print(line)

            try:
                cls.container.kill()
            except docker.errors.DockerException as ex:
                print(
                    "Unable to terminate docker container {}: {}."
                    "Stop it manually.".format(cls.container.short_id, ex),
                    file=sys.stderr,
                )


def wait_for(port, host="localhost", timeout=10):
    start_time = time.perf_counter()

    while True:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                break
        except OSError as ex:
            if time.perf_counter() - start_time >= timeout:
                raise TimeoutError(
                    "Waited too long for the port {} on host {} to start accepting "
                    "connections.".format(port, host)
                ) from ex

            time.sleep(1)


def random_string(length, alphabet=string.ascii_lowercase + string.digits):
    return "".join(random.choice(alphabet) for _ in range(length))


def read_stream(stream):
    buffer = io.BytesIO()
    buffer.writelines(stream)
    buffer.seek(0)
    return buffer.read()
