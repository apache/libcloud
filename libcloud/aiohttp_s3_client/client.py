import asyncio
import hashlib
import io
import logging
import os
import typing as t
from collections import deque
from contextlib import suppress
from functools import partial
from http import HTTPStatus
from itertools import chain
from mimetypes import guess_type
from mmap import PAGESIZE
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Any
from urllib.parse import quote

from aiohttp import ClientSession, hdrs
from aiohttp.client import _RequestContextManager as RequestContextManager
from aiohttp.client_exceptions import ClientError
from aiomisc import asyncbackoff, threaded, threaded_iterable
from aws_request_signer import UNSIGNED_PAYLOAD
from multidict import CIMultiDict, CIMultiDictProxy
from yarl import URL

from aiohttp_s3_client.credentials import (
    AbstractCredentials, collect_credentials,
)
from aiohttp_s3_client.xml import (
    AwsObjectMeta, create_complete_upload_request,
    parse_create_multipart_upload_id, parse_list_objects,
)


log = logging.getLogger(__name__)


CHUNK_SIZE = 2 ** 16
DONE = object()
EMPTY_STR_HASH = hashlib.sha256(b"").hexdigest()
PART_SIZE = 5 * 1024 * 1024  # 5MB

HeadersType = t.Union[t.Dict, CIMultiDict, CIMultiDictProxy]


threaded_iterable_constrained = threaded_iterable(max_size=2)


class AwsError(ClientError):
    pass


class AwsUploadError(AwsError):
    pass


class AwsDownloadError(AwsError):
    pass


@threaded
def concat_files(
    target_file: Path, files: t.List[t.IO[bytes]], buffer_size: int,
) -> None:
    with target_file.open("ab") as fp:
        for file in files:
            file.seek(0)
            while True:
                chunk = file.read(buffer_size)
                if not chunk:
                    break
                fp.write(chunk)
            file.close()


@threaded
def write_from_start(
    file: io.BytesIO, chunk: bytes, range_start: int, pos: int,
) -> None:
    file.seek(pos - range_start)
    file.write(chunk)


@threaded
def pwrite_absolute_pos(
    fd: int, chunk: bytes, range_start: int, pos: int,
) -> None:
    os.pwrite(fd, chunk, pos)


@threaded_iterable_constrained
def gen_without_hash(
    stream: t.Iterable[bytes],
) -> t.Generator[t.Tuple[None, bytes], None, None]:
    for data in stream:
        yield (None, data)


@threaded_iterable_constrained
def gen_with_hash(
    stream: t.Iterable[bytes],
) -> t.Generator[t.Tuple[str, bytes], None, None]:
    for data in stream:
        yield hashlib.sha256(data).hexdigest(), data


def file_sender(
    file_name: t.Union[str, Path], chunk_size: int = CHUNK_SIZE,
) -> t.Iterable[bytes]:
    with open(file_name, "rb") as fp:
        while True:
            data = fp.read(chunk_size)
            if not data:
                break
            yield data


async_file_sender = threaded_iterable_constrained(file_sender)


DataType = t.Union[bytes, str, t.AsyncIterable[bytes]]
ParamsType = t.Optional[t.Mapping[str, str]]


class S3Client:
    def __init__(
        self, session: ClientSession, url: t.Union[URL, str],
        secret_access_key: t.Optional[str] = None,
        access_key_id: t.Optional[str] = None,
        session_token: t.Optional[str] = None,
        region: str = "",
        credentials: t.Optional[AbstractCredentials] = None,
    ):
        url = URL(url)
        if credentials is None:
            credentials = collect_credentials(
                url=url,
                access_key_id=access_key_id,
                region=region,
                secret_access_key=secret_access_key,
                session_token=session_token,
            )

        if not credentials:
            raise ValueError(
                f"Credentials {credentials!r} is incomplete",
            )

        self._url = URL(url).with_user(None).with_password(None)
        self._session = session
        self._credentials = credentials

    @property
    def url(self) -> URL:
        return self._url

    def request(
        self, method: str, path: str,
        headers: t.Optional[HeadersType] = None,
        params: ParamsType = None,
        data: t.Optional[DataType] = None,
        data_length: t.Optional[int] = None,
        content_sha256: t.Optional[str] = None,
        **kwargs,
    ) -> RequestContextManager:
        if isinstance(data, bytes):
            data_length = len(data)
        elif isinstance(data, str):
            data = data.encode()
            data_length = len(data)

        headers = self._prepare_headers(headers)
        if data_length:
            headers[hdrs.CONTENT_LENGTH] = str(data_length)
        elif data is not None:
            kwargs["chunked"] = True

        if data is not None and content_sha256 is None:
            content_sha256 = UNSIGNED_PAYLOAD

        url = (self._url / path.lstrip("/"))
        url = url.with_path(quote(url.path), encoded=True).with_query(params)

        headers = self._make_headers(headers)
        headers.extend(
            self._credentials.signer.sign_with_headers(
                method, str(url), headers=headers, content_hash=content_sha256,
            ),
        )
        return self._session.request(
            method, url, headers=headers, data=data, **kwargs,
        )

    def get(self, object_name: str, **kwargs) -> RequestContextManager:
        return self.request("GET", object_name, **kwargs)

    def head(
        self, object_name: str,
        content_sha256=EMPTY_STR_HASH,
        **kwargs,
    ) -> RequestContextManager:
        return self.request(
            "HEAD", object_name, content_sha256=content_sha256, **kwargs,
        )

    def delete(
        self, object_name: str,
        content_sha256=EMPTY_STR_HASH,
        **kwargs,
    ) -> RequestContextManager:
        return self.request(
            "DELETE", object_name, content_sha256=content_sha256, **kwargs,
        )

    @staticmethod
    def _make_headers(headers: t.Optional[HeadersType]) -> CIMultiDict:
        headers = CIMultiDict(headers or {})
        return headers

    def _prepare_headers(
        self, headers: t.Optional[HeadersType],
        file_path: str = "",
    ) -> CIMultiDict:
        headers = self._make_headers(headers)

        if hdrs.CONTENT_TYPE not in headers:
            content_type = guess_type(file_path)[0]
            if content_type is None:
                content_type = "application/octet-stream"

            headers[hdrs.CONTENT_TYPE] = content_type

        return headers

    def put(
        self, object_name: str,
        data: t.Union[bytes, str, t.AsyncIterable[bytes]], **kwargs,
    ) -> RequestContextManager:
        return self.request("PUT", object_name, data=data, **kwargs)

    def post(
        self, object_name: str,
        data: t.Union[None, bytes, str, t.AsyncIterable[bytes]] = None,
        **kwargs,
    ) -> RequestContextManager:
        return self.request("POST", object_name, data=data, **kwargs)

    def put_file(
        self, object_name: t.Union[str, Path],
        file_path: t.Union[str, Path],
        *, headers: t.Optional[HeadersType] = None,
        chunk_size: int = CHUNK_SIZE, content_sha256: t.Optional[str] = None,
    ) -> RequestContextManager:

        headers = self._prepare_headers(headers, str(file_path))
        return self.put(
            str(object_name),
            headers=headers,
            data=async_file_sender(
                file_path,
                chunk_size=chunk_size,
            ),
            data_length=os.stat(file_path).st_size,
            content_sha256=content_sha256,
        )

    @asyncbackoff(
        None, None, 0,
        max_tries=3, exceptions=(ClientError,),
    )
    async def _create_multipart_upload(
        self,
        object_name: str,
        headers: t.Optional[HeadersType] = None,
    ) -> str:
        async with self.post(
            object_name,
            headers=headers,
            params={"uploads": 1},
            content_sha256=EMPTY_STR_HASH,
        ) as resp:
            payload = await resp.read()
            if resp.status != HTTPStatus.OK:
                raise AwsUploadError(
                    f"Wrong status code {resp.status} from s3 with message "
                    f"{payload.decode()}.",
                )
            return parse_create_multipart_upload_id(payload)

    @asyncbackoff(
        None, None, 0,
        max_tries=3, exceptions=(AwsUploadError, ClientError),
    )
    async def _complete_multipart_upload(
        self,
        upload_id: str,
        object_name: str,
        parts: t.List[t.Tuple[int, str]],
    ) -> None:
        complete_upload_request = create_complete_upload_request(parts)
        async with self.post(
            object_name,
            headers={"Content-Type": "text/xml"},
            params={"uploadId": upload_id},
            data=complete_upload_request,
            content_sha256=hashlib.sha256(complete_upload_request).hexdigest(),
        ) as resp:
            if resp.status != HTTPStatus.OK:
                payload = await resp.text()
                raise AwsUploadError(
                    f"Wrong status code {resp.status} from s3 with message "
                    f"{payload}.",
                )

    async def _put_part(
        self,
        upload_id: str,
        object_name: str,
        part_no: int,
        data: bytes,
        content_sha256: str,
        **kwargs,
    ) -> str:
        async with self.put(
            object_name,
            params={"partNumber": part_no, "uploadId": upload_id},
            data=data,
            content_sha256=content_sha256,
            **kwargs,
        ) as resp:
            payload = await resp.text()
            if resp.status != HTTPStatus.OK:
                raise AwsUploadError(
                    f"Wrong status code {resp.status} from s3 with message "
                    f"{payload}.",
                )
            return resp.headers["Etag"].strip('"')

    async def _part_uploader(
        self,
        upload_id: str,
        object_name: str,
        parts_queue: asyncio.Queue,
        results_queue: deque,
        part_upload_tries: int,
        **kwargs,
    ) -> None:
        backoff = asyncbackoff(
            None, None,
            max_tries=part_upload_tries,
            exceptions=(ClientError,),
        )
        while True:
            msg = await parts_queue.get()
            if msg is DONE:
                break
            part_no, part_hash, part = msg
            print('Uploading a part in parallel...')
            etag = await backoff(self._put_part)(
                upload_id=upload_id,
                object_name=object_name,
                part_no=part_no,
                data=part,
                content_sha256=part_hash,
                **kwargs,
            )
            log.debug(
                "Etag for part %d of %s is %s", part_no, upload_id, etag,
            )
            results_queue.append((part_no, etag, len(part)))

    async def _parts_generator(
        self, gen, workers_count: int, parts_queue: asyncio.Queue,
    ) -> int:
        part_no = 1
        async with gen:
            async for part_hash, part in gen:
                log.debug(
                    "Reading part %d (%d bytes)", part_no, len(part),
                )
                await parts_queue.put((part_no, part_hash, part))
                part_no += 1

        for _ in range(workers_count):
            await parts_queue.put(DONE)

        return part_no

    async def put_multipart(
        self,
        object_name: t.Union[str, Path],
        data: t.Iterable[bytes],
        *,
        headers: t.Optional[HeadersType] = None,
        workers_count: int = 1,
        max_size: t.Optional[int] = None,
        part_upload_tries: int = 3,
        calculate_content_sha256: bool = True,
        **kwargs,
    ) -> None:
        """
        Send data from iterable with multipart upload

        object_name: key in s3
        data: any iterable that returns chunks of bytes
        headers: additional headers, such as Content-Type
        workers_count: count of coroutines for asyncronous parts uploading
        max_size: maximum size of a queue with data to send (should be
            at least `workers_count`)
        part_upload_tries: how many times trying to put part to s3 before fail
        calculate_content_sha256: whether to calculate sha256 hash of a part
            for integrity purposes
        """
        if workers_count < 1:
            raise ValueError(
                f"Workers count should be > 0. Got {workers_count}",
            )
        max_size = max_size or workers_count

        upload_id = await self._create_multipart_upload(
            str(object_name),
            headers=headers,
        )
        log.debug("Got upload id %s for %s", upload_id, object_name)

        parts_queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        results_queue: deque = deque()
        workers = [
            asyncio.create_task(
                self._part_uploader(
                    upload_id,
                    str(object_name),
                    parts_queue,
                    results_queue,
                    part_upload_tries,
                    **kwargs,
                ),
            )
            for _ in range(workers_count)
        ]

        if calculate_content_sha256:
            gen = gen_with_hash(data)
        else:
            gen = gen_without_hash(data)

        parts_generator = asyncio.create_task(
            self._parts_generator(gen, workers_count, parts_queue),
        )
        try:
            part_no, *_ = await asyncio.gather(
                parts_generator,
                *workers,
            )
        except Exception:
            for task in chain([parts_generator], workers):
                if not task.done():
                    task.cancel()
            raise

        log.debug(
            "All parts (#%d) of %s are uploaded to %s",
            part_no - 1, upload_id, object_name,
        )

        # Parts should be in ascending order
        parts = sorted(results_queue, key=lambda x: x[0])
        await self._complete_multipart_upload(
            upload_id, object_name, parts,
        )

    async def _download_range(
        self,
        object_name: str,
        writer: t.Callable[[bytes, int, int], t.Coroutine],
        *,
        etag: str,
        pos: int,
        range_start: int,
        req_range_start: int,
        req_range_end: int,
        buffer_size: int,
        headers: t.Optional[HeadersType] = None,
        **kwargs,
    ) -> None:
        """
        Downloading range [req_range_start:req_range_end] to `file`
        """
        log.debug(
            "Downloading %s from %d to %d",
            object_name,
            req_range_start,
            req_range_end,
        )
        if not headers:
            headers = {}
        headers = headers.copy()
        headers["Range"] = f"bytes={req_range_start}-{req_range_end}"
        headers["If-Match"] = etag

        pos = req_range_start
        async with self.get(object_name, headers=headers, **kwargs) as resp:
            if resp.status not in (HTTPStatus.PARTIAL_CONTENT, HTTPStatus.OK):
                raise AwsDownloadError(
                    f"Got wrong status code {resp.status} on range download "
                    f"of {object_name}",
                )
            while True:
                chunk = await resp.content.read(buffer_size)
                if not chunk:
                    break
                await writer(chunk, range_start, pos)
                pos += len(chunk)

    async def _download_worker(
        self,
        object_name: str,
        writer: t.Callable[[bytes, int, int], t.Coroutine],
        *,
        etag: str,
        range_step: int,
        range_start: int,
        range_end: int,
        buffer_size: int,
        range_get_tries: int = 3,
        headers: t.Optional[HeadersType] = None,
        **kwargs,
    ) -> None:
        """
        Downloads data in range `[range_start, range_end)`
        with step `range_step` to file `file_path`.
        Uses `etag` to make sure that file wasn't changed in the process.
        """
        log.debug(
            "Starting download worker for range [%d:%d]",
            range_start,
            range_end,
        )
        backoff = asyncbackoff(
            None, None,
            max_tries=range_get_tries,
            exceptions=(ClientError,),
        )
        req_range_end = range_start
        for req_range_start in range(range_start, range_end, range_step):
            req_range_end += range_step
            if req_range_end > range_end:
                req_range_end = range_end
            await backoff(self._download_range)(
                object_name,
                writer,
                etag=etag,
                pos=(req_range_start - range_start),
                range_start=range_start,
                req_range_start=req_range_start,
                req_range_end=req_range_end - 1,
                buffer_size=buffer_size,
                headers=headers,
                **kwargs,
            )

    async def get_file_parallel(
        self,
        object_name: t.Union[str, Path],
        file_path: t.Union[str, Path],
        *,
        headers: t.Optional[HeadersType] = None,
        range_step: int = PART_SIZE,
        workers_count: int = 1,
        range_get_tries: int = 3,
        buffer_size: int = PAGESIZE * 32,
        **kwargs,
    ) -> None:
        """
        Download object in parallel with requests with Range.
        If file will change while download is in progress -
            error will be raised.

        object_name: s3 key to download
        file_path: target file path
        headers: additional headers
        range_step: how much data will be downloaded in single HTTP request
        workers_count: count of parallel workers
        range_get_tries: count of tries to download each range
        buffer_size: size of a buffer for on the fly data
        """
        file_path = Path(file_path)
        async with self.head(str(object_name), headers=headers) as resp:
            if resp.status != HTTPStatus.OK:
                raise AwsDownloadError(
                    f"Got response for HEAD request for {object_name}"
                    f"of a wrong status {resp.status}",
                )
            etag = resp.headers["Etag"]
            file_size = int(resp.headers["Content-Length"])
            log.debug(
                "Object's %s etag is %s and size is %d",
                object_name,
                etag,
                file_size,
            )

        workers = []
        files: t.List[t.IO[bytes]] = []
        worker_range_size = file_size // workers_count
        range_end = 0
        file: t.IO[bytes]
        try:
            with file_path.open("w+b") as fp:
                for range_start in range(0, file_size, worker_range_size):
                    range_end += worker_range_size
                    if range_end > file_size:
                        range_end = file_size
                    if hasattr(os, "pwrite"):
                        writer = partial(pwrite_absolute_pos, fp.fileno())
                    else:
                        if range_start:
                            file = NamedTemporaryFile(dir=file_path.parent)
                            files.append(file)
                        else:
                            file = fp
                        writer = partial(write_from_start, file)
                    workers.append(
                        self._download_worker(
                            str(object_name),
                            writer,  # type: ignore
                            buffer_size=buffer_size,
                            etag=etag,
                            headers=headers,
                            range_end=range_end,
                            range_get_tries=range_get_tries,
                            range_start=range_start,
                            range_step=range_step,
                            **kwargs,
                        ),
                    )

                await asyncio.gather(*workers)

            if files:
                # First part already in `file_path`
                log.debug("Joining %d parts to %s", len(files) + 1, file_path)
                await concat_files(
                    file_path, files, buffer_size=buffer_size,
                )
        except Exception:
            log.exception(
                "Error on file download. Removing possibly incomplete file %s",
                file_path,
            )
            with suppress(FileNotFoundError):
                os.unlink(file_path)
            raise

    async def list_objects_v2(
        self,
        object_name: t.Union[str, Path] = "/",
        *,
        bucket: t.Optional[str] = None,
        prefix: t.Optional[t.Union[str, Path]] = None,
        delimiter: t.Optional[str] = None,
        max_keys: t.Optional[int] = None,
        start_after: t.Optional[str] = None,
    ) -> t.AsyncIterator[t.List[AwsObjectMeta]]:
        """
        List objects in bucket.

        Returns an iterator over lists of metadata objects, each corresponding
        to an individual response result (typically limited to 1000 keys).

        object_name:
            path to listing endpoint, defaults to '/'; a `bucket` value is
            prepended to this value if provided.
        prefix:
            limits the response to keys that begin with the specified
            prefix
        delimiter: a delimiter is a character you use to group keys
        max_keys: maximum number of keys returned in the response
        start_after: keys to start listing after
        """

        params = {
            "list-type": "2",
        }

        if prefix:
            params["prefix"] = str(prefix)

        if delimiter:
            params["delimiter"] = delimiter

        if max_keys:
            params["max-keys"] = str(max_keys)

        if start_after:
            params["start-after"] = start_after

        if bucket is not None:
            object_name = f"/{bucket}"

        while True:
            async with self.get(str(object_name), params=params) as resp:
                if resp.status != HTTPStatus.OK:
                    raise AwsDownloadError(
                        f"Got response with wrong status for GET request for "
                        f"{object_name} with prefix '{prefix}'",
                    )
                payload = await resp.read()
                metadata, continuation_token = parse_list_objects(payload)
                if not metadata:
                    break
                yield metadata
                if not continuation_token:
                    break
                params["continuation-token"] = continuation_token

    # async def upload_file_multipart(
    #     self,
    #     object_name: t.Union[str, Path],
    #     file_name: str,
    #     upload_id: str,
    #     part_size: int = PART_SIZE,
    #     *,
    #     workers_count: int = 1,
    #     max_size: t.Optional[int] = None,
    #     part_upload_tries: int = 3,
    #     calculate_content_sha256: bool = True,
    #     **kwargs,
    # ) -> t.List[t.Tuple[int, str, int]]:
    #     """
    #     Send contents of a file using a multipart upload.
    #     Does not init, nor commit a multipart upload.
    #     Returns a list of parts uploaded.
    #     The list items are (part_number, etag, uploaded_size).
    #
    #     object_name: key in s3
    #     file_name: path of the file to upload
    #     upload_id: multipart upload id
    #     part_size: size of an individual chunk to upload (recommended: >5Mb)
    #
    #     headers: additional headers, such as Content-Type
    #     workers_count: count of coroutines for asyncronous parts uploading
    #     max_size: maximum size of a queue with data to send (should be
    #         at least `workers_count`)
    #     part_upload_tries: how many times trying to put part to s3 before fail
    #     calculate_content_sha256: whether to calculate sha256 hash of a part
    #         for integrity purposes
    #     """
    #     if workers_count < 1:
    #         raise ValueError(
    #             f"Workers count should be > 0. Got {workers_count}",
    #         )
    #     max_size = max_size or workers_count
    #
    #     parts_queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
    #     results_queue: deque = deque()
    #     workers = [
    #         asyncio.create_task(
    #             self._part_uploader(
    #                 upload_id,
    #                 str(object_name),
    #                 parts_queue,
    #                 results_queue,
    #                 part_upload_tries,
    #                 **kwargs,
    #             ),
    #         )
    #         for _ in range(workers_count)
    #     ]
    #
    #     data = file_sender(file_name, chunk_size=part_size)
    #
    #     if calculate_content_sha256:
    #         gen = gen_with_hash(data)
    #     else:
    #         gen = gen_without_hash(data)
    #
    #     parts_generator = asyncio.create_task(
    #         self._parts_generator(gen, workers_count, parts_queue),
    #     )
    #     try:
    #         part_no, *_ = await asyncio.gather(
    #             parts_generator,
    #             *workers,
    #         )
    #     except Exception:
    #         for task in chain([parts_generator], workers):
    #             if not task.done():
    #                 task.cancel()
    #         raise
    #
    #     log.debug(
    #         "All parts (#%d) of %s are uploaded to %s",
    #         part_no - 1, upload_id, object_name,
    #     )
    #
    #     # Parts should be in ascending order
    #     parts = sorted(results_queue, key=lambda x: x[0])
    #     return parts

    async def put_multipart_libcloud(
        self,
        object_name: t.Union[str, Path],
        data: t.Iterable[bytes],
        upload_id: str,
        *,
        workers_count: int = 1,
        max_size: t.Optional[int] = None,
        part_upload_tries: int = 3,
        calculate_content_sha256: bool = True,
        **kwargs,
    ) -> t.List[t.Tuple[int, str, int]]:
        """
        Send data from iterable with multipart upload.
        Unlike basic `put_multipart` this method returns a list of parts

        object_name: key in s3
        data: any iterable that returns chunks of bytes
        upload_id: multipart upload id
        workers_count: count of coroutines for asyncronous parts uploading
        max_size: maximum size of a queue with data to send (should be
            at least `workers_count`)
        part_upload_tries: how many times trying to put part to s3 before fail
        calculate_content_sha256: whether to calculate sha256 hash of a part
            for integrity purposes
        """
        if workers_count < 1:
            raise ValueError(
                f"Workers count should be > 0. Got {workers_count}",
            )
        max_size = max_size or workers_count

        parts_queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        results_queue: deque = deque()
        workers = [
            asyncio.create_task(
                self._part_uploader(
                    upload_id,
                    str(object_name),
                    parts_queue,
                    results_queue,
                    part_upload_tries,
                    **kwargs,
                ),
            )
            for _ in range(workers_count)
        ]

        if calculate_content_sha256:
            gen = gen_with_hash(data)
        else:
            gen = gen_without_hash(data)

        parts_generator = asyncio.create_task(
            self._parts_generator(gen, workers_count, parts_queue),
        )
        try:
            part_no, *_ = await asyncio.gather(
                parts_generator,
                *workers,
            )
        except Exception:
            for task in chain([parts_generator], workers):
                if not task.done():
                    task.cancel()
            raise

        log.debug(
            "All parts (#%d) of %s are uploaded to %s",
            part_no - 1, upload_id, object_name,
        )

        # Parts should be in ascending order
        parts = sorted(results_queue, key=lambda x: x[0])
        return parts
