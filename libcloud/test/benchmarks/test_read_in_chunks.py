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

from typing import Tuple, Callable

import pytest

from libcloud.utils.py3 import b, next
from libcloud.utils.files import CHUNK_SIZE, read_in_chunks


def _old_read_in_chunks(iterator, chunk_size=None, fill_size=False, yield_empty=False):
    """
    Old implementation of read_in_chunks without performance optimizations from #1847.

    It's only here so we can directly measure compare performance of old and the new version.
    """
    chunk_size = chunk_size or CHUNK_SIZE

    try:
        get_data = iterator.read
        args = (chunk_size,)
    except AttributeError:
        get_data = next
        args = (iterator,)

    data = b("")
    empty = False

    while not empty or len(data) > 0:
        if not empty:
            try:
                chunk = b(get_data(*args))
                if len(chunk) > 0:
                    data += chunk
                else:
                    empty = True
            except StopIteration:
                empty = True

        if len(data) == 0:
            if empty and yield_empty:
                yield b("")

            return

        if fill_size:
            if empty or len(data) >= chunk_size:
                yield data[:chunk_size]
                data = data[chunk_size:]
        else:
            yield data
            data = b("")


# fmt: off
@pytest.mark.parametrize(
    "data_chunk_size_tuple",
    [
        (b"c" * (40 * 1024 * 1024), 1 * 1024 * 1024),
        (b"c" * (40 * 1024 * 1024), 5 * 1024 * 1024),
        (b"c" * (80 * 1024 * 1024), 1 * 1024 * 1024),
    ],
    ids=[
        "40mb_data_1mb_chunk_size",
        "40mb_data_5mb_chunk_size",
        "80mb_data_1mb_chunk_size",
    ],
)
@pytest.mark.parametrize(
    "read_in_chunks_func",
    [
        _old_read_in_chunks,
        read_in_chunks,
    ],
    ids=[
        "old",
        "new",
    ],
)
# fmt: on
def test_scenario_1(
    benchmark, data_chunk_size_tuple: Tuple[bytes, int], read_in_chunks_func: Callable
):
    # similar to calling _upload_multipart_chunks with one large array of bytes
    data, chunk_size = data_chunk_size_tuple

    def run_benchmark():
        for _ in read_in_chunks_func(iter([data]), chunk_size=chunk_size, fill_size=True):
            pass

    benchmark(run_benchmark)


# fmt: off
# NOTE: Because the old implementation is very slow when there is a chunk size mismatch, we need to
# use smaller total objects size to prevent this benchmark from running for a very long time.
@pytest.mark.parametrize(
    "data_chunk_size_tuple",
    [
        (b"c" * (10 * 1024 * 1024), 8 * 1024),
        (b"c" * (20 * 1024 * 1024), 1 * 1024 * 1024),
        (b"c" * (30 * 1024 * 1024), 1 * 1024 * 1024),
    ],
    ids=[
        "10mb_data_8k_chunk_size",
        "20mb_data_1mb_chunk_size",
        "30mb_data_1mb_chunk_size",
    ],
)
@pytest.mark.parametrize(
    "read_in_chunks_func",
    [
        _old_read_in_chunks,
        read_in_chunks,
    ],
    ids=[
        "old",
        "new",
    ],
)
# fmt: on
def test_scenario_2(
    benchmark, data_chunk_size_tuple: Tuple[bytes, int], read_in_chunks_func: Callable
):
    # similar to calling _upload_multipart_chunks with one large array of bytes
    data, chunk_size = data_chunk_size_tuple
    response_chunk = 5 * 1024 * 1024

    # NOTE: It would be nice if we could also assert that data has been correctly add, but this
    # would add additional overhead (since we would also measure accumulating this data) so we have
    # those checks done separately in the unit tests.
    def run_benchmark():
        for a in read_in_chunks_func(
            iter([data[i : i + response_chunk] for i in range(0, len(data), response_chunk)]),
            chunk_size=chunk_size,
            fill_size=True,
        ):
            pass

    benchmark(run_benchmark)
