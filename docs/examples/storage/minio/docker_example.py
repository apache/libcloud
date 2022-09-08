from libcloud.storage.types import Provider, ContainerAlreadyExistsError
from libcloud.storage.providers import get_driver

FILE_PATH = "/home/user/myfile.tar.gz"

cls = get_driver(Provider.MINIO)
driver = cls("api key", "api secret key", secure=False, host="127.0.0.1", port=9000)

try:
    driver.create_container(container_name="my-backups-12345")
except ContainerAlreadyExistsError:
    pass

container = driver.get_container(container_name="my-backups-12345")

# This method blocks until all the parts have been uploaded.
with open(FILE_PATH, "rb") as iterator:
    obj = driver.upload_object_via_stream(
        iterator=iterator, container=container, object_name="backup.tar.gz"
    )
