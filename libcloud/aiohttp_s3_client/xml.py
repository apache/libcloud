from datetime import datetime, timezone
from sys import intern
from typing import List, NamedTuple, Optional, Tuple
from xml.etree import ElementTree as ET


NS = "http://s3.amazonaws.com/doc/2006-03-01/"


class AwsObjectMeta(NamedTuple):
    etag: str
    key: str
    last_modified: datetime
    size: int
    storage_class: str


def parse_create_multipart_upload_id(payload: bytes) -> str:
    root = ET.fromstring(payload)
    uploadid_el = root.find(f"{{{NS}}}UploadId")
    if uploadid_el is None:
        uploadid_el = root.find("UploadId")
    if uploadid_el is None or uploadid_el.text is None:
        raise ValueError(f"Upload id not found in {payload!r}")
    return uploadid_el.text


def create_complete_upload_request(parts: List[Tuple[str, int, str]]) -> bytes:
    ET.register_namespace("", NS)
    root = ET.Element(f"{{{NS}}}CompleteMultipartUpload")

    for upload_id, part_no, etag in parts:
        part_el = ET.SubElement(root, "Part")
        etag_el = ET.SubElement(part_el, "ETag")
        etag_el.text = etag
        part_number_el = ET.SubElement(part_el, "PartNumber")
        part_number_el.text = str(part_no)

    return (
        b'<?xml version="1.0" encoding="UTF-8"?>' +
        ET.tostring(root, encoding="UTF-8")
    )


def parse_list_objects(payload: bytes) -> Tuple[
    List[AwsObjectMeta], Optional[str],
]:
    root = ET.fromstring(payload)
    result = []
    for el in root.findall(f"{{{NS}}}Contents"):
        etag = key = last_modified = size = storage_class = None
        for child in el:
            tag = child.tag[child.tag.rfind("}") + 1:]
            text = child.text
            if text is None:
                continue
            if tag == "ETag":
                etag = text
            elif tag == "Key":
                key = text
            elif tag == "LastModified":
                assert text[-1] == "Z"
                last_modified = datetime.fromisoformat(text[:-1]).replace(
                    tzinfo=timezone.utc,
                )
            elif tag == "Size":
                size = int(text)
            elif tag == "StorageClass":
                storage_class = intern(text)
        if (
            etag and
            key and
            last_modified and
            size is not None and
            storage_class
        ):
            meta = AwsObjectMeta(etag, key, last_modified, size, storage_class)
            result.append(meta)
    nct_el = root.find(f"{{{NS}}}NextContinuationToken")
    continuation_token = nct_el.text if nct_el is not None else None
    return result, continuation_token
