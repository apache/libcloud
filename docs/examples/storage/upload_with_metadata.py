from libcloud.storage.types import Provider
from libcloud.storage.providers import get_driver

FILE_PATH = "/home/user/myfile.tar.gz"

cls = get_driver(Provider.S3)
driver = cls("api key", "api secret key")

container = driver.get_container(container_name="my-backups-12345")

extra = {"meta_data": {"owner": "myuser", "created": "2014-02-2"}}

with open(FILE_PATH, "rb") as iterator:
    obj = driver.upload_object_via_stream(
        iterator=iterator, container=container, object_name="backup.tar.gz", extra=extra
    )
